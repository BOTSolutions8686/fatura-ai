"""
3-tier item matching: Exact Code → Fuzzy Name → AI Disambiguation.
مطابقة الأصناف بثلاث مراحل مع دعم التعلم
"""
import frappe
from frappe import _
from frappe.utils import today
from typing import List, Dict, Any, Optional


FUZZY_CUTOFF = 60  # rapidfuzz 0-100 scale
_items_cache: list | None = None  # T020: module-level cache for batch matching


def clear_item_cache() -> None:
    """Reset the item list cache (call between requests or after item updates)."""
    global _items_cache
    _items_cache = None


def match_items(
    extracted_items: List[Dict],
    supplier: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Match each extracted item and return list with match metadata."""
    global _items_cache
    _items_cache = frappe.get_all('Item', filters={'disabled': 0}, fields=['name', 'item_name'])
    try:
        return [_match_single(item, supplier) for item in extracted_items]
    finally:
        clear_item_cache()


def _match_single(item: Dict, supplier: Optional[str]) -> Dict[str, Any]:
    """Run 3 tiers for one item; return enriched item dict."""
    text = item.get("description") or item.get("item_name") or ""

    result = (
        _match_by_learned_mapping(text, supplier)
        or _match_by_item_code(text)
        or _match_by_fuzzy_name(text)
        or _match_by_ai_placeholder(text)
    )
    return {**item, **result}


def _match_by_learned_mapping(text: str, supplier: Optional[str]) -> Optional[Dict]:
    """Check InvoiceAIItemMap first (highest confidence — user-validated)."""
    from fatura_ai.fatura_ai.doctype.invoice_ai_item_map.invoice_ai_item_map import InvoiceAIItemMap
    mapping = InvoiceAIItemMap.find_mapping(text, supplier)
    if not mapping:
        return None
    if not frappe.db.exists("Item", mapping.matched_item):
        return None
    return {
        "matched_item": mapping.matched_item,
        "method": "Learned",
        "confidence": 1.0,
        "times_used": mapping.times_used or 0,
    }


def _match_by_item_code(text: str) -> Optional[Dict]:
    """Tier 1 — exact match on item_code."""
    if frappe.db.exists("Item", text):
        return {"matched_item": text, "method": "Exact Code", "confidence": 1.0}
    return None


def _match_by_fuzzy_name(text: str) -> Optional[Dict]:
    """Tier 2 — rapidfuzz WRatio on item_name + item_code."""
    from rapidfuzz import process, fuzz

    items = _items_cache if _items_cache is not None else frappe.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name"])
    choices = {i["name"]: i["item_name"] for i in items}
    best = process.extractOne(text, choices, scorer=fuzz.WRatio, score_cutoff=FUZZY_CUTOFF)
    if not best:
        return None
    _name, score, key = best
    return {"matched_item": key, "method": "Fuzzy Name", "confidence": round(score / 100, 3)}


def _match_by_ai_placeholder(text: str) -> Dict:
    """Tier 3 — placeholder for AI disambiguation (implemented in T006)."""
    # TODO (T006): call AI to suggest top-N items
    return {"matched_item": None, "method": "Unmatched", "confidence": 0.0}


def persist_mappings(confirmed_items: List[Dict], supplier: Optional[str] = None):
    """Save user-confirmed item mappings to InvoiceAIItemMap for future learning."""
    for item in confirmed_items:
        text = item.get("description") or item.get("item_name") or ""
        matched = item.get("matched_item")
        if not text or not matched:
            continue
        _upsert_mapping(text, matched, supplier, item.get("confidence", 0.9))


def _upsert_mapping(text: str, item_code: str, supplier: Optional[str], confidence: float):
    """Insert or increment usage on an existing mapping."""
    filters = {"original_text": text, "matched_item": item_code}
    if supplier:
        filters["supplier"] = supplier
    existing = frappe.db.get_value("Invoice AI Item Map", filters, "name")
    if existing:
        doc = frappe.get_doc("Invoice AI Item Map", existing)
        doc.record_usage()
    else:
        mapping = frappe.get_doc({
            "doctype": "Invoice AI Item Map",
            "original_text": text,
            "matched_item": item_code,
            "supplier": supplier,
            "confidence_score": confidence,
            "times_used": 1,
            "last_used": today(),
        })
        mapping.flags.ignore_links = True
        mapping.insert(ignore_permissions=True)
