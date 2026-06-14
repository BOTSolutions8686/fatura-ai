"""Google Gemini Flash provider — tertiary provider, lowest cost."""
import frappe
from frappe import _
from typing import Dict, Any
from fatura_ai.api.providers.base_provider import BaseProvider


class GoogleProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract_invoice(self, file_url: str) -> Dict[str, Any]:
        # TODO (T019): implement Google Gemini extraction pipeline
        raise NotImplementedError(_("Google extraction not yet implemented"))
