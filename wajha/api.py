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

from wajha import icons, ordering

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

MAX_PAGE_LENGTH = 500  # ERPNext's own largest list page
KANBAN_MAX_ROWS = 1000  # rows a kanban board groups at most; beyond that, filter first
KANBAN_MAX_PER_COLUMN = 40  # cards shown per column before "+n more"

# Native ERPNext docstatus values, exposed to the client so it never has to
# guess badge text/colour on its own.
DOCSTATUS_LABELS = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


def desk_prefix():
    """Frappe 16 serves the Desk at /desk (and 301s /app there); 15 at /app."""
    try:
        return "/desk" if int(frappe.__version__.split(".")[0]) >= 16 else "/app"
    except (ValueError, AttributeError):
        return "/app"


def has_app_permission():
    return bool(frappe.session.user and frappe.session.user != "Guest")


# --------------------------------------------------------------------------- config
def _settings():
    return frappe.get_cached_doc("Shell Settings")


def module_label(m):
    """The label this user should read for a module.

    The apps pack stores the DocType's own English label, so ``frappe._``
    can give each user their own language at request time — the same rule
    the group name follows. A label an administrator typed differs from the
    English one and is returned exactly as typed.

    Before 0.22 the pack stored the label already translated into the site
    language, which froze it: a site that gained an Arabic catalogue later
    kept reading English in the sidebar while the Home tiles, translated
    live, were Arabic.
    """
    label = m.get("module_label") or ""
    if label and label == (m.get("module_label_en") or ""):
        return frappe._(label)
    return label


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
                "show_map", "scope", "show_in_mobile_bar", "auto_generated"],
        order_by="sequence asc, module_label asc",
    ):
        # A List module is only offered if the user can read its DocType.
        if m.view_type == "List":
            if not m.ref_doctype or not frappe.has_permission(m.ref_doctype, "read"):
                continue
            m["can_create"] = bool(frappe.has_permission(m.ref_doctype, "create"))
        # Group names and pack-seeded labels are stored as their source text;
        # frappe._ gives each user their own where a translation exists.
        m["group_label"] = frappe._(m.group) if m.group else ""
        # Where the group sits in the business order (see wajha.ordering):
        # the sidebar sorts pack-seeded groups by this, not by the alphabet.
        m["group_rank"] = ordering.rank(m.group) if m.group else 0
        # A pack-seeded link to a workspace takes the workspace's place too,
        # so an "Apps" group of links reads Selling, Buying, Stock, …
        m["module_rank"] = ordering.rank(m.module_label_en) if m.auto_generated else 0
        m["module_label"] = module_label(m)
        modules.append(icons.attach(m))

    home = None
    landing = (s.get("landing") if s.meta.has_field("landing") else None) or "Home"
    if landing == "Home":
        try:
            from wajha import discovery

            home = {"tiles": discovery.tiles() if discovery.enabled() else []}
        except Exception:
            frappe.log_error("wajha: home tiles failed")
            home = {"tiles": []}

    return {
        "enabled": True,
        "home": home,
        "brand": {
            "title": s.brand_title,
            "title_en": s.brand_title_en,
            "subtitle": s.brand_subtitle,
            "logo": s.logo,
            "footer_note": s.footer_note,
        },
        "layout": {
            "default_module": s.default_module,
            "landing": landing,
            "auto_modules": bool(s.auto_modules) if s.meta.has_field("auto_modules") else True,
            "mobile_breakpoint": cint(s.mobile_breakpoint) or 900,
            "show_clock": bool(s.show_clock),
            "show_user_chip": bool(s.show_user_chip),
            # Default on; the language_switch_default patch writes the 1 that
            # a Single never receives for a field added after its creation.
            "show_language_switch": bool(s.show_language_switch),
            # Absent field (site not yet migrated to 0.9) counts as on: the exit
            # to the rest of the Desk must never disappear by accident.
            "show_desk_link": bool(s.show_desk_link) if s.meta.has_field("show_desk_link") else True,
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


@frappe.whitelist()
def set_language(lang):
    """Switch the signed-in user's language; the shell reloads afterwards.

    Writes User.language the way the user's own settings page would, then
    clears that user's caches: Frappe keeps the resolved language and the
    whole boot payload (with the translated `__messages` and the shell
    config) per user, and both would otherwise serve the old language
    until they expired."""
    lang = (lang or "").strip()
    if not lang or not frappe.db.exists("Language", lang):
        frappe.throw(frappe._("Unknown language: {0}").format(lang))
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
    frappe.db.set_value("User", user, "language", lang, update_modified=False)
    frappe.clear_cache(user=user)
    return lang


@frappe.whitelist(allow_guest=True)
def manifest():
    """A web-app manifest built from Shell Settings, so "Add to Home Screen"
    installs the client's system — its name, its logo, its colours — rather
    than a generic Frappe icon. Served raw (not wrapped in {"message": …})
    because the browser parses the body as the manifest itself. Guest-readable
    on purpose: browsers fetch manifests without credentials, and nothing in
    it is secret — the same values are on the login page."""
    s = _settings()
    t = _theme_tokens(s.active_theme) if s.enabled else {}
    manifest_icons = []
    if s.logo:
        manifest_icons.append({"src": s.logo, "sizes": "any", "purpose": "any"})
    body = {
        "name": s.brand_title or "Wajha",
        "short_name": (s.brand_title_en or s.brand_title or "Wajha")[:12],
        "description": s.brand_subtitle or "",
        "start_url": f"{desk_prefix()}/wajha",
        "scope": f"{desk_prefix()}/",
        "display": "standalone",
        "orientation": "portrait",
        "dir": "rtl",
        "lang": "ar",
        "theme_color": t.get("primary") or "#013D28",
        "background_color": t.get("page_bg") or "#F2F3F1",
        "manifest_icons": manifest_icons,
    }
    frappe.local.response.update({
        "type": "download",
        "filename": "manifest.webmanifest",
        "filecontent": json.dumps(body, ensure_ascii=False),
        "content_type": "application/manifest+json",
        "display_content_as": "inline",
    })


# --------------------------------------------------------------------------- module data
def _get_module(module_key):
    from wajha import discovery

    if discovery.is_virtual(module_key):
        # A discovered DocType: an unsaved module built from its list view.
        # Permission is checked below exactly as for a saved module.
        if not discovery.enabled():
            frappe.throw(frappe._("Automatic discovery is off"), frappe.DoesNotExistError)
        m = discovery.virtual_module(module_key)
        if not m:
            frappe.throw(frappe._("Unknown module"), frappe.DoesNotExistError)
        frappe.has_permission(m.ref_doctype, "read", throw=True)
        return m
    if not module_key or not frappe.db.exists("Shell Module", module_key):
        frappe.throw(frappe._("Unknown module"), frappe.DoesNotExistError)
    m = frappe.get_cached_doc("Shell Module", module_key)
    if not m.enabled:
        frappe.throw(frappe._("This module is disabled"))
    if m.view_type != "List":
        frappe.throw(frappe._("This module is not a List module"))
    frappe.has_permission(m.ref_doctype, "read", throw=True)
    return m


# --------------------------------------------------------------------------- scope
# A "Mine" module narrows every query to the current user's own records, on
# the server, before the user's saved filters are even looked at. It is the
# difference between an HR admin browsing 700 employees and an employee
# opening "my leave" on a phone: the same DocType, the same permissions, but
# the second one must never be a list of everyone else. Frappe's role
# permissions still apply on top; this only ever removes rows.
SCOPES = ("All", "Mine (Owner)", "Mine (User Field)", "Mine (Employee Field)")

# Mirrors ERPNext's own convention for "the Employee behind this login".
EMPLOYEE_USER_FIELD = "user_id"


def _current_employee():
    """The Employee record linked to the session user, or None.

    Cached on the request: a Mine (Employee Field) module asks for it from the
    count query, the row query and the map query of the same request.
    """
    if not hasattr(frappe.local, "wajha_employee"):
        emp = None
        if frappe.db.exists("DocType", "Employee"):
            emp = frappe.db.get_value(
                "Employee", {EMPLOYEE_USER_FIELD: frappe.session.user, "status": "Active"}, "name"
            ) or frappe.db.get_value("Employee", {EMPLOYEE_USER_FIELD: frappe.session.user}, "name")
        frappe.local.wajha_employee = emp
    return frappe.local.wajha_employee


def scope_filters(module):
    """The [field, "=", value] filters a Mine module adds to every query.

    A user with no Employee record on an Employee-scoped module gets an
    impossible filter rather than an unscoped one: seeing nothing is the safe
    failure, seeing everyone is the dangerous one.
    """
    scope = getattr(module, "scope", None) or "All"
    if scope == "All":
        return []
    if scope == "Mine (Owner)":
        return [["owner", "=", frappe.session.user]]
    field = (module.scope_field or "").strip()
    if not field:
        return [["name", "=", "__wajha_unscoped__"]]
    if scope == "Mine (User Field)":
        return [[field, "=", frappe.session.user]]
    emp = _current_employee()
    return [[field, "=", emp or "__wajha_no_employee__"]]


def scope_defaults(module):
    """Values a new record should start with so it lands inside the scope."""
    scope = getattr(module, "scope", None) or "All"
    field = (module.scope_field or "").strip()
    if scope == "Mine (User Field)" and field:
        return {field: frappe.session.user}
    if scope == "Mine (Employee Field)" and field:
        emp = _current_employee()
        return {field: emp} if emp else {}
    return {}


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

    # Whatever the card and kanban views draw has to come back in every row.
    for f in _card_config(module, meta, by_name, out, status_field)["fields"]:
        if f in real and f not in out:
            out.append(f)

    if "name" not in out:
        out.insert(0, "name")
    return out, real, status_field


# What a card shows for DocTypes whose fields we know, used only for the
# parts an administrator left blank and only when the field exists. Employee
# is the one people compare with an HR app: photo, name, job title, contact
# lines, department and employment type as badges, a board by status.
CARD_PRESETS = {
    "Employee": {
        "subtitle": "designation",
        "meta": ["company_email", "cell_number"],
        "badges": ["department", "employment_type"],
        "kanban": "status",
    },
    "Customer": {"subtitle": "customer_group", "meta": ["email_id", "mobile_no"], "badges": ["territory", "customer_type"]},
    "Supplier": {"subtitle": "supplier_group", "meta": ["email_id", "mobile_no"], "badges": ["country", "supplier_type"]},
    "Lead": {"subtitle": "company_name", "meta": ["email_id", "mobile_no"], "badges": ["source"], "kanban": "status"},
    "Opportunity": {"subtitle": "party_name", "meta": ["contact_email", "contact_mobile"], "badges": ["opportunity_type"], "kanban": "status"},
    "Job Applicant": {"subtitle": "job_title", "meta": ["email_id", "phone_number"], "badges": ["source"], "kanban": "status"},
    "Task": {"subtitle": "project", "meta": ["exp_end_date"], "badges": ["priority"], "kanban": "status"},
    "Issue": {"subtitle": "customer", "meta": ["raised_by"], "badges": ["priority", "issue_type"], "kanban": "status"},
    "Project": {"subtitle": "customer", "meta": ["expected_end_date"], "badges": ["priority"], "kanban": "status"},
}


def _card_config(module, meta, by_name, columns, status_field):
    """What the Cards and Kanban views draw for a module, resolved from the
    module's own settings first and the DocType's shape second.

    An administrator may name each part on the Shell Module; anything left
    blank is derived: the DocType's image field, its title field, then the
    ordered columns minus the status. Everything is checked against the real
    fields, so a typo or a field renamed upstream degrades to "not drawn"
    rather than to a broken list."""
    real = set(by_name.keys()) | {"name", "modified", "creation", "owner"}
    if meta.is_submittable:
        real.add("docstatus")

    def ok(f):
        if not f or f not in real:
            return False
        df = by_name.get(f)
        return not (df and df.fieldtype in ("Table", "Table MultiSelect"))

    def setting(name):
        return (getattr(module, name, None) or "").strip()

    def label_of(f):
        df = by_name.get(f)
        return frappe._(df.label) if df and df.label else f

    preset = CARD_PRESETS.get(meta.name, {})
    plain = [c for c in columns if c != status_field and c != "name"]
    image = setting("card_image_field") or (meta.image_field or "") or next(
        (df.fieldname for df in meta.fields if df.fieldtype == "Attach Image"), "")
    title = setting("card_title_field") or (meta.title_field or "") or (plain[0] if plain else "name")
    if title != "name" and not ok(title):
        title = plain[0] if plain else "name"
    rest = [c for c in plain if c != title]
    subtitle = setting("card_subtitle_field") or (preset.get("subtitle") if ok(preset.get("subtitle")) else "") \
        or (rest[0] if rest else "")
    rest = [c for c in rest if c != subtitle]
    meta_fields = _split_fieldnames(setting("card_meta_fields")) \
        or [f for f in preset.get("meta", []) if ok(f)] or rest[:2]
    badge_fields = _split_fieldnames(setting("card_badge_fields")) or [f for f in preset.get("badges", []) if ok(f)]

    def kind_of(f):
        df = by_name.get(f)
        opts = (df.options or "") if df else ""
        if df and df.fieldtype == "Data" and opts in ("Email", "Phone"):
            return opts.lower()
        lf = f.lower()
        if "email" in lf:
            return "email"
        if any(h in lf for h in ("mobile", "phone", "cell", "tel")):
            return "phone"
        return "text"

    def is_select(f):
        df = by_name.get(f)
        return bool(df and df.fieldtype == "Select" and (df.options or "").strip())

    kanban = setting("kanban_field")
    if not kanban and status_field and status_field != "docstatus" and is_select(status_field):
        kanban = status_field
    if not kanban and is_select(preset.get("kanban", "")):
        kanban = preset["kanban"]
    if not kanban and is_select("status"):
        kanban = "status"
    if not kanban:
        kanban = next((c for c in columns if is_select(c)), "")
    if not kanban and status_field == "docstatus":
        kanban = "docstatus"
    kb = None
    if kanban == "docstatus" and meta.is_submittable:
        kb = {"field": "docstatus", "label": frappe._("Status"),
              "options": [str(k) for k in DOCSTATUS_LABELS], "docstatus": True}
    elif ok(kanban):
        df = by_name[kanban]
        options = [o for o in (df.options or "").split("\n") if o.strip()] if df.fieldtype == "Select" else None
        kb = {"field": kanban, "label": label_of(kanban), "options": options, "docstatus": False}

    fields = [f for f in [image, title, subtitle] + list(meta_fields) + list(badge_fields) + [kb["field"] if kb else ""] if f]
    return {
        "image": image if ok(image) else "",
        "title": title,
        "subtitle": [subtitle] if ok(subtitle) else [],
        "meta": [{"fieldname": f, "label": label_of(f), "kind": kind_of(f),
                  "format": _fmt_for(by_name[f].fieldtype) if f in by_name else "Text"}
                 for f in meta_fields if ok(f)],
        "badges": [{"fieldname": f, "label": label_of(f)} for f in badge_fields if ok(f)],
        "kanban": kb,
        "fields": [f for f in fields if f in real],
    }


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
        elif control == "Select":
            if isinstance(value, list):
                filters.append([fieldname, "in", value])
            else:
                filters.append([fieldname, "=", value])
        elif control == "Link":
            # A typed Link filter matches by "contains", not the exact name:
            # the shell applies filters as you type, and an exact match meant
            # the list emptied on every keystroke until the full name was in.
            # A list (from a multi-value client) still means an exact set.
            if isinstance(value, list):
                filters.append([fieldname, "in", value])
            else:
                filters.append([fieldname, "like", f"%{value}%"])
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
                    sort_field=None, sort_order=None, page_length=None, status_value=None):
    module = _get_module(module_key)
    fields, real, status_field = _allowed_fields(module)

    if isinstance(filters, str):
        filters = json.loads(filters or "{}")

    applied = scope_filters(module) + _build_filters(module, filters, real)
    # A tapped status chip on the dashboard: only the module's own status
    # field, never a client-named one.
    if status_value not in (None, "") and status_field:
        applied.append([status_field, "=", status_value])
    or_filters = _search_filters(module, search, real)

    page = max(cint(page), 1)
    # The client may ask for more rows per page (the shell offers 20/100/500,
    # ERPNext's sizes); the module's own setting is the default and MAX_PAGE_LENGTH the
    # ceiling either way, so a hand-edited request cannot pull the whole table.
    page_length = min(cint(page_length) or cint(module.page_length) or 20, MAX_PAGE_LENGTH)
    page_length = max(page_length, 1)

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


NUMERIC_FIELDTYPES = ("Currency", "Int", "Float", "Percent")
REPORT_GROUP_FIELDTYPES = ("Select", "Link", "Data", "Check", "Autocomplete")
REPORT_MAX_GROUPS = 60


@frappe.whitelist()
def get_module_report(module_key, group_by=None, filters=None, search=None, status_value=None):
    """The list summarised: one row per value of a field, with the count and
    the sums of the module's numeric columns. Same scope, filters and search
    as the list; grouped in SQL so a large table is one query."""
    module = _get_module(module_key)
    fields, real, status_field = _allowed_fields(module)
    meta = frappe.get_meta(module.ref_doctype)
    by_name = {df.fieldname: df for df in meta.fields}

    # Select and Link columns first (a department, a status), free text
    # last: grouping 900 employees by their name is 900 rows of one.
    choices = []
    for want in (("Select", "Link", "Autocomplete"), ("Check",), ("Data",)):
        for c in module.columns:
            df = by_name.get(c.fieldname)
            if df and df.fieldtype in want and c.fieldname not in choices:
                choices.append(c.fieldname)
    if status_field and status_field not in choices and (status_field == "docstatus" or status_field in by_name):
        choices.append(status_field)
    card = _card_config(module, meta, by_name, [c.fieldname for c in module.columns], status_field)
    kb = card.get("kanban")
    if kb and kb["field"] not in choices:
        choices.append(kb["field"])
    if not choices:
        frappe.throw(frappe._("This module has no field to group by"))
    gb = group_by if group_by in choices else choices[0]

    def label_of(f):
        if f == "docstatus":
            return frappe._("Status")
        df = by_name.get(f)
        return frappe._(df.label) if df and df.label else f

    sums = [c.fieldname for c in module.columns
            if by_name.get(c.fieldname) and by_name[c.fieldname].fieldtype in NUMERIC_FIELDTYPES]

    if isinstance(filters, str):
        filters = json.loads(filters or "{}")
    applied = scope_filters(module) + _build_filters(module, filters, real)
    if status_value not in (None, "") and status_field:
        applied.append([status_field, "=", status_value])
    or_filters = _search_filters(module, search, real)

    kwargs = dict(doctype=module.ref_doctype,
                  fields=[gb, {"COUNT": "*"}] + [{"SUM": f} for f in sums],
                  filters=applied, group_by=gb, as_list=True, limit_page_length=0)
    if or_filters:
        kwargs["or_filters"] = or_filters
    raw = frappe.get_list(**kwargs)

    def value_label(v):
        if v is None or v == "":
            return frappe._("Not set")
        if gb == "docstatus":
            return frappe._(DOCSTATUS_LABELS.get(cint(v), str(v)))
        if by_name.get(gb) and by_name[gb].fieldtype == "Check":
            return frappe._("Yes") if cint(v) else frappe._("No")
        return frappe._(str(v)) if by_name.get(gb) and by_name[gb].fieldtype == "Select" else str(v)

    rows = [{"value": "" if r[0] is None else str(r[0]), "label": value_label(r[0]),
             "count": cint(r[1]), "sums": [flt(x) for x in r[2:]]} for r in raw]
    rows.sort(key=lambda r: -r["count"])
    if len(rows) > REPORT_MAX_GROUPS:
        rest = rows[REPORT_MAX_GROUPS:]
        rows = rows[:REPORT_MAX_GROUPS] + [{
            "value": None, "label": frappe._("Others"), "count": sum(r["count"] for r in rest),
            "sums": [sum(r["sums"][i] for r in rest) for i in range(len(sums))]}]
    return {
        "group_by": gb, "group_label": label_of(gb),
        "choices": [{"fieldname": f, "label": label_of(f)} for f in choices],
        "sum_fields": [{"fieldname": f, "label": label_of(f), "format": _fmt_for(by_name[f].fieldtype)} for f in sums],
        "rows": rows,
        "total": sum(r["count"] for r in rows),
        "sum_totals": [sum(r["sums"][i] for r in rows) for i in range(len(sums))],
    }


@frappe.whitelist()
def get_module_kanban(module_key, filters=None, search=None, status_value=None):
    """The module's rows grouped by its kanban field: one column per value.

    Same permissions, scope, filters and search as the list; the grouping
    happens here so a board of a few hundred cards is one round trip. A
    Select field keeps its options' order (empty columns included, the way a
    pipeline board reads); anything else is ordered by size."""
    module = _get_module(module_key)
    fields, real, status_field = _allowed_fields(module)
    meta = frappe.get_meta(module.ref_doctype)
    by_name = {df.fieldname: df for df in meta.fields}
    card = _card_config(module, meta, by_name, [c.fieldname for c in module.columns], status_field)
    kb = card.get("kanban")
    if not kb:
        frappe.throw(frappe._("This module has no Kanban field"))

    if isinstance(filters, str):
        filters = json.loads(filters or "{}")
    applied = scope_filters(module) + _build_filters(module, filters, real)
    if status_value not in (None, "") and status_field:
        applied.append([status_field, "=", status_value])
    or_filters = _search_filters(module, search, real)

    sf = module.sort_field if module.sort_field in real else "modified"
    kwargs = dict(doctype=module.ref_doctype, fields=fields, filters=applied,
                  order_by=f"{sf} desc", limit_page_length=KANBAN_MAX_ROWS)
    if or_filters:
        kwargs["or_filters"] = or_filters
    rows = frappe.get_list(**kwargs)

    field = kb["field"]
    groups = {}
    for o in kb.get("options") or []:
        groups[o] = []
    for r in rows:
        v = r.get(field)
        groups.setdefault("" if v is None else str(v), []).append(r)

    def label(v):
        if not v:
            return frappe._("Not set")
        if kb.get("docstatus") and v.isdigit():
            return frappe._(DOCSTATUS_LABELS[int(v)])
        return frappe._(v)

    columns = [{"value": v, "label": label(v), "count": len(rs), "rows": rs[:KANBAN_MAX_PER_COLUMN]}
               for v, rs in groups.items()]
    if not kb.get("options"):
        columns.sort(key=lambda c: -c["count"])
    return {"field": field, "label": kb["label"], "columns": columns,
            "total": len(rows), "truncated": len(rows) >= KANBAN_MAX_ROWS}


def _module_actions(module):
    from wajha.records import module_actions

    try:
        return module_actions(module)
    except Exception:
        frappe.log_error("wajha: module actions failed")
        return []


@frappe.whitelist()
def get_module_meta(module_key):
    """Column/filter definitions + option lists for Select filters."""
    module = _get_module(module_key)
    meta = frappe.get_meta(module.ref_doctype)
    by_name = {df.fieldname: df for df in meta.fields}
    _fields, _real, status_field = _allowed_fields(module)

    # Column and filter labels are stored as the DocType's own English label
    # (or as an administrator typed them); frappe._ gives each reader their
    # language and lets a Translation record reach the list header, exactly
    # as it already reaches the record card.
    columns = [{
        "fieldname": c.fieldname,
        "label": frappe._(c.label or (by_name[c.fieldname].label if c.fieldname in by_name else c.fieldname)),
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
            "label": frappe._(f.label or (by_name[f.fieldname].label if f.fieldname in by_name else f.fieldname)),
            "control": f.control or "Text",
            "options": options,
            "link_doctype": f.options if f.control == "Link" else None,
        })

    return {
        "module_key": module.module_key,
        "label": module_label(module),
        "label_en": module.module_label_en,
        "virtual": bool(getattr(module, "name", "") and str(module.name).startswith("~")),
        "doctype": module.ref_doctype,
        "columns": columns,
        "filters": filters,
        "can_create": bool(frappe.has_permission(module.ref_doctype, "create")),
        # A Mine module's New starts inside the scope (the employee's own
        # leave, not a blank form asking which employee).
        "new_defaults": scope_defaults(module),
        "scope": getattr(module, "scope", None) or "All",
        # The in-shell New form is the default way to create; Frappe's form
        # stays reachable from it. Module-level Create actions (check in /
        # check out) sit above the list.
        "has_form": bool(frappe.has_permission(module.ref_doctype, "create")),
        "module_actions": _module_actions(module),
        # The card (phone rows, the Cards grid, Kanban tiles): image, title,
        # subtitle, extra lines and badges, from the module's own settings or
        # derived from the DocType, so nobody maintains a second field list.
        "card": _card_config(module, meta, by_name, [c["fieldname"] for c in columns], status_field),
        "views": {"default": (getattr(module, "default_view", None) or "Table")},
        "status_field": status_field,
        "show_dashboard": bool(cint(getattr(module, "show_dashboard", 1))),
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
def get_group(group_key):
    """One Home tile opened: the workspace's DocTypes this user may read,
    in the workspace's own card sections, or a folder's child tiles."""
    from wajha import discovery

    if not discovery.enabled():
        frappe.throw(frappe._("Automatic discovery is off"), frappe.DoesNotExistError)
    return discovery.group(group_key)


@frappe.whitelist()
def get_map_points(module_key, filters=None, search=None, limit=2000):
    """All matching points for the map — bypasses pagination, keeps permissions."""
    module = _get_module(module_key)
    if not module.show_map or not (module.map_lat_field and module.map_lon_field):
        return []
    fields, real, _status_field = _allowed_fields(module)
    if isinstance(filters, str):
        filters = json.loads(filters or "{}")
    applied = scope_filters(module) + _build_filters(module, filters, real)
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
    key = (module_key or frappe.scrub(doctype)).lower()
    if frappe.db.exists("Shell Module", key):
        frappe.throw(frappe._("Module {0} already exists").format(key))
    doc = build_module_doc(doctype, key, label, field_include, field_exclude)
    doc.insert()
    return doc.name


def build_module_doc(doctype, module_key, label=None, field_include=None, field_exclude=None):
    """An unsaved Shell Module for a DocType: columns from its list view,
    filters from its standard filters (or sensible fallbacks), search fields,
    map fields when it carries coordinates. Shared by the scaffold endpoint
    and the packs that seed self-service modules (wajha/packs)."""
    meta = frappe.get_meta(doctype)
    include = _split_fieldnames(field_include)
    exclude = set(_split_fieldnames(field_exclude))

    doc = frappe.new_doc("Shell Module")
    doc.module_key = module_key
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
    return doc


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

    The map view needs two separate numeric fields, so a conventional lat/lng
    field pair (checked against _LATLNG_NAME_PAIRS) is what we look for. A
    combined `Geolocation` field cannot drive the view on its own and is
    therefore ignored — it must not suppress a usable pair sitting alongside
    it, which is exactly the shape ERPNext's own `Location` DocType has
    (`latitude`/`longitude` Floats plus a `location` Geolocation field).
    Does nothing if no usable pair is found, or if either half of the pair was
    explicitly excluded via field_exclude.
    """
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
