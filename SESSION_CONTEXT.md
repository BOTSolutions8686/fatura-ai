# Fatura AI — Session Context

Last updated: 2026-06-16

## What we built (Sprints 1–4 + hotfixes)

A Frappe marketplace app that lets ERPNext users import supplier invoices via a 6-step wizard:
Upload PDF → AI Extraction → Supplier Match/Create → Item Confirmation → Review → Import

### Key files
- `fatura_ai/api/import_wizard.py` — main wizard API (run_ai_extraction, match_supplier, confirm_items, confirm_import)
- `fatura_ai/public/js/import_wizard.js` — full wizard UI (6-step progress bar, supplier radio picker, item table)
- `fatura_ai/helpers/supplier_matching.py` — 3-tier supplier matching (Exact VAT, Fuzzy, Manual)
- `fatura_ai/helpers/item_matching.py` — item matching with learned mappings
- `fatura_ai/helpers/ai_extraction.py` — AI extraction with retry/fallback
- `fatura_ai/helpers/zatca_qr.py` — ZATCA TLV QR code decoder
- `fatura_ai/helpers/pdf_extractor.py` — PDF text extraction + image PDF detection
- `fatura_ai/helpers/zatca_mapper.py` — maps extracted data to ksa_compliance custom fields
- `fatura_ai/api/extractor.py` — builds ERPNext doctype payload from confirmed items
- `fatura_ai/fatura_ai/doctype/fatura_import_log/` — log DocType tracking every import
- `fatura_ai/fatura_ai/doctype/invoice_ai_item_map/` — learned item mapping DocType

### Deployment (dev)
- Docker: `frappe_docker-backend-1` (Python) + `frappe_docker-frontend-1` (JS/nginx)
- Site: `frontend` at http://localhost:8080
- Python deploy: `docker cp` → clear `__pycache__` → `docker restart frappe_docker-backend-1`
- JS deploy: `docker cp` to `/home/frappe/frappe-bench/assets/fatura_ai/js/import_wizard.js` in frontend container
- After DocType JSON changes: `bench --site frontend migrate`

### Known issues / watch-outs
- `frappe.parse_json` does not exist in browser JS — use `JSON.parse` (fixed in 38f7af6)
- `Supplier` DocType in ERPNext v16 has no `default_company` field (fixed in f6a3a2c)
- `match_method` on FaturaImportLog must be one of: `""`, `"Exact VAT"`, `"Fuzzy Name"`, `"AI Disambiguation"`, `"Manual"` — never `"Auto-Created"` (fixed in 13f06af)
- Python bytecode cache: always clear `__pycache__` after `docker cp` or gunicorn serves stale code
- JS file location in frontend container: `/home/frappe/frappe-bench/assets/fatura_ai/js/import_wizard.js` (not `/usr/share/nginx/...`)

### What works end-to-end (as of this session)
- Upload PDF → ZATCA QR extraction → supplier match by VAT → supplier auto-create if missing → item matching + auto-create → Purchase Invoice saved in ERPNext ✓
- Arabic supplier names extracted and displayed correctly ✓
- Duplicate PI detection ✓
- Sanity checks (VAT/total) ✓
- Import history list view ✓

### What doesn't work yet
- Image-only PDFs and raw image uploads (JPG/PNG) — see Sprint 5
- OCR for invoices with no text layer
- Batch/bulk import of multiple invoices

## Agents setup (Mac Mini)
- Aider + DeepSeek: primary implementation worker (Terminal window, bordered TUI)
- Claude Code: architecture/review only (Terminal window, ❯ prompt)
- OpenCode + Qwen3: parallel implementation (Terminal window, TUI)
- Send tasks to Aider via AppleScript System Events keystroke injection to the correct Terminal window
- Hourly orchestrator check runs automatically via scheduled task

## Branch strategy
- `develop` — active development
- `main` — stable/release (fast-forward merged from develop)
