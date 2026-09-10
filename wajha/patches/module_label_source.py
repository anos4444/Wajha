"""0.22.0: seeded module labels were stored already translated into the site
language, so the sidebar froze at whatever the catalogue held on the day the
module was seeded. Since 0.22 the pack stores the DocType's own English
label and ``api.module_label`` translates it per user.

This resets the rows earlier releases seeded — but only those still holding
exactly what the pack would have written, so a label an administrator typed
is never touched. Rows already holding the English label need no change:
the request-time rule picks them up on its own.
"""

import frappe


def execute():
    if not frappe.db.table_exists("Shell Module"):
        return
    lang = frappe.db.get_single_value("System Settings", "language") or "en"
    if lang == "en":
        return

    reset = 0
    for m in frappe.get_all(
        "Shell Module",
        filters={"auto_generated": 1},
        fields=["name", "module_label", "module_label_en"],
    ):
        source = (m.module_label_en or "").strip()
        stored = (m.module_label or "").strip()
        if not source or not stored or stored == source:
            continue
        if stored == frappe._(source, lang=lang):
            frappe.db.set_value(
                "Shell Module", m.name, "module_label", source, update_modified=False
            )
            reset += 1
    if reset:
        print(f"wajha: {reset} module labels restored to their source text")
