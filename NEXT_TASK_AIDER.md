# Next Task for Aider: T042+T043 — Image Invoice Support (Vision AI)
<!-- Written by Claude Code Orchestrator at 2026-06-16 -->

**Priority:** P0
**Sprint:** 5
**Depends on:** T024 ✅ (pdf_extractor.py done), T025 ✅ (Gemini provider done)

## Task

Sprint 5 T042+T043: Add image invoice support to Fatura AI.

### T042 — Accept image file uploads in wizard

Update `run_ai_extraction` in `fatura_ai/api/import_wizard.py`:
- Accept image uploads (jpg, png, webp) in addition to PDF
- If the uploaded file is an image (check MIME type: `image/jpeg`, `image/png`, `image/webp`):
  - Use `pdf2image` or `Pillow` to convert to a temporary PDF, then process normally
  - OR pass directly to the vision path (T043)
- Update the file type validation guard at the top of `run_ai_extraction`
- Show appropriate label in wizard: "Invoice image uploaded"

### T043 — Vision AI extraction for image invoices

In `fatura_ai/helpers/ai_extraction.py`, add `_extract_from_image(image_path, provider)`:
- When `pdf_extractor.detect_pdf_type(path)` returns `"image"`, skip text extraction
- Convert PDF page(s) to images via `pdf2image.convert_from_path`
- Call the vision endpoint of the configured provider:
  - **Gemini:** `gemini-1.5-flash` with image_url part in message content
  - **OpenAI:** `gpt-4o` with image_url in message content
  - **Anthropic:** `claude-3-5-sonnet` with image base64 in message content
- Use the same structured extraction prompt as text extraction
- Return the same `extracted_json` schema so the rest of the pipeline is unchanged
- Fall back to `pytesseract` OCR if vision fails (install: `apt-get install tesseract-ocr tesseract-ocr-ara`)

## Deploy after each change:
```bash
# Python
docker cp fatura_ai/helpers/ai_extraction.py frappe_docker-backend-1:/home/frappe/frappe-bench/apps/fatura_ai/fatura_ai/helpers/
docker cp fatura_ai/api/import_wizard.py frappe_docker-backend-1:/home/frappe/frappe-bench/apps/fatura_ai/fatura_ai/api/
find frappe_docker-backend-1:/home/frappe/frappe-bench/apps/fatura_ai -name "__pycache__" -exec docker exec frappe_docker-backend-1 rm -rf {} + 2>/dev/null; docker restart frappe_docker-backend-1
```

## Commit when done:
```bash
git add fatura_ai/api/import_wizard.py fatura_ai/helpers/ai_extraction.py
git commit -m "feat(T042+T043): image invoice support via vision AI"
git push origin develop
```

Then update TASKS.md: move T042 and T043 from Backlog to Done.

## After T042+T043 — T044: Tesseract OCR fallback
See TASKS.md Sprint 5 section for full spec.
