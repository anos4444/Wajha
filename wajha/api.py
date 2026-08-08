"""Wajha public API.

Security model: the client never names a DocType, a field, or a filter operator.
It names a *module key*; the server loads that module's saved configuration and
builds the query from it. Frappe's own permission layer then applies on top via
frappe.get_list, so a user can never see rows or fields their roles forbid.
"""

import hashlib
import json

import frappe
from frappe.utils import cint

CONFIG_CACHE_KEY = "wajha_config"
FIELDS_CACHE_PREFIX = "wajha_fields_"
FIELDS_CACHE_TTL = 300  # 5 minutes; cleared immediately on module save regardless
COUNT_CACHE_PREFIX = "wajha_count_"
COUNT_CACHE_TTL = 20  # seconds -- short enough that a new/edited doc shows up
                      # in the pager quickly, long enough to absorb a user
                      # clicking Next/Previous through the same filtered view
                      # without re-running the same COUNT(*) on every click

TOKEN_FIELDS = [
    "primary", "primary_dark", "accent", "sidebar_bg", "sidebar_ink",
    "sidebar_active_bg", "sidebar_active_ink", "page_bg", "surface_bg",
    "ink", "muted_ink", "border", "danger", "warning", "success", "info",
    "font_family", "font_css_url", "base_font_size", "radius", "card_shadow",
    "sidebar_width",
]

MAX_PAGE_LENGTH = 200

# Native ERPNext docstatus values, exposed to the client so it never has to
# guess badge text/colour on its own.
DOCSTATUS_LABELS = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


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


def _compute_allowed_fields(module):
    """Configured fields only, and only those that really exist on the DocType.

    Child-table fields (fieldtype "Table"/"Table MultiSelect") cannot be
    projected into a flat frappe.get_list() row, so they're dropped even if
    someone configured one by hand (e.g. via a hand-edited fixture) rather
    than through scaffold_module_from_doctype, which already filters them out.

    For submittable native ERPNext DocTypes (Sales Order, Purchase Invoice,
    Journal Entry, …) docstatus is always pulled in automatically — unless
    the module explicitly names a different status_field — so the client can
    render a Draft/Submitted/Cancelled badge without extra configuration.
    """
    meta = frappe.get_meta(module.ref_doctype)
    by_name = {df.fieldname: df for df in meta.fields}
    real = set(by_name.keys())
    real.update(["name", "modified", "creation", "owner"])
    if meta.is_submittable:
        real.add("docstatus")

    out = []
    for c in module.columns:
        df = by_name.get(c.fieldname)
        if c.fieldname not in real:
            continue
        if df and df.fieldtype in ("Table", "Table MultiSelect"):
            continue  # can't render a child table in a flat list cell
        if c.fieldname not in out:
            out.append(c.fieldname)

    for extra in (module.map_lat_field, module.map_lon_field,
                  module.map_label_field, module.map_color_field):
        if extra and extra in real and extra not in out:
            out.append(extra)

    status_field = (module.status_field or "").strip() or None
    if not status_field and meta.is_submittable:
        status_field = "docstatus"
    if status_field and status_field not in real:
        status_field = None  # configured field doesn't actually exist; drop it silently
    if status_field and status_field not in out:
        out.append(status_field)

    if "name" not in out:
        out.insert(0, "name")
    return out, real, status_field


def _allowed_fields(module):
    """Cached wrapper around _compute_allowed_fields.

    DocType shape rarely changes between requests, so this is safe to cache
    briefly; Shell Module's on_update/on_trash hooks clear it immediately on
    save, so admins editing columns/filters never see stale results.
    """
    cache_key = FIELDS_CACHE_PREFIX + module.name
    cached = frappe.cache().get_value(cache_key)
    if cached:
        fields, real, status_field = cached
        return fields, set(real), status_field
    fields, real, status_field = _compute_allowed_fields(module)
    frappe.cache().set_value(cache_key, (fields, list(real), status_field),
                              expires_in_sec=FIELDS_CACHE_TTL)
    return fields, real, status_field


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
        elif control == "MultiSelect":
            values = value if isinstance(value, list) else [value]
            values = [v for v in values if v not in (None, "")]
            if values:
                filters.append([fieldname, "in", values])
        elif control == "Number Range":
            lo, hi = (value + [None, None])[:2] if isinstance(value, list) else (None, None)
            if lo not in (None, ""):
                filters.append([fieldname, ">=", lo])
            if hi not in (None, ""):
                filters.append([fieldname, "<=", hi])
        elif control in ("Date Range", "Datetime Range"):
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


def _cached_count(module, applied, or_filters):
    """Total row count for the current filter/search combination.

    A pager click (Next/Previous, or re-sorting the same filtered view)
    re-sends the identical filters+search on every request, but a COUNT(*)
    over a large, mostly-unindexed WHERE clause can be as expensive as the
    row fetch itself -- on a 100k-row table in testing, an unindexed range
    filter's count query alone ran ~150-200ms. Short-TTL caching means that
    cost is paid once per filter combination per COUNT_CACHE_TTL window
    instead of on every single page turn. 20s means a newly created or
    edited document can take up to that long to move the "total" number in
    the pager -- an acceptable trade for how much repeat-paging this saves.
    """
    key = COUNT_CACHE_PREFIX + hashlib.md5(
        json.dumps([module.name, applied, or_filters], sort_keys=True, default=str).encode()
    ).hexdigest()
    cached = frappe.cache().get_value(key)
    if cached is not None:
        return cached

    # v16 forbids SQL functions as strings in SELECT; use the dict form.
    count_kwargs = dict(doctype=module.ref_doctype, filters=applied,
                        fields=[{"COUNT": "*"}], as_list=True,
                        limit_page_length=0)
    if or_filters:
        count_kwargs["or_filters"] = or_filters
    total = frappe.get_list(**count_kwargs)
    total = cint(total[0][0]) if total else 0
    frappe.cache().set_value(key, total, expires_in_sec=COUNT_CACHE_TTL)
    return total


@frappe.whitelist()
def get_module_data(module_key, page=1, filters=None, search=None,
                    sort_field=None, sort_order=None):
    module = _get_module(module_key)
    fields, real, _status_field = _allowed_fields(module)

    if isinstance(filters, str):
        filters = json.loads(filters or "{}")

    applied = _build_filters(module, filters, real)
    or_filters = _search_filters(module, search, real)

    page = max(cint(page), 1)
    page_length = min(cint(module.page_length) or 20, MAX_PAGE_LENGTH)

    sf = sort_field if sort_field in real else (module.sort_field or "modified")
    if sf not in real:
        sf = "modified"
    so = "asc" if (sort_order or module.sort_order or "DESC").upper() == "ASC" else "desc"
    # v16's query engine rejects backtick notation in order_by; the fieldname is
    # already validated against the DocType's real fields above.
    order_by = f"{sf} {so}"

    kwargs = dict(doctype=module.ref_doctype, fields=fields, filters=applied,
                  order_by=order_by, limit_start=(page - 1) * page_length,
                  limit_page_length=page_length)
    if or_filters:
        kwargs["or_filters"] = or_filters

    rows = frappe.get_list(**kwargs)

    total = _cached_count(module, applied, or_filters)

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
    _fields, _real, status_field = _allowed_fields(module)

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
        if f.control in ("Select", "MultiSelect"):
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
        "status_field": status_field,
        "docstatus_labels": DOCSTATUS_LABELS if status_field == "docstatus" else None,
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
    fields, real, _status_field = _allowed_fields(module)
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
# Common naming conventions for a lat/lng field pair when a DocType doesn't
# use Frappe's own combined `Geolocation` fieldtype. Checked in order; the
# first pair where BOTH fieldnames exist on the DocType wins.
_LATLNG_NAME_PAIRS = (
    ("latitude", "longitude"),
    ("lat", "lng"),
    ("lat", "lon"),
    ("gps_latitude", "gps_longitude"),
)

# Select fields tend to make good filters even when the DocType author never
# flagged them `in_standard_filter` -- but only below a cardinality where a
# dropdown is still usable. Above this, a Select filter becomes an unusable
# 200-option dropdown, so it's skipped instead of forced in.
_SELECT_FILTER_MAX_OPTIONS = 15


@frappe.whitelist()
def scaffold_module_from_doctype(doctype, module_key=None, label=None,
                                  field_include=None, field_exclude=None):
    """Create a Shell Module pre-filled from a DocType's list-view fields.

    Convenience for setting up a new project quickly; requires Shell Manager.

    field_include: optional list (or comma-separated string) of fieldnames.
        When given, ONLY these fields are considered for columns/filters,
        instead of whatever the DocType meta happens to flag as
        in_list_view/in_standard_filter. Useful when the native DocType's
        own list-view configuration doesn't match what should show in the
        Wajha shell (e.g. a heavily-customized ERPNext DocType).
    field_exclude: optional list (or comma-separated string) of fieldnames
        to drop even if they would otherwise be picked up automatically
        (from in_list_view / in_standard_filter / geolocation detection).
        Applied after field_include, so it can also be used to trim an
        explicit include list.
    """
    frappe.only_for(["Shell Manager", "System Manager"])
    meta = frappe.get_meta(doctype)
    key = (module_key or frappe.scrub(doctype)).lower()
    if frappe.db.exists("Shell Module", key):
        frappe.throw(f"الوحدة {key} موجودة مسبقًا")

    include = _split_fieldnames(field_include)
    exclude = set(_split_fieldnames(field_exclude))

    doc = frappe.new_doc("Shell Module")
    doc.module_key = key
    doc.module_label = label or meta.get("label") or doctype
    doc.view_type = "List"
    doc.ref_doctype = doctype
    doc.sequence = 10
    if meta.is_submittable:
        doc.status_field = "docstatus"

    fields_by_name = {df.fieldname: df for df in meta.fields}

    if include:
        # Explicit include list wins outright; preserve the caller's order.
        listed = [fields_by_name[fn] for fn in include if fn in fields_by_name]
    else:
        listed = [df for df in meta.fields if df.in_list_view and df.fieldtype not in
                  ("Section Break", "Column Break", "Table", "Table MultiSelect", "HTML")]
        listed = listed or meta.fields[:5]
    listed = [df for df in listed if df.fieldname not in exclude]
    for df in listed:
        doc.append("columns", {"fieldname": df.fieldname, "label": df.label,
                               "format": _fmt_for(df.fieldtype)})

    # Filters: start from whatever the DocType itself flags as a standard
    # filter (respecting include/exclude same as columns). If the DocType
    # doesn't define ANY standard filters -- common on custom DocTypes that
    # were never wired up for the native list view -- fall back to a
    # reasonable default: Select fields with a manageable option count, and
    # Date/Datetime fields as ranges, so a scaffolded module isn't left with
    # zero filters just because nobody configured them upstream.
    filter_fields = [df for df in meta.fields
                      if df.in_standard_filter and df.fieldname not in exclude
                      and (not include or df.fieldname in include)]
    if not filter_fields:
        for df in meta.fields:
            if include and df.fieldname not in include:
                continue
            if df.fieldname in exclude:
                continue
            if df.fieldtype == "Select" and df.options:
                if 0 < len(df.options.splitlines()) <= _SELECT_FILTER_MAX_OPTIONS:
                    filter_fields.append(df)
            elif df.fieldtype in ("Date", "Datetime") and df.fieldname != "creation":
                filter_fields.append(df)
    for df in filter_fields:
        doc.append("filters", {
            "fieldname": df.fieldname, "label": df.label,
            "control": _control_for(df.fieldtype),
            "options": df.options if df.fieldtype in ("Select", "Link") else None,
        })

    doc.search_fields = ",".join(
        [df.fieldname for df in meta.fields
         if df.fieldtype in ("Data", "Small Text") and df.in_list_view][:3]) or "name"

    _autodetect_map_fields(doc, meta, fields_by_name, exclude)

    doc.insert()
    return doc.name


def _split_fieldnames(value):
    """Accept a list, a comma-separated string, or None -- normalize to a list."""
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [v for v in value if v]


def _autodetect_map_fields(doc, meta, fields_by_name, exclude):
    """Pre-fill map_lat_field/map_lon_field and enable the map view when the
    DocType clearly carries coordinates, instead of leaving map setup as a
    mandatory manual step after every scaffold.

    Two shapes are recognized: Frappe's own combined `Geolocation` fieldtype
    (a single field holding GeoJSON), and a conventional separate lat/lng
    field pair (checked against _LATLNG_NAME_PAIRS). Geolocation wins if
    both are somehow present. Does nothing if neither shape is found, or if
    either field was explicitly excluded via field_exclude.
    """
    geo_field = next((df for df in meta.fields
                       if df.fieldtype == "Geolocation" and df.fieldname not in exclude), None)
    if geo_field:
        # Geolocation stores {lat, lng} as one JSON value; Wajha's map view
        # expects two separate numeric fields, so this is flagged for the
        # caller rather than silently mis-mapped. show_map is left off.
        return

    for lat_name, lng_name in _LATLNG_NAME_PAIRS:
        if lat_name in exclude or lng_name in exclude:
            continue
        lat_df = fields_by_name.get(lat_name)
        lng_df = fields_by_name.get(lng_name)
        if lat_df and lng_df and lat_df.fieldtype in ("Float", "Data") \
                and lng_df.fieldtype in ("Float", "Data"):
            doc.map_lat_field = lat_name
            doc.map_lon_field = lng_name
            doc.show_map = 1
            return


def _fmt_for(fieldtype):
    return {
        "Percent": "Percent", "Currency": "Currency", "Date": "Date",
        "Datetime": "Datetime", "Link": "Link", "Int": "Int",
        "Float": "Float", "Select": "Badge",
        "Check": "Checkbox",
        "Rating": "Rating",
        "Attach": "Attachment",
        "Attach Image": "Image",
        "Image": "Image",
        "Geolocation": "Geolocation",
        "MultiSelectPill": "MultiSelectBadge",
        "JSON": "JSON",
        "Duration": "Duration",
    }.get(fieldtype, "Text")


def _control_for(fieldtype):
    if fieldtype == "Select":
        return "Select"
    if fieldtype == "Link":
        return "Link"
    if fieldtype in ("Int", "Float", "Currency", "Percent"):
        return "Number Range"
    if fieldtype == "Date":
        return "Date Range"
    if fieldtype == "Datetime":
        return "Datetime Range"
    return "Text"
