"""Module dashboards: a strip of cards above every list.

Three sources, in this order, all inside the module's scope and the user's
permissions:

1. Generic cards from the module's own data — a count per status (tap one
   to filter the list) and totals of the module's numeric columns. Every
   module gets these with no configuration.
2. App cards from a provider registered for the DocType (wajha/packs/*):
   leave balance, upcoming holidays, last check-in, last salary slip…
3. Frappe Number Cards pinned to the module, evaluated through Frappe's
   own Number Card code so its permission and filters apply unchanged.

A card is a small dict the client paints: kind (stat | chips | list |
progress), label, value, hint, and for chips/list/progress the items.
One failing provider is logged and skipped; it never takes the strip down.
"""

import frappe
from frappe.utils import cint, flt


from wajha import icons
from wajha.api import _allowed_fields, _get_module, _settings, module_label, scope_filters

MAX_STATUS_CHIPS = 8
MAX_SUM_COLUMNS = 3

# doctype -> [callable(module, ctx) -> list[card]]
PROVIDERS = {}


def register(doctype, fn):
    PROVIDERS.setdefault(doctype, []).append(fn)


def stat(label, value, hint=None, icon=None, tone=None, filter=None):
    return {"kind": "stat", "label": label, "value": value, "hint": hint, "icon": icon, "tone": tone, "filter": filter}


# --------------------------------------------------------------------------- generic
def _status_chips(module, meta, status_field):
    if not status_field:
        return None
    rows = frappe.get_list(
        module.ref_doctype, fields=[status_field, {"COUNT": "*"}],
        filters=scope_filters(module), group_by=status_field, as_list=True,
        order_by=None, limit_page_length=MAX_STATUS_CHIPS,
    )
    items = []
    for value, count in rows:
        if value in (None, ""):
            continue
        label = frappe._({0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(value, str(value))) \
            if status_field == "docstatus" else frappe._(str(value))
        items.append({"value": value, "label": label, "count": cint(count)})
    if not items:
        return None
    items.sort(key=lambda x: -x["count"])
    return {"kind": "chips", "label": frappe._("By status"), "field": status_field, "items": items}


def _sum_cards(module, meta):
    out = []
    by_name = {df.fieldname: df for df in meta.fields}
    for c in module.columns:
        df = by_name.get(c.fieldname)
        if not df or df.fieldtype not in ("Currency", "Float", "Int") or df.fieldname in ("idx", "docstatus"):
            continue
        rows = frappe.get_list(module.ref_doctype, fields=[{"SUM": df.fieldname}],
                               filters=scope_filters(module), as_list=True, limit_page_length=1)
        total = flt(rows[0][0]) if rows and rows[0] else 0
        value = frappe.format_value(total, df) if df.fieldtype == "Currency" else \
            (frappe.format_value(total, {"fieldtype": "Float", "precision": 2}) if df.fieldtype == "Float" else str(cint(total)))
        out.append(stat(frappe._(c.label or df.label), value, hint=frappe._("Total"), icon="Σ"))
        if len(out) >= MAX_SUM_COLUMNS:
            break
    return out


def _count_card(module):
    rows = frappe.get_list(module.ref_doctype, fields=[{"COUNT": "*"}], filters=scope_filters(module),
                           as_list=True, limit_page_length=1)
    total = cint(rows[0][0]) if rows else 0
    return stat(frappe._("Records"), str(total), icon="fa-hashtag")


# --------------------------------------------------------------------------- number cards
def _number_cards(module):
    out = []
    names = [r.number_card for r in (module.get("number_cards") or []) if r.number_card]
    if not names:
        return out
    from frappe.desk.doctype.number_card.number_card import get_result

    for name in names:
        try:
            card = frappe.get_doc("Number Card", name)
            if not card.has_permission("read"):
                continue
            if (card.get("type") or "Document Type") != "Document Type":
                continue
            value = get_result(card, card.filters_json)
            out.append(stat(frappe._(card.label or name), frappe.format_value(flt(value), {"fieldtype": "Float", "precision": 0}), icon="fa-chart-simple"))
        except Exception:
            frappe.log_error(title=f"wajha: number card {name} failed")
    return out


# --------------------------------------------------------------------------- endpoint
def _module_cards(module, generic="all"):
    """The cards for one module. ``generic="count"`` keeps only the record
    count from the generic set — the Home page wants a module's own cards
    (leave balance, last check-in) without a status strip per module."""
    meta = frappe.get_meta(module.ref_doctype)
    _fields, _real, status_field = _allowed_fields(module)
    cards = []

    steps = [lambda: [_count_card(module)]]
    if generic == "all":
        steps += [lambda: [c for c in [_status_chips(module, meta, status_field)] if c],
                  lambda: _sum_cards(module, meta)]
    for step in steps:
        try:
            cards.extend(step())
        except Exception:
            frappe.log_error(title=f"wajha: dashboard card failed for {module.name}")

    _load_packs()
    ctx = {"scope": scope_filters(module), "status_field": status_field}
    for fn in PROVIDERS.get(module.ref_doctype, []):
        try:
            cards.extend(fn(module, ctx) or [])
        except Exception:
            frappe.log_error(title=f"wajha: dashboard provider {fn.__name__} failed")

    try:
        cards.extend(_number_cards(module))
    except Exception:
        frappe.log_error(title=f"wajha: number cards failed for {module.name}")

    return [c for c in cards if c]


@frappe.whitelist()
def get_module_dashboard(module_key):
    module = _get_module(module_key)
    if not cint(getattr(module, "show_dashboard", 1)):
        return {"cards": []}
    return {"cards": _module_cards(module)}


# --------------------------------------------------------------------------- home dashboard
# Frappe's own Number Cards and Dashboard Charts, grouped by a Frappe
# Dashboard, mapped to a role in Shell Settings. The data definitions stay
# in Frappe where an administrator edits them; only the rendering is the
# shell's. Below that, every module flagged for the phone bar contributes
# its own cards, so an employee's Home carries leave balance, last check-in
# and last salary slip with no configuration.
INTERVAL_WORDS = {"Daily": "vs yesterday", "Weekly": "vs last week", "Monthly": "vs last month", "Yearly": "vs last year"}


def _dashboard_for(roles):
    """The first Shell Settings row whose role the user holds."""
    for row in _settings().get("dashboards") or []:
        if row.role in roles and row.dashboard and frappe.db.exists("Dashboard", row.dashboard):
            return row.dashboard
    return None


def _number_card_stat(card):
    from frappe.desk.doctype.number_card.number_card import get_percentage_difference, get_result

    filters = frappe.parse_json(card.filters_json) if card.filters_json else []
    value = get_result(card, list(filters or []))
    hint = None
    if card.get("show_percentage_stats"):
        try:
            diff = get_percentage_difference(card, list(filters or []), value)
            if diff is not None:
                hint = f"{'+' if diff > 0 else ''}{flt(diff):.0f}% {frappe._(INTERVAL_WORDS.get(card.stats_time_interval, 'vs last month'))}"
        except Exception:
            frappe.log_error(title=f"wajha: number card trend {card.name} failed")
    return stat(frappe._(card.label or card.name),
                frappe.format_value(flt(value), {"fieldtype": "Float", "precision": 0}),
                hint=hint, icon="fa-chart-simple")


def _frappe_dashboard(name):
    from frappe.desk.doctype.dashboard_chart.dashboard_chart import get as get_chart

    dash = frappe.get_doc("Dashboard", name)
    cards, charts = [], []
    for row in dash.get("cards") or []:
        try:
            card = frappe.get_doc("Number Card", row.card)
            # Frappe's own rule for who may see a card, then the data's own.
            if not card.has_permission("read"):
                continue
            if (card.get("type") or "Document Type") != "Document Type":
                continue  # Report and Custom cards need the Desk's own runners
            if not frappe.has_permission(card.document_type, "read"):
                continue
            cards.append(_number_card_stat(card))
        except Exception:
            frappe.log_error(title=f"wajha: number card {row.card} failed")
    for row in dash.get("charts") or []:
        try:
            chart = frappe.get_doc("Dashboard Chart", row.chart)
            if not chart.has_permission("read"):
                continue
            if chart.chart_type not in ("Count", "Sum", "Average", "Group By") or chart.type == "Heatmap":
                continue
            if chart.document_type and not frappe.has_permission(chart.document_type, "read"):
                continue
            data = get_chart(chart_name=chart.name)
            if not data or not data.get("labels"):
                continue
            charts.append({
                "kind": "chart", "name": chart.name, "label": frappe._(chart.chart_name or chart.name),
                "type": chart.type, "color": chart.color, "timeseries": cint(chart.timeseries),
                "width": row.width or "Half", "data": data,
            })
        except Exception:
            frappe.log_error(title=f"wajha: dashboard chart {row.chart} failed")
    return {"name": dash.name, "label": frappe._(dash.dashboard_name or dash.name), "cards": cards, "charts": charts}


@frappe.whitelist()
def get_home_dashboard():
    """What the Home page shows above Quick access: the Frappe Dashboard
    mapped to one of the user's roles (if any), then one card group per
    module flagged for the phone bar."""
    out = {"admin": None, "mine": []}
    name = _dashboard_for(set(frappe.get_roles()))
    if name:
        try:
            out["admin"] = _frappe_dashboard(name)
        except Exception:
            frappe.log_error(title=f"wajha: dashboard {name} failed")

    for m in frappe.get_all(
        "Shell Module",
        filters={"enabled": 1, "show_in_mobile_bar": 1, "view_type": "List"},
        fields=["name", "module_key", "module_label", "module_label_en", "ref_doctype", "icon", "sequence"],
        order_by="sequence asc, module_label asc",
    ):
        if not m.ref_doctype or not frappe.has_permission(m.ref_doctype, "read"):
            continue
        try:
            module = _get_module(m.module_key)
            if not cint(getattr(module, "show_dashboard", 1)):
                continue
            cards = _module_cards(module, generic="count")
        except Exception:
            frappe.log_error(title=f"wajha: home cards failed for {m.module_key}")
            continue
        if cards:
            out["mine"].append({
                "module_key": m.module_key, "label": module_label(m), "label_en": m.module_label_en,
                "icon": icons.normalize(m.icon, m.ref_doctype), "cards": cards,
            })
    return out


def _load_packs():
    """Importing a pack's cards module registers its providers."""
    import importlib

    if "hrms" in frappe.get_installed_apps():
        importlib.import_module("wajha.packs.hrms_cards")
