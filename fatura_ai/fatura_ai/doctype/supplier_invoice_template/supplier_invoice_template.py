import frappe
from frappe.model.document import Document
from frappe.utils import today


class SupplierInvoiceTemplate(Document):

    def record_usage(self):
        self.samples_count = (self.samples_count or 0) + 1
        self.last_used = today()
        self.save(ignore_permissions=True)

    @staticmethod
    def find_template(supplier, layout_hash):
        return frappe.db.get_value(
            "Supplier Invoice Template",
            {"supplier": supplier, "layout_hash": layout_hash},
            "name",
        )

    @staticmethod
    def find_similar(supplier, layout_hash, threshold=10):
        templates = frappe.db.get_all(
            "Supplier Invoice Template",
            filters={"supplier": supplier},
            fields=["name", "layout_hash", "confidence", "samples_count"],
        )
        best = None
        best_dist = threshold + 1
        for t in templates:
            dist = _hamming_distance(layout_hash, t.layout_hash)
            if dist < best_dist:
                best_dist = dist
                best = t
        return best if best_dist <= threshold else None


def _hamming_distance(h1, h2):
    if len(h1) != len(h2):
        return max(len(h1), len(h2))
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))
