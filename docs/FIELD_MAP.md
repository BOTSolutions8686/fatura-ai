# LavaLoon KSA Compliance — Field Compatibility Map
# App: lavaloon-eg/ksa_compliance
# Repo: https://github.com/lavaloon-eg/ksa_compliance
# Last verified: June 2026

---

## IMPORTANT
Before accessing ANY field prefixed with custom_ on Purchase Invoice or
Purchase Order, always call is_ksa_compliance_installed() from helpers/compatibility.py.
If ksa_compliance is not installed, skip ZATCA field population silently.

---

## Tested Versions
0.55.x — 0.61.x (confirmed compatible)

## How to Check Installed Version
frappe.get_installed_apps()  # check if ksa_compliance is in list
frappe.db.exists("DocType", "Sales Invoice Additional Fields")  # existence check

---

## Custom Fields Added to Purchase Invoice

| Field Name                        | Type | Description                        |
|-----------------------------------|------|------------------------------------|
| custom_vat_registration_number    | Data | Supplier VAT — 15 digits           |
| custom_cr_number                  | Data | Supplier CR — 10 digits            |
| custom_zatca_invoice_reference    | Data | Supplier's original invoice number |

**VERIFY THESE FIELD NAMES** against your installed version before using.
Run: python docs/scripts/check_lavaloon_fields.py

---

## Custom Fields Added to Sales Invoice (for reference — v2 only)

Sales Invoice Additional Fields is a child doctype created by ksa_compliance.
Fatura AI does not touch Sales Invoice in v1.

---

## ZATCA Field Validation Rules

| Field          | Rule                                      |
|----------------|-------------------------------------------|
| VAT Number     | Exactly 15 digits, starts with 3, ends with 3 |
| CR Number      | Exactly 10 digits                         |
| Invoice Date   | ISO 8601 format (YYYY-MM-DD)              |
| Currency       | SAR (default) or valid currency code      |

---

## What Fatura AI Does vs ksa_compliance

| Action                        | Fatura AI | ksa_compliance |
|-------------------------------|-----------|----------------|
| Extract fields from PDF/image | ✅        | ❌             |
| Validate VAT number format    | ✅        | ✅             |
| Populate Purchase Invoice     | ✅        | ❌             |
| Generate ZATCA XML            | ❌        | ✅             |
| Sign invoice (Phase 2)        | ❌        | ✅             |
| Submit to Fatoora portal      | ❌        | ✅             |
| Generate QR code              | ❌        | ✅             |

---

## Update Protocol

When ksa_compliance releases a new version:
1. GitHub Action lavaloon_monitor.yml will open an issue automatically
2. Developer installs new version on dev bench
3. Runs: python docs/scripts/check_lavaloon_fields.py
4. Updates this file with verified field names
5. Updates "Tested Versions" section above
6. Bumps fatura_ai patch version if any field names changed
