app_name = "fatura_ai"
app_title = "Fatura AI"
app_publisher = "BOT Solutions"
app_description = "AI-powered supplier invoice import for ERPNext — Saudi market"
app_icon = "assets/fatura_ai/images/fatura-ai.svg"
app_color = "#6B63FF"
app_email = "info@botsolutions.tech"
app_license = "MIT"
app_version = "1.0.0"

# Apps screen (v16 desktop — big icon cards)
add_to_apps_screen = [
    {
        "app_name": "fatura_ai",
        "title": "Fatura AI",
        "icon": "assets/fatura_ai/images/fatura-ai.svg",
        "route": "/app/fatura-ai",
    },
]

# DocType-specific JS injected on form load
doctype_js = {
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Fatura AI Settings": "public/js/settings.js",
}

# Global JS loaded on every page (wizard + utils)
app_include_js = ["/assets/fatura_ai/js/import_wizard.js"]

# Scheduled jobs (none for v1)
scheduler_events = {}

# DocType events (none for v1 — no auto-submit ever)
doc_events = {}

# Post-install checks
after_install = ["fatura_ai.setup.install.after_install"]

# Fixtures installed with the app
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Fatura AI"]]},
    {"dt": "Workspace", "filters": [["module", "=", "Fatura AI"]]},
    {"dt": "Number Card", "filters": [["module", "=", "Fatura AI"]]},
    {"dt": "Desktop Icon", "filters": [["app", "=", "fatura_ai"]]},
]
