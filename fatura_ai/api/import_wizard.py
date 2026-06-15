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

    log.status = "Draft"
    log.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        from fatura_ai.helpers.ai_extraction import extract_invoice_data
        result = extract_invoice_data(log.file_url)
    except Exception as e:
        log.mark_failed(str(e))
        frappe.db.commit()
        frappe.throw(
            _("AI extraction failed: {0}").format(str(e)),
            frappe.ValidationError,
        )

    # T039 — merge ZATCA QR data (ground truth) over AI result
    result = _merge_qr_data(result, file_path, log.file_url)

    # Detect image-based PDF so the wizard can warn the user
    if log.file_url and log.file_url.lower().endswith(".pdf"):
        try:
            from fatura_ai.helpers.pdf_extractor import detect_pdf_type
            result["pdf_type"] = detect_pdf_type(file_path)
        except Exception:
            result["pdf_type"] = "unknown"

    if result.get("line_items"):
        result["line_items"] = _normalize_line_items(result["line_items"])

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
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    try:
        log = frappe.get_doc("Fatura Import Log", log_name)

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
            return {"status": "error", "message": _("Cannot match supplier: no name or VAT in extracted data")}

        vat_source = extracted.get("vat_source", "AI")
        name_source = extracted.get("name_source", "AI")
        frappe.logger().info(
            "Fatura AI supplier match: tax_id=%s (from %s) name=%s (from %s)",
            tax_id, vat_source, vendor_name, name_source,
        )

        from fatura_ai.helpers.supplier_matching import match_supplier as _do_match
        match = _do_match(tax_id=tax_id, name=vendor_name)

        log.supplier_match_method = match.get("method")
        log.matched_supplier = match.get("supplier")
        log.supplier_confidence = match.get("confidence", 0.0)
        log.save(ignore_permissions=True)
        frappe.db.commit()

        return match
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Fatura AI match_supplier")
        return {"status": "error", "message": frappe.get_traceback()}


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
        _update_log_supplier(log_name, existing, "Manual")
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

    _update_log_supplier(log_name, doc.name, "Manual")
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

    # Validate items
    warnings = []
    for i, item in enumerate(items):
        if not item.get("item_code") and not item.get("matched_item"):
            warnings.append(
                _("Row {0}: no item code selected").format(i + 1)
            )
        qty = float(item.get("qty", 1) or 1)
        rate = float(item.get("rate", 0) or 0)
        if qty <= 0:
            warnings.append(
                _("Row {0}: quantity must be greater than zero").format(i + 1)
            )
        if rate < 0:
            warnings.append(
                _("Row {0}: rate cannot be negative").format(i + 1)
            )

    persist_mappings(items, supplier=log.matched_supplier)
    extracted = frappe.parse_json(log.extracted_json or "{}")
    extracted["confirmed_items"] = items
    log.extracted_json = frappe.as_json(extracted)
    log.status = "Confirmed"
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "ok",
        "saved": len(items),
        "warnings": warnings,
    }


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
def confirm_import(log_name, force=False):
    """
    Create a Draft Purchase Invoice / PO from the extracted + confirmed data.
    NEVER submits the document — only creates a Draft.
    لا يُقدَّم المستند أبداً — يُنشئ مسودة فقط
    """
    frappe.has_permission("Fatura Import Log", ptype="write", throw=True)
    log = frappe.get_doc("Fatura Import Log", log_name)

    if log.status == "Success":
        frappe.throw(_("This import has already been completed."))

    extracted = frappe.parse_json(log.extracted_json or "{}")
    confirmed_items = extracted.get("confirmed_items") or extracted.get("line_items", [])

    # T030 — duplicate detection (skipped when user explicitly forces)
    if not frappe.utils.cint(force):
        dup = _check_duplicate(log, extracted)
        if dup:
            return dup

    # Auto-create ERPNext Items for rows the user flagged with the checkbox
    for item in confirmed_items:
        if item.get("auto_create") and not item.get("matched_item"):
            item_label = item.get("item_name") or item.get("description") or "Unknown Item"
            new_code = _auto_create_item(item_label, item)
            item["matched_item"] = new_code
            item["item_code"] = new_code

    from fatura_ai.api.extractor import build_doctype_payload
    payload = build_doctype_payload(log, extracted, confirmed_items)
    company = _get_company(log)
    doc = _build_doc(log, payload, extracted, company)

    from fatura_ai.helpers.zatca_mapper import map_zatca_fields
    if not map_zatca_fields(log, doc):
        frappe.msgprint(
            _("ksa_compliance is not installed — ZATCA fields were skipped."),
            indicator="orange",
            alert=True,
        )
    frappe.db.commit()

    log.status = "Imported"
    log.linked_pi = doc.name if doc.doctype == "Purchase Invoice" else None
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "doctype": doc.doctype,
        "docname": doc.name,
        "status": doc.docstatus,
        "url": frappe.utils.get_url_to_form(doc.doctype, doc.name),
        "warnings": _run_sanity_checks(extracted, payload.get("items", [])),
    }


# ── confirm_import helpers ───────────────────────────────────────────────────

def _check_duplicate(log, extracted):
    """T030 — return duplicate info dict or None if no duplicate."""
    bill_no = extracted.get("invoice_number")
    supplier = log.matched_supplier
    doctype = log.source_doctype or "Purchase Invoice"
    if not bill_no or not supplier or doctype != "Purchase Invoice":
        return None
    existing = frappe.db.get_value(
        "Purchase Invoice",
        {"bill_no": bill_no, "supplier": supplier, "docstatus": ["!=", 2]},
        "name",
    )
    return {"status": "duplicate", "existing_pi": existing} if existing else None


def _get_company(log):
    return (
        None
        or frappe.defaults.get_user_default("Company")
        or (frappe.get_all("Company", limit=1) or [{}])[0].get("name")
    )


def _build_doc(log, payload, extracted, company):
    """Construct and insert the ERPNext document from the mapped payload."""
    doc = frappe.new_doc(log.source_doctype or "Purchase Invoice")
    doc.supplier = payload.get("supplier")
    doc.bill_no = payload.get("bill_no")
    doc.bill_date = payload.get("bill_date")
    doc.due_date = payload.get("due_date")
    # T031 — currency
    currency = _resolve_currency(extracted, company)
    if currency:
        doc.currency = currency
    # T032 — cost center default
    cost_center = frappe.db.get_value("Company", company, "cost_center") if company else None
    for item_data in payload.get("items", []):
        item_code = item_data.get("item_code")
        if not item_code:
            continue
        if not frappe.db.exists("Item", item_code):
            item_code = _auto_create_item(item_code, item_data)
        row = doc.append("items", {})
        row.item_code = item_code
        row.item_name = item_data.get("item_name") or item_code
        row.qty = item_data.get("qty", 1)
        row.rate = item_data.get("rate", 0)
        row.description = item_data.get("description")
        row.uom = _validate_uom(item_data.get("uom"))  # T033
        if cost_center:
            row.cost_center = cost_center
    if payload.get("taxes_and_charges"):
        doc.taxes_and_charges = payload.get("taxes_and_charges")
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


def _auto_create_item(item_code, item_data):
    """T035 — create Item with cleaned code (no trailing junk, ≤140 chars), Services group."""
    import re
    clean_code = (re.sub(r'[\s./\\:\-]+$', '', item_code.strip()) or item_code.strip())[:140]
    if frappe.db.exists("Item", clean_code):
        return clean_code
    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": clean_code,
        "item_name": (item_data.get("description") or clean_code)[:140],
        "item_group": "Services",
        "stock_uom": "Nos",
        "is_stock_item": 0,
        "is_purchase_item": 1,
    })
    item.insert(ignore_permissions=True)
    frappe.db.commit()
    return clean_code


def _resolve_currency(extracted, company):
    """T031 — validate extracted currency; fall back to company default."""
    currency = (extracted.get("currency") or "").strip().upper()
    if currency and frappe.db.exists("Currency", currency):
        return currency
    if currency:
        frappe.log_error(
            f"Currency '{currency}' not found in ERPNext; using company default",
            "Fatura T031 currency fallback",
        )
    return frappe.db.get_value("Company", company, "default_currency") if company else None


def _validate_uom(uom):
    """T033 — return UOM if it exists in ERPNext, otherwise fall back to Nos."""
    if uom and frappe.db.exists("UOM", uom):
        return uom
    if uom:
        frappe.log_error(f"UOM '{uom}' not found; falling back to Nos", "Fatura T033 UOM fallback")
    return "Nos"


def _run_sanity_checks(extracted, items):
    """T034 — non-blocking sanity checks; return list of warning strings."""
    warnings = []
    subtotal = float(extracted.get("subtotal") or 0)
    vat_amount = float(extracted.get("vat_amount") or extracted.get("tax_amount") or 0)
    total = float(extracted.get("total") or 0)
    if subtotal:
        calc_sub = sum(float(i.get("qty", 1)) * float(i.get("rate", 0)) for i in items)
        if abs(calc_sub - subtotal) >= 1.0:
            warnings.append(
                _("Line items total ({0}) differs from extracted subtotal ({1}) by >1 SAR").format(
                    round(calc_sub, 2), round(subtotal, 2)
                )
            )
    if subtotal and vat_amount and abs(vat_amount - subtotal * 0.15) >= 1.0:
        warnings.append(
            _("VAT amount ({0}) does not match 15% of subtotal ({1})").format(
                round(vat_amount, 2), round(subtotal * 0.15, 2)
            )
        )
    if total and subtotal and abs(total - subtotal - vat_amount) >= 1.0:
        warnings.append(
            _("Invoice total ({0}) does not match subtotal + VAT ({1})").format(
                round(total, 2), round(subtotal + vat_amount, 2)
            )
        )
    return warnings


# ── Helpers ─────────────────────────────────────────────────────────────────

def _normalize_line_items(items: list) -> list:
    """Normalize AI-extracted line items to ERPNext Purchase Invoice field names."""
    result = []
    for item in items:
        raw_name = item.get("item_name") or item.get("name") or item.get("description", "")
        raw_desc = item.get("description") or raw_name

        if "\n" in raw_name:
            parts = raw_name.split("\n", 1)
            item_name = parts[0].strip()
            description = parts[1].strip()
        else:
            item_name = raw_name.strip()
            description = raw_desc.strip()

        rate = (
            item.get("unit_price") or item.get("rate")
            or item.get("price") or item.get("unit_rate") or 0
        )
        qty = float(item.get("qty", 1) or 1)
        rate_f = float(rate or 0)

        result.append({
            "item_name": item_name[:140],
            "description": description,
            "qty": qty,
            "uom": item.get("uom") or item.get("unit") or "Nos",
            "rate": rate_f,
            "amount": float(item.get("amount") or (qty * rate_f)),
            "matched_item": item.get("matched_item"),
            "match_method": item.get("match_method"),
            "match_confidence": item.get("match_confidence"),
            "_original_text": raw_name,
        })
    return result


def _assert_doctype(source_doctype):
    allowed = {"Purchase Invoice", "Purchase Order"}
    if source_doctype not in allowed:
        frappe.throw(_("Invalid source doctype: {0}").format(source_doctype))


def _merge_qr_data(result: dict, file_path: str, file_url: str) -> dict:
    """T039 — overlay ZATCA QR ground-truth fields onto AI extraction result."""
    if not file_url or not file_url.lower().endswith(".pdf"):
        return result
    try:
        from fatura_ai.helpers.zatca_qr import extract_zatca_qr
        qr_data = extract_zatca_qr(file_path)
        if qr_data:
            for key in ("vat_number", "total", "vat_amount", "seller_name", "invoice_date"):
                if qr_data.get(key):
                    result[key] = qr_data[key]
            result["qr_data_found"] = True
            result["vat_source"] = "QR" if qr_data.get("vat_number") else "AI"
            result["name_source"] = "QR" if qr_data.get("seller_name") else "AI"
            frappe.logger().info(
                "Fatura AI QR merge: vat_source=%s name_source=%s",
                result["vat_source"], result["name_source"],
            )
        else:
            result["qr_data_found"] = False
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Fatura AI ZATCA QR")
    return result
