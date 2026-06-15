"""
PDF type detection — determines whether a PDF has a text layer or is image-only.
"""
import frappe
from typing import Literal


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
