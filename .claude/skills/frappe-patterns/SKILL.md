# Skill: Frappe Coding Patterns
# Read this before writing any Python or JavaScript for this Frappe app.

## Python — Core Patterns

### Reading documents
frappe.get_doc("Purchase Invoice", invoice_name)
frappe.db.get_value("Supplier", {"tax_id": vat_number}, "name")
frappe.db.get_list("Item", filters={"item_name": ["like", "%consulting%"]})

### Checking if app is installed
frappe.db.exists("DocType", "Sales Invoice Additional Fields")

### Whitelisted API endpoint
@frappe.whitelist()
def my_endpoint(param1, param2):
    # accessible from JS via frappe.call()
    return {"result": value}

### Calling from JavaScript
frappe.call({
    method: "fatura_ai.api.extractor.extract_invoice",
    args: { file_url: file_url },
    callback: function(r) {
        if (r.message) { ... }
    }
});

### Translations
Python: frappe._(  "Supplier not found")
JS:     __("Supplier not found")

### Error handling
raise frappe.ValidationError(_("VAT number format is invalid"))

## JavaScript — Frappe Dialog Pattern

const dialog = new frappe.ui.Dialog({
    title: __("Import Invoice"),
    fields: [],
    primary_action_label: __("Next"),
    primary_action(values) {
        // handle action
    }
});
dialog.show();

## Frappe Form — Button Injection

frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        if (frm.is_new()) {
            frm.add_custom_button(__("Import Invoice"), function() {
                // open wizard
            });
        }
    }
});

## Hooks.py — Keep it thin

# hooks.py should only have declarations, never logic
app_include_js = ["/assets/fatura_ai/js/purchase_invoice.js"]
doctype_js = {"Purchase Invoice": "public/js/purchase_invoice.js"}

## File Handling

# Get uploaded file content
file_doc = frappe.get_doc("File", {"file_url": file_url})
file_content = file_doc.get_content()  # returns bytes

## Settings Doctype (Single)

settings = frappe.get_single("Fatura AI Settings")
api_key = settings.get_password("api_key")
provider = settings.ai_provider
threshold = settings.confidence_threshold
