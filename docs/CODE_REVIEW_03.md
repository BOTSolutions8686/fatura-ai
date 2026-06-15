# CODE_REVIEW_03 — Final Frappe Best-Practice Pass (T018)

**Date:** 2026-06-15  
**Reviewer:** claude-sonnet-4-6 (automated)  
**Files reviewed:**
- `fatura_ai/api/import_wizard.py`
- `fatura_ai/helpers/supplier_matching.py`
- `fatura_ai/helpers/item_matching.py`
- `fatura_ai/helpers/ai_extraction.py`
- `fatura_ai/helpers/zatca_mapper.py`
- `fatura_ai/tests/test_supplier_matching.py`
- `fatura_ai/tests/test_item_matching.py`

---

## Checklist Results

| Check | Status | Notes |
|---|---|---|
| SQL injection via `frappe.db.sql` with `%s` | ✅ PASS | No `frappe.db.sql` calls found — all DB access via ORM |
| Missing `frappe.has_permission` on public APIs | ❌ FAIL | All whitelist endpoints affected — see §1 |
| Bare `except` clauses | ✅ PASS | Only `except Exception as e:` used |
| Hardcoded UI strings missing `_()` | ✅ PASS | All user-facing strings correctly wrapped |
| Missing docstrings on public functions | ✅ PASS | All public functions have docstrings |

---

## Critical Bugs (runtime failures)

### BUG-1 — `ImportError` in `match_supplier` endpoint
**File:** `import_wizard.py:90`  
**Severity:** CRITICAL — will crash every supplier-matching step at runtime

```python
# import_wizard.py:90 — WRONG
from fatura_ai.helpers.supplier_matching import find_supplier

# supplier_matching.py — actual export name
def match_supplier(tax_id: str, name: str) -> Dict[str, Any]:
```

`find_supplier` does not exist in `supplier_matching.py`. The exported function is `match_supplier`.

**Fix:** Change import to `from fatura_ai.helpers.supplier_matching import match_supplier` and update the call to `match_supplier(tax_id=tax_id, name=vendor_name)`.

---

### BUG-2 — Keyword argument mismatch on supplier call
**File:** `import_wizard.py:91–93`  
**Severity:** CRITICAL — would raise `TypeError` even if the import name were fixed

```python
# import_wizard.py:91-93 — WRONG kwargs
match = find_supplier(
    supplier_name=vendor_name,   # function expects 'name'
    vat_number=tax_id,           # function expects 'tax_id'
)
```

`supplier_matching.match_supplier` signature is `(tax_id: str, name: str)`. The positional/keyword names do not match.

**Fix:**
```python
match = match_supplier(tax_id=tax_id, name=vendor_name)
```

---

### BUG-3 — `confirm_import` always creates `Purchase Invoice`, ignores `source_doctype`
**File:** `import_wizard.py:206`  
**Severity:** CRITICAL — Purchase Order imports silently create a PI instead of a PO

```python
# import_wizard.py:206
doc = frappe.new_doc("Purchase Invoice")   # hardcoded — should branch on log.source_doctype
```

`_assert_doctype` permits both `"Purchase Invoice"` and `"Purchase Order"`, but `confirm_import` unconditionally creates a `Purchase Invoice`. An import initiated from a PO form will silently produce a PI.

**Fix:**
```python
doc = frappe.new_doc(log.source_doctype)
```

---

## Security Issues

### SEC-1 — Missing `frappe.has_permission` on all whitelist endpoints
**File:** `import_wizard.py` — all `@frappe.whitelist()` functions  
**Severity:** HIGH — any authenticated ERPNext user can read or mutate any import log

Frappe's `@frappe.whitelist()` decorator only authenticates the session; it does **not** check whether the user has permission on the documents being accessed. Every endpoint reads a `Fatura Import Log` by name without verifying ownership:

| Endpoint | Missing check |
|---|---|
| `upload_invoice` | `frappe.has_permission(source_doctype, "write", source_docname)` |
| `run_ai_extraction` | `frappe.has_permission("Fatura Import Log", "write", log_name)` |
| `match_supplier` | same |
| `confirm_supplier` | same |
| `match_items` | same |
| `confirm_items` | same |
| `get_review_summary` | `frappe.has_permission("Fatura Import Log", "read", log_name)` |
| `confirm_import` | `frappe.has_permission("Purchase Invoice", "create")` before `doc.insert()` |

**Recommended pattern:**
```python
if not frappe.has_permission("Fatura Import Log", "write", log_name):
    frappe.throw(_("Not permitted"), frappe.PermissionError)
```

---

### SEC-2 — `ignore_permissions=True` on document creation without pre-check
**File:** `import_wizard.py:26` (`upload_invoice`), `import_wizard.py:262` (`confirm_import`)  
**Severity:** MEDIUM

`doc.insert(ignore_permissions=True)` bypasses the standard Frappe permission system entirely. This is acceptable only when the calling user's permission has already been verified. Without the `has_permission` guard from SEC-1, an unprivileged user can create `Fatura Import Log` records and trigger `Purchase Invoice` creation.

---

## Performance Issues

### PERF-1 — Full supplier table scan in fuzzy matching
**File:** `supplier_matching.py:42`

```python
all_suppliers = frappe.get_all("Supplier", fields=["name", "supplier_name"])
```

No `limit` is set. On installations with thousands of suppliers this loads all rows into memory for every match attempt. Add `limit=500` or pre-filter to active suppliers (`"disabled": 0`).

---

### PERF-2 — Full item table scan in fuzzy matching
**File:** `item_matching.py:55`

```python
items = frappe.db.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name"])
```

Same pattern — no limit. Catalogs with 10 000+ items will make this slow. Consider limiting to `is_purchase_item = 1` and adding a result cap.

---

## Correctness Issues

### COR-1 — `None` tax_id can match suppliers with null `tax_id` field
**File:** `supplier_matching.py:15–33` (`match_by_tax_id`)

If `tax_id` is `None` (or empty string passed from extraction), `frappe.get_all("Supplier", filters={"tax_id": None})` will return suppliers whose `tax_id` column is NULL — a false match.

**Fix:** Guard at the top of `match_by_tax_id`:
```python
if not tax_id:
    return None
```

---

### COR-2 — `"items"` key lookup may miss AI output stored under `"line_items"`
**File:** `import_wizard.py:129` vs `import_wizard.py:64`

`run_ai_extraction` stores `log.line_items = frappe.as_json(result.get("line_items", []))` but also `log.extracted_json = frappe.as_json(result)`. Later, `match_items` reads:

```python
items = extracted.get("items", [])   # import_wizard.py:129
```

If the AI returns `{"line_items": [...]}`, the key is `"line_items"` in `extracted_json`, so `extracted.get("items", [])` returns `[]` and no items are matched. The extraction prompt output key and the consumer key must agree.

---

## Test Coverage Gap

### TEST-1 — Tests do not catch the `find_supplier` import name mismatch (BUG-1)
**File:** `test_supplier_matching.py:7`

Tests import `match_supplier` directly — they never exercise the import path through `import_wizard.py`. Add an integration smoke-test that calls `import_wizard.match_supplier` via `frappe.call` so the `ImportError` would be caught before merge.

---

## Items with No Issues

- `ai_extraction.py` — clean provider-selection logic; `_()` used correctly; all public functions documented.
- `zatca_mapper.py` — `is_ksa_compliance_installed()` guard is correctly applied; `_set_field` silently skips absent fields as designed.
- Both test files — no bare excepts, no SQL, correct `@patch` targeting of ORM calls.

---

## Summary: Action Required Before Merge

| ID | File | Line | Priority |
|---|---|---|---|
| BUG-1 | `import_wizard.py` | 90 | P0 — blocks runtime |
| BUG-2 | `import_wizard.py` | 91–93 | P0 — blocks runtime |
| BUG-3 | `import_wizard.py` | 206 | P0 — wrong doctype created |
| SEC-1 | `import_wizard.py` | all endpoints | P1 |
| SEC-2 | `import_wizard.py` | 26, 262 | P1 |
| COR-1 | `supplier_matching.py` | 20 | P1 |
| COR-2 | `import_wizard.py` | 129 | P1 |
| PERF-1 | `supplier_matching.py` | 42 | P2 |
| PERF-2 | `item_matching.py` | 55 | P2 |
| TEST-1 | `test_supplier_matching.py` | — | P2 |
