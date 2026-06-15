"""
3-tier supplier matching: Exact VAT → Fuzzy Name → AI Disambiguation.
مطابقة المورد بثلاث مراحل
"""
import frappe
from frappe import _
from typing import Dict, Any, Optional
import difflib


CONFIDENCE_EXACT = 1.0
CONFIDENCE_FUZZY_MIN = 0.85  # threshold for difflib


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
        "tier": 1,
    }


def match_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Tier 2 — fuzzy name matching using difflib.
    المستوى الثاني — مطابقة تقريبية لاسم المورد باستخدام difflib
    """
    all_suppliers = frappe.get_all("Supplier", fields=["name", "supplier_name"])
    if not all_suppliers:
        return None

    names = [s["supplier_name"] or s["name"] for s in all_suppliers]
    matches = difflib.get_close_matches(name, names, n=1, cutoff=CONFIDENCE_FUZZY_MIN)
    if not matches:
        return None

    best_name = matches[0]
    for s in all_suppliers:
        candidate = s["supplier_name"] or s["name"]
        if candidate == best_name:
            # compute actual difflib ratio for confidence
            ratio = difflib.SequenceMatcher(None, name, best_name).ratio()
            return {
                "supplier": s["name"],
                "supplier_name": s["supplier_name"],
                "confidence": ratio,
                "tier": 2,
            }
    return None


def match_supplier(tax_id: str, name: str) -> Dict[str, Any]:
    """
    Run the 3-tier matching pipeline.
    تشغيل سلسلة المطابقة ثلاثية المستويات
    """
    # Tier 1 — exact tax_id (skip if tax_id is None or empty)
    if tax_id:
        result = match_by_tax_id(tax_id)
        if result:
            return result

    # Tier 2 — fuzzy name
    result = match_by_name(name)
    if result:
        return result

    # Tier 3 — AI disambiguation (placeholder)
    return {
        "supplier": None,
        "supplier_name": None,
        "confidence": 0.0,
        "tier": 3,
    }
