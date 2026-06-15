/**
 * Fatura AI — Import Wizard (5-step)
 * معالج استيراد الفاتورة بخمس خطوات
 *
 * All step content renders into a single "step_content" HTML area.
 * This avoids the show/hide problem of having static fields for every step.
 */

window.FaturaWizard = class FaturaWizard {
	constructor(frm) {
		this.frm = frm;
		this.log_name = null;
		this.extracted = null;
		this.confirmed_supplier = null;
		this.confirmed_items = [];
		this.dialog = null;
		this.current_step = 0;
		this.file_url = null;
	}

	// ── Entry point ──────────────────────────────────────────────────────────

	open() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Import Invoice — فاتورة AI"),
			size: "large",
			fields: [
				{ fieldtype: "HTML", fieldname: "step_html", options: this._step_html(0) },
				{ fieldtype: "HTML", fieldname: "step_content", options: "" },
			],
			primary_action_label: __("Upload & Extract"),
			primary_action: () => this._do_upload(),
		});
		this.dialog.show();
		this._render_step(0);
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

	_set_content(html) {
		this.dialog.set_df_property("step_content", "options", html);
	}

	// ── Step 0: Upload ───────────────────────────────────────────────────────

	_render_upload() {
		this.dialog.set_primary_action(__("Upload & Extract"), () => this._do_upload());
		this._set_content(`
			<div class="fatura-upload-area"
				style="padding:32px; text-align:center; border:2px dashed #d1d5db;
					   border-radius:8px; margin:8px 0; background:#fafafa;">
				<p class="fatura-file-name" style="margin-bottom:12px; color:#6b7280; font-size:14px;">
					${__("No file selected")}
				</p>
				<button class="btn btn-default btn-sm fatura-browse-btn">
					📎 ${__("Choose Invoice (PDF / Image)")}
				</button>
			</div>
		`);

		// Attach click handler after DOM is updated
		setTimeout(() => {
			this.dialog.fields_dict.step_content.$wrapper
				.find(".fatura-browse-btn")
				.on("click", () => {
					new frappe.ui.FileUploader({
						doctype: null,
						docname: null,
						folder: "Home/Attachments",
						allow_multiple: false,
						on_success: (file_doc) => {
							this.file_url = file_doc.file_url;
							const name = file_doc.file_name || file_doc.file_url;
							this.dialog.fields_dict.step_content.$wrapper
								.find(".fatura-file-name")
								.html(`✅ <strong>${name}</strong>`);
						},
					});
				});
		}, 50);
	}

	_do_upload() {
		if (!this.file_url) {
			frappe.msgprint(__("Please attach an invoice file first"));
			return;
		}
		this._set_content(`<div style="padding:24px;text-align:center;color:#6b7280;">⏳ ${__("Uploading…")}</div>`);
		frappe.call({
			method: "fatura_ai.api.import_wizard.upload_invoice",
			args: {
				file_url: this.file_url,
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
		this.dialog.get_primary_btn().hide();
		this._set_content(`
			<div style="padding:32px; text-align:center;">
				<div style="font-size:32px; margin-bottom:12px;">🤖</div>
				<p style="color:#374151; font-weight:500;">${__("Extracting invoice data with AI…")}</p>
				<p style="color:#9ca3af; font-size:13px;">${__("This may take a few seconds")}</p>
			</div>
		`);
		frappe.call({
			method: "fatura_ai.api.import_wizard.run_ai_extraction",
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
		this._set_content(`<div style="padding:16px;color:#6b7280;">${__("Matching supplier…")}</div>`);

		frappe.call({
			method: "fatura_ai.api.import_wizard.match_supplier",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (r.message) this._show_supplier_match(r.message);
			},
		});
	}

	_show_supplier_match(match) {
		this.confirmed_supplier = match.supplier || "";
		const confidence_pct = Math.round((match.confidence || 0) * 100);
		const confidence_color = confidence_pct >= 80 ? "#16a34a" : confidence_pct >= 50 ? "#d97706" : "#dc2626";
		const supplier_label = match.supplier_name || match.supplier || __("No match found");
		const method = match.method || "";

		this._set_content(`
			<div style="padding:16px;">
				<p style="font-size:13px; color:#6b7280; margin-bottom:16px;">
					${__("AI extracted vendor")}:
					<strong>${(this.extracted || {}).vendor_name || "—"}</strong>
				</p>
				<table style="width:100%; border-collapse:collapse; font-size:14px;">
					<tr style="border-bottom:1px solid #e5e7eb;">
						<td style="padding:10px 0; color:#6b7280; width:40%;">${__("Matched Supplier")}</td>
						<td style="padding:10px 0; font-weight:500;">${supplier_label}</td>
					</tr>
					<tr style="border-bottom:1px solid #e5e7eb;">
						<td style="padding:10px 0; color:#6b7280;">${__("Match Method")}</td>
						<td style="padding:10px 0;">${method}</td>
					</tr>
					<tr>
						<td style="padding:10px 0; color:#6b7280;">${__("Confidence")}</td>
						<td style="padding:10px 0; color:${confidence_color}; font-weight:500;">${confidence_pct}%</td>
					</tr>
				</table>
				<div style="margin-top:16px;">
					<label style="font-size:13px; color:#374151; display:block; margin-bottom:6px;">
						${__("Override supplier (optional)")}
					</label>
					<input id="fatura-supplier-override" type="text"
						class="form-control input-sm"
						placeholder="${__("Start typing supplier name…")}"
						value="${this.confirmed_supplier}" />
				</div>
			</div>
		`);

		// Wire up supplier autocomplete after DOM settles
		setTimeout(() => {
			const $input = this.dialog.fields_dict.step_content.$wrapper.find("#fatura-supplier-override");
			$input.on("change keyup", () => {
				this.confirmed_supplier = $input.val();
			});
		}, 50);
	}

	_do_confirm_supplier() {
		const supplier = this.confirmed_supplier;
		if (!supplier) {
			frappe.msgprint(__("Please select or enter a supplier"));
			return;
		}
		frappe.call({
			method: "fatura_ai.api.import_wizard.confirm_supplier",
			args: { log_name: this.log_name, supplier },
			callback: () => this._go_to(3),
		});
	}

	// ── Step 3: Item Matching ────────────────────────────────────────────────

	_render_items() {
		this.dialog.set_primary_action(__("Confirm Items"), () => this._do_confirm_items());
		this._set_content(`<div style="padding:16px;color:#6b7280;">${__("Matching items…")}</div>`);

		frappe.call({
			method: "fatura_ai.api.import_wizard.match_items",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (r.message) {
					this.confirmed_items = r.message.items || [];
					this._show_items(r.message);
				}
			},
		});
	}

	_show_items(data) {
		const items = data.items || [];
		const s = data.summary || {};
		const rows = items.map((item, idx) => {
			const desc = item.description || item.item_name || "—";
			const match = item.matched_item || `<span style="color:#dc2626;">${__("Unmatched")}</span>`;
			const conf = Math.round((item.confidence || 0) * 100);
			return `<tr style="border-bottom:1px solid #e5e7eb;">
				<td style="padding:8px 4px; font-size:13px;">${desc}</td>
				<td style="padding:8px 4px; font-size:13px;">${match}</td>
				<td style="padding:8px 4px; font-size:13px; text-align:right;">${item.qty || 1}</td>
				<td style="padding:8px 4px; font-size:13px; text-align:right;">${item.rate || 0}</td>
				<td style="padding:8px 4px; font-size:13px; text-align:center; color:${conf >= 80 ? "#16a34a" : "#d97706"};">${conf}%</td>
			</tr>`;
		}).join("");

		this._set_content(`
			<div style="padding:16px;">
				<div style="margin-bottom:12px; font-size:13px; color:#6b7280;">
					${s.matched || 0}/${s.total || 0} ${__("items matched")}
					${s.unmatched ? ` · <span style="color:#dc2626;">${s.unmatched} ${__("unmatched")}</span>` : ""}
				</div>
				<table style="width:100%; border-collapse:collapse; font-size:13px;">
					<thead>
						<tr style="border-bottom:2px solid #e5e7eb; color:#6b7280;">
							<th style="padding:6px 4px; text-align:left; font-weight:500;">${__("Description")}</th>
							<th style="padding:6px 4px; text-align:left; font-weight:500;">${__("Item Code")}</th>
							<th style="padding:6px 4px; text-align:right; font-weight:500;">${__("Qty")}</th>
							<th style="padding:6px 4px; text-align:right; font-weight:500;">${__("Rate")}</th>
							<th style="padding:6px 4px; text-align:center; font-weight:500;">${__("Conf.")}</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
		`);
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
		frappe.call({
			method: "fatura_ai.api.import_wizard.get_review_summary",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (r.message) this._show_review(r.message);
			},
		});
	}

	_show_review(summary) {
		const log = summary.log || {};
		const ext = summary.extracted || {};
		this._set_content(`
			<div style="padding:16px;">
				<p style="font-weight:600; font-size:15px; margin-bottom:16px; color:#111827;">
					${__("Ready to import — please review")}
				</p>
				<table style="width:100%; border-collapse:collapse; font-size:14px;">
					<tr style="border-bottom:1px solid #e5e7eb;">
						<td style="padding:8px 0; color:#6b7280; width:40%;">${__("Supplier")}</td>
						<td style="padding:8px 0; font-weight:500;">${log.matched_supplier || "—"}</td>
					</tr>
					<tr style="border-bottom:1px solid #e5e7eb;">
						<td style="padding:8px 0; color:#6b7280;">${__("Invoice No.")}</td>
						<td style="padding:8px 0;">${ext.invoice_number || "—"}</td>
					</tr>
					<tr style="border-bottom:1px solid #e5e7eb;">
						<td style="padding:8px 0; color:#6b7280;">${__("Invoice Date")}</td>
						<td style="padding:8px 0;">${ext.invoice_date || "—"}</td>
					</tr>
					<tr style="border-bottom:1px solid #e5e7eb;">
						<td style="padding:8px 0; color:#6b7280;">${__("Total")}</td>
						<td style="padding:8px 0;">${ext.total || "—"}</td>
					</tr>
					<tr>
						<td style="padding:8px 0; color:#6b7280;">${__("Items")}</td>
						<td style="padding:8px 0;">${log.items_matched || 0} / ${log.items_count || 0} ${__("matched")}</td>
					</tr>
				</table>
				<div style="margin-top:16px; padding:12px; background:#fef3c7; border-radius:6px; font-size:13px; color:#92400e;">
					⚠️ ${__("The document will be created as a Draft. Review and submit manually.")}
				</div>
			</div>
		`);
	}

	_do_populate() {
		frappe.call({
			method: "fatura_ai.api.import_wizard.confirm_import",
			args: { log_name: this.log_name },
			callback: (r) => {
				if (!r.message) return;
				this.dialog.hide();
				frappe.show_alert({ message: __("Invoice imported successfully"), indicator: "green" });
				// Open the newly created document
				if (r.message.doctype && r.message.docname) {
					frappe.set_route("Form", r.message.doctype, r.message.docname);
				}
			},
		});
	}

	// ── Shared helpers ───────────────────────────────────────────────────────

	_step_html(step) {
		const labels = [__("Upload"), __("Extracting"), __("Supplier"), __("Items"), __("Review")];
		return `<div style="display:flex; gap:8px; padding:8px 0 16px; font-size:13px;">` +
			labels.map((l, i) => {
				const active = i === step;
				const done = i < step;
				const style = active
					? "color:#2563eb; font-weight:600; border-bottom:2px solid #2563eb; padding-bottom:4px;"
					: done
					? "color:#16a34a;"
					: "color:#9ca3af;";
				return `<span style="${style}">${done ? "✓ " : ""}${l}</span>${i < labels.length - 1 ? '<span style="color:#d1d5db;">›</span>' : ""}`;
			}).join("") +
			`</div>`;
	}
};
