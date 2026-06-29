import subprocess
import shutil
import frappe
from frappe import _


def after_install():
    _check_system_dependencies()
    _create_workspace_sidebar()
    _create_desktop_icon()


def _check_system_dependencies():
    missing = []

    if not shutil.which("tesseract"):
        missing.append("tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng")
    else:
        try:
            result = subprocess.run(
                ["tesseract", "--list-langs"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "ara" not in result.stdout:
                missing.append("tesseract-ocr-ara (Arabic language pack)")
        except Exception:
            pass

    if not shutil.which("pdftotext"):
        missing.append("poppler-utils")
    else:
        try:
            import ctypes.util
            if not (ctypes.util.find_library("zbar") or ctypes.util.find_library("libzbar")):
                missing.append("libzbar0")
        except Exception:
            pass

    if missing:
        _show_missing_deps_dialog(missing)


def _show_missing_deps_dialog(missing):
    pkg_list = "\n".join(f"  • {p}" for p in missing)
    debian_cmd = f"apt-get install -y {' '.join(missing)}"

    frappe.msgprint(
        _(
            "Fatura AI requires these system packages for full functionality:\n"
            "{0}\n\n"
            "Install on Debian/Ubuntu:\n"
            "<code>{1}</code>\n\n"
            "Without these, scanned PDF invoices and QR codes will not be processed."
        ).format(pkg_list, debian_cmd),
        title=_("Fatura AI — Missing System Packages"),
        indicator="orange",
    )


def _create_desktop_icon():
    if frappe.db.exists("Desktop Icon", {"app": "fatura_ai"}):
        return
    try:
        svg_path = frappe.get_app_path("fatura_ai", "public", "images", "fatura-ai.svg")
        with open(svg_path, "rb") as f:
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": "fatura-ai.svg",
                "content": f.read(),
                "is_private": 0,
            })
            file_doc.insert(ignore_permissions=True)

        frappe.get_doc({
            "doctype": "Desktop Icon",
            "app": "fatura_ai",
            "icon_type": "Link",
            "link_type": "Workspace Sidebar",
            "link_to": "Fatura AI",
            "logo_url": file_doc.file_url,
            "label": "Fatura AI",
            "standard": 1,
            "hidden": 0,
            "bg_color": "blue",
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass


def _create_workspace_sidebar():
    if frappe.db.exists("Workspace Sidebar", {"app": "fatura_ai"}):
        return
    try:
        frappe.get_doc({
            "doctype": "Workspace Sidebar",
            "title": "Fatura AI",
            "app": "fatura_ai",
            "standard": 1,
            "items": [
                {"title": "Settings", "link": "Fatura AI Settings", "type": "Link"},
                {"title": "Import Logs", "link": "Fatura Import Log", "type": "Link"},
                {"title": "Item Mappings", "link": "Invoice AI Item Map", "type": "Link"},
                {"title": "Supplier Templates", "link": "Supplier Invoice Template", "type": "Link"},
            ],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass
