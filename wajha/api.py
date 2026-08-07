"""Wajha public API.

Security model: the client never names a DocType, a field, or a filter operator.
It names a *module key*; the server loads that module's saved configuration and
builds the query from it. Frappe's own permission layer then applies on top via
frappe.get_list, so a user can never see rows or fields their roles forbid.
"""

import json

import frappe
from frappe.utils import cint

CONFIG_CACHE_KEY = "wajha_config"

TOKEN_FIELDS = [
    "primary", "primary_dark", "accent", "sidebar_bg", "sidebar_ink",
    "sidebar_active_bg", "sidebar_active_ink", "page_bg", "surface_bg",
    "ink", "muted_ink", "border", "danger", "warning", "success", "info",
    "font_family", "font_css_url", "base_font_size", "radius", "card_shadow",
    "sidebar_width",
]

MAX_PAGE_LENGTH = 200


def has_app_permission():
    return bool(frappe.session.user and frappe.session.user != "Guest")


# --------------------------------------------------------------------------- config
def _settings():
    return frappe.get_cached_doc("Shell Settings")


def _theme_tokens(theme_name):
    if not theme_name or not frappe.db.exists("Shell Theme", theme_name):
        return {}
    theme = frappe.get_cached_doc("Shell Theme", theme_name)
    return {f: theme.get(f) for f in TOKEN_FIELDS if theme.get(f)}


@frappe.whitelist()
def get_config():
    """Branding + theme tokens + the modules this user may actually see."""
    s = _settings()
    if not s.enabled:
        return {"enabled": False}

    modules = []
    for m in frappe.get_all(
        "Shell Module",
        filters={"enabled": 1},
        fields=["name", "module_key", "module_label", "module_label_en", "icon",
                "group", "sequence", "view_type", "ref_doctype", "route",
                "show_map"],
        order_by="sequence asc, module_label asc",
    ):
        # A List module is only offered if the user can read its DocType.
        if m.view_type == "List":
            if not m.ref_doctype or not frappe.has_permission(m.ref_doctype, "read"):
                continue
            m["can_create"] = bool(frappe.has_permission(m.ref_doctype, "create"))
        modules.append(m)

    return {
        "enabled": True,
        "brand": {
            "title": s.brand_title,
            "title_en": s.brand_title_en,
            "subtitle": s.brand_subtitle,
            "logo": s.logo,
            "footer_note": s.footer_note,
        },
        "layout": {
            "default_module": s.default_module,
            "mobile_breakpoint": cint(s.mobile_breakpoint) or 900,
            "show_clock": bool(s.show_clock),
            "show_user_chip": bool(s.show_user_chip),
            "hide_desk_sidebar": bool(s.hide_desk_sidebar),
            "apply_font_globally": bool(s.apply_font_globally),
            "apply_theme_globally": bool(s.apply_theme_globally),
        },
        "tokens": _theme_tokens(s.active_theme),
        "modules": modules,
        "user": {
            "name": frappe.session.user,
            "full_name": frappe.utils.get_fullname(frappe.session.user),
        },
    }


# --------------------------------------------------------------------------- module data
def _get_module(module_key):
    if not module_key or not frappe.db.exists("Shell Module", module_key):
        frappe.throw("وحدة غير معروفة", frappe.DoesNotExistError)
    m = frappe.get_cached_doc("Shell Module", module_key)
    if not m.enabled:
        frappe.throw("الوحدة غير مفعّلة")
    if m.view_type != "List":
        frappe.throw("هذه الوحدة ليست من نوع قائمة")
    frappe.has_permission(m.ref_doctype, "read", throw=True)
    return m


def _allowed_fields(module):
    """Configured fields only, and only those that really exist on the DocType."""
    meta = frappe.get_meta(module.ref_doctype)
    real = {df.fieldname for df in meta.fields}
    real.update(["name", "modified", "creation", "owner"])
    out = []
    for c in module.columns:
        if c.fieldname in real and c.fieldname not in out:
            out.append(c.fieldname)
    for extra in (module.map_lat_field, module.map_lon_field,
                  module.map_label_field, module.map_color_field):
        if extra and extra in real and extra not in out:
            out.append(extra)
    if "name" not in out:
        out.insert(0, "name")
    return out, real


def _build_filters(module, raw, real_fields):
    """Only fieldnames declared in the module's filter table are honoured."""
    declared = {f.fieldname: f for f in module.filters}
    filters = []
    for fieldname, value in (raw or {}).items():
        conf = declared.get(fieldname)
        if not conf or fieldname not in real_fields:
            continue  # silently ignore anything not configured
        if value in (None, "", []):
            continue
        control = conf.control or "Text"
        if control == "Text":
            filters.append([fieldname, "like", f"%{value}%"])
        elif control in ("Select", "Link"):
            if isinstance(value, list):
                filters.append([fieldname, "in", value])
            else:
                filters.append([fieldname, "=", value])
        elif control == "Number Range":
            lo, hi = (value + [None, None])[:2] if isinstance(value, list) else (None, None)
            if lo not in (None, ""):
                filters.append([fieldname, ">=", lo])
            if hi not in (None, ""):
                filters.append([fieldname, "<=", hi])
        elif control == "Date Range":
            lo, hi = (value + [None, None])[:2] if isinstance(value, list) else (None, None)
            if lo:
                filters.append([fieldname, ">=", lo])
            if hi:
                filters.append([fieldname, "<=", hi])
    return filters


def _search_filters(module, search, real_fields):
    if not search:
        return None
    fields = [f.strip() for f in (module.search_fields or "").split(",") if f.strip()]
    fields = [f for f in fields if f in real_fields]
    if not fields:
        return None
    return [[f, "like", f"%{search}%"] for f in fields]


@frappe.whitelist()
def get_module_data(module_key, page=1, filters=None, search=None,
                    sort_field=None, sort_order=None):
    module = _get_module(module_key)
    fields, real = _allowed_fields(module)

    if isinstance(filters, str):
        filters = json.loads(filters or "{}")

    applied = _build_filters(module, filters, real)
    or_filters = _search_filters(module, search, real)

    page = max(cint(page), 1)
    page_length = min(cint(module.page_length) or 20, MAX_PAGE_LENGTH)

    sf = sort_field if sort_field in real else (module.sort_field or "modified")
    so = "asc" if (sort_order or module.sort_order or "DESC").upper() == "ASC" else "desc"
    order_by = f"`{sf}` {so}"

    kwargs = dict(doctype=module.ref_doctype, fields=fields, filters=applied,
                  order_by=order_by, limit_start=(page - 1) * page_length,
                  limit_page_length=page_length)
    if or_filters:
        kwargs["or_filters"] = or_filters

    rows = frappe.get_list(**kwargs)
    total = frappe.get_list(doctype=module.ref_doctype, filters=applied,
                            or_filters=or_filters, limit_page_length=0,
                            as_list=True, fields=["count(name) as c"])
    total = cint(total[0][0]) if total else 0

    return {
        "rows": rows,
        "page": page,
        "page_length": page_length,
        "total": total,
        "doctype": module.ref_doctype,
    }


@frappe.whitelist()
def get_module_meta(module_key):
    """Column/filter definitions + option lists for Select filters."""
    module = _get_module(module_key)
    meta = frappe.get_meta(module.ref_doctype)
    by_name = {df.fieldname: df for df in meta.fields}

    columns = [{
        "fieldname": c.fieldname,
        "label": c.label or (by_name[c.fieldname].label if c.fieldname in by_name else c.fieldname),
        "format": c.format or "Text",
        "width": c.width,
        "align": c.align or "start",
    } for c in module.columns]

    filters = []
    for f in module.filters:
        options = []
        if f.control == "Select":
            if f.options:
                options = [o for o in (f.options or "").split("\n") if o.strip()]
            elif f.fieldname in by_name:
                options = [o for o in (by_name[f.fieldname].options or "").split("\n") if o.strip()]
        filters.append({
            "fieldname": f.fieldname,
            "label": f.label or (by_name[f.fieldname].label if f.fieldname in by_name else f.fieldname),
            "control": f.control or "Text",
            "options": options,
            "link_doctype": f.options if f.control == "Link" else None,
        })

    return {
        "module_key": module.module_key,
        "label": module.module_label,
        "label_en": module.module_label_en,
        "doctype": module.ref_doctype,
        "columns": columns,
        "filters": filters,
        "can_create": bool(frappe.has_permission(module.ref_doctype, "create")),
        "map": {
            "enabled": bool(module.show_map),
            "lat": module.map_lat_field,
            "lon": module.map_lon_field,
            "label": module.map_label_field,
            "color": module.map_color_field,
            "center": [module.map_center_lat or 24.7136, module.map_center_lon or 46.6753],
            "zoom": cint(module.map_zoom) or 10,
        },
    }


@frappe.whitelist()
def get_map_points(module_key, filters=None, search=None, limit=2000):
    """All matching points for the map — bypasses pagination, keeps permissions."""
    module = _get_module(module_key)
    if not module.show_map or not (module.map_lat_field and module.map_lon_field):
        return []
    fields, real = _allowed_fields(module)
    if isinstance(filters, str):
        filters = json.loads(filters or "{}")
    applied = _build_filters(module, filters, real)
    applied.append([module.map_lat_field, "!=", 0])
    return frappe.get_list(
        module.ref_doctype, fields=fields, filters=applied,
        or_filters=_search_filters(module, search, real),
        limit_page_length=min(cint(limit), 5000),
    )


# --------------------------------------------------------------------------- helper
@frappe.whitelist()
def scaffold_module_from_doctype(doctype, module_key=None, label=None):
    """Create a Shell Module pre-filled from a DocType's list-view fields.

    Convenience for setting up a new project quickly; requires Shell Manager.
    """
    frappe.only_for(["Shell Manager", "System Manager"])
    meta = frappe.get_meta(doctype)
    key = (module_key or frappe.scrub(doctype)).lower()
    if frappe.db.exists("Shell Module", key):
        frappe.throw(f"الوحدة {key} موجودة مسبقًا")

    doc = frappe.new_doc("Shell Module")
    doc.module_key = key
    doc.module_label = label or meta.get("label") or doctype
    doc.view_type = "List"
    doc.ref_doctype = doctype
    doc.sequence = 10

    listed = [df for df in meta.fields if df.in_list_view and df.fieldtype not in
              ("Section Break", "Column Break", "Table", "HTML")]
    for df in (listed or meta.fields[:5]):
        doc.append("columns", {"fieldname": df.fieldname, "label": df.label,
                               "format": _fmt_for(df.fieldtype)})
    for df in meta.fields:
        if df.in_standard_filter:
            doc.append("filters", {
                "fieldname": df.fieldname, "label": df.label,
                "control": "Select" if df.fieldtype == "Select"
                else ("Link" if df.fieldtype == "Link" else "Text"),
                "options": df.options if df.fieldtype in ("Select", "Link") else None,
            })
    doc.search_fields = ",".join(
        [df.fieldname for df in meta.fields
         if df.fieldtype in ("Data", "Small Text") and df.in_list_view][:3]) or "name"
    doc.insert()
    return doc.name


def _fmt_for(fieldtype):
    return {
        "Percent": "Percent", "Currency": "Currency", "Date": "Date",
        "Datetime": "Datetime", "Link": "Link", "Int": "Int",
        "Float": "Float", "Select": "Badge",
    }.get(fieldtype, "Text")
