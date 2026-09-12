"""0.24.0: the language switch is on by default, but a Check field's default
only applies to documents created after the field exists. Shell Settings is
a Single that already exists on every site, so its new `show_language_switch`
came back None: the form showed the box unticked and, read literally, the
switch would have been hidden. Set it once, where the site has never chosen.
"""

import frappe


def execute():
    if frappe.db.get_single_value("Shell Settings", "show_language_switch") is None:
        frappe.db.set_single_value("Shell Settings", "show_language_switch", 1)
        frappe.clear_cache()
