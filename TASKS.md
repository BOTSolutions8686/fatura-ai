# Fatura AI — Task Backlog
<!-- Orchestrated by Cowork. Last updated: 2026-06-16 09:12] Title | Agent | Priority | Status | Dependencies -->

## 🔄 In Progress
<!-- none -->

## 📋 Backlog

## Sprint 5 — Image Invoice Support (OCR + Vision AI)

**Goal:** Handle invoices that are images (JPG/PNG uploaded directly) or image-based PDFs (scanned documents with no text layer). The ZATCA QR code path already handles most Saudi e-invoices, but older or foreign invoices may have no QR and no extractable text.

### T042 — Accept image file uploads in wizard
- Allow JPG, PNG, WEBP uploads in addition to PDF
- If image uploaded: convert to single-page PDF using Pillow before processing
- Update file validation in `run_ai_extraction` to accept image MIME types
- Show appropriate label in wizard: "Invoice image uploaded"
- **Status:** Done

### T043 — Vision AI extraction for image invoices
- When `pdf_type == "image"` (detected by `pdf_extractor.detect_pdf_type`), skip text extraction
- Instead: convert PDF page(s) to image(s) using `pdf2image.convert_from_path`
- Pass image(s) to AI vision model for structured extraction
- Provider priority: Gemini Vision (gemini-1.5-flash has vision) → GPT-4V → Anthropic Claude Vision
- Prompt: same structured extraction prompt as text, but passed as image message content
- Return same `extracted_json` schema so the rest of the pipeline is unchanged
- **Status:** Done

### T044 — Tesseract OCR fallback
- If vision AI is not configured or fails, run Tesseract OCR on the image pages
- Install: `apt-get install tesseract-ocr tesseract-ocr-ara` (Arabic + English)
- Use `pytesseract.image_to_string(image, lang='ara+eng')`
- Pass OCR text to existing text-based AI extraction prompt
- This is lower accuracy than vision AI but works without an API key
- **Status:** Done

### T045 — Image quality warning
- Before attempting OCR/vision extraction on a scanned image, check resolution
- If DPI < 150: show warning in wizard "Image resolution may be too low for accurate extraction. Results may be incomplete."
- Log `pdf_quality: "low"/"ok"/"high"` in extracted_json
- **Status:** Done

### T046 — Batch import (multiple invoices)
- Allow uploading multiple PDFs at once (file input with `multiple` attribute)
- Process each in sequence, show a progress list: filename | status | supplier | PI number
- Failed ones can be retried individually
- This is a new wizard mode: "Batch Import" vs "Single Import"
- **Status:** Done

### T047 — Email-triggered import (bonus)
- Monitor a designated email inbox (configurable in Fatura AI Settings)
- When an invoice PDF is received as attachment, auto-trigger extraction and save as Draft FaturaImportLog
- User reviews and confirms from the Import History list view
- Requires email MCP or Frappe email configuration

**Priority order:** T042 → T043 → T044 → T045 → T046 → T047
**Start with:** T042 + T043 (these unlock image invoices end-to-end)
**Dependencies:** T043 requires at least one vision-capable AI provider configured

## 🚫 Blocked

## ✅ Done
- [T001] Scaffold Frappe app structure + DocTypes | claude-code | P0 | DONE | none
- [T002] Implement FaturaSettings DocType logic | aider | P0 | DONE | T001
- [T003] Implement AI extraction — Anthropic provider | aider | P0 | DONE | T001
- [T004] Implement AI extraction — OpenAI provider | opencode | P0 | DONE | T001
- [T005] Implement 3-tier supplier matching logic | aider | P0 | DONE | T001
- [T006] Implement 3-tier item matching logic | opencode | P0 | DONE | T001
- [T007] Build wizard — Step 1: File Upload UI | aider | P0 | DONE | T001
- [T008] Build wizard — Step 2: AI Extraction preview UI | opencode | P0 | DONE | T007
- [T009] Build wizard — Step 3: Supplier matching review UI | aider | P0 | DONE | T005,T008
- [T010] Build wizard — Step 4: Item matching review UI | opencode | P0 | DONE | T006,T008
- [T011] Build wizard — Step 5: Confirm + create PI/PO | aider | P0 | DONE | T009,T010
- [T012] ksa_compliance integration — ZATCA fields | claude-code | P0 | DONE | T011
- [T013] Write Arabic translations for all strings | orchestrator | P1 | DONE | T007
- [T014] Unit tests for supplier matching | aider | P1 | DONE | T005
- [T015] Unit tests for item matching | aider | P1 | DONE | T006
- [T016] Write unit tests for AI extraction | aider | P1 | DONE | T003,T004
- [T017] FaturaImportLog status tracking and error logging | aider | P1 | DONE | T001
- [T018] Code review pass | claude-code | P1 | DONE | T012
- [T019] Google Gemini AI provider | opencode | P2 | DONE | T003
- [T020] Performance: batch item matching caching | orchestrator | P2 | DONE | T006
- [T021] Fix P0 bugs BUG-1/BUG-2/BUG-3 in import_wizard.py | orchestrator | P0 | DONE | T018
- [T022] Fix COR-1 (None tax_id guard) + COR-2 (items vs line_items key) | aider | P1 | DONE | T021
- [T023] Fix SEC-1/SEC-2 | orchestrator | P1 | DONE | T021
- [T024] PDF text extractor + DeepSeek structured extraction | aider | P0 | DONE | none
- [T025] Gemini Flash vision provider (image/scan fallback) | opencode | P0 | DONE | T024
- [T026] Smart provider routing + extraction prompt template | aider | P0 | DONE | T025
- [T027] Add DeepSeek provider fields to FaturaSettings DocType | aider | P0 | DONE | T024
- [T028] Auto-create supplier from extracted invoice data | aider | P1 | DONE | T009
- [T029] VAT-ambiguous multi-supplier picker in wizard | opencode | P1 | DONE | T005
- [T030] Duplicate invoice detection + force-create UI in confirm_import | aider | P1 | DONE | T011
- [T034] Sanity warnings after confirm_import (non-blocking) | aider | P2 | DONE | T030
- [T042] Accept image file uploads in wizard (JPG/PNG/WEBP) | aider | P0 | DONE | none
- [T043] Vision AI extraction for image invoices | aider | P0 | DONE | T042
- [T044] Tesseract OCR fallback for image invoices | aider | P0 | DONE | T042
- [T045] Image quality warning (DPI check) | aider | P1 | DONE | T042
- [T046] Batch import (multiple invoices) | aider | P1 | DONE | T042
- [T047] Email-triggered import (email inbox monitor) | aider | P2 | DONE | T042
