frappe.listview_settings["Fatura Import Log"] = {
	add_fields: ["status", "matched_supplier", "linked_pi", "import_date"],

	get_indicator: function (doc) {
		const map = {
			Draft: ["orange", "status,=,Draft"],
			Extracted: ["blue", "status,=,Extracted"],
			Confirmed: ["yellow", "status,=,Confirmed"],
			Imported: ["green", "status,=,Imported"],
			Failed: ["red", "status,=,Failed"],
		};
		return map[doc.status] || ["gray", "status,=," + doc.status];
	},

	formatters: {
		linked_pi: function (value) {
			if (!value) return "—";
			const url = "/app/purchase-invoice/" + encodeURIComponent(value);
			return `<a href="${url}" style="color:#2563eb;">${value}</a>`;
		},
	},

	onload: function (listview) {
		listview.page.set_title(__("Import History"));
	},
};
