"""
AI extraction orchestrator — provider selection, auto-routing, and retry.
Auto-routes: native PDF → DeepSeek (cheap), image/scanned → Gemini Flash.
تنسيق استخراج البيانات بالذكاء الاصطناعي — اختيار المزود والتوجيه التلقائي
"""
import os
import time
import tempfile
import frappe
from frappe import _
from typing import Dict, Any

from pdf2image import convert_from_path

from fatura_ai.api.providers.base_provider import BaseProvider
from fatura_ai.api.providers.deepseek_provider import DeepSeekProvider
from fatura_ai.api.providers.google_provider import GoogleProvider
from fatura_ai.helpers.pdf_extractor import detect_pdf_type, extract_text_with_ocr, check_image_quality


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"}
_MAX_ATTEMPTS = 3


def _is_native_pdf(file_url: str) -> bool:
    return file_url.lower().endswith(".pdf")


def _is_image(file_url: str) -> bool:
    import os
    return os.path.splitext(file_url.lower())[1] in _IMAGE_EXTENSIONS


def _is_retriable(exc: Exception) -> bool:
    """Return True for timeout errors and HTTP 5xx server errors."""
    try:
        import requests
        if isinstance(exc, requests.exceptions.Timeout):
            return True
    except ImportError:
        pass
    exc_name = type(exc).__name__
    if any(k in exc_name for k in ("Timeout", "ServiceUnavailable", "InternalServer")):
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
    if status and int(status) >= 500:
        return True
    return False


def get_active_provider(file_url: str = None) -> BaseProvider:
    """
    Return the configured provider, with optional auto-routing by file type.
    Auto-routing (when api_provider = 'Auto'):
      - Native PDF  → DeepSeek (text extraction, cheapest)
      - Image / PDF → Google Gemini Flash (vision, cheap fallback)
    """
    settings = frappe.get_doc("Fatura AI Settings")
    provider_name = settings.api_provider or "Auto"

    if provider_name == "Auto" and file_url:
        if _is_native_pdf(file_url):
            provider_name = "DeepSeek"
        else:
            provider_name = "Google"

    if provider_name == "DeepSeek":
        return DeepSeekProvider(
            api_key=settings.get_password("deepseek_api_key"),
            model=settings.deepseek_model or "deepseek-chat",
        )
    if provider_name == "Google":
        return GoogleProvider(
            api_key=settings.get_password("google_api_key"),
            model=settings.google_model or "gemini-1.5-flash",
        )
    if provider_name == "Anthropic":
        from fatura_ai.api.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=settings.get_password("anthropic_api_key"),
            model=settings.anthropic_model or "claude-sonnet-4-6",
        )
    if provider_name == "OpenAI":
        from fatura_ai.api.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.get_password("openai_api_key"),
            model=settings.openai_model or "gpt-4o",
        )

    frappe.throw(_("Unknown AI provider: {0}").format(provider_name))


def extract_invoice_data(file_url: str) -> Dict[str, Any]:
    """Auto-select provider, run extraction with retry, tag provider name."""
    provider = get_active_provider(file_url=file_url)
    last_error = None

    # T044 — Tesseract OCR fallback for image PDFs
    local_path = None
    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        local_path = file_doc.get_full_path()
    except Exception:
        pass

    if local_path:
        pdf_type = detect_pdf_type(local_path)
        if pdf_type == "image":
            if isinstance(provider, GoogleProvider):
                # T043 — Vision AI extraction for image PDFs
                images = convert_from_path(local_path, dpi=200)
                image_paths = []
                for i, img in enumerate(images):
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    img.save(tmp.name, "JPEG")
                    image_paths.append(tmp.name)
                try:
                    result = provider.extract_invoice_from_image(image_paths)
                    result["provider"] = type(provider).__name__
                    # T045 — image quality check
                    quality_info = check_image_quality(local_path)
                    if quality_info:
                        result["pdf_quality"] = quality_info
                        if quality_info.get("quality") == "low":
                            warnings = result.setdefault("warnings", [])
                            warnings.append(
                                quality_info.get(
                                    "warning",
                                    _("Image resolution may be too low for accurate extraction."),
                                )
                            )
                    return result
                finally:
                    for p in image_paths:
                        try:
                            os.unlink(p)
                        except OSError:
                            pass
            else:
                # T044 — Tesseract OCR fallback for non‑Google providers
                ocr_text = extract_text_with_ocr(local_path)
                if ocr_text:
                    frappe.logger().info(
                        "Fatura AI T044: OCR extracted %d chars", len(ocr_text)
                    )
                    # Create a temporary File doc with the OCR text so the provider
                    # can read it as a normal text file.
                    import frappe
                    from frappe.utils import now_datetime

                    file_name = f"ocr_{frappe.generate_hash(length=8)}.txt"
                    ocr_file = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_name": file_name,
                            "content": ocr_text,
                            "is_private": 1,
                        }
                    )
                    ocr_file.insert(ignore_permissions=True)
                    file_url = ocr_file.file_url
                else:
                    frappe.logger().warning(
                        "Fatura AI T044: OCR returned empty text"
                    )

        # T045 — image quality check (for non‑image PDFs this is skipped)
        quality_info = None
        if pdf_type == "image":
            quality_info = check_image_quality(local_path)

    for attempt in range(_MAX_ATTEMPTS):
        try:
            result = provider.extract_invoice(file_url)
            result["provider"] = type(provider).__name__
            # T045 — attach quality info to result
            if quality_info:
                result["pdf_quality"] = quality_info
                if quality_info.get("quality") == "low":
                    warnings = result.setdefault("warnings", [])
                    warnings.append(
                        quality_info.get(
                            "warning",
                            _("Image resolution may be too low for accurate extraction."),
                        )
                    )
            return result
        except Exception as exc:
            if not _is_retriable(exc):
                raise
            last_error = exc
            frappe.logger().warning(
                "Fatura AI: extraction attempt %d/%d failed: %s",
                attempt + 1,
                _MAX_ATTEMPTS,
                str(exc),
            )
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(2 ** (attempt + 1))  # 2s, 4s

    frappe.throw(
        _("AI extraction timed out after {0} attempts. Please try again.").format(
            _MAX_ATTEMPTS
        ),
        frappe.ValidationError,
    )
