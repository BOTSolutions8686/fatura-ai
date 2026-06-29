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


def _get_vision_provider() -> BaseProvider:
    settings = frappe.get_doc("Fatura AI Settings")
    google_key = settings.get_password("google_api_key")
    if google_key:
        return GoogleProvider(
            api_key=google_key,
            model=settings.google_model or "gemini-1.5-flash",
        )
    anthropic_key = settings.get_password("anthropic_api_key")
    if anthropic_key:
        from fatura_ai.api.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=anthropic_key,
            model=settings.anthropic_model or "claude-sonnet-4-6",
        )
    return None


def _is_native_pdf(file_url: str) -> bool:
    return file_url.lower().endswith(".pdf")


def _is_image(file_url: str) -> bool:
    return os.path.splitext(file_url.lower())[1] in _IMAGE_EXTENSIONS


def _is_retriable(exc: Exception) -> bool:
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
    settings = frappe.get_doc("Fatura AI Settings")
    provider_name = settings.api_provider or "Auto"

    if provider_name == "Auto" and file_url:
        provider_name = "DeepSeek" if _is_native_pdf(file_url) else "Google"

    return _build_provider(provider_name, settings)


def _build_provider(provider_name: str, settings) -> BaseProvider:
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


def _resolve_local_path(file_url: str) -> str:
    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        return file_doc.get_full_path()
    except Exception:
        return None


def _attach_quality(result: dict, local_path: str) -> None:
    qi = check_image_quality(local_path)
    if not qi:
        return
    result["pdf_quality"] = qi
    if qi.get("quality") == "low":
        result.setdefault("warnings", []).append(
            qi.get("warning", _("Image resolution may be too low for accurate extraction."))
        )


def _extract_via_vision_images(provider: BaseProvider, local_path: str) -> dict:
    images = convert_from_path(local_path, dpi=200)
    image_paths = []
    for img in images:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        img.save(tmp.name, "JPEG")
        image_paths.append(tmp.name)
    try:
        result = provider.extract_invoice_from_image(image_paths)
        result["provider"] = type(provider).__name__
        _attach_quality(result, local_path)
        return result
    finally:
        for p in image_paths:
            try:
                os.unlink(p)
            except OSError:
                pass


def _extract_via_ocr(local_path: str) -> str:
    ocr_text = extract_text_with_ocr(local_path)
    if not ocr_text:
        return ""
    frappe.logger().info("Fatura AI T044: OCR extracted %d chars", len(ocr_text))
    file_name = f"ocr_{frappe.generate_hash(length=8)}.txt"
    ocr_file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "content": ocr_text,
        "is_private": 1,
    })
    ocr_file.insert(ignore_permissions=True)
    return ocr_file.file_url


def extract_invoice_data(file_url: str) -> Dict[str, Any]:
    provider = get_active_provider(file_url=file_url)
    local_path = _resolve_local_path(file_url)
    quality_info = None

    if local_path:
        pdf_type = detect_pdf_type(local_path)
        if pdf_type == "image":
            vision = _get_vision_provider() if not isinstance(provider, GoogleProvider) else provider
            if vision:
                return _extract_via_vision_images(vision, local_path)

            ocr_url = _extract_via_ocr(local_path)
            if ocr_url:
                file_url = ocr_url
            else:
                frappe.logger().warning("Fatura AI T044: OCR returned empty text")
            quality_info = check_image_quality(local_path)

    return _extract_with_retry(provider, file_url, quality_info, local_path)


def _extract_with_retry(provider, file_url, quality_info, local_path):
    for attempt in range(_MAX_ATTEMPTS):
        try:
            result = provider.extract_invoice(file_url)
            result["provider"] = type(provider).__name__
            if quality_info:
                _attach_quality_to_result(result, quality_info)
            return result
        except Exception as exc:
            err_msg = str(exc).lower()
            if _is_no_text_error(err_msg) and not isinstance(provider, GoogleProvider):
                vision = _get_vision_provider()
                if vision and local_path:
                    return _fallback_to_vision(vision, local_path, quality_info)
                frappe.throw(
                    _("This PDF is image-based (no text layer). "
                      "Please configure a Google or Anthropic API key "
                      "in Fatura AI Settings for vision extraction."),
                    frappe.ValidationError,
                )
            if not _is_retriable(exc):
                raise
            frappe.logger().warning(
                "Fatura AI: extraction attempt %d/%d failed: %s",
                attempt + 1, _MAX_ATTEMPTS, str(exc),
            )
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(2 ** (attempt + 1))

    frappe.throw(
        _("AI extraction timed out after {0} attempts. Please try again.").format(_MAX_ATTEMPTS),
        frappe.ValidationError,
    )


def _is_no_text_error(err_msg: str) -> bool:
    return "no extractable text" in err_msg or "use vision provider" in err_msg


def _fallback_to_vision(vision, local_path, quality_info):
    frappe.logger().info("Fatura AI T048: text provider failed — switching to vision")
    result = _extract_via_vision_images(vision, local_path)
    if quality_info and "pdf_quality" not in result:
        _attach_quality_to_result(result, quality_info)
    return result


def _attach_quality_to_result(result, quality_info):
    result["pdf_quality"] = quality_info
    if quality_info.get("quality") == "low":
        result.setdefault("warnings", []).append(
            quality_info.get("warning", _("Image resolution may be too low for accurate extraction."))
        )
