# Skill: LavaLoon ZATCA Fields Reference
# Read this before touching any ZATCA-related fields in code.

## Core Rule
NEVER access custom_ fields without checking ksa_compliance is installed.
Use: from fatura_ai.helpers.compatibility import is_ksa_compliance_installed

## Installation Check Pattern
if is_ksa_compliance_installed():
    doc.custom_vat_registration_number = extracted_data.get("supplier_vat")
    doc.custom_cr_number = extracted_data.get("supplier_cr")
# If not installed: silently skip. Never raise an error.

## Fields on Purchase Invoice (verify in docs/FIELD_MAP.md)
custom_vat_registration_number  — Supplier VAT number (15 digits)
custom_cr_number                — Supplier CR number (10 digits)
custom_zatca_invoice_reference  — Supplier's original invoice number

## ZATCA Field Validation Rules
VAT Number:
  - Exactly 15 digits
  - Starts with 3
  - Ends with 3
  - Regex: ^3\d{13}3$

CR Number:
  - Exactly 10 digits
  - Regex: ^\d{10}$

Invoice Date:
  - Must be ISO 8601: YYYY-MM-DD
  - Convert from Hijri if needed (use helpers/date_helpers.py)

## What Fatura AI Does NOT Do
- Does NOT generate ZATCA XML
- Does NOT sign invoices (Phase 2 cryptographic signing)
- Does NOT submit to Fatoora portal
- Does NOT generate QR codes
All of the above is handled by ksa_compliance after the user submits the invoice.

## Invoice Types
B2B (Standard Invoice): Both buyer and seller are VAT-registered businesses
B2C (Simplified Invoice): Buyer is an individual (no buyer VAT number)
Fatura AI detects type based on whether buyer VAT number is present on invoice.

## QR Code
Fatura AI detects if a QR code is present on the invoice image.
It decodes it to verify ZATCA TLV structure if possible.
It does NOT generate or validate QR codes — that is ksa_compliance's job.
