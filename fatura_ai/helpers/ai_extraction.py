"""
AI extraction helpers — thin wrappers around each provider.
Implements the provider-selection and delegation logic.
مساعدو استخراج الذكاء الاصطناعي
"""
import frappe
from frappe import _
from abc import ABC, abstractmethod
from typing import Dict, Any


# ── Abstract base ────────────────────────────────────────────────────────────

class BaseExtractionProvider(ABC):
    """Abstract interface every AI provider must implement."""

    @abstractmethod
    def extract(self, file_url: str) -> Dict[str, Any]:
        """Return structured invoice dict from the file at file_url."""


# ── Anthropic ────────────────────────────────────────────────────────────────

class AnthropicProvider(BaseExtractionProvider):
    """Claude vision extraction — default provider."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract(self, file_url: str) -> Dict[str, Any]:
        # TODO (T003): implement full Anthropic extraction pipeline
        raise NotImplementedError(_("Anthropic extraction not yet implemented"))


# ── OpenAI ───────────────────────────────────────────────────────────────────

class OpenAIProvider(BaseExtractionProvider):
    """GPT-4o vision extraction — secondary provider."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract(self, file_url: str) -> Dict[str, Any]:
        # TODO (T004): implement full OpenAI extraction pipeline
        raise NotImplementedError(_("OpenAI extraction not yet implemented"))


# ── Google ───────────────────────────────────────────────────────────────────

class GoogleProvider(BaseExtractionProvider):
    """Gemini Flash extraction — tertiary provider."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract(self, file_url: str) -> Dict[str, Any]:
        # TODO (T019): implement Google Gemini extraction pipeline
        raise NotImplementedError(_("Google extraction not yet implemented"))


# ── Provider factory ─────────────────────────────────────────────────────────

def get_active_provider() -> BaseExtractionProvider:
    """Read Settings and return the configured provider instance."""
    settings = frappe.get_doc("Fatura AI Settings")
    provider_name = settings.api_provider or "Anthropic"

    if provider_name == "Anthropic":
        return AnthropicProvider(
            api_key=settings.get_password("anthropic_api_key"),
            model=settings.anthropic_model or "claude-sonnet-4-6",
        )
    if provider_name == "OpenAI":
        return OpenAIProvider(
            api_key=settings.get_password("openai_api_key"),
            model=settings.openai_model or "gpt-4o",
        )
    if provider_name == "Google":
        return GoogleProvider(
            api_key=settings.get_password("google_api_key"),
            model=settings.google_model or "gemini-1.5-flash",
        )
    frappe.throw(_("Unknown AI provider: {0}").format(provider_name))


def extract_invoice_data(file_url: str) -> Dict[str, Any]:
    """Entry point: get provider from Settings, run extraction, tag provider name."""
    provider = get_active_provider()
    result = provider.extract(file_url)
    result["provider"] = type(provider).__name__
    return result
