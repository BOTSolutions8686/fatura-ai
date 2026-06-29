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
        if not key:
            return ""
        if len(key) <= 4:
            return "*" * len(key)
        return "*" * (len(key) - 4) + key[-4:]


@frappe.whitelist()
def test_deepseek_key(api_key, model):
    return _test_provider("DeepSeek", api_key, model)


@frappe.whitelist()
def test_google_key(api_key, model):
    return _test_provider("Google", api_key, model)


@frappe.whitelist()
def test_anthropic_key(api_key, model):
    return _test_provider("Anthropic", api_key, model)


@frappe.whitelist()
def test_openai_key(api_key, model):
    return _test_provider("OpenAI", api_key, model)


@frappe.whitelist()
def test_tesseract():
    try:
        import subprocess
        result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.split("\n")[0]
            langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=10)
            return {"success": True, "version": version, "languages": langs.stdout.strip()}
        return {"success": False, "error": result.stderr or "Tesseract returned non-zero exit code"}
    except FileNotFoundError:
        return {"success": False, "error": "Tesseract is not installed. Run: apt-get install tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _test_provider(provider_name, api_key, model):
    if not api_key:
        frappe.throw(_("Please enter an API key first."))
    try:
        if provider_name == "DeepSeek":
            return _test_deepseek(api_key, model)
        if provider_name == "Google":
            return _test_google(api_key, model)
        if provider_name == "Anthropic":
            return _test_anthropic(api_key, model)
        if provider_name == "OpenAI":
            return _test_openai(api_key, model)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Fatura AI Key Test")
        frappe.throw(_("Connection failed: {0}").format(str(e)))


def _test_deepseek(api_key, model):
    import openai
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with just the word OK"}],
        max_tokens=5,
        timeout=15,
    )
    return {"success": True, "message": _("DeepSeek connected successfully ({0})").format(model)}


def _test_google(api_key, model):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    m = genai.GenerativeModel(model)
    m.generate_content("Reply with just the word OK", generation_config={"max_output_tokens": 5})
    return {"success": True, "message": _("Google Gemini connected successfully ({0})").format(model)}


def _test_anthropic(api_key, model):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    client.messages.create(
        model=model,
        max_tokens=10,
        messages=[{"role": "user", "content": "Reply with just the word OK"}],
        timeout=15,
    )
    return {"success": True, "message": _("Anthropic connected successfully ({0})").format(model)}


def _test_openai(api_key, model):
    import openai
    client = openai.OpenAI(api_key=api_key)
    client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with just the word OK"}],
        max_tokens=5,
        timeout=15,
    )
    return {"success": True, "message": _("OpenAI connected successfully ({0})").format(model)}
