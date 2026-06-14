"""
3-tier supplier matching: Exact VAT → Fuzzy Name → AI Disambiguation.
مطابقة المورد بثلاث مراحل
"""
import frappe
from frappe import _
from typing import Dict, Any, Optional


CONFIDENCE_EXACT = 1.0
CONFIDENCE_FUZZY_MIN = 0.6  # below this we escalate to AI tier


def find_supplier(
    vat_number: Optional[str] = None,
    supplier_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the 3-tier matching pipeline and return a match dict.
    Keys: supplier, method, confidence, candidates (for disambiguation UI)
    """
    if vat_number:
        result = _match_by_vat(vat_number)
        if result:
            return result

    if supplier_name:
        result = _match_by_fuzzy_name(supplier_name)
        if result:
            return result

    return _match_by_ai(supplier_name, vat_number)


def _match_by_vat(vat_number: str) -> Optional[Dict[str, Any]]:
    """Tier 1 — exact match on tax_id field."""
    supplier = frappe.db.get_value("Supplier", {"tax_id": vat_number}, "name")
    if not supplier:
        return None
    return {"supplier": supplier, "method": "Exact VAT", "confidence": CONFIDENCE_EXACT}


def _match_by_fuzzy_name(supplier_name: str) -> Optional[Dict[str, Any]]:
    """Tier 2 — rapidfuzz WRatio on all supplier names."""
    from rapidfuzz import process, fuzz

    suppliers = frappe.db.get_all("Supplier", fields=["name", "supplier_name"])
    if not suppliers:
        return None

    choices = {s["name"]: s["supplier_name"] for s in suppliers}
    best = process.extractOne(
        supplier_name,
        choices,
        scorer=fuzz.WRatio,
        score_cutoff=int(CONFIDENCE_FUZZY_MIN * 100),
    )
    if not best:
        return None

    name, score, key = best
    return {
        "supplier": key,
        "method": "Fuzzy Name",
        "confidence": round(score / 100, 3),
    }


def _match_by_ai(supplier_name: Optional[str], vat_number: Optional[str]) -> Dict[str, Any]:
    """
    Tier 3 — return top candidates for user disambiguation.
    Full AI call implemented in T005.
    """
    # TODO (T005): call AI disambiguation endpoint
    candidates = _get_top_candidates(supplier_name)
    return {
        "supplier": None,
        "method": "AI Disambiguation",
        "confidence": 0.0,
        "candidates": candidates,
    }


def _get_top_candidates(query: Optional[str], limit: int = 5):
    """Return top supplier name candidates for the disambiguation dialog."""
    if not query:
        return []
    from rapidfuzz import process, fuzz
    suppliers = frappe.db.get_all("Supplier", fields=["name", "supplier_name"])
    choices = {s["name"]: s["supplier_name"] for s in suppliers}
    results = process.extract(query, choices, scorer=fuzz.WRatio, limit=limit)
    return [{"supplier": key, "name": name, "score": round(score / 100, 3)} for name, score, key in results]
