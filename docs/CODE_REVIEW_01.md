# Code Review 01 — fatura_ai scaffold (T001–T005)
<!-- Reviewer: Claude Code | Date: 2026-06-15 | Branch: develop -->
<!-- Scope: commits 9ab55c0 → 4cc5916 -->
<!-- Rule source: CLAUDE.md — checked against every rule listed there -->

---

## Summary

3 critical bugs that will cause runtime errors, 2 hard CLAUDE.md violations,
and 4 design issues. Nothing unshippable if the bugs are fixed before T007.

---

## 🔴 Critical — Will Cause Runtime Errors

### CR-01 · `import_wizard.py:60` — `find_supplier` does not exist

**File:** `fatura_ai/api/import_wizard.py:61`
**File:** `fatura_ai/helpers/supplier_matching.py`

`match_supplier()` in `import_wizard.py` calls:

```python
from fatura_ai.helpers.supplier_matching import find_supplier
match = find_supplier(vat_number=..., supplier_name=...)
```

`supplier_matching.py` exports `match_supplier(tax_id, name)`. There is no
`find_supplier`. This raises `ImportError` the first time the Step 2 wizard
endpoint is called.

**Fix:** Rename the helper function to `find_supplier` and accept `vat_number`
and `supplier_name` keyword arguments, OR update the call site to use
`match_supplier(tax_id=..., name=...)`. The WIZARD_SPEC (see `docs/WIZARD_SPEC.md`)
defines the canonical signature.

---

### CR-02 · `supplier_matching.py` — `confidence` is a string, not a float

**File:** `fatura_ai/helpers/supplier_matching.py:31,58,82`

All three return paths return `"confidence": "high"`, `"medium"`, or `"low"`.

`Fatura Import Log.supplier_confidence` is declared as `fieldtype: Float`.
When `import_wizard.py:68` does:

```python
log.supplier_confidence = match.get("confidence", 0.0)
```

Frappe's form save will either raise `frappe.exceptions.ValidationError`
(strict mode) or silently coerce the string to `0.0`, hiding the actual value.

**Fix:** Return a float from every tier:
- Tier 1 (exact VAT): `1.0`
- Tier 2 (fuzzy): the normalized ratio score (`score / 100`)
- Tier 3 (no match): `0.0`

---

### CR-03 · `supplier_matching.py:match_by_name` — no `None` guard

**File:** `fatura_ai/helpers/supplier_matching.py:37`

```python
def match_by_name(name: str) -> Optional[Dict[str, Any]]:
    ...
    matches = difflib.get_close_matches(name, names, ...)
```

`name` is typed `str` but the caller (`match_supplier`) passes whatever
`supplier_name` the AI extracted, which may be `None`. `difflib.get_close_matches(None, ...)`
raises `TypeError: argument should be a str or a bytes-like object`.

Identical risk exists in `match_by_tax_id` if `tax_id` is `None`.

**Fix:** Guard both functions at entry:

```python
if not name:
    return None
```

---

## 🟠 Hard CLAUDE.md Violations

### CV-01 · Wrong fuzzy library — `difflib` instead of `rapidfuzz`

**File:** `fatura_ai/helpers/supplier_matching.py:8,47`
**Rule:** CLAUDE.md Tech Stack — "Fuzzy matching: rapidfuzz"

Aider chose stdlib `difflib`. Issues:
1. Violates the explicitly declared tech stack.
2. `difflib.get_close_matches` does not return a numeric score, only a boolean
   threshold — this forced the string-confidence anti-pattern (CR-02).
3. `difflib` has no Arabic-optimised tokenisation; `rapidfuzz.fuzz.WRatio` handles
   mixed Arabic/English strings significantly better (tested on our invoice set).

**Fix:** Replace with `rapidfuzz.process.extractOne` + `fuzz.WRatio`, matching
the pattern already used correctly in `helpers/item_matching.py:57`.

---

### CV-02 · No tests for any `api/` function

**Files:** `fatura_ai/api/import_wizard.py`, `fatura_ai/api/extractor.py`
**Rule:** CLAUDE.md rule 9 — "ALWAYS write a test for every new function in
api/ directory."

Functions with zero test coverage:
- `upload_invoice`, `run_extraction`, `match_supplier`, `confirm_supplier`
- `match_items`, `confirm_items`, `get_review_summary`, `populate_document`
- `validate_file`, `build_doctype_payload`

The `tests/unit/` directory does not exist yet. No agent has created it.

**Fix (T014, T015, T016):** Create `tests/unit/` and write at minimum:
- `test_upload_invoice.py` — valid file, invalid extension, oversize file
- `test_match_supplier.py` — exact VAT hit, fuzzy hit, no match
- `test_match_items.py` — learned mapping, fuzzy hit, no match
- `test_validate_file.py` — extension allow/deny, size allow/deny

Do NOT mark any of T007–T011 done until matching tests exist.

---

## 🟡 Design Issues (not violations, but will cause bugs or bad UX)

### DI-01 · `run_extraction` has no exception handler — log stays at "Processing"

**File:** `fatura_ai/api/import_wizard.py:34–49`

```python
log.status = "Processing"
log.save(...)
result = extract_invoice_data(log.file_url)   # can throw
log.extracted_json = ...                       # never reached on throw
```

If the AI provider call times out, hits a rate limit, or returns malformed JSON,
the exception propagates to Frappe's RPC layer (returning a 500 to the JS) and
the log record stays stuck at "Processing" indefinitely.

**Fix:** Wrap in try/except and call the controller's `mark_failed()`:

```python
try:
    result = extract_invoice_data(log.file_url)
except Exception as e:
    log.mark_failed(str(e))
    frappe.db.commit()
    frappe.throw(_("AI extraction failed: {0}").format(str(e)))
```

---

### DI-02 · `_log_settings_update` reads Password fields directly

**File:** `fatura_ai/fatura_ai/doctype/fatura_ai_settings/fatura_ai_settings.py:43-45`

```python
"anthropic_api_key": self._mask_key(self.anthropic_api_key),
```

For `fieldtype: Password`, `self.anthropic_api_key` on a freshly-loaded document
returns the AES-encrypted ciphertext, not the plaintext key. The masking function
operates on random-looking bytes, so the logged value is meaningless.

**Fix:** Log only truthiness, never the value:

```python
"anthropic_api_key_set": bool(self.get("anthropic_api_key")),
```

Remove `_mask_key` entirely — it provides a false sense of security.

---

### DI-03 · `AnthropicProvider._build_prompt` is unreachable dead code

**File:** `fatura_ai/api/providers/anthropic_provider.py:25-34`

`_build_prompt` is defined but never called — `extract_invoice` raises
`NotImplementedError` before reaching it. The prompt template path it constructs
(`templates/prompts/extraction_prompt.txt`) also does not exist yet.

This is fine for a stub, but Aider implementing T003 must call `_build_prompt`
and the template file must exist before T003 is marked done.

---

### DI-04 · `fatura_ai_settings.py` changed `msgprint` to `frappe.throw` — UX regression

**File:** `fatura_ai/fatura_ai/doctype/fatura_ai_settings/fatura_ai_settings.py:27`

The T001 scaffold used non-blocking `frappe.msgprint(..., alert=True)`.
Aider's T002 changed this to `frappe.throw()`. This means a user cannot
save Settings unless the selected provider's API key is already filled in —
creating a chicken-and-egg problem during first-run onboarding.

Recommended behaviour: warn on missing key (allow save), throw only if
the user tries to run an actual import with no key configured.

---

## Checklist for T007 (wizard Step 1 UI) prerequisites

Before T007 starts, the following must be resolved:

- [ ] CR-01 fixed (find_supplier / rename)
- [ ] CR-02 fixed (confidence → float)
- [ ] CR-03 fixed (None guards)
- [ ] CV-01 fixed (switch to rapidfuzz in supplier_matching)
- [ ] DI-01 fixed (exception handler in run_extraction)

CV-02 (missing tests) should be tracked as P1 blocking the PR for any step
that adds a new `api/` function.
