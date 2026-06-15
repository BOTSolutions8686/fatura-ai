# Next Task for Aider: T014 — Unit Tests for Supplier Matching
<!-- Written by Cowork Orchestrator at 2026-06-15 03:09 -->

**Priority:** P1
**Depends on:** T005 ✅ (supplier_matching.py is done)

## Task

Write unit tests for the supplier matching module.

File to create: `fatura_ai/tests/test_supplier_matching.py`

Requirements:
- Mock `frappe.db.get_value`, `frappe.get_all`, and `frappe.db.sql` so tests run without a live Frappe instance
- Test **Tier 1**: exact match on supplier name and VAT number — assert `tier=1`, `action="matched"`
- Test **Tier 2**: fuzzy match — use a slightly misspelled supplier name, assert `tier=2`, score is within threshold
- Test **Tier 3**: no match — assert `action="create_new"`, `supplier_name=None`
- Test edge cases: empty string input, None input, duplicate suppliers
- Use Python `unittest` or `pytest` — whichever fits the project's test runner

Look at `fatura_ai/supplier_matching.py` for the exact function signatures to test.

## Commit when done:
```bash
git add fatura_ai/tests/test_supplier_matching.py
git commit -m "test(T014): unit tests for supplier matching"
```

Then update TASKS.md: move T014 from TODO to Done.

## After T014 — T016: Unit tests for AI extraction
File: `fatura_ai/tests/test_ai_extraction.py`
Dependencies: T003 ✅, T004 ✅
