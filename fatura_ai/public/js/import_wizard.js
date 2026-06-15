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
		this._auto_create_items = true;
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

		let settled = false;
		const timeoutId = setTimeout(() => {
			if (!settled) {
				settled = true;
				this._show_supplier_error(__("Supplier matching is taking too long — please try again"));
			}
		}, 15000);

		frappe.call({
			method: "fatura_ai.api.import_wizard.match_supplier",
			args: { log_name: this.log_name },
			callback: (r) => {
				clearTimeout(timeoutId);
				if (settled) return;
				settled = true;
				if (r.exc || (r.message && r.message.status === "error")) {
					const msg = (r.message && r.message.message) || r.exc || __("Supplier matching failed unexpectedly");
					this._show_supplier_error(msg);
					return;
				}
				if (r.message) {
					this._show_supplier_match(r.message);
				} else {
					this._show_supplier_error(__("Supplier matching returned no result — please try again"));
				}
			},
		});
	}

	_show_supplier_error(msg) {
		this._set_content(`
			<div style="padding:16px;">
				<div style="background:#fef2f2; border-radius:6px; padding:12px; font-size:13px; color:#991b1b; margin-bottom:12px;">
					❌ <strong>${__("Supplier matching failed")}</strong><br><br>
					<code style="font-size:11px; white-space:pre-wrap; word-break:break-all;">${frappe.utils.escape_html(String(msg))}</code>
				</div>
				<button class="btn btn-default btn-sm fatura-retry-supplier">${__("Retry")}</button>
			</div>
		`);
		setTimeout(() => {
			this.dialog.fields_dict.step_content.$wrapper
				.find(".fatura-retry-supplier")
				.on("click", () => this._render_supplier());
		}, 50);
	}

	_pdf_type_banner() {
		const extracted = JSON.parse(this.extracted?.extracted_json || "{}") || {};
		if (extracted.pdf_type !== "image") return "";
		return `<div style="background:#fef3c7; border-radius:6px; padding:10px 12px; margin-bottom:12px; font-size:12px; color:#92400e;">
			⚠️ ${__("This invoice appears to be image-based. Extraction accuracy may be lower. QR code data (if present) is used as the primary source.")}
		</div>`;
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
				${this._pdf_type_banner()}
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
		const extracted = JSON.parse(this.extracted?.extracted_json || "{}") || {};
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

	// T028 — no supplier found; offer search or auto-create from extracted data
	_show_supplier_autocreate(match) {
		this.dialog.get_primary_btn().hide();
		const extracted = JSON.parse(this.extracted?.extracted_json || "{}") || {};
		const vendor = extracted.vendor_name || extracted.seller_name || extracted.supplier_name || "";
		const tax_id = extracted.tax_id || extracted.vat_number || extracted.seller_vat || "";
		const qr_badge = extracted.qr_data_found
			? `<span style="font-size:11px; color:#16a34a; margin-left:6px;">✓ ${__("from ZATCA QR")}</span>`
			: "";
		this._autocreate_name = vendor;
		this._autocreate_tax_id = tax_id;
		this._set_content(`
			<div style="padding:16px;">
				${this._pdf_type_banner()}
				<div style="background:#fef3c7; border-radius:6px; padding:12px; margin-bottom:16px; font-size:13px; color:#92400e;">
					⚠️ <strong>${__("Supplier not found in ERPNext")}</strong>
				</div>
				<p style="font-size:13px; color:#374151; margin-bottom:12px; font-weight:500;">${__("Extracted from invoice")}:</p>
				<div style="margin-bottom:12px;">
					<label style="font-size:13px; color:#6b7280; display:block; margin-bottom:4px;">${__("Name")}</label>
					<input id="fatura-new-supplier-name" type="text" class="form-control input-sm"
						value="${frappe.utils.escape_html(vendor)}" />
				</div>
				<div style="margin-bottom:20px;">
					<label style="font-size:13px; color:#6b7280; display:block; margin-bottom:4px;">${__("VAT Number")}${qr_badge}</label>
					<input id="fatura-new-supplier-vat" type="text" class="form-control input-sm"
						value="${frappe.utils.escape_html(tax_id)}" />
				</div>
				<div style="display:flex; gap:8px; flex-wrap:wrap;">
					<button class="btn btn-default btn-sm fatura-search-supplier">
						🔍 ${__("Search existing supplier")}
					</button>
					<button class="btn btn-primary btn-sm fatura-create-supplier">
						➕ ${__("Create new supplier")}
					</button>
				</div>
			</div>
		`);
		setTimeout(() => {
			const $w = this.dialog.fields_dict.step_content.$wrapper;
			$w.find("#fatura-new-supplier-name").on("change keyup", (e) => { this._autocreate_name = e.target.value.trim(); });
			$w.find("#fatura-new-supplier-vat").on("change keyup", (e) => { this._autocreate_tax_id = e.target.value.trim(); });
			$w.find(".fatura-search-supplier").on("click", () => this._open_supplier_search());
			$w.find(".fatura-create-supplier").on("click", () => this._do_create_supplier());
		}, 50);
	}

	_open_supplier_search() {
		frappe.prompt(
			[{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier", reqd: 1 }],
			(values) => {
				this.confirmed_supplier = values.supplier;
				frappe.call({
					method: "fatura_ai.api.import_wizard.confirm_supplier",
					args: { log_name: this.log_name, supplier: values.supplier },
					callback: () => this._go_to(3),
				});
			},
			__("Search Supplier"),
			__("Select & Continue")
		);
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
		this.dialog.get_primary_btn().show();
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
		this.confirmed_items = items.map(item => Object.assign({}, item));
		this._set_content(this._items_html(items, s));
		this._bind_items_events();
	}

	_items_summary_text(items) {
		const list = items !== undefined ? items : this.confirmed_items;
		const total = list.length;
		const matched = list.filter(i => !!(i.matched_item || i.item_code)).length;
		const unmatched = total - matched;
		if (total === 0) return __("No items");
		if (unmatched === 0) return `${matched}/${total} ${__("items matched")}`;
		const action = this._auto_create_items ? __("will be auto-created") : __("will be skipped");
		return `${matched}/${total} ${__("items matched")} &nbsp;&middot;&nbsp; ${unmatched} ${action}`;
	}

	_items_html(items, s) {
		const matchedCount = s.matched || 0;
		const totalCount = s.total || 0;
		const partialCount = s.partial || 0;
		const unmatchedCount = s.unmatched || 0;
		const allMatched = matchedCount === totalCount && totalCount > 0;
		const legendColor = allMatched ? "#16a34a" : unmatchedCount > 0 ? "#dc2626" : "#ca8a04";
		const legendIcon = allMatched ? "✅" : unmatchedCount > 0 ? "❌" : "⚠️";
		const legend = `<div style="margin-bottom:10px;font-size:13px;color:#6b7280;">
			<span style="color:${legendColor};font-weight:500;">${legendIcon} ${matchedCount}/${totalCount} ${__("items matched")}</span>
			${partialCount > 0 ? ` &nbsp;·&nbsp; <span style="color:#ca8a04;">${partialCount} ${__("partial")}</span>` : ""}
			${unmatchedCount > 0 ? ` &nbsp;·&nbsp; <span style="color:#dc2626;">${unmatchedCount} ${__("unmatched")}</span>` : ""}
		</div>`;
		const autoCreateChecked = this._auto_create_items ? "checked" : "";
		const autoCreateHtml = `<div style="margin-bottom:10px;font-size:13px;color:#374151;">
			<label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
				<input type="checkbox" id="fatura-auto-create-items" ${autoCreateChecked}
					style="width:16px;height:16px;cursor:pointer;" />
				<span>${__("Auto-create missing items in ERPNext (uses item name as item code, group: Services)")}</span>
			</label>
			<div id="fatura-items-summary" style="margin-top:5px;margin-left:22px;font-size:12px;color:#6b7280;">
				${this._items_summary_text(items)}
			</div>
		</div>`;
		const empty = items.length === 0
			? `<p style="padding:20px 0;text-align:center;color:#6b7280;font-size:13px;">
				${__("No items found in invoice. Add items manually.")}
			   </p>`
			: "";
		const thead = `<thead><tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb;">
			<th style="padding:5px 4px;width:18px;color:#6b7280;font-weight:500;">#</th>
			<th style="padding:5px 4px;text-align:left;color:#6b7280;font-weight:500;min-width:90px;">${__("Item Code")}</th>
			<th style="padding:5px 4px;text-align:left;color:#6b7280;font-weight:500;min-width:110px;">${__("Item Name")}</th>
			<th style="padding:5px 4px;text-align:left;color:#6b7280;font-weight:500;min-width:130px;">${__("Description")}</th>
			<th style="padding:5px 4px;text-align:right;color:#6b7280;font-weight:500;width:46px;">${__("Qty")}</th>
			<th style="padding:5px 4px;text-align:left;color:#6b7280;font-weight:500;width:50px;">${__("UOM")}</th>
			<th style="padding:5px 4px;text-align:right;color:#6b7280;font-weight:500;width:66px;">${__("Rate")}</th>
			<th style="padding:5px 4px;text-align:right;color:#6b7280;font-weight:500;width:66px;">${__("Amount")}</th>
			<th style="padding:5px 4px;width:24px;"></th>
		</tr></thead>`;
		const tbody = `<tbody id="fatura-items-tbody">${this._items_tbody_html(items)}</tbody>`;
		return `<div style="padding:12px 16px;">
			${legend}${autoCreateHtml}${empty}
			<div style="overflow-x:auto;">
				<table style="width:100%;border-collapse:collapse;font-size:12px;">${thead}${tbody}</table>
			</div>
			<button class="btn btn-default btn-xs fatura-add-row" style="margin-top:10px;font-size:12px;">
				+ ${__("Add row")}
			</button>
		</div>`;
	}

	_items_tbody_html(items) {
		return items.map((item, idx) => this._item_row_html(item, idx)).join("");
	}

	_item_row_html(item, idx) {
		const matched = item.matched_item || item.item_code || "";
		const method = item.match_method || "";
		const conf = Math.round((item.match_confidence || 0) * 100);
		const isMatched = !!matched;
		const isHighConf = conf >= 80;
		const isMediumConf = conf >= 50 && conf < 80;
		const isLowConf = conf > 0 && conf < 50;
		const rowBg = isMatched ? (isHighConf ? "" : "background:#FFFBEB;") : "background:#FEF2F2;";
		const badgeColor = isHighConf ? "#16a34a" : isMediumConf ? "#ca8a04" : isLowConf ? "#dc2626" : "#9ca3af";
		const badgeIcon = isHighConf ? "✅" : isMediumConf ? "⚠️" : isLowConf ? "❌" : "—";
		const badgeText = method ? `${badgeIcon} ${method}` : badgeIcon;
		const tip = method ? `title="${frappe.utils.escape_html(method + (conf ? ` (${conf}%)` : ''))}"` : "";
		const codeStyle = isMatched ? "border-color:#34A853;background:#f0fdf4;" : "border-color:#dc2626;background:#fef2f2;";
		const qty = parseFloat(item.qty || 1);
		const rate = parseFloat(item.rate || item.unit_price || 0);
		const amount = parseFloat(item.amount || (qty * rate));
		return `<tr data-idx="${idx}" style="border-bottom:1px solid #f3f4f6;${rowBg}">
			<td style="padding:4px;color:#9ca3af;font-size:11px;text-align:center;">${idx + 1}</td>
			<td style="padding:4px;">
				<div style="display:flex;align-items:center;gap:4px;">
					<input type="text" class="fatura-item-code form-control input-xs" ${tip}
						style="height:26px;font-size:11px;width:100%;${codeStyle}"
						placeholder="${__("Search item…")}" value="${frappe.utils.escape_html(matched)}" />
					<span style="font-size:11px;color:${badgeColor};white-space:nowrap;" title="${frappe.utils.escape_html(method + (conf ? ` (${conf}%)` : ''))}">${badgeText}</span>
				</div>
			</td>
			<td style="padding:4px;">
				<input type="text" class="fatura-item-name form-control input-xs"
					style="height:26px;font-size:11px;width:100%;" maxlength="140"
					value="${frappe.utils.escape_html(item.item_name || "")}" />
			</td>
			<td style="padding:4px;">
				<textarea class="fatura-desc form-control"
					style="font-size:11px;resize:vertical;min-height:26px;height:38px;width:100%;"
					rows="1">${frappe.utils.escape_html(item.description || "")}</textarea>
			</td>
			<td style="padding:4px;">
				<input type="number" class="fatura-qty form-control input-xs"
					style="height:26px;font-size:11px;text-align:right;width:100%;"
					value="${qty}" min="0" step="0.001" />
			</td>
			<td style="padding:4px;">
				<input type="text" class="fatura-uom form-control input-xs"
					style="height:26px;font-size:11px;width:100%;"
					value="${frappe.utils.escape_html(item.uom || "Nos")}" />
			</td>
			<td style="padding:4px;">
				<input type="number" class="fatura-rate form-control input-xs"
					style="height:26px;font-size:11px;text-align:right;width:100%;"
					value="${rate}" min="0" step="0.001" />
			</td>
			<td style="padding:4px;text-align:right;font-size:11px;color:#374151;white-space:nowrap;" class="fatura-amount">${amount.toFixed(2)}</td>
			<td style="padding:4px;text-align:center;">
				<button class="btn btn-xs fatura-remove-row"
					style="padding:1px 5px;font-size:13px;line-height:1;color:#9ca3af;background:none;border:none;"
					title="${__("Remove row")}">×</button>
			</td>
		</tr>`;
	}

	_bind_items_events() {
		setTimeout(() => {
			const $w = this.dialog.fields_dict.step_content.$wrapper;
			$w.on("click.fatura-items", ".fatura-remove-row", (e) => {
				const idx = parseInt($(e.target).closest("tr").data("idx"));
				this._sync_from_dom();
				this.confirmed_items.splice(idx, 1);
				this._refresh_items_tbody();
			});
			$w.on("input.fatura-items change.fatura-items", ".fatura-qty, .fatura-rate", (e) => {
				const $tr = $(e.target).closest("tr");
				const qty = parseFloat($tr.find(".fatura-qty").val() || 0);
				const rate = parseFloat($tr.find(".fatura-rate").val() || 0);
				$tr.find(".fatura-amount").text((qty * rate).toFixed(2));
			});
			$w.find(".fatura-add-row").on("click", () => {
				this._sync_from_dom();
				this.confirmed_items.push({
					item_name: "", description: "", qty: 1,
					uom: "Nos", rate: 0, amount: 0, matched_item: null,
				});
				this._refresh_items_tbody();
			});
			// Auto-create checkbox — update state and summary line
			$w.find("#fatura-auto-create-items").on("change", (e) => {
				this._auto_create_items = e.target.checked;
				$w.find("#fatura-items-summary").html(this._items_summary_text());
			});
		}, 50);
	}

	_sync_from_dom() {
		const $w = this.dialog.fields_dict.step_content.$wrapper;
		$w.find("#fatura-items-tbody tr").each((_, tr) => {
			const $tr = $(tr);
			const idx = parseInt($tr.data("idx"));
			const item = this.confirmed_items[idx];
			if (!item) return;
			item.matched_item = $tr.find(".fatura-item-code").val().trim() || null;
			item.item_name = $tr.find(".fatura-item-name").val().trim();
			item.description = $tr.find(".fatura-desc").val().trim();
			item.qty = parseFloat($tr.find(".fatura-qty").val()) || 1;
			item.uom = $tr.find(".fatura-uom").val().trim() || "Nos";
			item.rate = parseFloat($tr.find(".fatura-rate").val()) || 0;
			item.amount = item.qty * item.rate;
		});
	}

	_refresh_items_tbody() {
		const $w = this.dialog.fields_dict.step_content.$wrapper;
		$w.find("#fatura-items-tbody").html(this._items_tbody_html(this.confirmed_items));
	}

	_do_confirm_items() {
		this._sync_from_dom();
		const autoCreate = this._auto_create_items;
		let items = this.confirmed_items.map(item => ({
			item_code: item.matched_item || null,
			item_name: item.item_name || "",
			description: item.description || "",
			qty: parseFloat(item.qty) || 1,
			uom: item.uom || "Nos",
			rate: parseFloat(item.rate) || 0,
			amount: parseFloat(item.amount) || 0,
			matched_item: item.matched_item || null,
			match_method: item.match_method || (item.matched_item ? "Manual" : null),
			match_confidence: item.match_confidence || 0,
		}));

		if (autoCreate) {
			// Mark rows without an item_code for auto-creation
			items = items.map(item => {
				if (!item.item_code && !item.matched_item) {
					item.auto_create = true;
					// Use item_name as the item_code for creation
					item.item_code = item.item_name || null;
				}
				return item;
			});
		} else {
			// Skip rows with no item_code
			const skipped = items.filter(item => !item.item_code && !item.matched_item).length;
			items = items.filter(item => item.item_code || item.matched_item);
			if (skipped > 0) {
				frappe.msgprint(
					__("{0} row(s) skipped because no item code was selected. Enable auto-create to include them.", [skipped])
				);
			}
		}

		this.dialog.get_primary_btn().prop("disabled", true).html(`<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${__("Saving…")}`);
		frappe.call({
			method: "fatura_ai.api.import_wizard.confirm_items",
			args: {
				log_name: this.log_name,
				confirmed_items: JSON.stringify(items),
			},
			callback: (r) => {
				this.dialog.get_primary_btn().prop("disabled", false).html(__("Confirm Items"));
				if (r.message && r.message.status === "ok") {
					this._show_item_match_result(r.message);
				} else {
					frappe.msgprint(__("Failed to confirm items. Please try again."));
				}
			},
		});
	}

	_show_item_match_result(result) {
		const saved = result.saved || 0;
		const warnings = result.warnings || [];
		let warningHtml = "";
		if (warnings.length > 0) {
			warningHtml = `<div style="background:#fef3c7;border-radius:6px;padding:12px;margin-bottom:12px;font-size:12px;color:#92400e;">
				${warnings.map(w => `<div>⚠️ ${w}</div>`).join("")}
			</div>`;
		}
		this._set_content(`
			<div style="padding:16px;text-align:center;">
				<div style="font-size:32px;margin-bottom:12px;">✅</div>
				<p style="font-weight:600;font-size:15px;color:#111827;margin-bottom:8px;">
					${__("{0} items confirmed", [saved])}
				</p>
				<p style="font-size:13px;color:#6b7280;margin-bottom:16px;">
					${__("Item mappings have been saved for future imports.")}
				</p>
				${warningHtml}
				<button class="btn btn-primary btn-sm fatura-continue-review" style="margin-top:8px;">
					${__("Continue to Review")} →
				</button>
			</div>
		`);
		setTimeout(() => {
			this.dialog.fields_dict.step_content.$wrapper
				.find(".fatura-continue-review")
				.on("click", () => this._go_to(4));
		}, 50);
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
		const labels = [
			__("Upload"), __("AI Extraction"), __("Supplier"),
			__("Items"), __("Review"), __("Done"),
		];
		const parts = labels.map((label, i) => {
			const done = i < step;
			const active = i === step;
			const circleColor = active ? "#1A73E8" : done ? "#34A853" : "#e5e7eb";
			const textColor = (active || done) ? "#fff" : "#9ca3af";
			const labelColor = active ? "#1A73E8" : done ? "#34A853" : "#9ca3af";
			const lineColor = done ? "#34A853" : "#e5e7eb";
			const circle = `<div style="width:26px;height:26px;border-radius:50%;background:${circleColor};
				color:${textColor};display:flex;align-items:center;justify-content:center;
				font-size:11px;font-weight:700;flex-shrink:0;">${done ? "✓" : i + 1}</div>`;
			const lbl = `<div style="font-size:10px;margin-top:3px;color:${labelColor};
				font-weight:${active ? 600 : 400};text-align:center;white-space:nowrap;">${label}</div>`;
			const connector = i < labels.length - 1
				? `<div style="flex:1;height:2px;background:${lineColor};margin-bottom:14px;min-width:8px;"></div>`
				: "";
			return `<div style="display:flex;flex-direction:column;align-items:center;">${circle}${lbl}</div>${connector}`;
		}).join("");
		return `<div style="display:flex;align-items:center;padding:10px 4px 14px;gap:2px;">${parts}</div>`;
	}
};
