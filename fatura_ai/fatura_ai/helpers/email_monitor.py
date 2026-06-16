import os
import tempfile
from typing import List, Dict, Any

import frappe
from frappe import _


def check_inbox_for_invoices() -> None:
    """Fetch unread emails from the configured inbox and trigger AI extraction
    for any PDF or image attachments."""
    settings = frappe.get_single("Fatura AI Settings")
    if not settings.get("email_import_enabled"):
        return

    inbox = settings.get("email_import_inbox")
    if not inbox:
        return

    # Find the Email Account that matches the configured inbox
    account_names = frappe.get_all(
        "Email Account",
        filters={"email_id": inbox},
        pluck="name",
    )
    if not account_names:
        frappe.logger().warning(
            _("No Email Account found for inbox {0}").format(inbox)
        )
        return

    for account_name in account_names:
        try:
            account = frappe.get_doc("Email Account", account_name)
            mails = account.get_inbound_mails()  # returns list of dicts
        except Exception as exc:
            frappe.logger().error(
                _("Failed to fetch inbound mails for {0}: {1}").format(
                    account_name, exc
                )
            )
            continue

        for mail in (mails or []):
            attachments: List[Dict[str, Any]] = mail.get("attachments") or []
            for att in attachments:
                filename: str = att.get("filename") or ""
                ext = os.path.splitext(filename)[1].lower()
                if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".webp"):
                    continue

                # Save attachment to a temporary file
                content = att.get("content")
                if not content:
                    continue

                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=ext
                )
                try:
                    tmp.write(content)
                    tmp.close()
                    file_path = tmp.name

                    # Create a FaturaImportLog in Draft status
                    log = frappe.get_doc(
                        {
                            "doctype": "Fatura Import Log",
                            "status": "Draft",
                            "file_url": file_path,
                            "title": filename,
                        }
                    )
                    log.insert(ignore_permissions=True)

                    # Run AI extraction on the newly created log
                    from fatura_ai.api.import_wizard import run_ai_extraction

                    run_ai_extraction(log_name=log.name, file_path=file_path)

                    # Mark the email as read (assumes the Email Account
                    # exposes a mark_as_read method)
                    uid = mail.get("uid") or mail.get("id")
                    if uid:
                        try:
                            account.mark_as_read(uid)
                        except Exception:
                            pass

                except Exception as exc:
                    frappe.logger().error(
                        _("Email import failed for attachment {0}: {1}").format(
                            filename, exc
                        )
                    )
                finally:
                    # Clean up the temporary file
                    try:
                        os.unlink(file_path)
                    except Exception:
                        pass
