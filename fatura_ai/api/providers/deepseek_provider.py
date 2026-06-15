"""
DeepSeek provider — text-based extraction for native PDFs.
يستخرج النص من ملفات PDF الأصلية ويرسله إلى DeepSeek للتحليل
"""
import json
import os
from typing import Dict, Any

import pdfplumber
import openai
import frappe

from fatura_ai.api.providers.base_provider import BaseProvider


class DeepSeekProvider(BaseProvider):
    """Extract invoice data from native PDFs via DeepSeek Chat."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def extract_invoice(self, file_url: str) -> Dict[str, Any]:
        """Extract from a native PDF via text+DeepSeek pipeline."""
        text = self._extract_pdf_text(file_url)
        if not text.strip():
            raise ValueError(_("PDF has no extractable text — use vision provider"))
        return self._call_deepseek(text)

    # ── Private helpers ────────────────────────────────────────────────

    def _extract_pdf_text(self, file_url: str) -> str:
        """Return concatenated text from all PDF pages."""
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        path = file_doc.get_full_path()
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    parts.append(page_text)
        return "\n".join(parts)

    def _load_prompt(self) -> str:
        """Load extraction prompt from template file."""
        prompt_path = frappe.get_app_path(
            "fatura_ai", "templates", "prompts", "extraction_prompt.txt"
        )
        if os.path.exists(prompt_path):
            with open(prompt_path) as f:
                return f.read()
        return "Extract invoice fields as JSON: vendor_name, vat_number, invoice_number, invoice_date, line_items, subtotal, vat_amount, total."

    def _call_deepseek(self, text: str) -> Dict[str, Any]:
        """Send extracted text to DeepSeek Chat and parse JSON response."""
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
        )
        prompt = self._load_prompt() + f"\n\nInvoice text:\n{text}\n\nReturn ONLY valid JSON."
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return self._parse_json(response.choices[0].message.content)

    def _parse_json(self, content: str) -> Dict[str, Any]:
        """Strip markdown fences and parse JSON."""
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
