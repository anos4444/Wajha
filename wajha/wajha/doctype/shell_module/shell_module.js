// The group is deliberately free text: packs create groups from workspace
// titles and hand-made modules name theirs at will, so a Link to a groups
// DocType would need every group to exist first (and a migration for
// every existing row). An Autocomplete keeps the freedom and still offers
// the groups already in use, so a typo no longer splits a group in two.
frappe.ui.form.on("Shell Module", {
	setup(frm) {
		frappe.db
			.get_list("Shell Module", { fields: ["group"], limit: 1000 })
			.then((rows) => {
				const groups = [...new Set(rows.map((r) => r.group).filter(Boolean))].sort((a, b) =>
					a.localeCompare(b, "ar")
				);
				const ctrl = frm.fields_dict.group;
				if (ctrl && ctrl.set_data) ctrl.set_data(groups);
			});
	},
});
