"""
3-tier supplier matching: Exact VAT → Fuzzy Name → AI Disambiguation.
مطابقة المورد بثلاث مراحل
"""
import re
import frappe
from frappe import _
from typing import Dict, Any, Optional
import difflib


CONFIDENCE_EXACT = 1.0
CONFIDENCE_FUZZY_MIN = 0.60  # lowered from 0.85; case-insensitive normalised comparison


def _normalise(text: str) -> str:
    """Lowercase, replace & with 'and', collapse whitespace."""
    text = text.lower()
    text = re.sub(r"\s*&\s*", " and ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def match_by_tax_id(tax_id: str) -> Optional[Dict[str, Any]]:
    """
    Tier 1 — exact match on tax_id field.
    المستوى الأول — تطابق تام على حقل الرقم الضريبي
    """
    suppliers = frappe.get_all(
        "Supplier",
        filters={"tax_id": tax_id},
        fields=["name", "supplier_name"],
        limit=1,
    )
    if not suppliers:
        return None
    s = suppliers[0]
    return {
        "supplier": s["name"],
        "supplier_name": s["supplier_name"],
        "confidence": 1.0,
        "method": "VAT Match",
    }


def match_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Tier 2 — fuzzy name matching (case-insensitive, normalised).
    المستوى الثاني — مطابقة تقريبية لاسم المورد
    """
    all_suppliers = frappe.get_all("Supplier", fields=["name", "supplier_name"])
    if not all_suppliers:
        return None

    norm_input = _normalise(name)
    # Build map: normalised_name → supplier row
    norm_map = {_normalise(s["supplier_name"] or s["name"]): s for s in all_suppliers}

    matches = difflib.get_close_matches(norm_input, norm_map.keys(), n=1, cutoff=CONFIDENCE_FUZZY_MIN)
    if not matches:
        return None

    best_norm = matches[0]
    s = norm_map[best_norm]
    ratio = difflib.SequenceMatcher(None, norm_input, best_norm).ratio()
    return {
        "supplier": s["name"],
        "supplier_name": s["supplier_name"],
        "confidence": round(ratio, 3),
        "method": "Name Match",
    }


def match_supplier(tax_id: str = None, name: str = None) -> Dict[str, Any]:
    """
    Run the 3-tier matching pipeline.
    تشغيل سلسلة المطابقة ثلاثية المستويات
    """
    # Tier 1 — exact tax_id (skip if tax_id is None or empty)
    if tax_id:
        result = match_by_tax_id(tax_id)
        if result:
            return result

    # Tier 2 — fuzzy name (skip if no name)
    if name:
        result = match_by_name(name)
        if result:
            return result

    # Tier 3 — no match found
    return {
        "supplier": None,
        "supplier_name": None,
        "confidence": 0.0,
        "method": "No Match",
    }
