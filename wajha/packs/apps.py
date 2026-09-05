"""All-apps pack: a Shell Module record for every DocType the installed
apps' workspaces link to.

The Home tiles and virtual modules (wajha/discovery.py) already make every
app browsable without records. This pack goes one step further for sites
that want the modules to *exist* — visible in the sidebar under their
workspace, editable in Shell Module, flaggable for the bottom bar — without
anyone creating them by hand. Seeded on install, on migrate and whenever an
app is installed later, so a new app's DocTypes appear as records too.

Rules, same as the HRMS pack: create only what is missing; never touch an
existing module; a DocType that already has an All-scope module (hand-made
or from another pack) is skipped. Switched by Shell Settings.seed_modules.
"""

import frappe
from frappe.utils import cint

from wajha.api import build_module_doc

SKIP_DOCTYPES = {"DocType", "Custom Field", "Property Setter", "Server Script", "Client Script",
                 "Print Format", "Report", "Page", "Workspace", "Desktop Icon"}
# Workspaces that are the Desk's own plumbing rather than an app's work.
SKIP_WORKSPACES = {"Home", "Build", "Welcome Workspace", "My Workspaces"}


def enabled():
    if not frappe.db.exists("DocType", "Shell Settings"):
        return False
    s = frappe.get_cached_doc("Shell Settings")
    return bool(s.meta.has_field("seed_modules") and cint(s.seed_modules))


def seed(app_name=None):
    """Runs from after_install, after_migrate and after_app_install."""
    if not frappe.db.exists("DocType", "Shell Module") or not enabled():
        return
    frappe.clear_cache(doctype="Shell Module")
    lang = frappe.db.get_single_value("System Settings", "language") or "en"
    covered = {m.ref_doctype for m in frappe.get_all(
        "Shell Module", filters={"view_type": "List"}, fields=["ref_doctype", "scope"])
        if (m.scope or "All") == "All"}
    existing_keys = set(frappe.get_all("Shell Module", pluck="module_key"))

    fields = ["name", "title", "sequence_id"]
    if frappe.get_meta("Workspace").has_field("app"):
        fields.append("app")
    created, skipped = [], 0
    for ws in frappe.get_all("Workspace", filters={"public": 1, "is_hidden": 0},
                             fields=fields, order_by="sequence_id asc, title asc"):
        if ws.name in SKIP_WORKSPACES:
            continue
        if app_name and ws.get("app") and ws.get("app") != app_name:
            # An app just installed: only its workspaces can be new.
            continue
        try:
            doc = frappe.get_cached_doc("Workspace", ws.name)
        except frappe.DoesNotExistError:
            continue
        order = 0
        for link in doc.links:
            if link.type != "Link" or link.link_type != "DocType" or link.hidden or not link.link_to:
                continue
            order += 1
            dt = link.link_to
            if dt in SKIP_DOCTYPES or dt in covered or not frappe.db.exists("DocType", dt):
                continue
            meta = frappe.get_meta(dt)
            if meta.istable or meta.issingle:
                continue
            key = frappe.scrub(dt)
            if key in existing_keys:
                skipped += 1
                continue
            try:
                _create(dt, key, link.label, ws, order, lang)
            except Exception:
                frappe.log_error(title=f"wajha: apps pack could not seed {dt}", message=frappe.get_traceback())
                skipped += 1
                continue
            covered.add(dt)
            existing_keys.add(key)
            created.append(key)
    if created or skipped:
        print(f"wajha: apps pack — created {len(created)} modules, skipped {skipped}")


def _create(dt, key, label, ws, order, lang):
    doc = build_module_doc(dt, key, frappe._(label or dt, lang=lang))
    doc.module_label_en = label or dt
    doc.group = frappe._(ws.title or ws.name, lang=lang)
    doc.sequence = 1000 + int((ws.sequence_id or 0) * 100) + order
    doc.auto_generated = 1
    doc.flags.ignore_permissions = True
    doc.flags.skip_filter_indexes = True
    doc.insert(ignore_permissions=True)
