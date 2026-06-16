app_name = "fatura_ai"
app_title = "Fatura AI"
app_publisher = "BOT Solutions"
app_description = "AI-powered supplier invoice import for ERPNext — Saudi market"
app_icon = "octicon octicon-file-text"
app_color = "#1A73E8"
app_email = "info@botsolutions.tech"
app_license = "MIT"
app_version = "1.0.0"

# DocType-specific JS injected on form load
doctype_js = {
    "Purchase Invoice": "public/js/purchase_invoice.js",
}

# Global JS loaded on every page (wizard + utils)
app_include_js = ["/assets/fatura_ai/js/import_wizard.js"]

# Scheduled jobs (none for v1)
scheduler_events = {
    "all": [
        "fatura_ai.helpers.email_monitor.check_inbox_for_invoices",
    ],
}

# DocType events (none for v1 — no auto-submit ever)
doc_events = {}

# Fixtures installed with the app
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Fatura AI"]]},
]
