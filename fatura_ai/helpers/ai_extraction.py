"""
AI extraction orchestrator — provider selection and auto-routing.
Auto-routes: native PDF → DeepSeek (cheap), image/scanned → Gemini Flash.
تنسيق استخراج البيانات بالذكاء الاصطناعي — اختيار المزود والتوجيه التلقائي
"""
import frappe
from frappe import _
from typing import Dict, Any

from fatura_ai.api.providers.base_provider import BaseProvider
from fatura_ai.api.providers.deepseek_provider import DeepSeekProvider
from fatura_ai.api.providers.google_provider import GoogleProvider


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"}


def _is_native_pdf(file_url: str) -> bool:
    return file_url.lower().endswith(".pdf")


def _is_image(file_url: str) -> bool:
    import os
    return os.path.splitext(file_url.lower())[1] in _IMAGE_EXTENSIONS


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
    """Entry point: auto-select provider, run extraction, tag provider name."""
    provider = get_active_provider(file_url=file_url)
    result = provider.extract_invoice(file_url)
    result["provider"] = type(provider).__name__
    return result
