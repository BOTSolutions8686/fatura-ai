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


def extract_zatca_qr(file_path: str) -> Optional[dict]:
    """
    Scan a PDF or image file for a ZATCA TLV QR code.
    Returns decoded fields dict, or None if no QR found or libs unavailable.
    """
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
    except ImportError:
        frappe.log_error(
            "pyzbar not installed. Run: pip install pyzbar && apt-get install libzbar0",
            "Fatura AI QR",
        )
        return None

    images = _file_to_images(file_path)
    if not images:
        return None

    for img in images:
        result = _scan_image(img, pyzbar_decode)
        if result:
            return result
    return None


def _file_to_images(file_path: str):
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if ext in ("png", "jpg", "jpeg", "webp", "tiff", "tif"):
        try:
            from PIL import Image
            return [Image.open(file_path)]
        except Exception as exc:
            frappe.logger().warning("Fatura AI: image open failed: %s", str(exc))
            return None
    try:
        from pdf2image import convert_from_path
        return convert_from_path(file_path, dpi=200, first_page=1, last_page=3)
    except ImportError:
        frappe.logger().warning("Fatura AI: pdf2image not installed — ZATCA QR skipped for PDFs")
    except Exception as exc:
        frappe.logger().warning("Fatura AI: pdf2image conversion failed: %s", str(exc))
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
