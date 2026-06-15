# Next Task for OpenCode: T044 — Tesseract OCR Fallback
<!-- Written by Cowork Orchestrator at 2026-06-16 -->
**Priority:** P1
**Sprint:** 5
**Depends on:** T042+T043 (can be developed in parallel — same files, different code path)

## Task
Implement Tesseract OCR fallback for image invoices when vision AI is not configured or fails.

### Steps
1. Ensure `pytesseract` is importable (add `pytesseract>=0.3.10` to requirements.txt if missing)
2. In `fatura_ai/helpers/ai_extraction.py`, add `_extract_via_ocr(image_path)`:
   - Convert PDF pages to images using `pdf2image.convert_from_path`
   - Run `pytesseract.image_to_string(image, lang='ara+eng')` on each page
   - Concatenate text from all pages
   - Pass OCR text to the existing text-based AI extraction prompt (`_build_extraction_prompt`)
   - Return same `extracted_json` schema
3. In the main extraction dispatch (where `pdf_type == "image"` is handled):
   - Try vision AI first (T043 code path)
   - On failure or if no vision provider configured: fall back to `_extract_via_ocr`
   - Log which path was taken in `FaturaImportLog.extraction_method`

### Note on Tesseract install
Tesseract must be installed on the Docker container:
```bash
docker exec frappe_docker-backend-1 bash -c "apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-ara"
```
Add a graceful `ImportError` catch around pytesseract import so the app doesn't break if not installed — just skip the OCR fallback and surface a warning.

## Deploy after changes:
```bash
docker cp fatura_ai/helpers/ai_extraction.py frappe_docker-backend-1:/home/frappe/frappe-bench/apps/fatura_ai/fatura_ai/helpers/
find frappe_docker-backend-1:/home/frappe/frappe-bench/apps/fatura_ai -name "__pycache__" -exec docker exec frappe_docker-backend-1 rm -rf {} + 2>/dev/null
docker restart frappe_docker-backend-1
```

## Commit when done:
```bash
git add fatura_ai/helpers/ai_extraction.py requirements.txt
git commit -m "feat(T044): Tesseract OCR fallback for image invoices"
git push origin develop
```
Then update TASKS.md: move T044 from Backlog to Done.

## After T044 — T045: Image quality warning
Check DPI of uploaded image before OCR/vision. If DPI < 150, show warning in wizard.
See TASKS.md Sprint 5 section for full spec.
