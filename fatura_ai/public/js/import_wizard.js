/**
 * Fatura AI — Import Wizard (5-step)
 * معالج استيراد الفاتورة بخمس خطوات
 *
 * Steps:
 *   0 — Upload file
 *   1 — AI extraction (progress indicator)
 *   2 — Supplier review & confirmation
 *   3 — Item matching review
 *   4 — Review summary + populate document
 */

window.FaturaWizard = class FaturaWizard {
	constructor(frm) {
		this.frm = frm;
		this.log_name = null;
		this.extracted = null;
		this.confirmed_items = [];
		this.dialog = null;
		this.current_step = 0;
	}

	// ── Entry point ──────────────────────────────────────────────────────────

	open() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Import Invoice — فاتورة AI"),
			size: "large",
			fields: this._get_step_fields(0),
		});
		this._render_step(0);
		this.dialog.show();
	}

	// ── Step navigation ──────────────────────────────────────────────────────

	_go_to(step) {
		this.current_step = step;
		this.dialog.set_df_property("step_html", "options", this._step_html(step));
		this._render_step(step);
	}

	_render_step(step) {
		const renderers = [
			() => this._render_upload(),
			() => this._render_extraction(),
			() => this._render_supplier(),
			() => this._render_items(),
			() => this._render_review(),
		];
		renderers[step] && renderers[step]();
	}

	// ── Step 0: Upload ───────────────────────────────────────────────────────

	_render_upload() {
		this.dialog.set_primary_action(__("Upload & Extract"), () => this._do_upload());
		this.dialog.set_secondary_action(__("Cancel"), () => this.dialog.hide());
	}

	_do_upload() {
		const file_url = this.dialog.get_value("file_url");
		if (!file_url) {
			frappe.msgprint(__("Please attach an invoice file first"));
			return;
		}
		frappe.call({
			method: "fatura_ai.api.import_wizard.upload_invoice",
			args: {
				file_url,
				source_doctype: this.frm.doctype,
				source_docname: this.frm.docname,
			},
			callback: (r) => {
				if (r.message && r.message.log_name) {
					this.log_name = r.message.log_name;
					this._go_to(1);
				}
			},
		});
	}

	// ── Step 1: AI Extraction ────────────────────────────────────────────────

	_render_extraction() {
		this.dialog.set_primary_action(__(""), () => {});
		this.dialog.get_primary_btn().hide();
		frappe.call({
			method: "fatura_ai.api.import_wizard.run_extraction",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (r.message) {
					this.extracted = r.message;
					this._go_to(2);
				}
			},
		});
	}

	// ── Step 2: Supplier Review ──────────────────────────────────────────────

	_render_supplier() {
		this.dialog.get_primary_btn().show();
		this.dialog.set_primary_action(__("Confirm Supplier"), () => this._do_confirm_supplier());
		this.dialog.set_secondary_action(__("Back"), () => this._go_to(0));
		frappe.call({
			method: "fatura_ai.api.import_wizard.match_supplier",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (r.message) this._show_supplier_match(r.message);
			},
		});
	}

	_show_supplier_match(match) {
		// Rendered by step HTML; update dialog fields with match result
		this.dialog.set_value("matched_supplier", match.supplier || "");
		this.dialog.set_value("supplier_confidence", match.confidence || 0);
	}

	_do_confirm_supplier() {
		const supplier = this.dialog.get_value("matched_supplier");
		frappe.call({
			method: "fatura_ai.api.import_wizard.confirm_supplier",
			args: { log_name: this.log_name, supplier },
			callback: () => this._go_to(3),
		});
	}

	// ── Step 3: Item Matching ────────────────────────────────────────────────

	_render_items() {
		this.dialog.set_primary_action(__("Confirm Items"), () => this._do_confirm_items());
		this.dialog.set_secondary_action(__("Back"), () => this._go_to(2));
		frappe.call({
			method: "fatura_ai.api.import_wizard.match_items",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (r.message) this.confirmed_items = r.message.items || [];
			},
		});
	}

	_do_confirm_items() {
		frappe.call({
			method: "fatura_ai.api.import_wizard.confirm_items",
			args: {
				log_name: this.log_name,
				confirmed_items: JSON.stringify(this.confirmed_items),
			},
			callback: () => this._go_to(4),
		});
	}

	// ── Step 4: Review & Populate ────────────────────────────────────────────

	_render_review() {
		this.dialog.set_primary_action(__("Import to Document"), () => this._do_populate());
		this.dialog.set_secondary_action(__("Back"), () => this._go_to(3));
		frappe.call({
			method: "fatura_ai.api.import_wizard.get_review_summary",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (r.message) this._show_review(r.message);
			},
		});
	}

	_show_review(summary) {
		// TODO (T011): render structured summary with confidence badges
		console.log("[FaturaWizard] Review summary:", summary);
	}

	_do_populate() {
		frappe.call({
			method: "fatura_ai.api.import_wizard.populate_document",
			args: {
				log_name: this.log_name,
				confirmed_items: JSON.stringify(this.confirmed_items),
			},
			callback: (r) => {
				if (!r.message) return;
				this._apply_to_form(r.message);
				this.dialog.hide();
				frappe.show_alert({ message: __("Invoice imported successfully"), indicator: "green" });
			},
		});
	}

	_apply_to_form(payload) {
		// Populate fields — NEVER auto-submit (مهم: لا يُقدَّم تلقائياً أبداً)
		const frm = this.frm;
		if (payload.supplier) frm.set_value("supplier", payload.supplier);
		if (payload.bill_no) frm.set_value("bill_no", payload.bill_no);
		if (payload.bill_date) frm.set_value("bill_date", payload.bill_date);
		if (payload.due_date) frm.set_value("due_date", payload.due_date);
		(payload.items || []).forEach((item) => frm.add_child("items", item));
		frm.refresh_field("items");
	}

	// ── Shared helpers ───────────────────────────────────────────────────────

	_step_html(step) {
		const labels = [
			__("Upload"),
			__("Extracting"),
			__("Supplier"),
			__("Items"),
			__("Review"),
		];
		return labels.map((l, i) => {
			const cls = i === step ? "active" : i < step ? "done" : "";
			return `<span class="fatura-step ${cls}">${l}</span>`;
		}).join(" › ");
	}

	_get_step_fields(step) {
		// Minimal field scaffold — full field definitions in T007–T011
		return [
			{ fieldtype: "HTML", fieldname: "step_html", options: this._step_html(step) },
			{ fieldtype: "Attach", fieldname: "file_url", label: __("Invoice File (PDF / Image)") },
			{ fieldtype: "Link", fieldname: "matched_supplier", label: __("Matched Supplier"), options: "Supplier" },
			{ fieldtype: "Float", fieldname: "supplier_confidence", label: __("Confidence"), read_only: 1 },
		];
	}
};
