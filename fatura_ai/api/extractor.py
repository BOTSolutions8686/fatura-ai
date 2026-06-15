"""
Extraction pipeline orchestrator.
Delegates to the active AI provider; does not contain provider logic.
منسق خط أنابيب الاستخراج
"""
import frappe
from frappe import _
from fatura_ai.helpers.ai_extraction import get_active_provider


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"}
MAX_FILE_SIZE_MB = 20


def validate_file(file_url):
    """Raise ValidationError if file type or size is unsupported."""
    import os
    ext = os.path.splitext(file_url)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        frappe.throw(
            _("Unsupported file type: {0}. Allowed: PDF, PNG, JPG, WEBP").format(ext)
        )
    file_doc = frappe.db.get_value("File", {"file_url": file_url}, ["file_size"], as_dict=True)
    if file_doc and file_doc.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        frappe.throw(_("File exceeds {0} MB limit").format(MAX_FILE_SIZE_MB))


def build_doctype_payload(log, extracted, confirmed_items):
    """
    Map extracted + confirmed data to ERPNext field names.
    Returns a dict the form_populator writes to the open document.
    """
    return {
        "supplier": log.matched_supplier,
        "bill_no": extracted.get("invoice_number"),
        "bill_date": extracted.get("invoice_date"),
        "due_date": extracted.get("due_date"),
        "items": [_map_item(i) for i in confirmed_items if i.get("matched_item")],
        "taxes_and_charges": _get_default_tax_template(log.matched_supplier),
    }


def _map_item(confirmed_item):
    # Normalise rate — DeepSeek may return unit_price, price, unit_rate, etc.
    rate = (
        confirmed_item.get("rate")
        or confirmed_item.get("unit_price")
        or confirmed_item.get("price")
        or confirmed_item.get("unit_rate")
        or 0
    )
    return {
        "item_code": confirmed_item["matched_item"],
        "qty": confirmed_item.get("qty", 1),
        "rate": float(rate),
        "uom": confirmed_item.get("uom") or confirmed_item.get("unit") or "Nos",
        "description": confirmed_item.get("description", ""),
    }


def _get_default_tax_template(supplier):
    """Return the default Purchase Taxes and Charges template for the company, or None."""
    try:
        company = (
            frappe.db.get_value("Supplier", supplier, "default_company")
            or frappe.defaults.get_user_default("Company")
            or (frappe.get_all("Company", limit=1) or [{}])[0].get("name")
        )
        if not company:
            return None
        return frappe.db.get_value(
            "Purchase Taxes and Charges Template",
            {"company": company, "is_default": 1},
            "name",
        )
    except Exception:
        return None
