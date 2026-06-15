"""
ZATCA field mapper — populates ksa_compliance custom fields on Purchase Invoice.
يعبئ حقول ZATCA على فاتورة الشراء إذا كان ksa_compliance مثبتاً.
"""
import frappe
from frappe import _
from fatura_ai.helpers.compatibility import is_ksa_compliance_installed, get_ksa_field


def map_zatca_fields(log_doc, pi_doc):
    """
    Copy ZATCA fields from FaturaImportLog onto a Purchase Invoice.
    Returns True when fields were written, False when ksa_compliance is absent.
    """
    if not is_ksa_compliance_installed():
        return False

    extracted = frappe.parse_json(log_doc.extracted_json or "{}")

    _set_field(pi_doc, "custom_vat_registration_number",
               extracted.get("tax_id") or extracted.get("vat_number"))

    _set_field(pi_doc, "custom_zatca_invoice_reference",
               extracted.get("invoice_uuid") or extracted.get("invoice_number"))

    _set_field(pi_doc, "custom_supply_date",
               extracted.get("supply_date") or extracted.get("invoice_date"))

    _set_field(pi_doc, "custom_vat_amount",
               extracted.get("vat_amount"))

    pi_doc.save(ignore_permissions=True)
    return True


def _set_field(doc, fieldname, value):
    """Set a guarded ksa_compliance field; skip silently if absent in this version."""
    if value is None:
        return
    if get_ksa_field(doc.doctype, fieldname):
        setattr(doc, fieldname, value)
