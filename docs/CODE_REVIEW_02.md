# Code Review 02 — T018 Early Review
<!-- Reviewer: Claude Code | Date: 2026-06-15 -->
<!-- Files reviewed: fatura_ai/api/import_wizard.py, docs/WIZARD_SPEC.md -->
<!-- Scope: CLAUDE.md violations + WIZARD_SPEC endpoint contract compliance -->

---

## Summary

`import_wizard.py` is clean in the areas where CLAUDE.md has bright-line rules
(function length, whitelist decoration, translation coverage), but it diverges
from `WIZARD_SPEC.md` on **endpoint names**, **signatures**, **helper names**,
and **Step 5 behaviour** in ways that will break the JS integration layer.
None of the Python files should be merged to develop until these are reconciled.

---

## 1. CLAUDE.md Violation Checklist

### 1a. Functions over 40 lines — PASS

| Function | Lines | Verdict |
|----------|-------|---------|
| `upload_invoice` | ~17 | ✓ |
| `run_extraction` | ~33 | ✓ |
| `match_supplier` | ~19 | ✓ |
| `confirm_supplier` | ~10 | ✓ |
| `match_items` | ~15 | ✓ |
| `confirm_items` | ~8 | ✓ |
| `get_review_summary` | ~8 | ✓ |
| `populate_document` | ~19 | ✓ |
| `_assert_doctype` | ~4 | ✓ |

All functions are within the 40-line limit.

### 1b. Missing `@frappe.whitelist()` — PASS

Every public endpoint has the decorator. `_assert_doctype` is correctly private
(no decorator needed).

### 1c. Raw SQL / forbidden DB calls — PASS (with note)

No raw SQL is present. `frappe.db.exists("Supplier", supplier)` at line 98 is an
ORM call, not SQL. The approved list in CLAUDE.md (`get_doc`, `get_value`,
`get_list`) does not enumerate `exists`, but this is standard Frappe and
acceptable. No action required.

### 1d. Missing `_()` around user-facing strings — PASS

`from frappe import _` is imported at line 7. Every `frappe.throw()` call wraps
its message in `_()`. No bare string literals reach the user.

---

## 2. WIZARD_SPEC.md Contract Violations

### 2a. Step 2 — Endpoint name mismatch (CRITICAL)

| | SPEC | Actual |
|-|------|--------|
| Function name | `run_ai_extraction` | `run_extraction` |

The JS layer calls `fatura_ai.api.import_wizard.run_ai_extraction`. The current
function is named `run_extraction` — the JS call will 404 at runtime.

**Fix:** rename `run_extraction` → `run_ai_extraction`.

### 2b. Step 2 — No "Processing" status before extraction (SPEC §Step 2 algorithm)

SPEC step 2: *"Set `log.status = "Processing"` and save"* before calling the AI
provider. The current implementation only saves status `"Extracted"` on success.
A crash mid-extraction leaves the log in `"Draft"` with no signal that work
started.

**Fix:** set and save `log.status = "Processing"` before calling `extract_invoice`.

### 2c. Step 2 — No error handling on AI extraction call (SPEC §Step 2 algorithm)

SPEC step 5: on any exception call `log.mark_failed(str(e))`, commit, re-raise as
`frappe.ValidationError`. The current implementation has no `try/except` block
around the AI call — an unhandled exception will bubble up as a 500 with a raw
traceback, the log will stay in `"Processing"` state, and the JS Retry button
will never get a clean error message.

**Fix:** wrap `extract_invoice(...)` in `try/except Exception as e:`, call
`log.mark_failed(str(e))`, commit, then re-raise as
`frappe.ValidationError(_("AI extraction failed: {0}").format(e))`.

### 2d. Step 2 — Wrong helper function name and argument type

| | SPEC | Actual |
|-|------|--------|
| Helper import | `extract_invoice_data` | `extract_invoice` |
| Argument passed | `log.file_url` (URL string) | `file_path` (resolved filesystem path) |

The spec defines the helper contract as `extract_invoice_data(file_url)` in
`helpers/ai_extraction.py`. The implementation additionally resolves the URL to a
filesystem path via a second `frappe.get_doc("File", …)` call — a contract
deviation that couples `import_wizard.py` to filesystem layout instead of
delegating resolution to the helper.

### 2e. Step 2 — Dead-code null guard after `frappe.get_doc` (lines 37–39, 75–77)

```python
log = frappe.get_doc("Fatura Import Log", log_name)
if not log:
    frappe.throw(...)
```

`frappe.get_doc()` **raises `frappe.DoesNotExistError`** when the document is not
found — it never returns `None`. The `if not log:` branch is unreachable dead
code. This pattern appears in `run_extraction` (lines 37–39) and `match_supplier`
(lines 75–77).

The SPEC mandates a checked throw on missing log; to honour that, use
`frappe.db.exists` before `frappe.get_doc`, or catch `frappe.DoesNotExistError`.

### 2f. Step 3 — Wrong helper function name and parameter names

| | SPEC | Actual |
|-|------|--------|
| Helper import | `find_supplier` | `find_supplier_match` |
| VAT kwarg | `vat_number=tax_id` | `tax_id=tax_id` |
| Name kwarg | `supplier_name=vendor_name` | `vendor_name=vendor_name` |

If `helpers/supplier_matching.py` exposes `find_supplier`, the import will
`ImportError` at runtime. The kwarg names also differ, so even if the wrong name
happens to exist it will pass arguments to the wrong positions.

### 2g. Step 3 — Missing validation for both-empty inputs (SPEC §Step 3 errors)

SPEC: *"If `vendor_name` and `tax_id` both empty: `frappe.throw(_("Cannot match supplier: no name or VAT in extracted data"))`"*

Current implementation passes `None, None` straight into the helper with no guard.

**Fix:** add an early guard:
```python
if not vendor_name and not tax_id:
    frappe.throw(_("Cannot match supplier: no name or VAT in extracted data"))
```

### 2h. Step 4 — Missing `line_items_json` parameter (CRITICAL)

| | SPEC | Actual |
|-|------|--------|
| Signature | `match_items(log_name, line_items_json)` | `match_items(log_name)` |

SPEC explicitly explains the design decision: *"Pass complex arrays as stringified
JSON and parse inside the function."* The JS sends `this.extracted.items` as
`line_items_json`. The current endpoint ignores this and re-reads items from
`log.extracted_json` — meaning any in-flight edits the user made on Step 3 are
silently discarded.

### 2i. Step 4 — Return value missing `summary` field (SPEC §Step 4 return value)

SPEC return: `{items: [...], summary: {total, matched, partial, unmatched}}`

Actual return: `{"items": matched}` — no `summary`. The JS step renders a summary
bar from this field; omitting it will crash the frontend.

### 2j. Step 5 — Endpoint name and signature mismatch (CRITICAL)

| | SPEC | Actual |
|-|------|--------|
| Function name | `confirm_import` | `populate_document` |
| Parameters | `(log_name)` | `(log_name, confirmed_items)` |
| Return value | `{doctype, docname, status, url}` | `payload` dict |
| Behaviour | Creates and inserts a new doc via `frappe.new_doc` | Builds payload dict only; **no doc is created** |

This is the most significant deviation. Per the spec, Step 5 is where the
Purchase Invoice / PO actually comes into existence as a Draft. The current
`populate_document` returns a field map but never calls `frappe.new_doc()` or
`doc.insert()`, so no document is ever created. The wizard would complete
successfully on the JS side while silently doing nothing in ERPNext.

Additionally, the SPEC says all item data is read from the log's `extracted_json`
— the endpoint takes no `confirmed_items` parameter. Having the JS re-send items
here means the log's confirmed-item state (written by `confirm_items`) can
diverge from what `populate_document` acts on.

### 2k. Step 5 — Missing guard for `log.status == "Success"` (SPEC §Step 5 errors)

SPEC: *"If `log.status` is already 'Success': `frappe.throw(_("This import has already been completed. Open {0}.").format(log.source_docname))`"*

Not present in `populate_document`. Without this guard, a double-click or browser
refresh can create duplicate Purchase Invoices.

### 2l. Step 5 — Private helper name differs from SPEC

SPEC: `_build_doctype_payload(log, extracted)` (private, 2 args)
Actual call (line 165): `build_doctype_payload(log, extracted, items)` (public name, 3 args)

The SPEC places this helper in `api/extractor.py` as a private function; calling
it without the underscore prefix implies it is exposed externally, which it should
not be.

---

## 3. Endpoint Contract Summary

| Step | SPEC function | Actual function | Name OK | Signature OK | Behaviour OK |
|------|--------------|-----------------|---------|--------------|--------------|
| 1 | `upload_invoice` | `upload_invoice` | ✅ | ✅ | ✅ |
| 2 | `run_ai_extraction` | `run_extraction` | ❌ | — | ❌ (no error handling, no Processing status) |
| 3 | `match_supplier` | `match_supplier` | ✅ | ⚠️ (params optional not required) | ❌ (wrong helper name/kwargs, missing guard) |
| 3b | `confirm_supplier` | `confirm_supplier` | ✅ | ✅ | ✅ |
| 4 | `match_items` | `match_items` | ✅ | ❌ (missing line_items_json) | ❌ (missing summary, discards edits) |
| 4b | `confirm_items` | `confirm_items` | ✅ | ✅ | ✅ |
| 4c | `get_review_summary` | `get_review_summary` | ✅ | ✅ | ✅ |
| 5 | `confirm_import` | `populate_document` | ❌ | ❌ | ❌ (no doc created) |

---

## 4. Priority Order for Fixes

1. **Rename `run_extraction` → `run_ai_extraction`** (JS call will break otherwise)
2. **Rename `populate_document` → `confirm_import`**, remove `confirmed_items`
   param, add `frappe.new_doc` + `doc.insert()`, return `{doctype, docname, status, url}`
3. **Add `line_items_json` param to `match_items`**, parse it instead of reading from log
4. **Add `summary` to `match_items` return value**
5. **Fix Step 2 error handling** (try/except, `mark_failed`, `Processing` status)
6. **Fix helper import names** (`find_supplier` / `extract_invoice_data`)
7. **Remove dead-code null guards** after `frappe.get_doc` — handle `DoesNotExistError` instead
8. **Add both-empty guard** to `match_supplier`
9. **Add already-completed guard** to `confirm_import`
10. **Prefix `build_doctype_payload` with `_`** in extractor.py
