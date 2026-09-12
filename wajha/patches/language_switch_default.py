"""0.24.0: the language switch is on by default, but a Check field's default
only applies to documents created after the field exists. Shell Settings is
a Single that already exists on every site, so its new `show_language_switch`
has no row in tabSingles; Frappe reads a missing Check as 0 (never None),
which read as "off" and hid the switch. Write the default once, where the
site has never chosen — judged by the raw tabSingles row, since every
higher-level getter already casts the gap to 0.
"""

import frappe


def execute():
    stored = frappe.db.get_value(
        "Singles", {"doctype": "Shell Settings", "field": "show_language_switch"}, "value"
    )
    if stored is None:
        frappe.db.set_single_value("Shell Settings", "show_language_switch", 1)
        frappe.clear_cache()
