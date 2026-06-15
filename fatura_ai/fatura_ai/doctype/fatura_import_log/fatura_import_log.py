
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class FaturaImportLog(Document):
    # سجل استيراد الفاتورة — للقراءة فقط بعد الإنشاء

    def before_insert(self):
        if not self.import_date:
            self.import_date = frappe.utils.today()
        if not self.title:
            self.title = self._build_title()

    def _build_title(self):
        source = self.source_docname or _("Unknown")
        provider = self.provider_used or _("AI")
        return _("{0} — {1} import").format(source, provider)

    def mark_success(self, matched_supplier=None, items_matched=0):
        self.status = "Success"
        self.matched_supplier = matched_supplier
        self.items_matched = items_matched
        self.save(ignore_permissions=True)

    def mark_failed(self, error_message):
        self.status = "Failed"
        self.error_message = str(error_message)[:500]
        self.save(ignore_permissions=True)
