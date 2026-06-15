"""Google Gemini Flash provider — tertiary provider, lowest cost."""
import json
import frappe
from frappe import _
from typing import Dict, Any
import google.generativeai as genai
from fatura_ai.api.providers.base_provider import BaseProvider


class GoogleProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        genai.configure(api_key=api_key)

    def extract_invoice(self, file_url: str) -> Dict[str, Any]:
        file_bytes, mime_type = self._load_file_bytes(file_url)
        model = genai.GenerativeModel(self.model)
        prompt = (
            "You are an invoice data extraction assistant. "
            "Extract the following fields from the invoice image/PDF below and return them "
            "as a JSON object with these keys:\n"
            "vendor_name, vat_number, invoice_number, invoice_date, "
            "line_items (list of dicts with keys: description, qty, unit_price, amount), "
            "subtotal, vat_amount, total.\n\n"
            "Return ONLY valid JSON, no extra text."
        )
        response = model.generate_content(
            [
                {"mime_type": mime_type, "data": file_bytes},
                prompt,
            ]
        )
        return self._parse_json_response(response.text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_file_bytes(self, file_url: str):
        """Return (bytes, mime_type) for the file at file_url."""
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        path = file_doc.get_full_path()
        with open(path, "rb") as f:
            file_bytes = f.read()

        ext = file_url.lower().rsplit(".", 1)[-1] if "." in file_url else ""
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")
        return file_bytes, mime_type

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Strip markdown fences and parse JSON from response text."""
        content = text.strip()
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
