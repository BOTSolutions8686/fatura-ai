/**
 * Fatura AI — Purchase Invoice button
 * Adds "Import from Invoice" button to the Purchase Invoice form.
 */
frappe.ui.form.on("Purchase Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(
				__("Import from Invoice"),
				() => {
					if (window.FaturaWizard) {
						new window.FaturaWizard(frm).open();
					} else {
						frappe.msgprint(__("Fatura AI wizard failed to load. Please refresh the page."));
					}
				},
				__("Fatura AI")
			);
		}
	},
});
