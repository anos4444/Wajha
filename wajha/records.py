"""One record, inside the shell: the card a user opens from a list, and the
actions they can take on it without ever being handed to Frappe's form.

Same contract as wajha.api: the client names a module key and a record name,
never a DocType or a field. The server resolves the module, loads the record
through frappe.get_doc, and applies three layers of permission before a byte
leaves:

1. Frappe's own document permission (read / write / submit / cancel), via
   doc.check_permission — role permissions, user permissions, share rules.
2. The module's scope (wajha.api.scope_filters): a "Mine" module refuses a
   record that is not the user's own even when their roles could read it —
   an employee typing a colleague's leave id into the URL gets nothing.
3. Field-level (permlevel) access: only fields the user may read are
   serialised, only fields they may write can be set by an action.

Actions come from two places. Automatic ones are Frappe's own — the
workflow transitions the user is allowed to take (frappe.model.workflow),
or Submit / Cancel where there is no workflow — so an approval built in
Workflow works from the card with zero configuration. Configured ones live
in the module's Actions table: set a field, call a whitelisted method, or
jump to a route.
"""

import json

import frappe
from frappe.model.workflow import apply_workflow, get_transitions, get_workflow_name
from frappe.utils import cint, sanitize_html, strip_html

from wajha.api import _get_module, desk_prefix, scope_filters

# Layout-only fieldtypes: never carry a value.
LAYOUT_TYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Fold", "Heading"}
# Never shown on a card, whatever the permission says.
NEVER_SHOWN = {"Password", "Table MultiSelect", "Barcode", "Signature", "Geolocation"}
RICH_TYPES = {"Text Editor", "HTML Editor", "Markdown Editor"}
FILE_TYPES = {"Attach", "Attach Image", "Image"}
CODE_TYPES = {"Code", "JSON"}

MAX_TABLE_ROWS = 50
MAX_COMMENTS = 10
MAX_ATTACHMENTS = 20

DOCSTATUS_NAMES = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


# --------------------------------------------------------------------------- loading
def _load(module, name):
    """The record, or an error the client can show. Read + scope enforced."""
    doc = frappe.get_doc(module.ref_doctype, name)
    doc.check_permission("read")
    for field, _op, value in scope_filters(module):
        if (doc.get(field) or None) != value:
            # Same message as a genuinely missing record on purpose: a scoped
            # list must not confirm that someone else's record exists.
            frappe.throw("السجل غير موجود", frappe.DoesNotExistError)
    return doc


def _readable_permlevels(doc):
    try:
        return set(doc.get_permlevel_access("read"))
    except Exception:
        return {0}


def _writable_permlevels(doc):
    try:
        return set(doc.get_permlevel_access("write"))
    except Exception:
        return {0}


# --------------------------------------------------------------------------- serialising
def _format(df, value, doc):
    """One field as the client should paint it. Text is escaped client-side;
    only the rich types come back as (sanitised) HTML, flagged as such."""
    ft = df.fieldtype
    if ft == "Check":
        return {"kind": "check", "value": bool(cint(value))}
    if ft in RICH_TYPES:
        return {"kind": "html", "value": sanitize_html(str(value))}
    if ft in FILE_TYPES:
        return {"kind": "image" if ft in ("Attach Image", "Image") else "file", "value": str(value)}
    if ft in CODE_TYPES:
        return {"kind": "code", "value": str(value)}
    if ft == "Color":
        return {"kind": "color", "value": str(value)}
    if ft == "Link":
        return {"kind": "link", "value": str(value), "doctype": df.options}
    if ft == "Dynamic Link":
        return {"kind": "link", "value": str(value), "doctype": doc.get(df.options) if df.options else None}
    if ft in ("Rating",):
        return {"kind": "rating", "value": frappe.utils.flt(value)}
    try:
        text = frappe.format_value(value, df=df, doc=doc)
    except Exception:
        text = str(value)
    # format_value wraps some numeric types in markup; the card wants text.
    return {"kind": "text", "value": strip_html(str(text)) if "<" in str(text) else str(text)}


def _sections(module, doc, meta, readable):
    """Fields grouped the way the form groups them — but only the ones that
    hold a value. A Frappe form is mostly empty boxes; a card that repeats
    them is the reason people hate ERP on a phone."""
    by_name = {df.fieldname: df for df in meta.fields}
    wanted = [f for f in (module.detail_fields or "").split(",") if f.strip()]

    def field_payload(df):
        value = doc.get(df.fieldname)
        if value in (None, "") or df.fieldtype in LAYOUT_TYPES or df.fieldtype in NEVER_SHOWN:
            return None
        if df.fieldtype in ("Table",):
            return None
        if df.permlevel not in readable:
            return None
        out = _format(df, value, doc)
        # Through frappe._ so an ERPNext label reads in the user's language,
        # exactly as the form would show it.
        out.update({"fieldname": df.fieldname, "label": frappe._(df.label or df.fieldname), "fieldtype": df.fieldtype})
        return out

    if wanted:
        fields = [p for p in (field_payload(by_name[f]) for f in wanted if f in by_name) if p]
        return [{"label": "", "fields": fields}] if fields else []

    sections, current = [], {"label": "", "fields": []}
    for df in meta.fields:
        if df.fieldtype in ("Section Break", "Tab Break"):
            if current["fields"]:
                sections.append(current)
            current = {"label": frappe._(df.label) if df.label else "", "fields": []}
            continue
        if df.hidden:
            continue
        p = field_payload(df)
        if p:
            current["fields"].append(p)
    if current["fields"]:
        sections.append(current)
    return sections


def _tables(doc, meta, readable):
    out = []
    for df in meta.fields:
        if df.fieldtype != "Table" or df.permlevel not in readable or df.hidden:
            continue
        rows = doc.get(df.fieldname) or []
        if not rows:
            continue
        child_meta = frappe.get_meta(df.options)
        cols = [c for c in child_meta.fields
                if c.in_list_view and c.fieldtype not in LAYOUT_TYPES
                and c.fieldtype not in NEVER_SHOWN and c.fieldtype != "Table"][:4]
        if not cols:
            continue
        out.append({
            "fieldname": df.fieldname,
            "label": frappe._(df.label or df.options),
            "columns": [{"fieldname": c.fieldname, "label": frappe._(c.label or c.fieldname)} for c in cols],
            "rows": [
                {c.fieldname: (_format(c, row.get(c.fieldname), row)["value"]
                               if row.get(c.fieldname) not in (None, "") else "")
                 for c in cols}
                for row in rows[:MAX_TABLE_ROWS]
            ],
            "total": len(rows),
        })
    return out


def _attachments(doc):
    try:
        return frappe.get_list(
            "File",
            filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
            fields=["name", "file_name", "file_url", "is_private"],
            order_by="creation desc",
            limit_page_length=MAX_ATTACHMENTS,
        )
    except frappe.PermissionError:
        return []


def _comments(doc):
    try:
        rows = frappe.get_list(
            "Comment",
            filters={"reference_doctype": doc.doctype, "reference_name": doc.name,
                     "comment_type": "Comment"},
            fields=["name", "content", "owner", "creation"],
            order_by="creation desc",
            limit_page_length=MAX_COMMENTS,
        )
    except frappe.PermissionError:
        return []
    for r in rows:
        r["text"] = strip_html(r.pop("content") or "")
        r["by"] = frappe.utils.get_fullname(r["owner"])
        r["when"] = frappe.utils.pretty_date(r["creation"])
    return rows


# --------------------------------------------------------------------------- actions
def _visible(row, doc):
    if not row.show_when:
        return True
    return DOCSTATUS_NAMES.get(cint(doc.docstatus)) == row.show_when


def _actions(module, doc, meta):
    """What this user may do to this record, right now."""
    actions = []
    auto = cint(getattr(module, "auto_actions", 1))
    workflow = get_workflow_name(doc.doctype) if auto else None
    if workflow:
        try:
            transitions = get_transitions(doc)
        except Exception:
            transitions = []
        for t in transitions:
            actions.append({
                "kind": "workflow", "value": t.get("action"),
                "label": frappe._(t.get("action")), "style": "Primary",
                "hint": frappe._(t.get("next_state") or ""), "confirm": 1,
            })
    elif auto and meta.is_submittable:
        if cint(doc.docstatus) == 0 and doc.has_permission("submit"):
            actions.append({"kind": "submit", "label": frappe._("Submit"), "style": "Primary", "confirm": 1})
        elif cint(doc.docstatus) == 1 and doc.has_permission("cancel"):
            actions.append({"kind": "cancel", "label": frappe._("Cancel"), "style": "Danger", "confirm": 1})

    for i, row in enumerate(module.actions or []):
        if not _visible(row, doc):
            continue
        if row.action_type == "Set Value" and not doc.has_permission("write"):
            continue
        actions.append({
            "kind": "custom", "idx": i, "type": row.action_type,
            "label": row.label, "label_en": row.label_en, "icon": row.icon,
            "style": row.style or "Default", "confirm": cint(row.confirm),
            # Only a Route needs its value on the client; the rest stay server-side.
            "value": row.value if row.action_type == "Route" else None,
        })
    return actions


def _run_custom(module, doc, idx):
    rows = module.actions or []
    if idx < 0 or idx >= len(rows):
        frappe.throw("إجراء غير معروف")
    row = rows[idx]
    if not _visible(row, doc):
        frappe.throw("هذا الإجراء غير متاح لهذا السجل")

    if row.action_type == "Set Value":
        fieldname, _, value = row.value.partition("=")
        fieldname = fieldname.strip()
        df = doc.meta.get_field(fieldname)
        if not df or df.fieldtype in LAYOUT_TYPES or df.fieldtype == "Table":
            frappe.throw(f"الحقل {fieldname} غير موجود")
        doc.check_permission("write")
        if df.permlevel not in _writable_permlevels(doc):
            frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
        doc.set(fieldname, value.strip())
        doc.save()
    elif row.action_type == "Server Method":
        fn = frappe.get_attr(row.value)
        # Whitelisted or nothing: an admin typo must not become a way to call
        # arbitrary Python from a button on a phone.
        frappe.is_whitelisted(fn)
        frappe.call(fn, doctype=doc.doctype, name=doc.name)
    else:
        frappe.throw("هذا الإجراء يُنفَّذ من المتصفح")


# --------------------------------------------------------------------------- endpoints
@frappe.whitelist()
def get_record(module_key, name):
    module = _get_module(module_key)
    doc = _load(module, name)
    meta = doc.meta
    readable = _readable_permlevels(doc)

    title = doc.get(meta.title_field) if meta.title_field else None
    status_field = (module.status_field or "").strip() or ("docstatus" if meta.is_submittable else None)
    status = doc.get(status_field) if status_field else None
    if status_field == "docstatus":
        status = {"value": cint(doc.docstatus), "label": frappe._(DOCSTATUS_NAMES[cint(doc.docstatus)])}
    elif status not in (None, ""):
        status = {"value": status, "label": frappe._(str(status))}
    else:
        status = None

    return {
        "doctype": doc.doctype,
        "name": doc.name,
        "title": str(title or doc.name),
        "status": status,
        "docstatus": cint(doc.docstatus),
        "modified": frappe.utils.pretty_date(doc.modified),
        "modified_by": frappe.utils.get_fullname(doc.modified_by),
        "sections": _sections(module, doc, meta, readable),
        "tables": _tables(doc, meta, readable),
        "attachments": _attachments(doc),
        "comments": _comments(doc),
        "actions": _actions(module, doc, meta),
        "can_write": bool(doc.has_permission("write")),
        # Same slug rule as frappe.router.slug on the client.
        "desk_url": f"{desk_prefix()}/{doc.doctype.lower().replace(' ', '-')}/{doc.name}",
    }


@frappe.whitelist()
def run_action(module_key, name, action):
    module = _get_module(module_key)
    if isinstance(action, str):
        action = json.loads(action or "{}")
    doc = _load(module, name)
    kind = action.get("kind")

    if kind == "workflow":
        if not cint(getattr(module, "auto_actions", 1)):
            frappe.throw("الإجراءات التلقائية معطّلة لهذه الوحدة")
        # apply_workflow re-checks that this transition is allowed for the
        # user's roles and the document's current state.
        apply_workflow(doc.as_dict(), action.get("value"))
    elif kind == "submit":
        doc.check_permission("submit")
        doc.submit()
    elif kind == "cancel":
        doc.check_permission("cancel")
        doc.cancel()
    elif kind == "custom":
        _run_custom(module, doc, cint(action.get("idx", -1)))
    else:
        frappe.throw("إجراء غير معروف")

    return get_record(module_key, name)


@frappe.whitelist()
def add_comment(module_key, name, text):
    module = _get_module(module_key)
    doc = _load(module, name)
    text = (text or "").strip()
    if not text:
        frappe.throw("اكتب تعليقًا")
    doc.add_comment("Comment", frappe.utils.escape_html(text[:2000]))
    return _comments(doc)
