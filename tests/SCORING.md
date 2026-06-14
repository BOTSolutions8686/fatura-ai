# Invoice Test Scoring Rubric
# Used by: run_eval.py, arabic-tester agent, qa-reviewer agent

## Scoring Per Invoice (100 points total)

| Field                        | Points | Pass Condition                                    |
|------------------------------|--------|---------------------------------------------------|
| Supplier name extracted      | 20     | Name present and matches expected (fuzzy ≥85%)    |
| VAT number extracted         | 20     | Extracted, correct format (15 digits, starts/ends 3) |
| Invoice number extracted     | 10     | Exact match to fixture                            |
| Invoice date extracted       | 10     | Correct Gregorian date (YYYY-MM-DD)               |
| All line items extracted     | 20     | Count matches fixture ±1 (partial credit allowed) |
| Totals match                 | 20     | Subtotal + VAT + grand total all within 1 SAR     |

## Partial Credit — Line Items
- All items correct: 20 pts
- Missing 1 item: 14 pts
- Missing 2 items: 8 pts
- Missing 3+ items: 0 pts
- Wrong quantity on any item: -3 pts per item
- Wrong price on any item: -3 pts per item

## Pass Threshold
- Individual invoice: ≥85 pts = PASS
- Category average: ≥85% = PASS
- Overall average: ≥85% = PASS (required before moving to next sprint)

## Test Categories

arabic/     — Arabic-only invoices (target: 5+ invoices)
english/    — English-only invoices (target: 5+ invoices)
mixed/      — Mixed Arabic/English (target: 8+ invoices) ← most important
scanned/    — Low quality scans/photos (target: 5+ invoices)
multi-page/ — Multi-page invoices (target: 3+ invoices)
zatca/      — Invoices with QR codes and ZATCA fields (target: 4+ invoices)

## Fixture Format (tests/invoices/fixtures/invoice-name.json)
{
  "invoice_name": "arabic-001",
  "language": "arabic",
  "expected": {
    "supplier_name": "شركة الأمانة للتجارة",
    "supplier_name_en": "Al Amanah Trading Company",
    "supplier_vat": "300XXXXXXXXXX003",
    "supplier_cr": "XXXXXXXXXX",
    "invoice_number": "INV-2025-4821",
    "invoice_date": "2025-03-15",
    "due_date": "2025-04-15",
    "currency": "SAR",
    "subtotal": 11250.00,
    "vat_amount": 1687.50,
    "vat_percent": 15,
    "grand_total": 12937.50,
    "line_items": [
      {
        "description": "Consulting Services",
        "description_ar": "خدمات استشارية",
        "quantity": 1,
        "unit_price": 5000.00,
        "total": 5000.00
      }
    ]
  }
}

## Adding New Test Invoices
1. Place invoice file in correct category folder under tests/invoices/
2. Create matching fixture JSON in tests/invoices/fixtures/
3. Name both files identically (e.g. arabic-006.pdf + arabic-006.json)
4. Run: python tests/run_eval.py --invoice arabic-006 to verify fixture is correct
