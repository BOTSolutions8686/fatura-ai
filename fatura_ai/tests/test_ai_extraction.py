"""
Unit tests for AI extraction pipeline (T016).
Tests only the file validation logic in extractor.py.
"""
import unittest
from unittest.mock import patch, MagicMock
import frappe
from fatura_ai.api.extractor import validate_file


class TestAIExtraction(unittest.TestCase):
    """Test the file validation pipeline."""

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_rejects_unsupported_extension(self, mock_get_value, mock_throw):
        """Unsupported file extension should raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.doc")
        mock_throw.assert_called_once()
        args, _ = mock_throw.call_args
        self.assertIn("Unsupported file type", args[0])

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_rejects_file_over_20mb(self, mock_get_value, mock_throw):
        """File over 20 MB should raise ValidationError."""
        mock_get_value.return_value = {"file_size": 21 * 1024 * 1024}
        validate_file("invoice.pdf")
        mock_throw.assert_called_once()
        args, _ = mock_throw.call_args
        self.assertIn("MB limit", args[0])

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_pdf(self, mock_get_value, mock_throw):
        """.pdf should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.pdf")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_png(self, mock_get_value, mock_throw):
        """.png should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.png")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_jpg(self, mock_get_value, mock_throw):
        """.jpg should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.jpg")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_jpeg(self, mock_get_value, mock_throw):
        """.jpeg should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.jpeg")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_webp(self, mock_get_value, mock_throw):
        """.webp should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.webp")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_tiff(self, mock_get_value, mock_throw):
        """.tiff should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.tiff")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_tif(self, mock_get_value, mock_throw):
        """.tif should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.tif")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_rejects_exe(self, mock_get_value, mock_throw):
        """.exe should raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.exe")
        mock_throw.assert_called_once()
        args, _ = mock_throw.call_args
        self.assertIn("Unsupported file type", args[0])

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_rejects_empty_extension(self, mock_get_value, mock_throw):
        """No extension should raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice")
        mock_throw.assert_called_once()
        args, _ = mock_throw.call_args
        self.assertIn("Unsupported file type", args[0])

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_rejects_uppercase_unsupported(self, mock_get_value, mock_throw):
        """Uppercase unsupported extension should raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.DOC")
        mock_throw.assert_called_once()
        args, _ = mock_throw.call_args
        self.assertIn("Unsupported file type", args[0])

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_accepts_uppercase_pdf(self, mock_get_value, mock_throw):
        """Uppercase .PDF should not raise ValidationError."""
        mock_get_value.return_value = {"file_size": 1024}
        validate_file("invoice.PDF")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_rejects_file_exactly_20mb(self, mock_get_value, mock_throw):
        """File exactly 20 MB should be accepted (not over limit)."""
        mock_get_value.return_value = {"file_size": 20 * 1024 * 1024}
        validate_file("invoice.pdf")
        mock_throw.assert_not_called()

    @patch("fatura_ai.api.extractor.frappe.throw")
    @patch("fatura_ai.api.extractor.frappe.db.get_value")
    def test_rejects_file_just_over_20mb(self, mock_get_value, mock_throw):
        """File just over 20 MB should raise ValidationError."""
        mock_get_value.return_value = {"file_size": 20 * 1024 * 1024 + 1}
        validate_file("invoice.pdf")
        mock_throw.assert_called_once()
        args, _ = mock_throw.call_args
        self.assertIn("MB limit", args[0])


if __name__ == "__main__":
    unittest.main()
