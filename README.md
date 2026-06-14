# Fatura AI

**AI-powered invoice importer for ERPNext — built for Saudi Arabia**

Fatura AI extracts supplier invoice data from PDFs and images using AI,
then guides you through populating your ERPNext Purchase Invoice with
a simple 5-step wizard — with full Arabic/English support.

---

## What it does

- Upload a supplier invoice (PDF, photo, or image)
- AI extracts: supplier, items, amounts, dates, VAT, ZATCA fields
- Smart matching to your existing ERPNext suppliers and items
- Guided wizard confirms every field before populating the form
- You review and save — nothing is auto-submitted

Built specifically for Saudi Arabia:
- Arabic/English mixed invoice support
- ZATCA Phase 2 field extraction (seller VAT, buyer VAT, QR detection)
- Compatible with LavaLoon KSA Compliance app

---

## Requirements

- ERPNext v14 or v15
- LavaLoon KSA Compliance app (recommended for full ZATCA field support)
- API key from one of: Anthropic, OpenAI, or Google AI

---

## What Fatura AI does NOT do

- Does not sign or submit invoices to ZATCA (handled by KSA Compliance app)
- Does not process Sales Invoices (v2 roadmap)
- Does not process invoices in bulk (v2 roadmap)
- Does not parse emails (v2 roadmap)

---

## Data Privacy

Your invoice files are sent to your chosen AI provider for extraction.
Fatura AI does not store or transmit your data to any other server.
Review your AI provider's data privacy policy before use.

---

## Compatibility

Tested with ksa_compliance versions 0.55.x – 0.61.x

---

## Installation

```bash
bench get-app https://github.com/BOTSolutions8686/fatura_ai
bench --site your-site.com install-app fatura_ai
```

Then open Fatura AI Settings and complete the 3-step setup.

---

## Support

support@botsolutions.tech
https://botsolutions.tech

Built by BOT Solutions — ERPNext implementation and support, Jeddah, Saudi Arabia.
