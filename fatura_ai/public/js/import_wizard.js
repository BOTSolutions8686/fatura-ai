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
		this._force_import = false;
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
		this._supplier_match = match;

		// T029 — multiple suppliers share the same VAT
		if (match.method === "VAT Ambiguous") {
			this._show_vat_ambiguous(match);
			return;
		}

		// T028 — no match found at all: offer auto-create
		if (!match.supplier) {
			this._show_supplier_autocreate(match);
			return;
		}

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

		setTimeout(() => {
			const $input = this.dialog.fields_dict.step_content.$wrapper.find("#fatura-supplier-override");
			$input.on("change keyup", () => {
				this.confirmed_supplier = $input.val();
			});
		}, 50);
	}

	// T029 — VAT matched multiple suppliers; let user pick one
	_show_vat_ambiguous(match) {
		this.dialog.set_primary_action(__("Confirm Supplier"), () => this._do_confirm_supplier());
		const extracted = frappe.parse_json(this.extracted?.extracted_json || "{}") || {};
		const vendor = extracted.vendor_name || (this.extracted || {}).vendor_name || "—";
		const candidates = match.candidates || [];
		const rows = candidates.map((c, i) => `
			<label style="display:flex; align-items:center; gap:8px; padding:10px 0; border-bottom:1px solid #e5e7eb; cursor:pointer;">
				<input type="radio" name="fatura-vat-candidate" value="${c.name}" ${i === 0 ? "checked" : ""} />
				<span style="font-size:14px;">${c.supplier_name || c.name}</span>
			</label>`).join("");
		this._set_content(`
			<div style="padding:16px;">
				<div style="background:#fef3c7; border-radius:6px; padding:12px; margin-bottom:16px; font-size:13px; color:#92400e;">
					⚠️ ${__("Multiple suppliers share this VAT number. Please select the correct one.")}
				</div>
				<p style="font-size:13px; color:#6b7280; margin-bottom:12px;">
					${__("AI extracted vendor")}: <strong>${vendor}</strong>
				</p>
				<div>${rows}</div>
			</div>
		`);
		setTimeout(() => {
			const $wrapper = this.dialog.fields_dict.step_content.$wrapper;
			$wrapper.find("input[name=fatura-vat-candidate]").on("change", (e) => {
				this.confirmed_supplier = e.target.value;
			});
			// Default to first candidate
			if (candidates.length) this.confirmed_supplier = candidates[0].name;
		}, 50);
	}

	// T028 — no supplier found; offer to auto-create from extracted data
	_show_supplier_autocreate(match) {
		this.dialog.set_primary_action(__("Create & Continue"), () => this._do_create_supplier());
		const extracted = frappe.parse_json(this.extracted?.extracted_json || "{}") || {};
		const vendor = extracted.vendor_name || extracted.seller_name || extracted.supplier_name || "";
		const tax_id = extracted.tax_id || extracted.vat_number || extracted.seller_vat || "";
		this._autocreate_name = vendor;
		this._autocreate_tax_id = tax_id;
		this._set_content(`
			<div style="padding:16px;">
				<div style="background:#fef2f2; border-radius:6px; padding:12px; margin-bottom:16px; font-size:13px; color:#991b1b;">
					❌ ${__("No matching supplier found in ERPNext.")}
				</div>
				<p style="font-size:13px; color:#374151; margin-bottom:16px;">
					${__("Auto-create a new supplier from the extracted invoice data:")}
				</p>
				<div style="margin-bottom:12px;">
					<label style="font-size:13px; color:#374151; display:block; margin-bottom:4px;">${__("Supplier Name")}</label>
					<input id="fatura-new-supplier-name" type="text" class="form-control input-sm" value="${vendor}" />
				</div>
				<div style="margin-bottom:12px;">
					<label style="font-size:13px; color:#374151; display:block; margin-bottom:4px;">${__("VAT Number")}</label>
					<input id="fatura-new-supplier-vat" type="text" class="form-control input-sm" value="${tax_id}" />
				</div>
				<p style="font-size:12px; color:#6b7280;">
					${__("Or type an existing supplier name below to link instead:")}
				</p>
				<input id="fatura-supplier-override" type="text" class="form-control input-sm"
					placeholder="${__("Existing supplier name…")}" value="" />
			</div>
		`);
		setTimeout(() => {
			const $w = this.dialog.fields_dict.step_content.$wrapper;
			$w.find("#fatura-new-supplier-name").on("change keyup", (e) => { this._autocreate_name = e.target.value.trim(); });
			$w.find("#fatura-new-supplier-vat").on("change keyup", (e) => { this._autocreate_tax_id = e.target.value.trim(); });
			$w.find("#fatura-supplier-override").on("change keyup", (e) => { this.confirmed_supplier = e.target.value.trim(); });
		}, 50);
	}

	_do_create_supplier() {
		// If user typed an existing supplier name in the override box, use confirm_supplier instead
		if (this.confirmed_supplier) {
			this._do_confirm_supplier();
			return;
		}
		if (!this._autocreate_name) {
			frappe.msgprint(__("Please enter a supplier name"));
			return;
		}
		frappe.call({
			method: "fatura_ai.api.import_wizard.create_supplier",
			args: {
				log_name: this.log_name,
				supplier_name: this._autocreate_name,
				tax_id: this._autocreate_tax_id || null,
			},
			callback: (r) => {
				if (r.message && r.message.supplier) {
					frappe.show_alert({
						message: __("Supplier created: {0}", [r.message.supplier]),
						indicator: "green",
					});
					this._go_to(3);
				}
			},
		});
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
		// Store mutable copy so edits persist
		this.confirmed_items = items.map(item => Object.assign({}, item));

		const rows = items.map((item, idx) => {
			const desc = item.description || item.item_name || "—";
			const matched = item.matched_item || "";
			const conf = Math.round((item.confidence || 0) * 100);
			const confColor = conf >= 80 ? "#16a34a" : conf >= 40 ? "#d97706" : "#dc2626";
			const badge = matched
				? `<span style="color:${confColor}; font-size:11px;">${conf}% match</span>`
				: `<span style="color:#dc2626; font-size:11px;">${__("No match — will create")}</span>`;
			return `<tr style="border-bottom:1px solid #e5e7eb;">
				<td style="padding:8px 4px; font-size:13px; max-width:200px; word-wrap:break-word;">${desc}</td>
				<td style="padding:6px 4px;">
					<input
						data-idx="${idx}"
						class="fatura-item-input form-control input-xs"
						style="font-size:12px; height:28px;"
						placeholder="${__("Item code / name")}"
						value="${matched}" />
					<div style="margin-top:2px;">${badge}</div>
				</td>
				<td style="padding:8px 4px; font-size:13px; text-align:right;">${item.qty || 1}</td>
				<td style="padding:8px 4px; font-size:13px; text-align:right;">${item.rate || item.unit_price || 0}</td>
			</tr>`;
		}).join("");

		this._set_content(`
			<div style="padding:16px;">
				<div style="margin-bottom:12px; font-size:13px; color:#6b7280;">
					${s.matched || 0}/${s.total || 0} ${__("items matched")} &nbsp;·&nbsp;
					${__("Edit item codes below. Blank rows will be skipped. New codes will be created automatically.")}
				</div>
				<div style="overflow-x:auto;">
				<table style="width:100%; border-collapse:collapse; font-size:13px;">
					<thead>
						<tr style="border-bottom:2px solid #e5e7eb; color:#6b7280;">
							<th style="padding:6px 4px; text-align:left; font-weight:500; width:45%;">${__("Description from Invoice")}</th>
							<th style="padding:6px 4px; text-align:left; font-weight:500; width:35%;">${__("ERPNext Item Code")}</th>
							<th style="padding:6px 4px; text-align:right; font-weight:500;">${__("Qty")}</th>
							<th style="padding:6px 4px; text-align:right; font-weight:500;">${__("Rate")}</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
				</div>
			</div>
		`);

		// Wire up input changes
		setTimeout(() => {
			this.dialog.fields_dict.step_content.$wrapper
				.find(".fatura-item-input")
				.on("change keyup", (e) => {
					const idx = parseInt($(e.target).data("idx"));
					this.confirmed_items[idx].matched_item = e.target.value.trim();
				});
		}, 50);
	}

	_do_confirm_items() {
		// Collect final values from inputs (in case of rapid changes)
		const $wrapper = this.dialog.fields_dict.step_content.$wrapper;
		$wrapper.find(".fatura-item-input").each((_, el) => {
			const idx = parseInt($(el).data("idx"));
			if (this.confirmed_items[idx]) {
				this.confirmed_items[idx].matched_item = el.value.trim();
			}
		});

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
			args: { log_name: this.log_name, force: this._force_import ? 1 : 0 },
			callback: (r) => {
				if (!r.message) return;
				// T030 — duplicate detected; let user decide
				if (r.message.status === "duplicate") {
					this._show_duplicate_warning(r.message.existing_pi);
					return;
				}
				// T034 — show non-blocking sanity warnings
				(r.message.warnings || []).forEach(w =>
					frappe.msgprint({ message: w, indicator: "orange", title: __("Import Warning") })
				);
				this.dialog.hide();
				frappe.show_alert({ message: __("Invoice imported successfully"), indicator: "green" });
				if (r.message.doctype && r.message.docname) {
					frappe.set_route("Form", r.message.doctype, r.message.docname);
				}
			},
		});
	}

	// T030 — show duplicate warning with link and force-create option
	_show_duplicate_warning(existing_pi) {
		const pi_url = `/app/purchase-invoice/${encodeURIComponent(existing_pi)}`;
		this._set_content(`
			<div style="padding:16px;">
				<div style="background:#fef3c7; border-radius:6px; padding:16px; margin-bottom:16px; font-size:14px; color:#92400e;">
					⚠️ <strong>${__("Duplicate Invoice Detected")}</strong><br><br>
					${__("A Purchase Invoice with this invoice number already exists:")}
					<a href="${pi_url}" target="_blank"
					   style="color:#2563eb; text-decoration:underline; margin-left:4px;">${existing_pi}</a>
				</div>
				<p style="font-size:13px; color:#374151; margin-bottom:16px;">
					${__("Open the existing invoice, or force-create a new one if needed.")}
				</p>
				<div style="display:flex; gap:8px;">
					<a href="${pi_url}" class="btn btn-default btn-sm" target="_blank">
						${__("Open Existing Invoice")}
					</a>
					<button class="btn btn-warning btn-sm fatura-force-create">
						${__("Force Create Anyway")}
					</button>
				</div>
			</div>
		`);
		setTimeout(() => {
			this.dialog.fields_dict.step_content.$wrapper
				.find(".fatura-force-create")
				.on("click", () => {
					this._force_import = true;
					this._do_populate();
				});
		}, 50);
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
