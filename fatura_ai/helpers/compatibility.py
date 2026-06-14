"""
App install checks — guards for optional dependencies like ksa_compliance.
فحص تثبيت التطبيقات الاختيارية
"""
import frappe

_ksa_cache = None  # module-level cache; reset on bench restart


def is_ksa_compliance_installed():
    """Return True only if lavaloon-eg/ksa_compliance DocType is present."""
    global _ksa_cache
    if _ksa_cache is None:
        _ksa_cache = frappe.db.exists("DocType", "Sales Invoice Additional Fields") == "Sales Invoice Additional Fields"
    return _ksa_cache


def get_ksa_field(doctype, fieldname):
    """
    Safe accessor for ksa_compliance custom fields.
    Returns None (not an error) if the app is not installed.
    """
    if not is_ksa_compliance_installed():
        return None
    meta = frappe.get_meta(doctype)
    if not meta.has_field(fieldname):
        return None
    return fieldname
