"""
DeepSeek provider — text‑based extraction for native PDFs.
"""
import json
from typing import Dict, Any

import pdfplumber
import openai
import frappe

from fatura_ai.helpers.ai_extraction import BaseExtractionProvider


class DeepSeekProvider(BaseExtractionProvider):
    """Extract invoice data from native PDFs via DeepSeek Chat."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract(self, file_url: str) -> Dict[str, Any]:
        # 1. Validate file type
        if not file_url.lower().endswith(".pdf"):
            raise ValueError("Not a native PDF — use vision provider")

        # 2. Extract text from PDF
        text = self._extract_pdf_text(file_url)
        if not text:
            raise ValueError("Not a native PDF — use vision provider")

        # 3. Call DeepSeek API
        return self._call_deepseek(text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_pdf_text(self, file_url: str) -> str:
        """Return concatenated text from all pages of a native PDF."""
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        path = file_doc.get_full_path() if hasattr(file_doc, "get_full_path") else file_doc.file_url

        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _call_deepseek(self, text: str) -> Dict[str, Any]:
        """Send extracted text to DeepSeek Chat and parse JSON response."""
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
        )

        prompt = (
            "You are an invoice data extraction assistant. "
            "Extract the following fields from the invoice text below and return them "
            "as a JSON object with these keys:\n"
            "vendor_name, vat_number, invoice_number, invoice_date, "
            "line_items (list of dicts with keys: description, qty, unit_price, amount), "
            "subtotal, vat_amount, total.\n\n"
            "Invoice text:\n"
            f"{text}\n\n"
            "Return ONLY valid JSON, no extra text."
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content
        # Remove possible markdown fences
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
