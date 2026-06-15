# Next Task: T012 — ksa_compliance ZATCA Integration
<!-- Written by Cowork Orchestrator at 2026-06-15 02:09 -->

**Priority:** P0  
**Depends on:** T011 ✅ (wizard step 5 is done)

## Task

Link the Fatura import flow to ERPNext's ZATCA/ksa_compliance fields.

Specifically:
1. After the user confirms in wizard Step 5, the created Purchase Invoice must have ZATCA-required fields populated from the extracted invoice data (VAT registration number, invoice UUID/IRN, supply date, total VAT amount, etc.)
2. Inspect `ksa_compliance` app's DocType customizations for Purchase Invoice — identify which fields are added and how they're populated normally.
3. Map Fatura's extracted fields (from AI extraction + import log) to those ZATCA fields on PI creation.
4. Add validation: if ZATCA fields are missing and ksa_compliance is installed, warn the user (don't block — allow save as draft).
5. Unit test or at least a manual test checklist in `tests/test_zatca_integration.py`.

Key files to look at:
- `fatura_ai/api/import_wizard.py` (step 5 confirm endpoint)
- `fatura_ai/doctype/fatura_import_log/fatura_import_log.py`
- `~/frappe-bench/apps/ksa_compliance/` (if installed)

Commit with message: `feat(T012): link Fatura import to ZATCA fields`  
Then update TASKS.md: move T012 from In Progress to Done.
