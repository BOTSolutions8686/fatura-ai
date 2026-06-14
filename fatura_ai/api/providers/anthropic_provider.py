"""Anthropic Claude vision provider — default, best for Arabic/mixed invoices."""
import frappe
from frappe import _
from typing import Dict, Any
from fatura_ai.api.providers.base_provider import BaseProvider


class AnthropicProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def extract_invoice(self, file_url: str) -> Dict[str, Any]:
        # TODO (T003): implement prompt + response parsing
        raise NotImplementedError(_("Anthropic extraction not yet implemented"))

    def _build_prompt(self) -> str:
        """Load extraction prompt from template file."""
        import os
        prompt_path = frappe.get_app_path(
            "fatura_ai", "templates", "prompts", "extraction_prompt.txt"
        )
        if os.path.exists(prompt_path):
            with open(prompt_path) as f:
                return f.read()
        return ""
