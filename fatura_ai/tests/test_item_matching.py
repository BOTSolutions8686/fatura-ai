"""
Unit tests for item matching (T015).
"""
import unittest
from unittest.mock import patch
import frappe
from fatura_ai.helpers.item_matching import match_items


class TestItemMatching(unittest.TestCase):
    """Test the 3‑tier item matching pipeline."""

    def setUp(self):
        # Ensure _match_by_learned_mapping returns None for all tests
        self.learned_patch = patch(
            "fatura_ai.helpers.item_matching._match_by_learned_mapping",
            return_value=None,
        )
        self.learned_patch.start()

    def tearDown(self):
        self.learned_patch.stop()

    @patch("fatura_ai.helpers.item_matching.frappe.db.exists")
    def test_exact_item_code_match_returns_tier1_high(self, mock_exists):
        """Exact item_code match should return method='Exact Code', confidence=1.0."""
        mock_exists.return_value = True
        items = [{"description": "ITEM-001", "item_name": "Some Item"}]
        result = match_items(items)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["matched_item"], "ITEM-001")
        self.assertEqual(r["method"], "Exact Code")
        self.assertEqual(r["confidence"], 1.0)

    @patch("fatura_ai.helpers.item_matching.frappe.db.get_all")
    @patch("fatura_ai.helpers.item_matching.frappe.db.exists")
    def test_fuzzy_description_above_80_returns_tier2_medium(
        self, mock_exists, mock_get_all
    ):
        """Fuzzy description match above 80% should return method='Fuzzy Name', confidence~0.8+."""
        mock_exists.return_value = False  # no exact code match
        # Return a list of items for fuzzy matching
        mock_get_all.return_value = [
            {"name": "ITEM-002", "item_name": "Acme Widget"},
            {"name": "ITEM-003", "item_name": "Beta Gadget"},
        ]
        items = [{"description": "Acme Widget", "item_name": ""}]
        result = match_items(items)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["matched_item"], "ITEM-002")
        self.assertEqual(r["method"], "Fuzzy Name")
        self.assertGreaterEqual(r["confidence"], 0.8)

    @patch("fatura_ai.helpers.item_matching.frappe.db.get_all")
    @patch("fatura_ai.helpers.item_matching.frappe.db.exists")
    def test_no_match_returns_tier3_unmatched(self, mock_exists, mock_get_all):
        """No match should return matched_item=None, method='Unmatched', confidence=0.0."""
        mock_exists.return_value = False
        mock_get_all.return_value = []  # no items in DB
        items = [{"description": "NonExistentItem", "item_name": ""}]
        result = match_items(items)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertIsNone(r["matched_item"])
        self.assertEqual(r["method"], "Unmatched")
        self.assertEqual(r["confidence"], 0.0)

    @patch("fatura_ai.helpers.item_matching.frappe.db.get_all")
    @patch("fatura_ai.helpers.item_matching.frappe.db.exists")
    def test_arabic_item_names_fuzzy_matched(self, mock_exists, mock_get_all):
        """Arabic item names should be matched via fuzzy logic."""
        mock_exists.return_value = False
        mock_get_all.return_value = [
            {"name": "ITEM-AR-01", "item_name": "منتج الأمل"},
            {"name": "ITEM-AR-02", "item_name": "أداة البركة"},
        ]
        # Exact Arabic name
        items = [{"description": "منتج الأمل", "item_name": ""}]
        result = match_items(items)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["matched_item"], "ITEM-AR-01")
        self.assertEqual(r["method"], "Fuzzy Name")
        self.assertGreaterEqual(r["confidence"], 0.8)

        # Slightly different but still above 80% similarity
        items2 = [{"description": "منتج الأمل الممتاز", "item_name": ""}]
        result2 = match_items(items2)
        self.assertEqual(len(result2), 1)
        r2 = result2[0]
        self.assertEqual(r2["matched_item"], "ITEM-AR-01")
        self.assertEqual(r2["method"], "Fuzzy Name")
        self.assertGreaterEqual(r2["confidence"], 0.8)

    @patch("fatura_ai.helpers.item_matching.frappe.db.get_all")
    @patch("fatura_ai.helpers.item_matching.frappe.db.exists")
    def test_empty_or_none_inputs_handled(self, mock_exists, mock_get_all):
        """Empty or None description/item_name should not crash and return Unmatched."""
        mock_exists.return_value = False
        mock_get_all.return_value = []
        # Empty description
        items = [{"description": "", "item_name": ""}]
        result = match_items(items)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertIsNone(r["matched_item"])
        self.assertEqual(r["method"], "Unmatched")

        # None description (should be converted to empty string)
        items2 = [{"description": None, "item_name": None}]
        result2 = match_items(items2)
        self.assertEqual(len(result2), 1)
        r2 = result2[0]
        self.assertIsNone(r2["matched_item"])
        self.assertEqual(r2["method"], "Unmatched")


if __name__ == "__main__":
    unittest.main()
