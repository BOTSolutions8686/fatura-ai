"""Google Gemini Flash provider — tertiary provider, lowest cost."""
import base64
import json
import os
import tempfile
import frappe
from frappe import _
from typing import Dict, Any, List
import google.generativeai as genai
from pdf2image import convert_from_path
from fatura_ai.api.providers.base_provider import BaseProvider


class GoogleProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        genai.configure(api_key=api_key)

    def _build_extraction_prompt(self) -> str:
        prompt_path = frappe.get_app_path(
            "fatura_ai", "templates", "prompts", "extraction_prompt.txt"
        )
        try:
            with open(prompt_path) as f:
                return f.read()
        except Exception:
            return (
                "You are an invoice data extraction assistant. "
                "Extract the following fields from the invoice and return them "
                "as a JSON object with these keys:\n"
                "vendor_name, vat_number, invoice_number, invoice_date, "
                "line_items (list of dicts with keys: item_name, description, qty, uom, unit_price, amount), "
                "subtotal, vat_amount, total, currency.\n\n"
                "Return ONLY valid JSON, no extra text."
            )

    def extract_invoice(self, file_url: str) -> Dict[str, Any]:
        ext = file_url.lower().rsplit(".", 1)[-1] if "." in file_url else ""
        if ext == "pdf":
            return self._extract_pdf(file_url)
        file_bytes, mime_type = self._load_file_bytes(file_url)
        model = genai.GenerativeModel(self.model)
        prompt = self._build_extraction_prompt()
        response = model.generate_content([
            {"mime_type": mime_type, "data": file_bytes},
            prompt,
        ])
        result = self._parse_json_response(response.text)
        self._attach_usage(result, response)
        return result

    def _extract_pdf(self, file_url: str) -> Dict[str, Any]:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        local_path = file_doc.get_full_path()
        images = convert_from_path(local_path, dpi=200)
        image_paths = []
        for img in images:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            img.save(tmp.name, "JPEG")
            image_paths.append(tmp.name)
        try:
            return self.extract_invoice_from_image(image_paths)
        finally:
            for p in image_paths:
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def extract_invoice_from_image(self, image_paths: List[str]) -> Dict[str, Any]:
        """Send one or more image files to Gemini Vision and return parsed JSON."""
        model = genai.GenerativeModel(self.model)
        prompt = self._build_extraction_prompt()
        parts = [{"text": prompt}]
        for path in image_paths:
            with open(path, "rb") as f:
                img_bytes = f.read()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64,
                }
            })
        response = model.generate_content({"parts": parts})
        result = self._parse_json_response(response.text)
        self._attach_usage(result, response)
        return result

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

    def _attach_usage(self, result: dict, response) -> None:
        try:
            um = response.usage_metadata
            result["_usage"] = {
                "input_tokens": um.prompt_token_count,
                "output_tokens": um.candidates_token_count,
            }
        except Exception:
            pass
