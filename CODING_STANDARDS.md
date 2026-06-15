# Fatura AI — Coding Standards

These rules exist to prevent the class of bugs found during Sprint 2 testing.
All agents MUST follow them. No exceptions.

---

## 1. Python Module Paths

Frappe app module paths always repeat the app name:

```
# CORRECT
from fatura_ai.fatura_ai.doctype.invoice_ai_item_map.invoice_ai_item_map import InvoiceAIItemMap
from fatura_ai.fatura_ai.doctype.fatura_import_log.fatura_import_log import FaturaImportLog

# WRONG — missing the inner module name
from fatura_ai.doctype.invoice_ai_item_map.invoice_ai_item_map import InvoiceAIItemMap
```

Pattern: `{app_name}.{app_name}.doctype.{doctype_snake}.{doctype_snake}`

---

## 2. Frappe Imports — Always Include `_`

Every Python file that uses the `_()` translation function must import it:

```python
# CORRECT — always at the top
import frappe
from frappe import _

# WRONG — _ is not a Python builtin
frappe.throw(_("some message"))  # NameError if _ not imported
```

---

## 3. Function Names Must Match Across JS and Python

Before a JS file calls a Python method, verify the Python function name exactly.

| Python function | JS method string |
|---|---|
| `run_ai_extraction` | `"fatura_ai.api.import_wizard.run_ai_extraction"` |
| `build_doctype_payload` | called as `build_doctype_payload(...)` — no underscore prefix |

Rules:
- Private helpers (not whitelisted) use a `_` prefix: `def _build_title(self)`
- Public API endpoints (whitelisted or imported by name) use NO underscore prefix
- Never add/remove `_` when referencing a function across files — copy the name exactly

---

## 4. DocType Field Names — Check Before Using

Do not assume a field exists on a DocType. Before using `doc.some_field`, confirm the
field is declared in the DocType JSON (`fields` array).

```python
# WRONG — vendor_name is not a field on FaturaImportLog
vendor_name = log.vendor_name  # AttributeError

# CORRECT — read from the stored JSON blob
extracted = frappe.parse_json(log.extracted_json or "{}")
vendor_name = extracted.get("vendor_name")
```

The canonical field list for `FaturaImportLog`:
`title, status, import_date, provider_used, source_doctype, source_docname,
file_url, supplier_match_method, matched_supplier, supplier_confidence,
items_count, items_matched, processing_time, extracted_json, error_message`

---

## 5. DocType Select Field Values — Check JSON Before Using

Select fields only accept values defined in the DocType JSON `options`.
Before setting a select field, check the allowed values.

| DocType | Field | Allowed values |
|---|---|---|
| Fatura Import Log | `status` | `Draft, Processing, Success, Partial, Failed` |
| Fatura Import Log | `supplier_match_method` | `Exact VAT, Fuzzy Name, AI Disambiguation, Manual` |

Never invent new values (`"Extracted"`, `"VAT Match"`, `"Name Match"` are wrong).

---

## 6. New Source Documents — Skip Link Validation

When the wizard is opened on an unsaved ERPNext form, `frm.docname` is a temp string
like `"new-purchase-invoice-xxx"`. This is NOT a real database record.

When inserting a `FaturaImportLog` with such a `source_docname`:

```python
log.flags.ignore_links = True
log.insert(ignore_permissions=True)
```

And store `None` (not the temp string) so Frappe doesn't reject it later:
```python
real_docname = source_docname if source_docname and not source_docname.startswith("new-") else None
```

---

## 7. JS File Deployment — Always Copy to Both Containers

After editing any JS file under `public/js/`, copy to BOTH Docker containers:

```bash
# Backend (source of truth for bench build)
docker cp <file> frappe_docker-backend-1:/home/frappe/frappe-bench/apps/fatura_ai/fatura_ai/public/js/<file>

# Frontend (what nginx actually serves)
docker cp <file> frappe_docker-frontend-1:/home/frappe/frappe-bench/sites/assets/fatura_ai/js/<file>
```

A cache bust via `bench clear-cache` + hard refresh is needed after every JS change.

---

## 8. Supplier / Item Match Method Values

The `supplier_match_method` field only accepts these exact strings:
- `"Exact VAT"` — matched via tax_id
- `"Fuzzy Name"` — matched via fuzzy name comparison
- `"AI Disambiguation"` — matched via AI (or no match, tier 3 fallback)
- `"Manual"` — user overrode the match

---

## 9. Patches Format — Frappe v16

`patches.txt` in Frappe v16 uses `[pre_model_sync]` / `[post_model_sync]` sections,
NOT `[pre_migrate]` / `[post_migrate]`. Using the wrong headers causes `KeyError` on install.

---

## 10. Don't Modify ERPNext Core

All code must live inside the `fatura_ai` app. The button on Purchase Invoice and
Purchase Order is added via `frappe.ui.form.on(...)` in our own JS — not by patching
ERPNext source. Users install the app; nothing else changes on their system.
