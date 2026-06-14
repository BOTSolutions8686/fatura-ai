# /check-lavaloon
# Verifies LavaLoon ksa_compliance field compatibility with current installed version.

When this command is invoked:

1. Read .env to get DEV_SITE_NAME and SSH credentials.

2. SSH to dev server and run:
   bench --site $DEV_SITE_NAME execute fatura_ai.helpers.compatibility.get_ksa_compliance_version

3. Compare the installed version against tested versions in docs/FIELD_MAP.md.

4. For each custom field listed in docs/FIELD_MAP.md:
   Check it exists on the Purchase Invoice doctype on the dev server:
   bench --site $DEV_SITE_NAME execute \
     "frappe.get_meta('Purchase Invoice').get_field('custom_vat_registration_number')"

5. Report:

   LAVALON COMPATIBILITY CHECK
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Installed version: X.XX.X
   Tested range: 0.55.x – 0.61.x
   Status: ✅ COMPATIBLE / ⚠️ WARNING / ❌ INCOMPATIBLE

   Field verification:
   custom_vat_registration_number  ✅ / ❌
   custom_cr_number                ✅ / ❌
   custom_zatca_invoice_reference  ✅ / ❌

6. If WARNING or INCOMPATIBLE:
   "Update docs/FIELD_MAP.md with correct field names before continuing development."
   List which fields need verification.

7. If all PASS:
   "LavaLoon compatibility confirmed. Safe to continue."
