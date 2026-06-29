"""
PDF type detection — determines whether a PDF has a text layer or is image-only.
"""
import frappe
from typing import Literal
from pdf2image import convert_from_path


def detect_pdf_type(file_path: str) -> Literal["text", "image"]:
    """
    Return "text" if the PDF has extractable text (>=100 chars on first page),
    "image" if it appears to be a scanned/image-only document.
    Falls back to "image" on any error or missing library.
    """
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(file_path, maxpages=1)
        if text and len(text.strip()) >= 100:
            return "text"
    except ImportError:
        frappe.logger().debug("Fatura AI: pdfminer not installed; cannot detect PDF type")
    except Exception as exc:
        frappe.logger().warning("Fatura AI: PDF type detection failed: %s", str(exc))
    return "image"


def extract_text_with_ocr(file_path: str) -> str:
    """
    Convert PDF pages to images and run Tesseract OCR (Arabic + English).
    Returns joined text from all pages, or empty string on failure.
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as exc:
        frappe.logger().warning(
            "Fatura AI T044: %s not installed; OCR unavailable", str(exc)
        )
        return ""

    try:
        images = convert_from_path(file_path, dpi=200)
        page_texts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="ara+eng")
            page_texts.append(text)
        return "\n".join(page_texts)
    except Exception as exc:
        frappe.logger().warning(
            "Fatura AI T044: OCR extraction failed: %s", str(exc)
        )
        return ""


def check_image_quality(file_path: str) -> dict:
    """
    Check the DPI of the first page of a PDF and return a quality assessment.

    Returns a dict with:
        - dpi (int): the horizontal DPI of the first page
        - quality (str): 'low' (<150), 'ok' (150-299), 'high' (>=300)
        - warning (str or None): a human‑readable warning if quality is low
    """
    try:
        images = convert_from_path(file_path, dpi=72)
        if not images:
            return {"dpi": 0, "quality": "low", "warning": frappe._("Could not read any page from the PDF.")}
        first_page = images[0]
        dpi = first_page.info.get("dpi", (72, 72))[0]
        dpi = int(dpi)
        if dpi < 150:
            quality = "low"
            warning = frappe._(
                "Image resolution is too low ({0} DPI). "
                "Extraction accuracy may be reduced."
            ).format(dpi)
        elif dpi < 300:
            quality = "ok"
            warning = None
        else:
            quality = "high"
            warning = None
        return {"dpi": dpi, "quality": quality, "warning": warning}
    except Exception as exc:
        frappe.logger().warning(
            "Fatura AI T045: image quality check failed: %s", str(exc)
        )
        return {"dpi": 0, "quality": "low", "warning": frappe._("Could not determine image resolution.")}
