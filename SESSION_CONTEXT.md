# Fatura AI — Session Context

Last updated: 2026-06-29

## Today's session (June 29) — Major fixes + Phase 1 learning

### Critical fixes
- **QR scanning was dead** — `libzbar0` and `poppler-utils` missing from Docker image. Fixed via custom Dockerfile.
- **Google model removed** — `gemini-1.5-flash` deleted by Google, updated to `gemini-2.5-flash` everywhere.
- **OCR was broken** — `extract_text_with_ocr` returns empty string because OCR logic was orphaned at module level. Fixed.
- **Vision fallback was a no-op** — called `extract_invoice()` (text-based) instead of `extract_invoice_from_image()` (vision). Fixed.
- **Google PDF error** — Google provider sent raw PDF bytes to Gemini which rejects them. Fixed: auto-converts PDFs to images.
- **Image PDFs routed wrong** — Went OCR→DeepSeek→fail instead of directly to Google Vision. Fixed in `extract_invoice_data`.
- **QR ran AFTER extraction** — If extraction crashed, QR never scanned. Fixed: QR runs FIRST, AI second.
- **quality_info crash** — Variable uninitialized when `local_path` was None. Fixed.
- **Supplier dead-end** — Hard error when no name/VAT extracted. Changed to no-match result → shows search/create UI.
- **email_monitor hook** — Registered but file didn't exist. Removed.
- **banksync orphan** — Removed from DB, apps.txt, and DefaultValue.

### New features built today
- **API cost tracking** — `cost`, `tokens_input`, `tokens_output` on Fatura Import Log. Pricing in `constants.py`.
- **Provider test buttons** — Settings page has "Test Key" for DeepSeek, Google, Anthropic, OpenAI. Tesseract status checker.
- **`after_install` hook** — Checks tesseract/poppler/libzbar on install, shows dialog if missing.
- **Learned/trusted badges** — Item wizard shows 🧠 learned count, ⭐ trusted (5+ uses), per-item usage count (3x).
- **Supplier Invoice Template** — New doctype. Layout fingerprinting (aHash) on every import. Tracks per-supplier templates.
- **Template match UI** — Wizard shows: 📄 Known layout, 🔄 Similar (changed), 🆕 New layout.
- **Google prompt unified** — Uses same `extraction_prompt.txt` template as DeepSeek (was bare minimum).
- **QR scans images too** — `extract_zatca_qr` now handles JPG/PNG directly, not just PDFs.

### Docker setup (local dev)
- **Custom image**: `frappe-erpnext-tesseract:v16.22.0` (built from `Dockerfile` in `~/dev-environments/frappe_docker/`)
- **System packages in image**: tesseract-ocr + ara/eng, poppler-utils, libzbar0
- **Bind mounts**: fatura_ai and ksa_compliance mounted from host to `/home/frappe/frappe-bench/apps/`
- **Startup**: `pip install -e apps/fatura_ai -e apps/ksa_compliance` on backend boot
- **pwd.yml**: Updated with bind mounts and custom image for backend
- **Note**: Every backend recreate changes IP → frontend nginx needs restart (DNS caching issue)

### Deploy steps
```bash
cd ~/dev-environments/frappe_docker
docker compose -f pwd.yml exec backend bash -c "find ... -name __pycache__ -delete"
docker compose -f pwd.yml exec backend bench build --app fatura_ai
docker compose -f pwd.yml exec backend bench --site frontend migrate
docker compose -f pwd.yml up -d --force-recreate backend frontend
docker compose -f pwd.yml restart frontend  # fix nginx DNS cache
```

### Git
- `develop` at `991c2b1` — pushed to origin
- `.gitignore` updated: iCloud conflict copies (`* 2/`)

### API keys configured on dev instance
- DeepSeek: set (existing)
- Google: set (session-only, not in code)

### Known issues / watch-outs
- Frontend nginx caches backend IP — need restart after backend recreate
- iCloud sync creates `* 2` conflict folders — gitignored, safe to delete
- Google `google-generativeai` package is deprecated — should migrate to `google-genai` eventually
- Anthropic and OpenAI providers are stubs (raise NotImplementedError)
- Scheduler/queue workers need `pip install` in startup commands (like backend)

### What works end-to-end
- PDF upload → QR scan → AI extraction → supplier match → item match + learning → Purchase Invoice ✓
- Image PDFs → auto-route to Google Vision ✓
- Cost tracking per extraction ✓
- Template learning (layout fingerprinting) ✓
- Provider test buttons in Settings ✓
- Tesseract OCR status in Settings ✓

### What doesn't work yet / next
- Template-first extraction (use known layout positions to skip AI) — Phase 2 WIP
- Supplier template field position storage and extraction
- Anthropic/OpenAI provider implementation
- `google-generativeai` → `google-genai` migration
- Confidence feedback loop (track per-field correction rate)
