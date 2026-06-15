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
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    _assert_doctype(source_doctype)
    from fatura_ai.api.extractor import validate_file
    validate_file(file_url)

    # source_docname may be a temp name (e.g. "new-purchase-invoice-xxx") when
    # the user opens the wizard on an unsaved form — skip link validation so
    # Frappe doesn't reject it.
    real_docname = source_docname if source_docname and not source_docname.startswith("new-") else None

    log = frappe.get_doc({
        "doctype": "Fatura Import Log",
        "status": "Draft",
        "source_doctype": source_doctype,
        "source_docname": real_docname,
        "file_url": file_url,
    })
    log.flags.ignore_links = True
    log.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"log_name": log.name, "status": "ok"}


# ── Step 1: AI Extraction ───────────────────────────────────────────────────

@frappe.whitelist()
def run_ai_extraction(log_name):
    """Fetch log, run AI extraction, update log fields, return log as dict."""
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    log = frappe.get_doc("Fatura Import Log", log_name)

    # Get attached file path
    file_doc = frappe.get_doc("File", {"file_url": log.file_url})
    file_path = file_doc.get_full_path()

    # Mark as Processing before calling AI
    log.status = "Processing"
    log.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        from fatura_ai.helpers.ai_extraction import extract_invoice_data
        result = extract_invoice_data(log.file_url)
    except Exception as e:
        log.mark_failed(str(e))
        log.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.throw(
            _("AI extraction failed: {0}").format(str(e)),
            frappe.ValidationError,
        )

    # Update log fields
    log.extracted_json = frappe.as_json(result)
    log.provider_used = result.get("provider")
    log.status = "Processing"
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return log.as_dict()


# ── Step 2: Supplier Matching ───────────────────────────────────────────────

@frappe.whitelist()
def match_supplier(log_name, vendor_name=None, tax_id=None):
    """Run 3-tier supplier matching using vendor_name and tax_id."""
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    log = frappe.get_doc("Fatura Import Log", log_name)

    # Read from extracted log data if not passed explicitly
    extracted = frappe.parse_json(log.extracted_json or "{}")
    if not vendor_name:
        vendor_name = (
            extracted.get("vendor_name")
            or extracted.get("seller_name")
            or extracted.get("supplier_name")
        )
    if not tax_id:
        tax_id = (
            extracted.get("tax_id")
            or extracted.get("vat_number")
            or extracted.get("seller_vat")
            or extracted.get("seller_vat_number")
        )

    if not vendor_name and not tax_id:
        frappe.throw(
            _("Cannot match supplier: no name or VAT in extracted data")
        )

    from fatura_ai.helpers.supplier_matching import match_supplier
    match = match_supplier(tax_id=tax_id, name=vendor_name)

    log.supplier_match_method = match.get("method")
    log.matched_supplier = match.get("supplier")
    log.supplier_confidence = match.get("confidence", 0.0)
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return match


@frappe.whitelist()
def confirm_supplier(log_name, supplier):
    """User manually confirmed or overrode the matched supplier."""
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    log = frappe.get_doc("Fatura Import Log", log_name)
    if not frappe.db.exists("Supplier", supplier):
        frappe.throw(_("Supplier {0} not found").format(supplier))
    _update_log_supplier(log_name, supplier, "Manual")
    return {"status": "ok", "supplier": supplier}


@frappe.whitelist()
def create_supplier(log_name, supplier_name, tax_id=None):
    """Auto-create a minimal Supplier record from extracted invoice data."""
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    if not supplier_name:
        frappe.throw(_("Supplier name is required"))

    # Return existing supplier if already in system
    existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
    if not existing and tax_id:
        existing = frappe.db.get_value("Supplier", {"tax_id": tax_id}, "name")
    if existing:
        _update_log_supplier(log_name, existing, "Auto-Created")
        return {"supplier": existing, "status": "existing"}

    doc = frappe.get_doc({
        "doctype": "Supplier",
        "supplier_name": supplier_name,
        "supplier_group": "All Supplier Groups",
        "supplier_type": "Company",
    })
    if tax_id:
        doc.tax_id = tax_id
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    _update_log_supplier(log_name, doc.name, "Auto-Created")
    return {"supplier": doc.name, "status": "created"}


def _update_log_supplier(log_name, supplier, method):
    log = frappe.get_doc("Fatura Import Log", log_name)
    log.matched_supplier = supplier
    log.supplier_match_method = method
    log.save(ignore_permissions=True)
    frappe.db.commit()


# ── Step 3: Item Matching ───────────────────────────────────────────────────

@frappe.whitelist()
def match_items(log_name, line_items_json=None):
    """Run 3-tier item matching on all extracted line items."""
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    log = frappe.get_doc("Fatura Import Log", log_name)

    # Use passed-in items if provided (user may have edited them)
    if line_items_json:
        items = frappe.parse_json(line_items_json)
    else:
        extracted = frappe.parse_json(log.extracted_json or "{}")
        items = extracted.get("line_items", [])

    from fatura_ai.helpers.item_matching import match_items as _match
    matched = _match(items, supplier=log.matched_supplier)

    total = len(items)
    matched_count = sum(1 for i in matched if i.get("matched_item"))
    partial_count = sum(
        1 for i in matched if i.get("confidence", 0) < 1.0 and i.get("matched_item")
    )
    unmatched_count = total - matched_count

    log.items_count = total
    log.items_matched = matched_count
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "items": matched,
        "summary": {
            "total": total,
            "matched": matched_count,
            "partial": partial_count,
            "unmatched": unmatched_count,
        },
    }


@frappe.whitelist()
def confirm_items(log_name, confirmed_items):
    """User confirmed or corrected item mappings; persist learned mappings."""
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    from fatura_ai.helpers.item_matching import persist_mappings
    items = frappe.parse_json(confirmed_items) if isinstance(confirmed_items, str) else confirmed_items
    log = frappe.get_doc("Fatura Import Log", log_name)
    persist_mappings(items, supplier=log.matched_supplier)
    # Store confirmed items on the log so confirm_import can read them back
    extracted = frappe.parse_json(log.extracted_json or "{}")
    extracted["confirmed_items"] = items
    log.extracted_json = frappe.as_json(extracted)
    log.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "saved": len(items)}


# ── Step 4: Review Details ──────────────────────────────────────────────────

@frappe.whitelist()
def get_review_summary(log_name):
    """Return everything the Review step needs to render its summary card."""
    frappe.has_permission("Fatura Import Log", ptype="read", throw=True)
    log = frappe.get_doc("Fatura Import Log", log_name)
    extracted = frappe.parse_json(log.extracted_json or "{}")
    return {
        "log": log.as_dict(),
        "extracted": extracted,
    }


# ── Step 5: Create Document ─────────────────────────────────────────────────

@frappe.whitelist()
def confirm_import(log_name):
    """
    Create a Draft Purchase Invoice / PO from the extracted + confirmed data.
    NEVER submits the document — only creates a Draft.
    لا يُقدَّم المستند أبداً — يُنشئ مسودة فقط
    """
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    log = frappe.get_doc("Fatura Import Log", log_name)

    # Guard against double-import
    if log.status == "Success":
        frappe.throw(
            _("This import has already been completed.")
        )

    extracted = frappe.parse_json(log.extracted_json or "{}")
    confirmed_items = extracted.get("confirmed_items") or extracted.get("line_items", [])

    from fatura_ai.api.extractor import build_doctype_payload
    payload = build_doctype_payload(log, extracted, confirmed_items)

    # Create the document
    doc = frappe.new_doc(log.source_doctype or "Purchase Invoice")
    doc.supplier = payload.get("supplier")
    doc.bill_no = payload.get("bill_no")
    doc.bill_date = payload.get("bill_date")
    doc.due_date = payload.get("due_date")

    for item_data in payload.get("items", []):
        item_code = item_data.get("item_code")
        if not item_code:
            continue
        # Auto-create item if it doesn't exist in ERPNext
        if not frappe.db.exists("Item", item_code):
            new_item = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": (item_data.get("description") or item_code)[:140],
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "is_purchase_item": 1,
            })
            new_item.insert(ignore_permissions=True)
            frappe.db.commit()
        row = doc.append("items", {})
        row.item_code = item_code
        row.qty = item_data.get("qty", 1)
        row.rate = item_data.get("rate", 0)
        row.description = item_data.get("description")

    # Apply default tax template — ERPNext populates account rows automatically
    taxes_and_charges = payload.get("taxes_and_charges")
    if taxes_and_charges:
        doc.taxes_and_charges = taxes_and_charges

        doc.insert(ignore_permissions=True)
    frappe.db.commit()

    from fatura_ai.helpers.zatca_mapper import map_zatca_fields
    if not map_zatca_fields(log, doc):
        frappe.msgprint(
            _("ksa_compliance is not installed — ZATCA fields were skipped."),
            indicator="orange",
            alert=True,
        )
    frappe.db.commit()

    log.status = "Success"
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "doctype": doc.doctype,
        "docname": doc.name,
        "status": doc.docstatus,
        "url": frappe.utils.get_url_to_form(doc.doctype, doc.name),
    }

# ── Helpers ─────────────────────────────────────────────────────────────────

def _assert_doctype(source_doctype):
    allowed = {"Purchase Invoice", "Purchase Order"}
    if source_doctype not in allowed:
        frappe.throw(_("Invalid source doctype: {0}").format(source_doctype))
