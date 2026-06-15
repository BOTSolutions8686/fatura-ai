"""Quick test runner for Sprint 3 T030-T035 helper functions."""


def run_sprint3_tests():
    from fatura_ai.api.import_wizard import (
        _check_duplicate, _validate_uom, _resolve_currency, _run_sanity_checks,
    )
    import types
    import re

    results = []

    # T030: duplicate check (no match)
    log = types.SimpleNamespace(matched_supplier="NoSuchSupplierXYZ", source_doctype="Purchase Invoice")
    r = _check_duplicate(log, {"invoice_number": "UNIQUE-FATURA-TEST-99999"})
    results.append(("T030 no-dup returns None", r is None, r))

    # T031: valid currency SAR
    r = _resolve_currency({"currency": "SAR"}, None)
    results.append(("T031 SAR resolves", r == "SAR", r))

    # T031: invalid currency falls back
    r = _resolve_currency({"currency": "BADCUR"}, None)
    results.append(("T031 bad currency is None", r is None, r))

    # T033: Nos exists
    results.append(("T033 Nos", _validate_uom("Nos") == "Nos", _validate_uom("Nos")))
    results.append(("T033 bad→Nos", _validate_uom("BADUNIT") == "Nos", _validate_uom("BADUNIT")))
    results.append(("T033 None→Nos", _validate_uom(None) == "Nos", _validate_uom(None)))

    # T034: clean invoice, no warnings
    items = [{"qty": 1, "rate": 100}]
    warns = _run_sanity_checks({"subtotal": 100, "vat_amount": 15, "total": 115}, items)
    results.append(("T034 clean=no warns", warns == [], warns))
    warns2 = _run_sanity_checks({"subtotal": 100, "vat_amount": 20, "total": 130}, items)
    results.append(("T034 bad=2 warns", len(warns2) == 2, warns2))

    # T035: regex cleanup
    code = "Test Item / "
    clean = (re.sub(r"[\s./\\:\-]+$", "", code.strip()) or code.strip())[:140]
    results.append(("T035 strip trailing", clean == "Test Item", clean))
    code2 = "A" * 200
    clean2 = (re.sub(r"[\s./\\:\-]+$", "", code2.strip()) or code2.strip())[:140]
    results.append(("T035 truncate 140", len(clean2) == 140, len(clean2)))

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== Sprint 3 Helper Unit Tests ({passed}/{len(results)} passed) ===")
    for name, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    return {"passed": passed, "total": len(results), "all_ok": passed == len(results)}
