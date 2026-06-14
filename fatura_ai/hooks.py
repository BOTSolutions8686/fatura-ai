app_name = "fatura_ai"
app_title = "Fatura AI"
app_publisher = "BOT Solutions"
app_description = "AI-powered invoice import for ERPNext"
app_email = "support@botsolutions.tech"
app_license = "MIT"
app_version = "1.0.0"

# DocType-specific JS injected on form load
doctype_js = {
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Purchase Order": "public/js/purchase_order.js",
}

# Global JS loaded on every page (wizard + utils)
app_include_js = ["/assets/fatura_ai/js/import_wizard.js"]

# Scheduled jobs (none for v1)
scheduler_events = {}

# DocType events (none for v1 — no auto-submit ever)
doc_events = {}

# Fixtures installed with the app
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Fatura AI"]]},
]
