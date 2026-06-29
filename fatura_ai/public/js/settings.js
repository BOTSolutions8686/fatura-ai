frappe.ui.form.on("Fatura AI Settings", {
    refresh: function (frm) {
        frm.trigger("update_tesseract_status");
    },

    update_tesseract_status: function (frm) {
        frappe.call({
            method: "fatura_ai.fatura_ai.doctype.fatura_ai_settings.fatura_ai_settings.test_tesseract",
            callback: function (r) {
                if (r.message && r.message.success) {
                    frm.set_value("tesseract_status",
                        __("Installed") + " — " + r.message.version);
                    frm.set_value("tesseract_languages", r.message.languages);
                } else {
                    frm.set_value("tesseract_status",
                        __("Not installed") + " — " + (r.message?.error || ""));
                    frm.set_value("tesseract_languages", "");
                }
            },
        });
    },

    test_deepseek_key: function (frm) {
        _test_key(frm, "DeepSeek", frm.doc.deepseek_api_key, frm.doc.deepseek_model,
            "deepseek_status");
    },

    test_google_key: function (frm) {
        _test_key(frm, "Google", frm.doc.google_api_key, frm.doc.google_model,
            "google_status");
    },

    test_anthropic_key: function (frm) {
        _test_key(frm, "Anthropic", frm.doc.anthropic_api_key, frm.doc.anthropic_model,
            "anthropic_status");
    },

    test_openai_key: function (frm) {
        _test_key(frm, "OpenAI", frm.doc.openai_api_key, frm.doc.openai_model,
            "openai_status");
    },

    test_tesseract: function (frm) {
        frappe.call({
            method: "fatura_ai.fatura_ai.doctype.fatura_ai_settings.fatura_ai_settings.test_tesseract",
            freeze: true,
            freeze_message: __("Checking Tesseract OCR..."),
            callback: function (r) {
                if (r.message && r.message.success) {
                    frm.set_value("tesseract_status",
                        __("Installed") + " — " + r.message.version);
                    frm.set_value("tesseract_languages", r.message.languages);
                    frappe.msgprint({
                        title: __("Tesseract OCR"),
                        indicator: "green",
                        message: r.message.version + "<br>" +
                            __("Languages:") + " " + r.message.languages,
                    });
                } else {
                    frm.set_value("tesseract_status",
                        __("Not installed") + " — " + (r.message?.error || ""));
                    frm.set_value("tesseract_languages", "");
                    _show_tesseract_install_guide();
                }
            },
        });
    },
});

function _test_key(frm, provider, api_key, model, status_field) {
    if (!api_key) {
        frappe.msgprint(__("Please enter a {0} API key first.", [provider]));
        return;
    }
    const method_map = {
        "DeepSeek": "test_deepseek_key",
        "Google": "test_google_key",
        "Anthropic": "test_anthropic_key",
        "OpenAI": "test_openai_key",
    };
    frappe.call({
        method: "fatura_ai.fatura_ai.doctype.fatura_ai_settings.fatura_ai_settings."
            + method_map[provider],
        args: { api_key: api_key, model: model },
        freeze: true,
        freeze_message: __("Testing {0} connection...", [provider]),
        callback: function (r) {
            if (r.message && r.message.success) {
                frm.set_value(status_field, r.message.message);
                frappe.msgprint({
                    title: provider,
                    indicator: "green",
                    message: r.message.message,
                });
            }
        },
    });
}

function _show_tesseract_install_guide() {
    var d = new frappe.ui.Dialog({
        title: __("Install Tesseract OCR"),
        fields: [
            {
                fieldname: "info",
                fieldtype: "HTML",
                options: `
<div style="font-size:13px; line-height:1.6;">
<p><strong>` + __("Tesseract OCR is required for scanned/image-based PDF invoices.") + `</strong></p>
<p>` + __("If Tesseract is not installed, invoices without a text layer (scanned documents) will fail to extract.") + `</p>
<hr style="margin:12px 0;">
<p><strong>` + __("Installation Commands") + `</strong></p>
<table style="width:100%; font-size:12px;">
<tr><td style="padding:4px 8px 4px 0; font-weight:600;">Debian / Ubuntu</td>
<td style="padding:4px 0;"><code>apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng</code></td></tr>
<tr><td style="padding:4px 8px 4px 0; font-weight:600;">CentOS / RHEL</td>
<td style="padding:4px 0;"><code>yum install -y tesseract tesseract-langpack-ara</code></td></tr>
<tr><td style="padding:4px 8px 4px 0; font-weight:600;">macOS</td>
<td style="padding:4px 0;"><code>brew install tesseract tesseract-lang</code></td></tr>
<tr><td style="padding:4px 8px 4px 0; font-weight:600;">Docker</td>
<td style="padding:4px 0;">` + __("Add to Dockerfile:") + `<br>
<code>RUN apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng</code></td></tr>
</table>
<hr style="margin:12px 0;">
<p style="color:#6b7280; font-size:11px;">` + __("After installing, click \"Check Tesseract OCR Status\" to verify.") + `</p>
</div>`,
            },
        ],
    });
    d.show();
}

