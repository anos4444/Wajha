"""Seed theme presets, roles and default settings. Idempotent."""

import frappe

PRESETS = [
    {
        "theme_name": "الأخضر المؤسسي",
        "primary": "#013D28", "primary_dark": "#00291B", "accent": "#D9A21B",
        "sidebar_bg": "#00543C", "sidebar_ink": "#CFE3D8",
        "sidebar_active_bg": "#FFFFFF", "sidebar_active_ink": "#013D28",
        "page_bg": "#F2F3F1", "surface_bg": "#FFFFFF", "ink": "#182620",
        "muted_ink": "#6B7C74", "border": "#E2E6E0",
        "danger": "#C0392B", "warning": "#E07B1A", "success": "#2E7D4F",
        "info": "#00838F",
    },
    {
        "theme_name": "الأزرق الحكومي",
        "primary": "#0B3C6B", "primary_dark": "#072949", "accent": "#C9A227",
        "sidebar_bg": "#0B3C6B", "sidebar_ink": "#CFDDEB",
        "sidebar_active_bg": "#FFFFFF", "sidebar_active_ink": "#0B3C6B",
        "page_bg": "#F1F3F6", "surface_bg": "#FFFFFF", "ink": "#16202B",
        "muted_ink": "#6B7684", "border": "#E0E4EA",
        "danger": "#B3261E", "warning": "#B26B00", "success": "#1E6E43",
        "info": "#0F6C8C",
    },
    {
        "theme_name": "الرمادي المحايد",
        "primary": "#2F3437", "primary_dark": "#1D2123", "accent": "#B07D2B",
        "sidebar_bg": "#22272A", "sidebar_ink": "#CBD2D6",
        "sidebar_active_bg": "#FFFFFF", "sidebar_active_ink": "#22272A",
        "page_bg": "#F4F5F6", "surface_bg": "#FFFFFF", "ink": "#1B1F21",
        "muted_ink": "#6E7679", "border": "#E3E6E8",
        "danger": "#B3261E", "warning": "#A96A00", "success": "#2A6B47",
        "info": "#2B6A7C",
    },
    {
        "theme_name": "العنابي",
        "primary": "#5B1F33", "primary_dark": "#3F1523", "accent": "#C08A2E",
        "sidebar_bg": "#5B1F33", "sidebar_ink": "#EBD6DC",
        "sidebar_active_bg": "#FFFFFF", "sidebar_active_ink": "#5B1F33",
        "page_bg": "#F5F2F3", "surface_bg": "#FFFFFF", "ink": "#231A1D",
        "muted_ink": "#7A6B70", "border": "#E8E1E3",
        "danger": "#B3261E", "warning": "#A96A00", "success": "#2A6B47",
        "info": "#2B6A7C",
    },
]


def after_install():
    """Seed a freshly installed site.

    Registered separately from after_migrate because `bench install-app` does
    not run migrate hooks: without this, a fresh install left Shell Settings
    with no active_theme and no Shell Theme records at all, so the shell
    rendered untokenised until someone happened to run `bench migrate`.
    """
    _seed()


def after_migrate():
    _seed()


def _seed():
    create_role()
    seed_themes()
    ensure_settings()
    frappe.db.commit()


def create_role():
    if not frappe.db.exists("Role", "Shell Manager"):
        frappe.get_doc({"doctype": "Role", "role_name": "Shell Manager",
                        "desk_access": 1}).insert(ignore_permissions=True)


def seed_themes():
    for p in PRESETS:
        if frappe.db.exists("Shell Theme", p["theme_name"]):
            continue
        doc = frappe.new_doc("Shell Theme")
        doc.update(p)
        doc.is_preset = 1
        doc.insert(ignore_permissions=True)
    print(f"wajha: theme presets ready ({len(PRESETS)})")


def ensure_settings():
    s = frappe.get_single("Shell Settings")
    changed = False
    if not s.active_theme:
        s.active_theme = PRESETS[0]["theme_name"]
        changed = True
    if not s.brand_title:
        s.brand_title = "نظام الإدارة"
        changed = True
    # 0.9.0 added show_desk_link. A Check that was never stored loads as 0
    # (Document init fills unset Checks), so `not s.show_desk_link` cannot
    # tell "never set" from "turned off" — the same trap the Swift master
    # switch hit in 0.7.0. The stored row can: get_single_value is None only
    # when the field was never saved. Never set -> on; an explicit 0 stays.
    if s.meta.has_field("show_desk_link") and \
            frappe.db.get_single_value("Shell Settings", "show_desk_link") is None:
        s.show_desk_link = 1
        changed = True
    if changed:
        s.save(ignore_permissions=True)
