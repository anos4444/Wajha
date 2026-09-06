"""Remove every trace the Swift Theme module (0.6.0 – 0.16.x) left in a site.

The module shipped inside Wajha as a port of the standalone swift_theme app.
Its stylesheets loaded on every Desk page whether the theme was on or off,
and one of them painted a fallback canvas exactly when it was off — the
navy/pale band under the Desk reported on two sites. The owner asked for
Swift to go entirely (0.17.0). Deleting the code leaves the site carrying
its DocTypes, Page, Module Def and the nine swift_* Custom Fields on User;
Frappe's migrate never removes those on its own, so this patch does.

Idempotent: every step tolerates the thing already being gone, so a site
that installed after the removal is untouched.
"""

import frappe

DOCTYPES = ["Swift Theme Sound Event", "Swift Home Card", "Swift Theme Settings"]
PAGES = ["swift_home"]
MODULE = "Swift Theme"


def execute():
    # Custom Fields first: the User form reads them on every load, and they
    # point at the module we are about to delete.
    for name in frappe.get_all(
        "Custom Field", filters={"dt": "User", "fieldname": ["like", "swift_%"]}, pluck="name"
    ):
        frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True, ignore_missing=True)
    for name in frappe.get_all("Property Setter", filters={"module": MODULE}, pluck="name"):
        frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True, ignore_missing=True)

    for page in PAGES:
        if frappe.db.exists("Page", page):
            frappe.delete_doc("Page", page, force=True, ignore_permissions=True, ignore_missing=True)
    for dt in DOCTYPES:
        if frappe.db.exists("DocType", dt):
            # Singles keep their values in tabSingles; child rows sit in their
            # own tables. Deleting the DocType drops the table and the meta.
            frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True, ignore_missing=True, delete_permanently=True)
    frappe.db.delete("Singles", {"doctype": ["in", DOCTYPES]})

    # Frappe's own registrations of the module's page: a Workspace filed under
    # the module, and Desktop Icons that link to the page. Field names differ
    # between Frappe versions, so each lookup is guarded.
    for dt, filters in (("Workspace", {"module": MODULE}), ("Desktop Icon", {"link_to": "swift_home"}),
                        ("Desktop Icon", {"label": "Swift Home"})):
        try:
            names = frappe.get_all(dt, filters=filters, pluck="name")
        except Exception:
            continue
        for name in names:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True, ignore_missing=True)

    if frappe.db.exists("Module Def", MODULE):
        frappe.delete_doc("Module Def", MODULE, force=True, ignore_permissions=True, ignore_missing=True)

    frappe.clear_cache()
