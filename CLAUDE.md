# Fatura AI — Agent Context (CLAUDE.md)

## What This Project Is
Fatura AI is a Frappe marketplace app that imports supplier invoices (PDF/image)
into ERPNext Purchase Invoice and Purchase Order using AI extraction.

- Target market: Saudi Arabia (Arabic/English mixed invoices)
- Paid app on Frappe Marketplace — annual subscription
- Open source code, MIT license
- Built by BOT Solutions (botsolutions.tech), Jeddah, Saudi Arabia

## Product Scope — v1 ONLY
DO NOT build anything outside this list. If a feature is not here, it is v2.

v1 features:
- Import Invoice button on Purchase Invoice form
- Import Invoice button on Purchase Order form
- Upload dialog (PDF, PNG, JPG, WEBP)
- AI extraction — supplier, items, totals, dates, ZATCA fields
- 3-tier supplier matching (exact VAT → fuzzy name → AI disambiguation)
- 3-tier item matching (exact code → fuzzy name → AI disambiguation)
- Guided 5-step wizard with RTL support
- LavaLoon ksa_compliance field population (guarded)
- Fatura AI Settings doctype
- Invoice AI Import Log doctype
- Invoice AI Item Map doctype (learned mappings)
- Onboarding checklist (setup page)
- First-time user tooltips in wizard

NOT in v1 (do not build):
- Sales Invoice import
- Email parsing / email-triggered import
- Bulk import
- ZATCA signing or submission (that is ksa_compliance's job)
- Prompt-based invoice entry
- Mobile camera capture

## Dev Server — REQUIRED BEFORE CODING
Before writing any code, check if .env exists and has these values.
If .env is missing or incomplete, ask the user for:
  - DEV_SERVER_IP
  - DEV_SERVER_SSH_USER
  - DEV_SERVER_SSH_KEY_PATH
  - DEV_SITE_NAME (e.g. dev.botsolutions.tech)
  - ERPNEXT_API_KEY
  - ERPNEXT_API_SECRET

Save them to .env (never commit .env to git).
Use these to SSH, run bench commands, and test against the real dev site.

## Tech Stack
- Frappe Framework v14 and v15 (support both)
- Python backend, JavaScript frontend (Frappe native dialogs)
- AI providers: Anthropic (default), OpenAI, Google
- Fuzzy matching: rapidfuzz
- ZATCA: depends on lavaloon-eg/ksa_compliance app

## Critical Rules — Never Violate These
1. NEVER auto-submit a Purchase Invoice or Purchase Order. Only populate fields.
2. NEVER hardcode API keys, model names, or thresholds. Always read from Settings doctype.
3. NEVER commit .env or any file with credentials to git.
4. NEVER use raw SQL. Use frappe.get_doc(), frappe.db.get_value(), frappe.db.get_list().
5. NEVER access LavaLoon custom fields without checking ksa_compliance is installed first.
6. NEVER mix prompt changes and code changes in the same PR/commit.
7. NEVER write a function longer than 40 lines. Split it.
8. NEVER create a utils.py. Put helpers in focused files in helpers/ directory.
9. ALWAYS write a test for every new function in api/ directory.
10. ALWAYS run bench run-tests --app fatura_ai before marking any task done.

## Frappe Coding Conventions
- Decorators: @frappe.whitelist() for all API endpoints
- File handling: frappe.get_doc("File") — not os.path
- Custom fields from other apps: check with frappe.get_meta() before accessing
- JS dialogs: frappe.ui.Dialog only — no native browser alert/confirm
- Translations: wrap all user-facing strings with __() in JS, _() in Python
- Hooks: hooks.py must stay thin and declarative — no logic inside it

## File Responsibility Map
Each file has exactly one job. Do not mix responsibilities.

Python:
  api/extractor.py          → orchestrates extraction pipeline only
  api/file_handler.py       → file validation and preprocessing only
  api/matcher.py            → all matching logic only (3-tier)
  api/validator.py          → ZATCA field validation rules only
  api/import_logger.py      → import log creation only
  api/exceptions.py         → all custom exceptions only
  api/providers/base_provider.py        → abstract interface only
  api/providers/anthropic_provider.py  → Anthropic API only
  api/providers/openai_provider.py     → OpenAI API only
  api/providers/google_provider.py     → Google AI API only
  helpers/compatibility.py  → app install checks only
  helpers/date_helpers.py   → date parsing and conversion only
  helpers/text_helpers.py   → RTL detection and Arabic text only
  constants.py              → ALL magic values and strings

JavaScript:
  public/js/purchase_invoice.js  → button injection only, calls wizard
  public/js/purchase_order.js    → button injection only, calls wizard
  public/js/wizard/wizard_manager.js  → step orchestration only
  public/js/wizard/step_upload.js     → Step 0 logic only
  public/js/wizard/step_supplier.js   → Step 1 logic only
  public/js/wizard/step_details.js    → Step 2 logic only
  public/js/wizard/step_items.js      → Step 3 logic only
  public/js/wizard/step_review.js     → Step 4 logic only
  public/js/utils/rtl_handler.js      → RTL detection and styling only
  public/js/utils/confidence_badges.js → ✅⚠️❌ badge rendering only
  public/js/utils/form_populator.js    → writes extracted data to ERPNext form only

## LavaLoon Compatibility
- App: lavaloon-eg/ksa_compliance
- Tested versions: 0.55.x – 0.61.x
- Always check: frappe.db.exists("DocType", "Sales Invoice Additional Fields")
- Guard function lives in: helpers/compatibility.py → is_ksa_compliance_installed()
- Field map lives in: docs/FIELD_MAP.md — read this before touching any custom_ field
- Do NOT sign or submit to ZATCA — that is ksa_compliance's job entirely

## Dev Commands
- Start bench: bench start
- Run tests: bench run-tests --app fatura_ai
- Build JS: bench build --app fatura_ai
- Check LavaLoon fields: python docs/scripts/check_lavaloon_fields.py
- SSH to dev server: ssh $DEV_SERVER_SSH_USER@$DEV_SERVER_IP

## Git Standards
- Branches: main (prod), develop (integration), feature/F##-name, fix/name, prompt/name
- PRs: must reference feature ID e.g. [F03] AI extraction pipeline
- Max 400 lines diff per PR — split larger changes
- No direct commits to main
- Prompt-only changes always in separate prompt/ branch

## Testing Requirements
- Every function in api/ must have a test in tests/unit/
- Extraction accuracy target: >85% on full invoice test set
- Run full test suite before any PR is marked ready
- Test invoice set lives in: tests/invoices/ (arabic/, english/, mixed/)
- Scoring rubric lives in: tests/SCORING.md

## AI Providers — Priority Order
1. Anthropic (Claude Sonnet) — default, best for Arabic/mixed
2. OpenAI (GPT-4o) — secondary, fastest
3. Google (Gemini Flash) — tertiary, cheapest

## Extraction Prompts
- Main prompt: fatura_ai/templates/prompts/extraction_prompt.txt
- PO variant: fatura_ai/templates/prompts/po_extraction_prompt.txt
- Disambiguation: fatura_ai/templates/prompts/disambiguation_prompt.txt
- Log ALL prompt changes in: docs/PROMPT_LOG.md with before/after scores

## UX Principles (enforce in all UI work)
1. Zero learning curve — first import requires no documentation
2. Never block the user — cancel/back/skip available at every wizard step
3. Confidence is visible — green/amber/red on every matched field
4. RTL is first class — Arabic content always rendered right-to-left
5. Never auto-submit — populate only, user saves manually
6. Feel native to Frappe — use Frappe's own dialog system and patterns

## Onboarding Flow (built into app)
- Admin sees setup checklist on first login after install
- 3 setup steps: choose provider → test API key → run test import
- Test import is non-destructive (no doctype created)
- End user sees one-time tooltip on first visit to Purchase Invoice
- First-use wizard shows per-step tips (dismissible, shown once only)
- After 3 imports: reinforcement message about learning system

## Pricing
- Annual subscription per site
- Starter: SAR 1,200/year
- Professional: SAR 2,400/year
- Partner tier for BOT Solutions clients (direct)

## Who Built This
- Company: BOT Solutions, Jeddah, Saudi Arabia
- Owner: Talha (toetoe)
- GitHub: BOTSolutions8686
- Support: support@botsolutions.tech
