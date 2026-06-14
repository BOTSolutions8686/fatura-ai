import frappe
from frappe.model.document import Document


class FaturaAISettings(Document):
    # إعدادات فاتورة AI — singleton يُحرَّر من System Manager فقط

    def validate(self):
        self._validate_threshold()
        self._validate_model_names()

    def _validate_threshold(self):
        if not (0.0 <= (self.fuzzy_match_threshold or 0.8) <= 1.0):
            frappe.throw(_("Fuzzy match threshold must be between 0 and 1"))

    def _validate_model_names(self):
        if self.api_provider == "Anthropic" and not self.anthropic_api_key:
            frappe.msgprint(
                _("Anthropic API key is not set. Add it before running imports."),
                alert=True,
            )
        elif self.api_provider == "OpenAI" and not self.openai_api_key:
            frappe.msgprint(
                _("OpenAI API key is not set. Add it before running imports."),
                alert=True,
            )
        elif self.api_provider == "Google" and not self.google_api_key:
            frappe.msgprint(
                _("Google API key is not set. Add it before running imports."),
                alert=True,
            )
