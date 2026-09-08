"""0.20.1: auto-generated modules stored their group as the workspace title
already translated into the site's language, so an English user on an
Arabic site read Arabic group headers over English entries. Since 0.20.0
the apps pack stores the workspace's source title and get_config
translates it per user; this rewrites what earlier releases seeded.

Groups that do not match a workspace title in the site's language are
left alone: they were named by hand and belong to the administrator.
"""

import frappe


def execute():
    if not frappe.db.table_exists("Shell Module"):
        return
    lang = frappe.db.get_single_value("System Settings", "language") or "en"
    if lang == "en":
        return

    # {the title as this site shows it: the source title}
    back = {}
    for ws in frappe.get_all("Workspace", filters={"public": 1}, fields=["name", "title"]):
        source = ws.title or ws.name
        translated = frappe._(source, lang=lang)
        if translated and translated != source:
            back.setdefault(translated, source)
    if not back:
        return

    fixed = 0
    for m in frappe.get_all(
        "Shell Module", filters={"auto_generated": 1}, fields=["name", "group"]
    ):
        source = back.get((m.group or "").strip())
        if source and source != m.group:
            frappe.db.set_value("Shell Module", m.name, "group", source, update_modified=False)
            fixed += 1
    if fixed:
        print(f"wajha: {fixed} module groups restored to their source workspace titles")
