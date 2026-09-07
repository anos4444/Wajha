"""0.19.0: the Font Awesome glyphs are Desk symbols now, named ``fa-<name>``
as the icon picker lists them; 0.18 wrote them ``fa:<name>``. Rewrite the
Shell Module records and action rows that carry the old spelling."""

import frappe


def execute():
    for dt in ("Shell Module", "Shell Module Action"):
        if not frappe.db.table_exists(dt):
            continue
        for row in frappe.get_all(dt, filters={"icon": ["like", "fa:%"]}, fields=["name", "icon"]):
            frappe.db.set_value(dt, row.name, "icon", "fa-" + row.icon[3:], update_modified=False)
