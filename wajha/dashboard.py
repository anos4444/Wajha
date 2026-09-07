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

from wajha.api import _allowed_fields, _get_module, scope_filters

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
    return stat(frappe._("Records"), str(total), icon="fa:hashtag")


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
            out.append(stat(frappe._(card.label or name), frappe.format_value(flt(value), {"fieldtype": "Float", "precision": 0}), icon="fa:chart-simple"))
        except Exception:
            frappe.log_error(title=f"wajha: number card {name} failed")
    return out


# --------------------------------------------------------------------------- endpoint
@frappe.whitelist()
def get_module_dashboard(module_key):
    module = _get_module(module_key)
    if not cint(getattr(module, "show_dashboard", 1)):
        return {"cards": []}
    meta = frappe.get_meta(module.ref_doctype)
    _fields, _real, status_field = _allowed_fields(module)
    cards = []

    for step in (lambda: [_count_card(module)],
                 lambda: [c for c in [_status_chips(module, meta, status_field)] if c],
                 lambda: _sum_cards(module, meta)):
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

    cards = [c for c in cards if c]
    return {"cards": cards, "icons": icons.table(c.get("icon") for c in cards)}


def _load_packs():
    """Importing a pack's cards module registers its providers."""
    import importlib

    if "hrms" in frappe.get_installed_apps():
        importlib.import_module("wajha.packs.hrms_cards")
