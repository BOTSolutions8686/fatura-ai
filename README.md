# Fatura AI — فاتورة AI

**AI-powered supplier invoice import for ERPNext — built for the Saudi market**

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![ERPNext v16](https://img.shields.io/badge/ERPNext-v16-0089ff)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

Upload a supplier invoice PDF and let Fatura AI do the heavy lifting:

1. **Upload** — drop a PDF, PNG, JPG, or WEBP into the wizard
2. **AI extraction** — DeepSeek / OpenAI / Anthropic / Google Gemini reads every field automatically
3. **ZATCA QR decode** — QR code on Saudi invoices gives ground-truth supplier VAT, name, and amounts
4. **Supplier match** — matched to your ERPNext records by VAT number, fuzzy name, or created on the fly
5. **Item match** — line items matched to existing ERPNext Items, or auto-created with your approval
6. **Draft Purchase Invoice** — all fields pre-filled; you review and save — nothing is auto-submitted
7. **Arabic-native** — supplier names and item descriptions in Arabic are handled and displayed correctly
8. **Duplicate detection** — same invoice number from the same supplier won't be imported twice
9. **Sanity checks** — VAT total and line-item total mismatches are flagged before anything is saved
10. **Full import history** — every import logged with status: Draft → Extracted → Confirmed → Imported → Failed

---

## Features

- **Multi-provider AI** — DeepSeek (recommended), OpenAI GPT-4o, Anthropic Claude, Google Gemini; automatic retry and fallback if one provider fails
- **ZATCA Phase 1 & 2 QR parsing** — TLV-format QR decoded on-device; no external service needed
- **3-tier supplier matching** — Exact VAT number → Fuzzy name (RapidFuzz) → Manual selection
- **VAT ambiguity resolution** — one VAT number, multiple companies (common in Saudi holding groups) resolved via a disambiguation picker
- **Item matching with learned mappings** — Fatura AI remembers your corrections and applies them next time
- **Auto-create suppliers and items** — missing records created from extracted data with one click
- **Arabic text normalization** — NFC normalization for accurate fuzzy matching on Arabic names
- **Currency extraction** — detected from invoice and mapped to ERPNext currency list
- **Cost centre auto-assign** — defaults to the company's default cost centre
- **UOM extraction** — unit-of-measure pulled from invoice with fallback to ERPNext default
- **Image-heavy PDF detection** — warns when a PDF is scanned/image-only (affects extraction quality)
- **Step progress bar** — Upload → AI Extraction → Supplier → Items → Review → Done
- **Inline item confirmation table** — ERPNext-style table; edit quantity, rate, or description before import

---

## Supported Version

| Component | Version |
|---|---|
| Frappe / ERPNext | v16 |
| Python | 3.10+ |
| LavaLoon KSA Compliance | 0.55.x – 0.61.x (optional) |

---

## Requirements

**System packages (Ubuntu/Debian):**
```bash
sudo apt-get install -y poppler-utils libzbar0
```

**Python packages:**
```
pyzbar
pdf2image
pdfminer.six
fuzzywuzzy
python-levenshtein
rapidfuzz
```

**AI provider API key** — at least one of:
- DeepSeek (recommended for cost): https://platform.deepseek.com
- OpenAI: https://platform.openai.com
- Anthropic: https://console.anthropic.com
- Google AI: https://aistudio.google.com

---

## Installation

```bash
# From your frappe-bench directory
bench get-app https://github.com/botsolutions-tech/fatura_ai
bench --site your-site install-app fatura_ai
bench --site your-site migrate

# System dependencies
sudo apt-get install -y poppler-utils libzbar0

# Python dependencies
pip install pyzbar pdf2image pdfminer.six fuzzywuzzy python-levenshtein rapidfuzz
```

---

## Configuration

1. In ERPNext, search for **Fatura AI Settings**
2. Select your AI provider (DeepSeek recommended)
3. Enter your API key
4. Save

That's it. No other setup is required for basic use.

---

## Usage

1. Open any **Purchase Invoice** (new or existing draft)
2. Click **فاتورة AI — Import Invoice** in the toolbar
3. Upload the supplier invoice PDF or image
4. The wizard walks you through each step — confirm the supplier, review line items, check totals
5. Click **Import** — the Purchase Invoice is populated and ready for your review
6. Submit manually when satisfied

---

## Saudi Market Specifics

- **ZATCA QR codes** (Phase 1 and Phase 2) are decoded on-device using TLV parsing — no API call needed for QR data
- **Arabic** supplier names and item descriptions are stored and displayed right-to-left
- **Multi-CR scenarios** — one VAT number registered under multiple companies (a common pattern in Saudi holding structures) are handled with a disambiguation picker so you choose the correct supplier record
- **LavaLoon KSA Compliance** integration populates `custom_zatca_*` fields when the app is installed; Fatura AI does NOT sign or submit invoices to ZATCA — that is the compliance app's job

---

## What Fatura AI Does NOT Do

- Does not sign or submit invoices to ZATCA (handled by LavaLoon KSA Compliance)
- Does not process Sales Invoices (planned for v2)
- Does not process emails (planned for v2)
- Does not bulk-import multiple invoices at once (planned for v2)
- Does not capture from a mobile camera (planned for v2)

---

## Data Privacy

Invoice files are sent to your chosen AI provider for extraction. Fatura AI does not transmit your data to any BOT Solutions server. Review your AI provider's data retention policy before use in production.

---

## License

MIT — see [LICENSE](LICENSE)

---

## Developed By

**BOT Solutions** — ERPNext implementation and support, Jeddah, Saudi Arabia
info@botsolutions.tech · https://botsolutions.tech
