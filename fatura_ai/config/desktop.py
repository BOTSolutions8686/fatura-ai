from frappe import _

data = {
    "label": _("Fatura AI"),
    "color": "#6B63FF",
    "reverse": 1,
    "icon": "octicon octicon-file-text",
    "type": "module",
    "link": "Fatura AI",
    "items": [
        {
            "type": "doctype",
            "name": "Fatura AI Settings",
            "label": _("Settings"),
            "description": _("Configure AI provider and matching thresholds"),
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
            "description": _("Learned invoice text → ERPNext item mappings"),
        },
    ],
}
