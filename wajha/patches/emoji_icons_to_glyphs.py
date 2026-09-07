"""0.18.1: turn the emoji icons of existing Shell Module records into the
Font Awesome glyphs 0.18 draws, so a site that installed earlier looks
like a fresh one. Known emoji map by meaning (📍 → location-dot); anything
else takes the DocType's own glyph. Records already on ``fa:`` are left
alone, and modified stamps are not touched."""

import frappe

from wajha import icons


def execute():
    if not frappe.db.table_exists("Shell Module"):
        return
    for m in frappe.get_all("Shell Module", fields=["name", "icon", "ref_doctype", "route", "view_type"]):
        new = icons.from_emoji(m.icon, m.ref_doctype if m.view_type == "List" else None, m.route)
        if new != (m.icon or ""):
            frappe.db.set_value("Shell Module", m.name, "icon", new, update_modified=False)
