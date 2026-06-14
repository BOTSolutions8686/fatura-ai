# Fatura AI — Product Specification (Living Document)
# Last updated: June 2026
# Status: Pre-development — approved for Sprint 0

---

## 1. Product Identity

**App Name:** Fatura AI (فاتورة AI)
**Frappe App ID:** fatura_ai
**Tagline:** AI-powered invoice importer for ERPNext — built for Saudi Arabia
**License:** MIT (open source, paid on marketplace)
**Pricing:** Annual subscription — SAR 1,200 (Starter) / SAR 2,400 (Professional)

---

## 2. Problem Statement

ERPNext users in Saudi Arabia receive supplier invoices as PDFs or images,
often in mixed Arabic/English. Manual data entry is slow and error-prone.
No existing Frappe app handles Arabic/English mixed invoice extraction
natively with guided ERPNext field mapping and LavaLoon ZATCA compatibility.

---

## 3. v1 Feature List (Must Have)

| ID  | Feature                                          | Priority |
|-----|--------------------------------------------------|----------|
| F01 | Import Invoice button on Purchase Invoice form   | Must     |
| F02 | Upload dialog — PDF and image                    | Must     |
| F03 | AI extraction (supplier, items, totals, ZATCA)   | Must     |
| F04 | Supplier matching — 3-tier                       | Must     |
| F05 | Guided 5-step wizard                             | Must     |
| F06 | Line item matching with learned mappings         | Must     |
| F07 | LavaLoon ksa_compliance field population         | Must     |
| F08 | Import Invoice button on Purchase Order form     | Must     |
| F09 | Fatura AI Settings doctype                       | Must     |
| F10 | Invoice AI Import Log doctype                    | Must     |
| F11 | RTL support in wizard                            | Must     |
| F12 | Typed error handling with user messages          | Must     |
| F13 | API key validation on settings save              | Must     |

---

## 4. v1.1 Feature List (Should Have)

| ID  | Feature                                          |
|-----|--------------------------------------------------|
| F14 | Re-import — overwrite existing draft invoice     |
| F15 | Extraction confidence score visible to user      |
| F16 | Item map management UI                           |
| F17 | Import history view per document                 |

---

## 5. v2 Feature List (Roadmap — Do Not Build Now)

| ID  | Feature                                          |
|-----|--------------------------------------------------|
| F18 | Sales Invoice import                             |
| F19 | Email-triggered import                           |
| F20 | Bulk import from folder                          |
| F21 | Prompt-based invoice entry                       |
| F22 | Mobile camera capture                            |

---

## 6. Wizard Flow (5 Steps)

**Step 0:** Upload — PDF/image drag & drop
**Step 1:** Supplier — confirm match (3 states: high/medium/no match)
**Step 2:** Invoice Details — number, date, due date, currency (all editable)
**Step 3:** Line Items — table with accept/change/skip per row
**Step 4:** Review & Populate — totals, ZATCA summary, final action

Rules:
- Cancel available at every step
- Back available at every step
- Never auto-submit — populate only

---

## 7. Matching Logic

**Tier 1 — Exact field match (free, instant)**
- VAT number exact match → confidence 1.0
- CR number exact match → confidence 0.95

**Tier 2 — RapidFuzz (fast, no API cost)**
- Score ≥85% → show match, ask user to confirm
- Score 65–84% → show as suggestion, user must select
- Score <65% → no match found

**Tier 3 — AI disambiguation (only when Tier 1 & 2 fail)**
- Send extracted name + top 3 fuzzy candidates to AI
- One small API call — used sparingly

**Item Map Learning:**
- Confirmed mappings stored in Invoice AI Item Map doctype
- After 3 confirmations → treated as Tier 1 confidence

---

## 8. ZATCA Fields (LavaLoon Compatible)

Fields to extract and populate (guarded by ksa_compliance install check):
- Seller VAT Number (15 digits, starts and ends with 3)
- Buyer VAT Number (same format)
- Invoice UUID
- QR Code (detected/decoded)
- Invoice Date + Time (ISO 8601)
- Invoice Type (B2B / B2C, inferred)

Fatura AI extracts and validates these fields.
Fatura AI does NOT sign or submit to ZATCA.
Signing and submission is handled entirely by ksa_compliance.

---

## 9. Onboarding Flow

**Stage 1 — Install**
Notification banner on first System Manager login after install.

**Stage 2 — Setup (Admin, 3 steps)**
Step 1: Choose AI provider
Step 2: Enter and test API key (must pass connection test)
Step 3: Run non-destructive test import

**Stage 3 — First Import (End User)**
One-time tooltip on Purchase Invoice form.
First-use wizard tips per step (dismissible, shown once).
Post-import success banner.

**Stage 4 — Reinforcement**
After 3 imports: message explaining learning system.

---

## 10. Error Taxonomy

| Exception                  | Trigger                          | User Message                              |
|----------------------------|----------------------------------|-------------------------------------------|
| InvalidAPIKeyError         | 401 from AI provider             | "API key not accepted. Check settings."   |
| ExtractionFailedError      | AI returned unusable output      | "Could not read invoice. Try again."      |
| FileTooLargeError          | Exceeds max file size            | "File too large. Max {n}MB."              |
| UnsupportedFileError       | Wrong mime type                  | "Unsupported format. Use PDF/PNG/JPG."    |
| LavaLoonNotInstalledError  | ksa_compliance not found         | ZATCA fields silently skipped (no error)  |
| MatchingError              | Matching pipeline failed         | "Matching failed. Please select manually."|

---

## 11. PO-Specific Rules

- No bill_no field on PO
- No ZATCA step in PO wizard (step 4 skipped entirely)
- Higher confidence threshold for items (90% vs 80% default)
- schedule_date defaults to invoice date + 30 days if not found
- Use po_extraction_prompt.txt (PO-specific prompt variant)
- Same supplier matching logic as Purchase Invoice

---

## 12. README Structure (for Marketplace)

Sections:
1. What it does
2. Requirements (ERPNext v14/v15, ksa_compliance recommended, API key)
3. What it does NOT do
4. Data privacy statement
5. Compatibility (tested ksa_compliance versions)
6. Installation
7. Support (support@botsolutions.tech)
