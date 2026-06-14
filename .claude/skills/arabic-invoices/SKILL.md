# Skill: Arabic Invoice Extraction Patterns
# Read this before writing or modifying extraction prompts or matching logic.

## Common Arabic Field Labels on Saudi Invoices

| Arabic Label                  | English Meaning              | Field              |
|-------------------------------|------------------------------|--------------------|
| الرقم الضريبي                  | VAT Registration Number      | supplier_vat       |
| السجل التجاري                  | Commercial Registration (CR) | supplier_cr        |
| رقم الفاتورة                   | Invoice Number               | invoice_number     |
| تاريخ الفاتورة                 | Invoice Date                 | invoice_date       |
| تاريخ الاستحقاق                | Due Date                     | due_date           |
| المجموع قبل الضريبة            | Subtotal (before VAT)        | subtotal           |
| ضريبة القيمة المضافة           | VAT Amount                   | vat_amount         |
| نسبة الضريبة                   | VAT Rate                     | vat_percent        |
| المجموع شامل الضريبة           | Grand Total Including VAT    | grand_total        |
| الكمية                        | Quantity                     | quantity           |
| سعر الوحدة                     | Unit Price                   | unit_price         |
| الإجمالي                      | Line Total                   | line_total         |
| وصف                           | Description                  | description        |

## Mixed Invoice Patterns (Most Common in Saudi Arabia)

- Company name appears in BOTH Arabic and English on the same invoice
- Numbers are ALWAYS in Western format (1, 2, 3) even on fully Arabic invoices
- Currency: SAR or ر.س or SR — all mean Saudi Riyal
- VAT rate is almost always 15% — confirm if invoice states otherwise
- Dates may appear in Hijri (e.g. 1446/09/15) — must convert to Gregorian
- Building number (رقم المبنى) is a 4-digit number, part of Saudi address format
- Postal code (الرمز البريدي) is 5 digits in Saudi addresses

## Hijri to Gregorian Conversion
Use helpers/date_helpers.py → hijri_to_gregorian(hijri_date_string)
Hijri format on invoices: YYYY/MM/DD or DD/MM/YYYY (Hijri)
Always output Gregorian ISO 8601: YYYY-MM-DD

## Common Matching Failures — Arabic Supplier Names

Problem: "شركة الراجحي التجارية" vs "Al Rajhi Trading Company"
These are the same company — Arabic and English versions of the same name.
Matching must handle:
- Al / Al- prefix variations
- شركة (company), مؤسسة (establishment), مجموعة (group) prefix handling
- ذ.م.م / LLC suffix variations

Solution: Try matching on VAT number first (Tier 1).
If VAT number not available, fuzzy match BOTH the Arabic and English names.
Pass both to the AI disambiguation (Tier 3) if fuzzy fails.

## Line Item Splitting
Some invoices show multi-line item descriptions that span visual rows.
The AI must treat these as one item, not multiple.
Signal: second line has no quantity or price — it's a continuation.

## Low Quality Scans
Mobile camera photos of invoices are common.
Extraction will be less accurate. Lower expected confidence threshold.
The wizard will show more amber/red indicators — this is expected behavior.
Instruct users to use flat, well-lit scans when possible.

## Invoice Structure Variations
Saudi invoices do not follow one standard layout.
Common variations:
- Header: seller info top-left, buyer top-right (or reversed)
- Items table: may have Arabic column headers only
- Totals: may appear mid-page (after items) or bottom
- VAT breakdown: may be in a separate box from the grand total
- Stamp/signature: common in Saudi invoices — ignore for extraction
