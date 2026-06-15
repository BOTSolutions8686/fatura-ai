"""
ZATCA TLV QR code extractor for Saudi e-invoices.
Decodes the embedded QR per ZATCA Phase 2 specification.
استخراج رمز QR من الفواتير الإلكترونية السعودية وفق متطلبات هيئة الزكاة والضريبة
"""
import base64
import frappe
from typing import Optional


_TLV_TAGS = {
    1: "seller_name",
    2: "vat_number",
    3: "invoice_date",
    4: "total",
    5: "vat_amount",
}


def extract_zatca_qr(pdf_path: str) -> Optional[dict]:
    """
    Scan up to the first 3 pages of a PDF for a ZATCA TLV QR code.
    Returns decoded fields dict, or None if no QR found or libs unavailable.
    """
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        from pdf2image import convert_from_path
    except ImportError:
        frappe.logger().warning("Fatura AI: pyzbar/pdf2image not installed — ZATCA QR skipped")
        return None

    try:
        images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=3)
    except Exception as exc:
        frappe.logger().warning("Fatura AI: pdf2image conversion failed: %s", str(exc))
        return None

    for img in images:
        result = _scan_image(img, pyzbar_decode)
        if result:
            return result
    return None


def _scan_image(img, pyzbar_decode) -> Optional[dict]:
    """Find and decode the first ZATCA QR code in a PIL image."""
    decoded_objs = pyzbar_decode(img)
    for obj in decoded_objs:
        if obj.type != "QRCODE":
            continue
        parsed = _try_tlv(obj.data)
        if parsed:
            return parsed
        parsed = _try_base64_tlv(obj.data)
        if parsed:
            return parsed
    return None


def _try_base64_tlv(raw: bytes) -> Optional[dict]:
    """Attempt base64-decode then TLV parse (ZATCA Phase 2 encoding)."""
    try:
        tlv_bytes = base64.b64decode(raw)
        return _decode_tlv(tlv_bytes)
    except Exception:
        return None


def _try_tlv(raw: bytes) -> Optional[dict]:
    """Attempt direct TLV parse on raw bytes."""
    try:
        return _decode_tlv(raw)
    except Exception:
        return None


def _decode_tlv(data: bytes) -> Optional[dict]:
    """
    Parse ZATCA simple TLV: [tag 1B][length 1B][value N bytes] repeated.
    Returns None if no known tags were found.
    """
    result = {}
    i = 0
    while i + 2 <= len(data):
        tag = data[i]
        length = data[i + 1]
        i += 2
        if i + length > len(data):
            break
        value_bytes = data[i: i + length]
        i += length
        if tag in _TLV_TAGS:
            result[_TLV_TAGS[tag]] = value_bytes.decode("utf-8", errors="replace")
    return result if result else None
