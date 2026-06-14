import frappe
from frappe import _
from frappe.model.document import Document


class FaturaAISettings(Document):
    # إعدادات فاتورة AI — singleton يُحرَّر من System Manager فقط

    def validate(self):
        self._validate_threshold()
        self._validate_api_keys()

    def _validate_threshold(self):
        threshold = self.fuzzy_match_threshold or 0.8
        if not (0.0 <= threshold <= 1.0):
            frappe.throw(_("Fuzzy match threshold must be between 0 and 1"))

    def _validate_api_keys(self):
        provider = self.api_provider
        key_field_map = {
            "Anthropic": "anthropic_api_key",
            "OpenAI": "openai_api_key",
            "Google": "google_api_key",
        }
        field = key_field_map.get(provider)
        if field and not self.get(field):
            frappe.throw(
                _("{0} API key is required for the selected provider.").format(provider)
            )

    def get_active_provider(self):
        """Return the currently selected AI provider name."""
        return self.api_provider

    def on_update(self):
        """Log settings changes with masked API keys."""
        if not frappe.flags.in_install:
            self._log_settings_update()

    def _log_settings_update(self):
        masked = {
            "api_provider": self.api_provider,
            "anthropic_api_key": self._mask_key(self.anthropic_api_key),
            "openai_api_key": self._mask_key(self.openai_api_key),
            "google_api_key": self._mask_key(self.google_api_key),
            "fuzzy_match_threshold": self.fuzzy_match_threshold,
            "enable_item_learning": self.enable_item_learning,
        }
        frappe.logger().info(
            _("Fatura AI Settings updated: {0}").format(masked)
        )

    @staticmethod
    def _mask_key(key):
        """Mask all but last 4 characters of an API key."""
        if not key:
            return ""
        if len(key) <= 4:
            return "*" * len(key)
        return "*" * (len(key) - 4) + key[-4:]
