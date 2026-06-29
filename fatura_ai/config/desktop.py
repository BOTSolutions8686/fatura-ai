from frappe import _

def get_data():
    return {
        "module_name": "Fatura AI",
        "category": "Modules",
        "label": _("Fatura AI"),
        "color": "#6B63FF",
        "icon": "assets/fatura_ai/images/fatura-ai.svg",
        "type": "module",
        "description": _("AI-powered supplier invoice import"),
        "items": [
            {
                "type": "doctype",
                "name": "Fatura AI Settings",
                "label": _("Settings"),
                "description": _("Configure AI providers and matching"),
            },
            {
                "type": "doctype",
                "name": "Fatura Import Log",
                "label": _("Import Logs"),
                "description": _("View history of AI invoice imports"),
            },
            {
                "type": "doctype",
                "name": "Invoice AI Item Map",
                "label": _("Item Mappings"),
                "description": _("Learned invoice text → ERPNext item"),
            },
            {
                "type": "doctype",
                "name": "Supplier Invoice Template",
                "label": _("Supplier Templates"),
                "description": _("Learned invoice layout templates"),
            },
        ],
    }
