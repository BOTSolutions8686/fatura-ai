"""
End-to-end pipeline runner — tests extraction, supplier matching, and item matching
for the 6 known invoice files. Does NOT call confirm_import (to avoid creating docs).
Run via: bench --site frontend execute fatura_ai.tests.test_e2e_pipeline.run_e2e_tests
"""
import frappe


INVOICE_FILES = [
    "/files/United Metal industry company-INV100.pdf",
    "/files/PRO-213FCA000362.pdf",
    "/files/HUTA Marine Works Ltd.pdf",
    "/files/ACC-SINV-2026-00340.pdf",
    "/files/25-1971.pdf",
    "/files/08120.pdf",
]


def run_e2e_tests():
    from fatura_ai.api.import_wizard import (
        upload_invoice, run_ai_extraction,
        match_supplier, match_items, confirm_items,
    )

    results = []
    for file_url in INVOICE_FILES:
        fname = file_url.split("/")[-1]
        try:
            if not frappe.db.exists("File", {"file_url": file_url}):
                results.append({"file": fname, "status": "SKIP", "reason": "File not in DB"})
                continue

            r = upload_invoice(
                file_url=file_url,
                source_doctype="Purchase Invoice",
                source_docname="new-purchase-invoice-e2e",
            )
            log_name = r["log_name"]

            run_ai_extraction(log_name)
            match = match_supplier(log_name)
            items_r = match_items(log_name)
            confirm_items(log_name, items_r["items"])

            results.append({
                "file": fname,
                "status": "PASS",
                "supplier": match.get("supplier") or "(none)",
                "method": match.get("method"),
                "items": f"{items_r['summary']['matched']}/{items_r['summary']['total']}",
            })
        except Exception as e:
            results.append({"file": fname, "status": "FAIL", "error": str(e)[:300]})
            frappe.db.rollback()

    passed = sum(1 for r in results if r["status"] == "PASS")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print(f"\n=== End-to-End Pipeline ({passed} pass / {skipped} skip / {failed} fail) ===")
    for r in results:
        if r["status"] == "PASS":
            print(f"  [PASS] {r['file']}")
            print(f"         supplier: {r['supplier']} via {r['method']}, items: {r['items']}")
        elif r["status"] == "SKIP":
            print(f"  [SKIP] {r['file']}: {r.get('reason')}")
        else:
            print(f"  [FAIL] {r['file']}: {r.get('error')}")

    return {"passed": passed, "skipped": skipped, "failed": failed, "all_ok": failed == 0}
