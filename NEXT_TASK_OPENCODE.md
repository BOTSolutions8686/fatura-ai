# Next Task for OpenCode

**Date:** 2026-06-15 02:00

## Current: T006 — Finish item_matching.py

File to create: `fatura_ai/fatura_ai/item_matching.py`

If you haven't finished yet, complete the 3-tier item matching logic:
- **Tier 1:** Exact match on `item_code` or `item_name` via `frappe.db.get_value`
- **Tier 2:** Fuzzy match on `item_name` and `description` using `rapidfuzz` (threshold from FaturaAISettings.fuzzy_match_threshold, default 0.8)
- **Tier 3:** Return `action: "create_new"` if no match

Return: `{tier: int, item_code: str|None, item_name: str|None, score: float|None, action: "matched"|"fuzzy"|"create_new"}`

Also implement `find_item_match(description, uom=None, supplier=None)` and `persist_mappings(items, supplier)` (used by import_wizard.py).

Commit when done:
```bash
git add fatura_ai/fatura_ai/item_matching.py
git commit -m "feat(T006): implement 3-tier item matching logic"
```

Then update TASKS.md: move T006 from In Progress to Done.

## After T006 — T015: Unit tests for item matching

File: `fatura_ai/tests/test_item_matching.py`

Same pattern as supplier matching tests — mock frappe calls, test all 3 tiers.
Dependencies: T006 ✅ (once you finish it above)
