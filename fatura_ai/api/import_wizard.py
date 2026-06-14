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
def run_ai_extraction(log_name):
    """Fetch log, run AI extraction, update log fields, return log as dict."""
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

    if not vendor_name and not tax_id:
        frappe.throw(
            _("Cannot match supplier: no name or VAT in extracted data")
        )

    from fatura_ai.helpers.supplier_matching import find_supplier
    match = find_supplier(
        supplier_name=vendor_name,
        vat_number=tax_id,
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
def match_items(log_name, line_items_json=None):
    """Run 3-tier item matching on all extracted line items."""
    log = frappe.get_doc("Fatura Import Log", log_name)

    # Use passed-in items if provided (user may have edited them)
    if line_items_json:
        items = frappe.parse_json(line_items_json)
    else:
        extracted = frappe.parse_json(log.extracted_json or "{}")
        items = extracted.get("items", [])

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
def confirm_import(log_name):
    """
    Create a Draft Purchase Invoice / PO from the extracted + confirmed data.
    NEVER submits the document — only creates a Draft.
    لا يُقدَّم المستند أبداً — يُنشئ مسودة فقط
    """
    log = frappe.get_doc("Fatura Import Log", log_name)

    # Guard against double-import
    if log.status == "Success":
        frappe.throw(
            _("This import has already been completed. Open {0}.").format(
                log.source_docname
            )
        )

    extracted = frappe.parse_json(log.extracted_json or "{}")

    from fatura_ai.api.extractor import _build_doctype_payload
    payload = _build_doctype_payload(log, extracted)

    # Create the document
    doc = frappe.new_doc("Purchase Invoice")
    doc.supplier = payload.get("supplier")
    doc.bill_no = payload.get("bill_no")
    doc.bill_date = payload.get("bill_date")
    doc.due_date = payload.get("due_date")
    doc.taxes_and_charges = payload.get("taxes_and_charges")
    doc.taxes = payload.get("taxes", [])
    for item_data in payload.get("items", []):
        row = doc.append("items", {})
        row.item_code = item_data.get("item_code")
        row.qty = item_data.get("qty", 1)
        row.rate = item_data.get("rate", 0)
        row.amount = item_data.get("amount", 0)
        row.description = item_data.get("description")
        row.uom = item_data.get("uom")
        row.conversion_factor = item_data.get("conversion_factor", 1)
        row.stock_uom = item_data.get("stock_uom")
        row.stock_qty = item_data.get("stock_qty", 1)
        row.warehouse = item_data.get("warehouse")
        row.expense_account = item_data.get("expense_account")
        row.project = item_data.get("project")
        row.cost_center = item_data.get("cost_center")
        row.schedule_date = item_data.get("schedule_date")
        row.delivery_note = item_data.get("delivery_note")
        row.sales_invoice = item_data.get("sales_invoice")
        row.purchase_order = item_data.get("purchase_order")
        row.purchase_receipt = item_data.get("purchase_receipt")
        row.brand = item_data.get("brand")
        row.manufacturer = item_data.get("manufacturer")
        row.allow_zero_valuation_rate = item_data.get("allow_zero_valuation_rate", 0)
        row.set_warehouse = item_data.get("set_warehouse")
        row.item_tax_template = item_data.get("item_tax_template")
        row.item_group = item_data.get("item_group")
        row.image = item_data.get("image")
        row.page_break = item_data.get("page_break", 0)
        row.weight_per_unit = item_data.get("weight_per_unit")
        row.weight_uom = item_data.get("weight_uom")
        row.total_weight = item_data.get("total_weight")
        row.fixed_asset = item_data.get("fixed_asset", 0)
        row.asset_category = item_data.get("asset_category")
        row.asset_location = item_data.get("asset_location")
        row.asset_depreciation = item_data.get("asset_depreciation")
        row.asset_quantity = item_data.get("asset_quantity", 1)
        row.asset_value = item_data.get("asset_value", 0)
        row.asset_serial_no = item_data.get("asset_serial_no")
        row.asset_batch_no = item_data.get("asset_batch_no")
        row.asset_warehouse = item_data.get("asset_warehouse")
        row.asset_cost_center = item_data.get("asset_cost_center")
        row.asset_project = item_data.get("asset_project")
        row.asset_department = item_data.get("asset_department")
        row.asset_employee = item_data.get("asset_employee")
        row.asset_customer = item_data.get("asset_customer")
        row.asset_supplier = item_data.get("asset_supplier")
        row.asset_manufacturer = item_data.get("asset_manufacturer")
        row.asset_manufacturer_part_no = item_data.get("asset_manufacturer_part_no")

    doc.insert(ignore_permissions=True)
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
