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
		// The icon is free text too (an emoji stays an emoji); the list
		// offers the Font Awesome names the shell can draw, so "fa:coins"
		// is picked rather than guessed.
		frappe.call("wajha.api.get_icon_names").then((r) => {
			const ctrl = frm.fields_dict.icon;
			if (ctrl && ctrl.set_data) ctrl.set_data(r.message || []);
		});
	},
});
