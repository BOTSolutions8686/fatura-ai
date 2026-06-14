"""
Wizard API endpoints — one per wizard step.
All endpoints are @frappe.whitelist() and return JSON-serialisable dicts.
تحكم كامل في خطوات معالج الاستيراد
"""
import frappe
from frappe import _


# ── Step 0: Upload ──────────────────────────────────────────────────────────

@frappe.whitelist()
def upload_invoice(file_url, source_doctype, source_docname):
    """Validate upload and create a Draft import log."""
    _assert_doctype(source_doctype)
    from fatura_ai.api.extractor import validate_file
    validate_file(file_url)

    log = frappe.get_doc({
        "doctype": "Fatura Import Log",
        "status": "Draft",
        "source_doctype": source_doctype,
        "source_docname": source_docname,
        "file_url": file_url,
    })
    log.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"log_name": log.name, "status": "ok"}


# ── Step 1: AI Extraction ───────────────────────────────────────────────────

@frappe.whitelist()
def run_extraction(log_name):
    """Fetch log, run AI extraction, update log fields, return log as dict."""
    log = frappe.get_doc("Fatura Import Log", log_name)
    if not log:
        frappe.throw(_("Import log not found: {0}").format(log_name))

    # Get attached file path
    file_doc = frappe.get_doc("File", {"file_url": log.file_url})
    if not file_doc:
        frappe.throw(_("Attached file not found"))
    file_path = file_doc.get_full_path()
    if not file_path:
        frappe.throw(_("Could not resolve file path"))

    # Run AI extraction
    from fatura_ai.helpers.ai_extraction import extract_invoice
    result = extract_invoice(file_path)

    # Update log fields
    log.vendor_name = result.get("vendor_name")
    log.invoice_number = result.get("invoice_number")
    log.invoice_date = result.get("invoice_date")
    log.line_items = frappe.as_json(result.get("line_items", []))
    log.subtotal = result.get("subtotal")
    log.vat_amount = result.get("vat_amount")
    log.total = result.get("total")
    log.extracted_json = frappe.as_json(result)
    log.provider_used = result.get("provider")
    log.status = "Extracted"
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return log.as_dict()


# ── Step 2: Supplier Matching ───────────────────────────────────────────────

@frappe.whitelist()
def match_supplier(log_name, vendor_name=None, tax_id=None):
    """Run 3-tier supplier matching using vendor_name and tax_id."""
    log = frappe.get_doc("Fatura Import Log", log_name)
    if not log:
        frappe.throw(_("Import log not found: {0}").format(log_name))

    from fatura_ai.helpers.supplier_matching import find_supplier_match
    match = find_supplier_match(
        vendor_name=vendor_name,
        tax_id=tax_id,
    )

    log.supplier_match_method = match.get("method")
    log.matched_supplier = match.get("supplier")
    log.supplier_confidence = match.get("confidence", 0.0)
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return match


@frappe.whitelist()
def confirm_supplier(log_name, supplier):
    """User manually confirmed or overrode the matched supplier."""
    log = frappe.get_doc("Fatura Import Log", log_name)
    if not frappe.db.exists("Supplier", supplier):
        frappe.throw(_("Supplier {0} not found").format(supplier))
    log.matched_supplier = supplier
    log.supplier_match_method = "Manual"
    log.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "supplier": supplier}


# ── Step 3: Item Matching ───────────────────────────────────────────────────

@frappe.whitelist()
def match_items(log_name):
    """Run 3-tier item matching on all extracted line items."""
    log = frappe.get_doc("Fatura Import Log", log_name)
    extracted = frappe.parse_json(log.extracted_json or "{}")
    items = extracted.get("items", [])

    from fatura_ai.helpers.item_matching import match_items as _match
    matched = _match(items, supplier=log.matched_supplier)

    log.items_count = len(items)
    log.items_matched = sum(1 for i in matched if i.get("matched_item"))
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return {"items": matched}


@frappe.whitelist()
def confirm_items(log_name, confirmed_items):
    """User confirmed or corrected item mappings; persist learned mappings."""
    from fatura_ai.helpers.item_matching import persist_mappings
    items = frappe.parse_json(confirmed_items) if isinstance(confirmed_items, str) else confirmed_items
    log = frappe.get_doc("Fatura Import Log", log_name)
    persist_mappings(items, supplier=log.matched_supplier)
    frappe.db.commit()
    return {"status": "ok", "saved": len(items)}


# ── Step 4: Review Details ──────────────────────────────────────────────────

@frappe.whitelist()
def get_review_summary(log_name):
    """Return everything the Review step needs to render its summary card."""
    log = frappe.get_doc("Fatura Import Log", log_name)
    extracted = frappe.parse_json(log.extracted_json or "{}")
    return {
        "log": log.as_dict(),
        "extracted": extracted,
    }


# ── Step 5: Create Document ─────────────────────────────────────────────────

@frappe.whitelist()
def populate_document(log_name, confirmed_items):
    """
    Write extracted + confirmed data into the ERPNext Purchase Invoice / PO.
    NEVER submits the document — only populates fields.
    لا يُقدَّم المستند أبداً — يُعبئ الحقول فقط
    """
    log = frappe.get_doc("Fatura Import Log", log_name)
    extracted = frappe.parse_json(log.extracted_json or "{}")
    items = frappe.parse_json(confirmed_items) if isinstance(confirmed_items, str) else confirmed_items

    from fatura_ai.api.extractor import build_doctype_payload
    payload = build_doctype_payload(log, extracted, items)

    log.status = "Success"
    log.items_matched = len([i for i in items if i.get("matched_item")])
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return payload


# ── Helpers ─────────────────────────────────────────────────────────────────

def _assert_doctype(source_doctype):
    allowed = {"Purchase Invoice", "Purchase Order"}
    if source_doctype not in allowed:
        frappe.throw(_("Invalid source doctype: {0}").format(source_doctype))
