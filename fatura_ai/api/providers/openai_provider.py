"""OpenAI GPT-4o vision provider — secondary provider."""
import frappe
from frappe import _
from typing import Dict, Any
from fatura_ai.api.providers.base_provider import BaseProvider


class OpenAIProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def extract_invoice(self, file_url: str) -> Dict[str, Any]:
        # TODO (T004): implement full OpenAI extraction pipeline
        raise NotImplementedError(_("OpenAI extraction not yet implemented"))
