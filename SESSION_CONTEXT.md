# Fatura AI — Session Context

Last updated: 2026-06-29

## Today's session (June 29) — Major fixes + Phase 1 learning + Market-ready

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
- **`after_install` hook** — Checks tesseract/poppler/libzbar on install, shows dialog if missing. Creates Workspace Sidebar + Desktop Icon.
- **Learned/trusted badges** — Item wizard shows 🧠 learned count, ⭐ trusted (5+ uses), per-item usage count (3x).
- **Supplier Invoice Template** — New doctype. Layout fingerprinting (aHash) on every import. Tracks per-supplier templates.
- **Template match UI** — Wizard shows: 📄 Known layout, 🔄 Similar (changed), 🆕 New layout.
- **Google prompt unified** — Uses same `extraction_prompt.txt` template as DeepSeek (was bare minimum).
- **QR scans images too** — `extract_zatca_qr` now handles JPG/PNG directly, not just PDFs.
- **Market-ready packaging**: Custom SVG icon, Workspace with dashboard/Number Cards, Workspace Sidebar, Desktop Icon for v16 apps screen, LICENSE (MIT).

### Current app structure
```
fatura_ai/
├── api/                          # @frappe.whitelist() endpoints
│   ├── import_wizard.py          # Main wizard — all steps
│   ├── extractor.py              # Builds ERPNext doctype payload
│   └── providers/                # AI provider implementations
├── helpers/                      # Business logic, no @frappe.whitelist
│   ├── ai_extraction.py          # Provider selection, routing, retry
│   ├── supplier_matching.py      # 3-tier matching
│   ├── item_matching.py          # Item matching + learned mappings
│   ├── pdf_extractor.py          # PDF type detection, OCR, quality
│   ├── zatca_qr.py               # ZATCA TLV QR decoder
│   ├── layout_hasher.py          # Invoice layout fingerprinting (aHash)
│   └── compatibility.py          # ksa_compliance checks
├── public/js/                    # Frontend
│   ├── import_wizard.js          # Full 6-step wizard UI
│   ├── settings.js               # Fatura AI Settings form handlers
│   └── purchase_invoice.js       # Button injection on PI form
├── fatura_ai/doctype/            # DocType definitions
│   ├── fatura_ai_settings/       # Singleton: API keys, provider, thresholds
│   ├── fatura_import_log/        # Per-import log with cost tracking
│   ├── invoice_ai_item_map/      # Learned item mappings
│   └── supplier_invoice_template/# Layout learning per supplier
├── fatura_ai/workspace/          # Workspace dashboard JSON
├── config/desktop.py             # Module icon + sidebar items
├── templates/prompts/            # AI extraction prompts
├── translations/ar.csv           # Arabic translations
├── setup/install.py              # after_install hook
└── constants.py                  # Provider pricing per 1M tokens
```

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
- `develop` at `83ef8e6` — pushed to origin
- `.gitignore` updated: iCloud conflict copies (`* 2/`)

### API keys configured on dev instance
- DeepSeek: set (existing)
- Google: set (session-only, not in code — stored in Fatura AI Settings doctype)

---

## Frappe / ERPNext Lessons Learned (MUST READ BEFORE NEXT SESSION)

### Docker & Deployment
- **Bind mounts sync instantly** — no need to `docker cp`. Code changes on host are live immediately.
- **`pip install -e` needed per container** — each container has its own venv writable layer. The startup command in pwd.yml handles this.
- **Frontend nginx DNS caching** — when backend IP changes (container recreate), nginx caches old IP. Must restart frontend too. Fix: always restart both together.
- **`docker compose up -d` recreates containers** — `apps/` directory content (like cloned ksa_compliance) is LOST. Use bind mounts for any app that isn't in the base image.
- **`docker compose run` creates separate container** — changes to that container don't affect running services. Use `exec` for live containers.
- **DB name uses hash prefix** — `_75688bd1a09ff23a` in this setup. Find with: `mariadb -u root -padmin -e "SHOW DATABASES;"`
- **Gunicorn workers need ~10s to boot** — wait after recreate before testing.
- **`su frappe -c` doesn't exec properly** — use `exec /usr/local/bin/entrypoint.sh` directly. The image entrypoint already handles user switching.

### Frappe Framework
- **`bench execute` uses `eval` mode** — only single expressions, no statements. Use `bench execute "frappe.db.get_value(...)"` without semicolons/prints.
- **`bench execute` fails on `frappe.db.set_value`** — because it tries `eval("frappe.db.set_value(...)")` which is a statement, not expression.
- **Direct Python access needs log dirs** — `frappe.init()` + `frappe.connect()` needs `/home/frappe/logs/` and `.../frontend/logs/` to exist. Create them first.
- **Venv Python vs system Python** — must use `/home/frappe/frappe-bench/env/bin/python` to access frappe module.
- **`db.get_global("installed_apps")` is cached in Redis** — updating `tabDefaultValue` directly doesn't clear the cache. Must flush Redis or use `frappe.db.set_global()`.
- **`tabDefaultValue` stores `installed_apps` as JSON array** — key is `installed_apps`, parent is `__global`.
- **`apps.txt` in sites directory** — lists all installed apps. Must match `installed_apps` in DB. Read by `get_all_apps()`.
- **Database table names use backtick-escaped spaces** — `tabInstalled Application`, `tabGlobal Defaults`, `tabModule Def`. Use backticks in SQL.
- **Frappe serves do not serve SVGs as static assets** — `/assets/fatura_ai/images/icon.svg` returns 404. Must upload as File doctype and use `/files/icon.svg`.

### Doctype & Fixtures
- **Doctype JSON is strict** — `field_order` must contain ONLY string fieldnames, not objects. JSON parse errors during migrate are cryptic ("bad json at line 73").
- **Fixtures auto-export to app directory** — on migrate, Frappe exports current DB state to `fatura_ai/<doctype_snake>/<name>.json`. These become the source of truth.
- **Fixture filter fields must exist** — `{"dt": "Desktop Icon", "filters": [["app", "=", "fatura_ai"]]}` — the `app` field must exist on Desktop Icon doctype. Use the actual field names.
- **Currency field rounds to 2 decimals** — use Float with `"precision": "6"` for micro-costs like $0.000428.
- **Button fields in doctype JSON** — `"fieldtype": "Button"` with `"depends_on": "eval:doc.fieldname"`. JS handler matches fieldname exactly.

### v16 Desktop & Workspace
- **`add_to_apps_screen` hook** — registers app on /desk page. Must return list of dicts with `app_name`, `title`, `icon`, `route`.
- **Desktop Icon doctype fields**: `app`, `label`, `icon_type` ("Link"), `link_type` ("Workspace Sidebar" or "External"), `link_to` (sidebar name), `logo_url` (/files/*.svg), `bg_color` ("blue" or "gray"), `standard` (1).
- **Workspace Sidebar items**: use `label` (not `title`), `link_type` ("Workspace"/"DocType"/"Page"), `link_to` (workspace/doc name), `type` ("Link").
- **SVG icons require File doctype** — upload SVG as `File` doc, use `/files/icon.svg` in `logo_url`. Asset paths (`/assets/...`) don't serve SVGs.
- **Workspace JSON format** — `content` field is a JSON string of blocks. Number Cards, Shortcuts, Cards, Headers are all block types.
- **Number Card doctype** — needs `document_type`, `filters_json`, `function` (Count/Sum), `report_field` (for Sum), `type` ("Document Type"/"Report").

### Providers & AI
- **Google Gemini model names change** — always check `genai.list_models()` before hardcoding. `gemini-1.5-flash` was completely removed.
- **`google-generativeai` is deprecated** — Google recommends `google-genai`. Still works but shows FutureWarning.
- **Gemini PDF support is limited** — some models don't support PDF input. Always convert PDFs to images for Gemini.
- **DeepSeek uses OpenAI-compatible API** — same client, different `base_url`.
- **Token usage (cost)**: DeepSeek response has `response.usage.prompt_tokens`, Google has `response.usage_metadata.prompt_token_count`.

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
- Desktop icon on v16 /desk page ✓
- Workspace dashboard with number cards ✓

### What doesn't work yet / next
- Template-first extraction (use known layout positions to skip AI) — Phase 2 WIP
- Supplier template field position storage and extraction
- Anthropic/OpenAI provider implementation
- `google-generativeai` → `google-genai` migration
- Confidence feedback loop (track per-field correction rate)
