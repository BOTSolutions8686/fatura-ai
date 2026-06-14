# Fatura AI — Import Wizard Implementation Spec
<!-- Author: Claude Code | Date: 2026-06-15 -->
<!-- Implements: T007–T011 | Consumed by: Aider (Python), OpenCode (JS) -->
<!-- Base reference: CLAUDE.md, fatura_ai/api/import_wizard.py (Step 1) -->

---

## Overview

The wizard is a 5-step `frappe.ui.Dialog` (size: "large") that runs in the
context of an open Purchase Invoice or Purchase Order form. It never submits
the document. The user always saves manually.

```
Step 1  →  Step 2  →  Step 3  →  Step 4  →  Step 5
Upload     Extract    Supplier   Items      Review &
File       (auto)     Review     Review     Populate
```

Step 1 (`upload_invoice`) is already implemented. This spec covers Steps 2–5.

**Python rules (enforced by CLAUDE.md):**
- `@frappe.whitelist()` on every server function
- `frappe.get_doc()` for document reads; `frappe.db.get_value()` for scalar
- `_()` around every user-facing string
- Max 40 lines per function — split helpers as needed
- No auto-submit, no auto-save of the target PI/PO

**JavaScript rules:**
- `frappe.ui.Dialog` only — no native browser dialogs
- `__()` around every user-facing string
- Confidence rendered as ✅ (≥0.9) / ⚠️ (0.6–0.89) / ❌ (<0.6) badges
- Back button available at every step
- RTL: wrap Arabic content in `<span dir="rtl">...</span>`

---

## State carried between steps

The wizard passes `log_name` (a `Fatura Import Log` docname) between every
server call. All intermediate state lives in the log's `extracted_json` field.

The JS `FaturaWizard` instance holds:
```js
this.log_name          // string — set after Step 1
this.extracted         // object — set after Step 2
this.matched_supplier  // string — set after Step 3
this.confirmed_items   // array  — set after Step 4
```

---

## Step 2 — AI Extraction

### Purpose
Send the uploaded file to the configured AI provider, receive structured invoice
data, and store it in the log. This step runs automatically (no user input).
The dialog shows a spinner while the call is in flight.

### Python endpoint

```python
@frappe.whitelist()
def run_ai_extraction(log_name: str) -> dict:
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `log_name` | `str` | Name of the `Fatura Import Log` created in Step 1 |

**Algorithm:**
1. Load `Fatura Import Log` via `frappe.get_doc`.
2. Set `log.status = "Processing"` and save.
3. Call `fatura_ai.helpers.ai_extraction.extract_invoice_data(log.file_url)`.
4. On success: store result as `log.extracted_json`, set `log.provider_used`.
5. On any exception: call `log.mark_failed(str(e))`, commit, re-raise as
   `frappe.ValidationError` with `_("AI extraction failed: {0}").format(e)`.
6. Commit and return the parsed dict.

**Return value (success):**

```json
{
  "invoice_number":  "INV-2025-001",
  "invoice_date":    "2025-03-15",
  "due_date":        "2025-04-15",
  "currency":        "SAR",
  "supplier_name":   "شركة الأمانة للتجارة",
  "supplier_vat":    "310122393500003",
  "subtotal":        1000.00,
  "vat_amount":      150.00,
  "total_amount":    1150.00,
  "items": [
    {
      "description": "طابعة ليزر HP LaserJet",
      "qty":         2,
      "unit_price":  450.00,
      "vat_rate":    0.15,
      "line_total":  900.00
    }
  ],
  "provider":        "AnthropicProvider",
  "confidence":      0.92
}
```

**Return value (failure):**

```json
{ "error": "AI extraction failed: rate limit exceeded" }
```

The endpoint raises `frappe.ValidationError`; the JS catches it and shows the
error message with a Retry button.

**Error cases to handle:**

| Condition | Action |
|-----------|--------|
| `log_name` does not exist | `frappe.throw(_("Import log {0} not found"))` |
| `log.file_url` is empty | `frappe.throw(_("No file attached to this import log"))` |
| AI provider raises any exception | `log.mark_failed(str(e))`, commit, re-raise |
| Response JSON is malformed | `log.mark_failed("Malformed AI response")`, commit, re-raise |
| `log.status` is already "Success" | `frappe.throw(_("This import has already been completed"))` |

### JS behaviour

- Triggered automatically when `FaturaWizard._go_to(2)` is called.
- Show a full-width spinner with message `__("Extracting invoice data…")`.
- Disable the Back button while the call is in flight.
- On success: store result in `this.extracted`, auto-advance to Step 3.
- On error: hide spinner, show error message with `__("Retry")` and
  `__("Cancel")` buttons. Retry re-calls the same endpoint.

---

## Step 3 — Supplier Review

### Purpose
Run 3-tier supplier matching (Exact VAT → Fuzzy Name → AI candidates) against
the name/VAT extracted in Step 2. Present the result for user confirmation.
The user can accept, search for a different supplier, or create a new one.

### Python endpoint

```python
@frappe.whitelist()
def match_supplier(log_name: str, vendor_name: str, tax_id: str) -> dict:
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `log_name` | `str` | Name of the `Fatura Import Log` |
| `vendor_name` | `str` | Supplier name as extracted by AI (may be Arabic) |
| `tax_id` | `str` | VAT / tax registration number from invoice |

**Algorithm:**
1. Call `fatura_ai.helpers.supplier_matching.find_supplier(vat_number=tax_id, supplier_name=vendor_name)`.
2. Store `log.matched_supplier`, `log.supplier_match_method`, `log.supplier_confidence`.
3. Save log and commit.
4. Return the match dict.

**Return value:**

```json
{
  "supplier":    "SUP-00042",
  "supplier_name": "شركة الأمانة للتجارة",
  "method":      "Exact VAT",
  "confidence":  1.0,
  "candidates":  []
}
```

`candidates` is non-empty only when `method` is `"AI Disambiguation"`:

```json
{
  "supplier":    null,
  "supplier_name": null,
  "method":      "AI Disambiguation",
  "confidence":  0.0,
  "candidates": [
    { "supplier": "SUP-00042", "supplier_name": "شركة الأمانة", "score": 0.81 },
    { "supplier": "SUP-00107", "supplier_name": "الأمانة للتوريدات", "score": 0.74 }
  ]
}
```

**Confidence scale:**

| Value | Meaning | Badge |
|-------|---------|-------|
| 1.0 | Exact VAT match | ✅ |
| 0.6 – 0.99 | Fuzzy name match | ⚠️ |
| 0.0 | No match found | ❌ |

**Error cases to handle:**

| Condition | Action |
|-----------|--------|
| `vendor_name` and `tax_id` both empty | `frappe.throw(_("Cannot match supplier: no name or VAT in extracted data"))` |
| No suppliers in the system | Return `{supplier: null, method: "No Suppliers", confidence: 0.0, candidates: []}` — do not throw |
| `log_name` not found | `frappe.throw(_("Import log {0} not found"))` |

### JS behaviour

- On entry, auto-calls `match_supplier` with values from `this.extracted`.
- Show a two-column card:
  - Left: "Extracted from invoice" — raw `vendor_name` and `tax_id` (RTL if Arabic).
  - Right: "Matched in ERPNext" — supplier link, confidence badge, match method.
- If `confidence >= 0.9`: show green card, primary button = `__("Confirm & Continue")`.
- If `0.6 <= confidence < 0.9`: show amber card with warning, same primary button.
- If `confidence < 0.6` or `candidates` non-empty: show red card with
  disambiguation list. Each candidate is a clickable row that selects it.
- Always show a `__("Search suppliers…")` Link field as fallback.
- Primary button calls `confirm_supplier(log_name, supplier)` (existing endpoint)
  then advances to Step 4.
- Back button returns to Step 1 (re-upload is allowed).

---

## Step 4 — Item Matching

### Purpose
Run 3-tier matching (Learned → Exact Code → Fuzzy Name → AI placeholder) for
every line item the AI extracted. Present results in an editable table. The user
corrects wrong matches before proceeding.

### Python endpoint

```python
@frappe.whitelist()
def match_items(log_name: str, line_items_json: str) -> dict:
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `log_name` | `str` | Name of the `Fatura Import Log` |
| `line_items_json` | `str` | JSON string — array of extracted item dicts (from `this.extracted.items`) |

**Why JSON string?** Frappe's `@frappe.whitelist()` auto-JSON-parses only top-level
scalars. Pass complex arrays as stringified JSON and parse inside the function.

**Algorithm:**
1. Parse `line_items_json` with `frappe.parse_json`.
2. Call `fatura_ai.helpers.item_matching.match_items(items, supplier=log.matched_supplier)`.
3. Update `log.items_count` and `log.items_matched`.
4. Save log and commit.
5. Return the matched items list.

**Return value:**

```json
{
  "items": [
    {
      "description":   "طابعة ليزر HP LaserJet",
      "qty":           2,
      "unit_price":    450.00,
      "line_total":    900.00,
      "matched_item":  "IT-00123",
      "item_name":     "HP LaserJet Pro M404n",
      "method":        "Learned",
      "confidence":    1.0,
      "candidates":    []
    },
    {
      "description":   "حبر طابعة",
      "qty":           5,
      "unit_price":    35.00,
      "line_total":    175.00,
      "matched_item":  null,
      "item_name":     null,
      "method":        "Unmatched",
      "confidence":    0.0,
      "candidates": [
        { "item_code": "IT-00201", "item_name": "HP Toner 85A", "score": 0.71 }
      ]
    }
  ],
  "summary": {
    "total":    2,
    "matched":  1,
    "partial":  0,
    "unmatched": 1
  }
}
```

**Confidence scale:**

| Value | Meaning | Badge |
|-------|---------|-------|
| 1.0 | Learned mapping or exact code | ✅ |
| 0.6 – 0.99 | Fuzzy match | ⚠️ |
| 0.0 | Unmatched | ❌ |

**Error cases to handle:**

| Condition | Action |
|-----------|--------|
| `line_items_json` is empty or `[]` | Return `{items: [], summary: {total:0, matched:0, partial:0, unmatched:0}}` — do not throw; warn in JS |
| `log.matched_supplier` is not set | Allow matching without supplier scope (global mapping only) |
| `frappe.parse_json` fails | `frappe.throw(_("Invalid item list — please retry from Step 2"))` |
| `log_name` not found | `frappe.throw(_("Import log {0} not found"))` |

### JS behaviour

- On entry, auto-calls `match_items` with `this.extracted.items`.
- Show a table with columns: Original Text | Qty | Unit Price | Matched Item | Confidence.
- Each "Matched Item" cell is a `frappe.ui.form.ControlLink` targeting the `Item` doctype,
  pre-filled with `matched_item`. The user can edit inline.
- Confidence column shows ✅/⚠️/❌ badge.
- Show a summary bar: "X of Y items matched" with colour coding.
- If any item is ❌ (unmatched), show amber banner: `__("{0} items need manual matching")`.
- "Add Row" button allows inserting extra items not on the invoice.
- "Remove Row" (×) on each row.
- Primary button = `__("Confirm Items")` — enabled even if some are unmatched
  (user may choose to skip an item). Calls `confirm_items` (existing endpoint)
  then advances to Step 5.
- Back button returns to Step 3.

---

## Step 5 — Review & Populate

### Purpose
Show a read-only summary of everything the wizard will write to the document.
On confirmation, call `confirm_import` to create a **Draft** Purchase Invoice
or Purchase Order via `frappe.new_doc`. The wizard then closes and the user
is redirected to the new document. They must save/submit manually.

### Python endpoint

```python
@frappe.whitelist()
def confirm_import(log_name: str) -> dict:
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `log_name` | `str` | Name of the `Fatura Import Log` |

All data (supplier, items, extracted fields) is read from the log's
`extracted_json` and related fields. The JS does not re-send item data here.

**Algorithm:**
1. Load log and parse `extracted_json`.
2. Assert `log.matched_supplier` is set; throw if not.
3. Assert at least one item has a `matched_item`; throw if not.
4. Call `_build_doctype_payload(log, extracted)` — returns a field map.
5. Create the target document:
   ```python
   doc = frappe.new_doc(log.source_doctype)
   doc.supplier       = log.matched_supplier
   doc.bill_no        = extracted.get("invoice_number")
   doc.bill_date      = extracted.get("invoice_date")
   # ... all fields from payload
   for item in payload["items"]:
       doc.append("items", item)
   doc.insert(ignore_permissions=True)   # creates Draft — NEVER .submit()
   ```
6. Update `log.status = "Success"`, `log.source_docname = doc.name`.
7. Commit and return.

**Return value:**

```json
{
  "doctype":  "Purchase Invoice",
  "docname":  "ACC-PINV-2025-00042",
  "status":   "Draft",
  "url":      "/app/purchase-invoice/ACC-PINV-2025-00042"
}
```

**Error cases to handle:**

| Condition | Action |
|-----------|--------|
| `log.matched_supplier` is null | `frappe.throw(_("Supplier must be confirmed before import"))` |
| Zero items with `matched_item` set | `frappe.throw(_("At least one item must be matched before import"))` |
| `frappe.new_doc` raises `ValidationError` | Catch, call `log.mark_failed(str(e))`, commit, re-raise |
| `log.status` is already "Success" | `frappe.throw(_("This import has already been completed. Open {0}.").format(log.source_docname))` |
| `log_name` not found | `frappe.throw(_("Import log {0} not found"))` |

**NEVER call `.submit()` on the created document.** This is an absolute rule.

### Helper — `_build_doctype_payload(log, extracted) → dict`

This is a private function (no `@frappe.whitelist()`). Lives in `api/extractor.py`.

```python
def _build_doctype_payload(log, extracted: dict) -> dict:
    return {
        "supplier":      log.matched_supplier,
        "bill_no":       extracted.get("invoice_number"),
        "bill_date":     _parse_date(extracted.get("invoice_date")),
        "due_date":      _parse_date(extracted.get("due_date")),
        "currency":      extracted.get("currency", "SAR"),
        "items":         _build_items(extracted.get("items", []), log),
        "taxes":         _build_taxes(extracted),
    }
```

`_parse_date`, `_build_items`, `_build_taxes` must each be ≤40 lines.

### JS behaviour

- On entry, call `get_review_summary(log_name)` (existing endpoint).
- Render a read-only summary card:
  ```
  Supplier:         شركة الأمانة للتجارة ✅
  Invoice No:       INV-2025-001
  Invoice Date:     15 Mar 2025
  Due Date:         15 Apr 2025
  Subtotal:         SAR 1,000.00
  VAT (15%):        SAR 150.00
  Total:            SAR 1,150.00

  Items (2 matched, 0 unmatched):
  ┌─────────────────────────────┬──────┬───────────┬───────────┐
  │ Item                        │ Qty  │ Unit Price│ Total     │
  ├─────────────────────────────┼──────┼───────────┼───────────┤
  │ HP LaserJet Pro M404n  ✅   │  2   │  450.00   │  900.00   │
  │ HP Toner 85A           ⚠️   │  5   │   35.00   │  175.00   │
  └─────────────────────────────┴──────┴───────────┴───────────┘
  ```
- If any unmatched items remain, show amber warning (do not block).
- Primary button = `__("Import to {doctype}")` where `{doctype}` is localised.
- On success: close dialog, navigate to new doc via
  `frappe.set_route("Form", data.doctype, data.docname)`.
- Show `frappe.show_alert({message: __("Invoice imported as Draft"), indicator: "green"})`.
- Back button returns to Step 4.
- NEVER show a Submit button.

---

## Endpoint Summary Table

| Step | Function | Method | File |
|------|----------|--------|------|
| 1 | `upload_invoice(file_url, source_doctype, source_docname)` | `@frappe.whitelist()` | `api/import_wizard.py` |
| 2 | `run_ai_extraction(log_name)` | `@frappe.whitelist()` | `api/import_wizard.py` |
| 3 | `match_supplier(log_name, vendor_name, tax_id)` | `@frappe.whitelist()` | `api/import_wizard.py` |
| 4 | `match_items(log_name, line_items_json)` | `@frappe.whitelist()` | `api/import_wizard.py` |
| 5 | `confirm_import(log_name)` | `@frappe.whitelist()` | `api/import_wizard.py` |

Support:
| Function | File |
|----------|------|
| `find_supplier(vat_number, supplier_name)` | `helpers/supplier_matching.py` |
| `match_items(items, supplier)` | `helpers/item_matching.py` |
| `persist_mappings(confirmed_items, supplier)` | `helpers/item_matching.py` |
| `extract_invoice_data(file_url)` | `helpers/ai_extraction.py` |
| `validate_file(file_url)` | `api/extractor.py` |
| `_build_doctype_payload(log, extracted)` | `api/extractor.py` |

---

## Data Contract — `extracted_json` schema

All intermediate steps read from `Fatura Import Log.extracted_json`. Aider
must not invent field names — use exactly these keys:

```
invoice_number    str   — bill reference on the invoice
invoice_date      str   — ISO 8601 date or DD/MM/YYYY or Arabic numeral date
due_date          str   — same format options as invoice_date
currency          str   — ISO 4217 (default "SAR")
supplier_name     str   — as printed on invoice (may be Arabic)
supplier_vat      str   — 15-digit Saudi VAT number
subtotal          float
vat_amount        float
total_amount      float
confidence        float — overall extraction confidence 0.0–1.0
provider          str   — class name of provider used
items             list  — see item schema below
```

Item sub-schema:
```
description   str   — text on invoice line (may be Arabic)
qty           float
unit_price    float
vat_rate      float — e.g. 0.15 for 15%
line_total    float
item_code     str   — only set after item matching
matched_item  str   — ERPNext Item.name, null until matched
method        str   — "Learned" / "Exact Code" / "Fuzzy Name" / "Unmatched"
confidence    float — 0.0–1.0
candidates    list  — [{item_code, item_name, score}]
```

---

## ksa_compliance Integration Note

When writing to `Purchase Invoice`, check `is_ksa_compliance_installed()` from
`helpers/compatibility.py` before setting any `custom_` field. Never set ZATCA
fields directly — that is ksa_compliance's job (T012).

---

## Testing Requirements (CLAUDE.md rule 9)

Each endpoint implemented by T007–T011 requires a unit test in `tests/unit/`:

| Task | Test file | Min test cases |
|------|-----------|----------------|
| T007 | `tests/unit/test_run_ai_extraction.py` | mock provider success; provider throws; already-completed log |
| T008 | N/A (JS-only step) | — |
| T009 | `tests/unit/test_match_supplier.py` | exact VAT; fuzzy hit; no match; null inputs |
| T010 | `tests/unit/test_match_items.py` | learned mapping; exact code; fuzzy; unmatched; empty list |
| T011 | `tests/unit/test_confirm_import.py` | happy path PI; happy path PO; no supplier; no items; already done |
