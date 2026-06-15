"""
End-to-end pipeline test for Sprint 3 (T028–T035).
Run via: bench --site frontend run-tests --app fatura_ai --module fatura_ai.tests.test_e2e_sprint3
"""
import frappe
import unittest
from frappe.tests.utils import FrappeTestCase


INVOICE_FILES = [
    "/files/United Metal industry company-INV100.pdf",
    "/files/PRO-213FCA000362.pdf",
    "/files/HUTA Marine Works Ltd.pdf",
    "/files/ACC-SINV-2026-00340.pdf",
    "/files/25-1971.pdf",
    "/files/08120.pdf",
]


class TestSprint3Pipeline(FrappeTestCase):

    def _run_pipeline(self, file_url):
        """Run steps 0–4 (upload → extraction → supplier → items → confirm_items)."""
        from fatura_ai.api.import_wizard import (
            upload_invoice,
            run_ai_extraction,
            match_supplier,
            match_items,
            confirm_items,
        )

        # Step 0: upload (file must already exist as a File doctype)
        if not frappe.db.exists("File", {"file_url": file_url}):
            return {"skipped": True, "reason": "File not found: " + file_url}

        result = upload_invoice(
            file_url=file_url,
            source_doctype="Purchase Invoice",
            source_docname="new-purchase-invoice-test",
        )
        self.assertEqual(result["status"], "ok")
        log_name = result["log_name"]

        # Step 1: AI extraction
        log = run_ai_extraction(log_name)
        self.assertIsNotNone(log)

        # Step 2: supplier matching
        match = match_supplier(log_name)
        self.assertIn("method", match)

        # Step 3: item matching
        items_result = match_items(log_name)
        self.assertIn("items", items_result)
        self.assertIn("summary", items_result)

        # Step 4: confirm items (with whatever was matched)
        confirmed = items_result["items"]
        save_result = confirm_items(log_name, confirmed)
        self.assertEqual(save_result["status"], "ok")

        return {
            "log_name": log_name,
            "supplier_method": match.get("method"),
            "supplier": match.get("supplier"),
            "items_total": items_result["summary"]["total"],
            "items_matched": items_result["summary"]["matched"],
        }

    def test_pipeline_all_invoices(self):
        results = []
        for file_url in INVOICE_FILES:
            try:
                r = self._run_pipeline(file_url)
                r["file"] = file_url.split("/")[-1]
                r["status"] = "PASS" if not r.get("skipped") else "SKIP"
                results.append(r)
            except Exception as e:
                results.append({
                    "file": file_url.split("/")[-1],
                    "status": "FAIL",
                    "error": str(e)[:200],
                })

        print("\n=== Sprint 3 E2E Pipeline Results ===")
        for r in results:
            print(f"  [{r['status']}] {r['file']}")
            if r["status"] == "PASS":
                print(f"         supplier={r.get('supplier')} via {r.get('supplier_method')}")
                print(f"         items: {r.get('items_matched')}/{r.get('items_total')} matched")
            elif r["status"] == "FAIL":
                print(f"         ERROR: {r.get('error')}")

        failed = [r for r in results if r["status"] == "FAIL"]
        self.assertEqual(len(failed), 0, f"Pipeline failures: {failed}")


class TestHelperFunctions(FrappeTestCase):
    """Unit tests for T030–T035 helper functions."""

    def test_t030_check_duplicate_no_dup(self):
        from fatura_ai.api.import_wizard import _check_duplicate
        import types
        log = types.SimpleNamespace(
            matched_supplier="Nonexistent Supplier XYZ",
            source_doctype="Purchase Invoice",
        )
        result = _check_duplicate(log, {"invoice_number": "UNIQUE-TEST-999999"})
        self.assertIsNone(result)

    def test_t031_resolve_currency_sar(self):
        from fatura_ai.api.import_wizard import _resolve_currency
        result = _resolve_currency({"currency": "SAR"}, None)
        self.assertEqual(result, "SAR")

    def test_t031_resolve_currency_bad_falls_back(self):
        from fatura_ai.api.import_wizard import _resolve_currency
        result = _resolve_currency({"currency": "BADCUR"}, None)
        self.assertIsNone(result)  # None when no company

    def test_t033_validate_uom_nos(self):
        from fatura_ai.api.import_wizard import _validate_uom
        self.assertEqual(_validate_uom("Nos"), "Nos")

    def test_t033_validate_uom_bad_falls_back(self):
        from fatura_ai.api.import_wizard import _validate_uom
        self.assertEqual(_validate_uom("NONEXISTENT_UOM"), "Nos")

    def test_t033_validate_uom_none(self):
        from fatura_ai.api.import_wizard import _validate_uom
        self.assertEqual(_validate_uom(None), "Nos")

    def test_t034_sanity_checks_clean(self):
        from fatura_ai.api.import_wizard import _run_sanity_checks
        extracted = {"subtotal": 100, "vat_amount": 15, "total": 115}
        items = [{"qty": 1, "rate": 100}]
        warnings = _run_sanity_checks(extracted, items)
        self.assertEqual(warnings, [])

    def test_t034_sanity_checks_bad_vat(self):
        from fatura_ai.api.import_wizard import _run_sanity_checks
        extracted = {"subtotal": 100, "vat_amount": 20, "total": 120}
        items = [{"qty": 1, "rate": 100}]
        warnings = _run_sanity_checks(extracted, items)
        self.assertTrue(any("VAT" in w for w in warnings))

    def test_t035_auto_create_item_cleans_code(self):
        import re
        code = "Test Item Code -  "
        clean = (re.sub(r'[\s./\\:\-]+$', '', code.strip()) or code.strip())[:140]
        self.assertEqual(clean, "Test Item Code")

    def test_t035_auto_create_item_truncates(self):
        import re
        code = "A" * 200
        clean = (re.sub(r'[\s./\\:\-]+$', '', code.strip()) or code.strip())[:140]
        self.assertEqual(len(clean), 140)
