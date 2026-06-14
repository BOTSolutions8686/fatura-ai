import frappe
from frappe.model.document import Document
from frappe.utils import today


class InvoiceAIItemMap(Document):
    # خريطة تطابق الأصناف — تتعلم تلقائياً عند كل استيراد ناجح

    def record_usage(self):
        """Increment usage counter and update last-used date."""
        self.times_used = (self.times_used or 0) + 1
        self.last_used = today()
        self.save(ignore_permissions=True)

    @staticmethod
    def find_mapping(original_text, supplier=None):
        """Return best existing mapping for invoice text, supplier-scoped first."""
        filters = {"original_text": original_text}
        if supplier:
            filters["supplier"] = supplier
        name = frappe.db.get_value("Invoice AI Item Map", filters, "name")
        if not name and supplier:
            filters.pop("supplier")
            name = frappe.db.get_value("Invoice AI Item Map", filters, "name")
        return frappe.get_doc("Invoice AI Item Map", name) if name else None
