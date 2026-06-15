# CODE_REVIEW_03 — Final Review Pass (T018)
<!-- Reviewer: Dispatch/Claude | Date: 2026-06-15 | Files: import_wizard, supplier_matching, item_matching, zatca_mapper, providers -->

## Summary

5 issues found: 2 critical (will fail at runtime), 2 major (logic/convention violations), 1 minor.
Providers are stubs — AI extraction pipeline is not yet implemented (known, tracked separately).

---

## CRITICAL Issues

### CR3-01 — Wrong import path in `_match_by_learned_mapping`
**File:** `fatura_ai/helpers/item_matching.py` — `_match_by_learned_mapping()`  
**Severity:** Critical  
**Problem:** The function imports from `fatura_ai.fatura_ai.doctype.invoice_ai_item_map...` — double `fatura_ai` in the path. This will raise `ModuleNotFoundError` at runtime.

```python
# Current (broken)
from fatura_ai.fatura_ai.doctype.invoice_ai_item_map.invoice_ai_item_map import InvoiceAIItemMap

# Fix
from fatura_ai.doctype.invoice_ai_item_map.invoice_ai_item_map import InvoiceAIItemMap
```

---

### CR3-02 — `confirm_import()` exceeds 40-line limit by ~35 lines
**File:** `fatura_ai/api/import_wizard.py` — `confirm_import()`  
**Severity:** Critical (CLAUDE.md rule 7: NEVER write a function longer than 40 lines)  
**Problem:** `confirm_import()` is ~75 lines. The item row population block alone is 40+ lines of repetitive `row.field = payload.get("field")` assignments that don't belong in the endpoint.

**Fix:** Extract into a private helper:

```python
# Extract this into import_wizard.py:
def _populate_item_row(row, item_data: dict):
    """Copy payload fields onto one child table row."""
    for field in ("item_code", "qty", "rate", "amount", "description",
                  "uom", "conversion_factor", "stock_uom", "stock_qty",
                  "warehouse", "expense_account", "project", "cost_center"):
        setattr(row, field, item_data.get(field))
```

Only set the fields actually present in extracted invoice data. The current implementation copies ~30 fields (fixed_asset, asset_category, asset_location, etc.) that can never appear in an AI-extracted invoice — this is dead code that inflates the function and will cause confusion.

---

## MAJOR Issues

### CR3-03 — `supplier_confidence` type mismatch
**File:** `fatura_ai/helpers/supplier_matching.py` — `match_by_tax_id()`, `match_by_name()`  
**Severity:** Major  
**Problem:** Both functions return `"confidence": "high"` or `"confidence": "medium"` (strings). In `import_wizard.py`, line `log.supplier_confidence = match.get("confidence", 0.0)` saves a string into what is likely a Float field on the DocType. This will either raise a `ValidationError` or silently store `0` (Frappe coerces non-numeric to 0).

**Fix:** Return numeric confidence scores to match item_matching.py convention:

```python
# In match_by_tax_id:
"confidence": 1.0, "tier": 1

# In match_by_name:
"confidence": round(difflib.SequenceMatcher(None, name, best_name).ratio(), 3), "tier": 2

# In Tier 3 fallback:
"confidence": 0.0, "tier": 3
```

---

### CR3-04 — `frappe.db.get_all()` instead of `frappe.get_all()`
**File:** `fatura_ai/helpers/item_matching.py` — `_match_by_fuzzy_name()`  
**Severity:** Major (CLAUDE.md rule 4)  
**Problem:** `frappe.db.get_all()` is a lower-level call that bypasses Frappe hooks, permissions, and field validation. CLAUDE.md explicitly requires `frappe.get_all()`.

```python
# Current (violates CLAUDE.md rule 4)
items = frappe.db.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name"])

# Fix
items = frappe.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name"])
```

---

## MINOR Issues

### CR3-05 — `match_by_tax_id()` does not guard against `None` / empty tax_id
**File:** `fatura_ai/helpers/supplier_matching.py` — `match_by_tax_id()` and `match_supplier()`  
**Severity:** Minor  
**Problem:** `match_supplier(tax_id=None, ...)` passes `None` directly to `match_by_tax_id(None)`, which then queries `filters={"tax_id": None}`. Frappe treats this as "tax_id IS NULL" and will return all suppliers with no tax_id — potentially a large set with limit=1 returning a random result.

**Fix:** Guard at the top of `match_supplier()`:

```python
def match_supplier(tax_id: str, name: str) -> Dict[str, Any]:
    if tax_id:
        result = match_by_tax_id(tax_id)
        if result:
            return result
    if name:
        result = match_by_name(name)
        if result:
            return result
    return {"supplier": None, "supplier_name": None, "confidence": 0.0, "tier": 3}
```

---

## Non-Issues (OK as-is)

- **`zatca_mapper.py`** — 41 lines total but individual functions are well under 40 lines. File length limit only applies to functions. ✅
- **Provider stubs** — All three providers raise `NotImplementedError`. This is correct for the scaffold stage; actual implementations are tracked in T003, T004, T019.
- **`confirm_import` naming of imported `match_supplier`** — Python scoping prevents shadowing (import is local to function). Confusing but not broken.
- **FUZZY_CUTOFF = 60** — rapidfuzz uses 0-100 scale; 60 maps to roughly 60% similarity. Task descriptions said 80% but implementation uses 60. This may be intentional (more permissive matching for noisy OCR text). Recommend documenting the rationale in a comment.

---

## Action Items for Aider

| ID | File | Fix |
|----|------|-----|
| CR3-01 | `helpers/item_matching.py` | Fix double `fatura_ai.fatura_ai` import path |
| CR3-02 | `api/import_wizard.py` | Extract `_populate_item_row()` helper, strip dead asset fields |
| CR3-03 | `helpers/supplier_matching.py` | Change confidence returns from strings to floats |
| CR3-04 | `helpers/item_matching.py` | Replace `frappe.db.get_all()` with `frappe.get_all()` |
| CR3-05 | `helpers/supplier_matching.py` | Guard None/empty tax_id before querying |

Priority order: CR3-01 → CR3-03 → CR3-04 → CR3-05 → CR3-02
