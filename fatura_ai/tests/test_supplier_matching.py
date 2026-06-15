"""
Unit tests for supplier matching (T014).
"""
import unittest
from unittest.mock import patch
import frappe
from fatura_ai.helpers.supplier_matching import match_supplier


class TestSupplierMatching(unittest.TestCase):
    """Test the 3‑tier supplier matching pipeline."""

    @patch("fatura_ai.helpers.supplier_matching.frappe.get_all")
    def test_exact_vat_match_returns_tier1_high(self, mock_get_all):
        """Exact VAT match should return tier=1, confidence=high."""
        mock_get_all.return_value = [
            {"name": "SUP-00001", "supplier_name": "Acme Corp"}
        ]
        result = match_supplier(tax_id="1234567890", name="Acme Corp")
        self.assertEqual(result["tier"], 1)
        self.assertEqual(result["confidence"], "high")
        self.assertEqual(result["supplier"], "SUP-00001")
        self.assertEqual(result["supplier_name"], "Acme Corp")

    @patch("fatura_ai.helpers.supplier_matching.frappe.get_all")
    def test_fuzzy_name_above_85_returns_tier2_medium(self, mock_get_all):
        """Fuzzy name match above 85% should return tier=2, confidence=medium."""
        def side_effect(doctype, filters=None, fields=None, limit=None):
            if filters and "tax_id" in filters:
                return []  # no tax_id match
            # name matching call
            return [
                {"name": "SUP-00002", "supplier_name": "Acme Corporation"},
                {"name": "SUP-00003", "supplier_name": "Beta Ltd"},
            ]
        mock_get_all.side_effect = side_effect
        result = match_supplier(tax_id="", name="Acme Corp")
        self.assertEqual(result["tier"], 2)
        self.assertEqual(result["confidence"], "medium")
        self.assertEqual(result["supplier"], "SUP-00002")
        self.assertEqual(result["supplier_name"], "Acme Corporation")

    @patch("fatura_ai.helpers.supplier_matching.frappe.get_all")
    def test_no_match_returns_action_create_new(self, mock_get_all):
        """No match should return supplier=None, tier=3 (create new)."""
        mock_get_all.return_value = []
        result = match_supplier(tax_id="999999999", name="NonExistent")
        self.assertIsNone(result["supplier"])
        self.assertIsNone(result["supplier_name"])
        self.assertEqual(result["tier"], 3)
        self.assertEqual(result["confidence"], "low")

    @patch("fatura_ai.helpers.supplier_matching.frappe.get_all")
    def test_none_or_empty_handled(self, mock_get_all):
        """Empty or None tax_id/name should not crash and return appropriate result."""
        mock_get_all.return_value = []
        result = match_supplier(tax_id="", name="")
        self.assertIsNone(result["supplier"])
        self.assertEqual(result["tier"], 3)

        # None values (function expects strings, but we test it doesn't raise)
        result = match_supplier(tax_id=None, name=None)  # type: ignore
        self.assertIsNone(result["supplier"])
        self.assertEqual(result["tier"], 3)

    @patch("fatura_ai.helpers.supplier_matching.frappe.get_all")
    def test_arabic_names_handled(self, mock_get_all):
        """Arabic supplier names should be matched via fuzzy logic."""
        def side_effect(doctype, filters=None, fields=None, limit=None):
            if filters and "tax_id" in filters:
                return []
            return [
                {"name": "SUP-AR-01", "supplier_name": "شركة الأمل للتجارة"},
                {"name": "SUP-AR-02", "supplier_name": "مؤسسة البركة"},
            ]
        mock_get_all.side_effect = side_effect
        # Exact Arabic name
        result = match_supplier(tax_id="", name="شركة الأمل للتجارة")
        self.assertEqual(result["tier"], 2)
        self.assertEqual(result["supplier"], "SUP-AR-01")
        self.assertEqual(result["supplier_name"], "شركة الأمل للتجارة")

        # Slightly different but still above 85% similarity
        result2 = match_supplier(tax_id="", name="شركة الأمل للتجارة المحدودة")
        self.assertEqual(result2["tier"], 2)
        self.assertEqual(result2["supplier"], "SUP-AR-01")


if __name__ == "__main__":
    unittest.main()
