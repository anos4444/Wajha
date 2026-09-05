"""Auto-discovery: the shell adapts to whatever apps the site has.

Two sources, both Frappe's own, so nothing here decides what a user may see:

- Tiles for the Home grid come from Frappe 16's Desktop Icons (the same
  cards the Desk home shows), filtered by the icon's roles and by whether
  the user can read anything behind it; on a Desk without Desktop Icons
  the public Workspaces stand in.
- Modules inside a tile come from the Workspace's own link list: every
  DocType link the user may read becomes a virtual module ("~<doctype>")
  built on the fly from the DocType's list-view configuration, exactly as
  the scaffold would build a Shell Module record — except nothing is
  written. A hand-made Shell Module for the same DocType wins.

Nothing is cached across users except the key→DocType map (which carries
no permission); everything permission-bearing is computed for the caller.
"""

import frappe
from frappe.utils import cint

VIRTUAL_PREFIX = "~"
GROUP_PREFIX = "@"
MAP_CACHE_KEY = "wajha_virtual_map"
MAP_CACHE_TTL = 600

SKIP_DOCTYPES = {"DocType", "Custom Field", "Property Setter", "Server Script", "Client Script"}


def enabled():
    s = frappe.get_cached_doc("Shell Settings")
    return bool(s.meta.has_field("auto_modules") and cint(s.auto_modules))


# --------------------------------------------------------------------------- keys
def slug(text):
    return frappe.scrub(text or "").replace("_", "-")


def virtual_key(doctype):
    return VIRTUAL_PREFIX + slug(doctype)


def group_key(workspace):
    return GROUP_PREFIX + slug(workspace)


def is_virtual(key):
    return bool(key) and key.startswith(VIRTUAL_PREFIX)


def is_group(key):
    return bool(key) and key.startswith(GROUP_PREFIX)


# --------------------------------------------------------------------------- workspaces
def _workspaces():
    fields = ["name", "title", "module", "icon", "sequence_id", "parent_page"]
    meta = frappe.get_meta("Workspace")
    if meta.has_field("app"):
        fields.append("app")
    return frappe.get_all(
        "Workspace",
        filters={"public": 1, "is_hidden": 0},
        fields=fields,
        order_by="sequence_id asc, title asc",
    )


def _workspace_doc(name):
    return frappe.get_cached_doc("Workspace", name)


def _readable_doctype(dt):
    if not dt or dt in SKIP_DOCTYPES or not frappe.db.exists("DocType", dt):
        return False
    meta = frappe.get_meta(dt)
    if meta.istable or meta.issingle:
        return False
    return bool(frappe.has_permission(dt, "read"))


def workspace_sections(workspace_name):
    """The DocTypes of a workspace the user may read, grouped by its Card
    Breaks — the structure the Desk shows, minus reports and pages."""
    try:
        ws = _workspace_doc(workspace_name)
    except frappe.DoesNotExistError:
        return []
    handmade = _handmade_by_doctype()
    sections, current, seen = [], {"label": "", "modules": []}, set()
    for link in ws.links:
        if link.type == "Card Break":
            if current["modules"]:
                sections.append(current)
            current = {"label": frappe._(link.label or ""), "modules": []}
            continue
        if link.hidden or link.link_type != "DocType" or not link.link_to:
            continue
        dt = link.link_to
        if dt in seen or not _readable_doctype(dt):
            continue
        seen.add(dt)
        current["modules"].append(handmade.get(dt) or _virtual_summary(dt, link.label))
    if current["modules"]:
        sections.append(current)
    return sections


def _virtual_summary(dt, label=None):
    return {
        "name": virtual_key(dt),
        "module_key": virtual_key(dt),
        "module_label": frappe._(label or dt),
        "module_label_en": label or dt,
        "view_type": "List",
        "ref_doctype": dt,
        "virtual": 1,
        "can_create": bool(frappe.has_permission(dt, "create")),
    }


def _handmade_by_doctype():
    out = {}
    for m in frappe.get_all(
        "Shell Module", filters={"enabled": 1, "view_type": "List"},
        fields=["name", "module_key", "module_label", "module_label_en", "icon", "ref_doctype", "scope"],
    ):
        # A "mine" module is not a substitute for browsing the DocType.
        if (m.scope or "All") != "All":
            continue
        if m.ref_doctype and frappe.has_permission(m.ref_doctype, "read"):
            m["view_type"] = "List"
            out.setdefault(m.ref_doctype, m)
    return out


# --------------------------------------------------------------------------- virtual modules
def _virtual_map():
    """key → DocType for every DocType any public workspace links to.
    Permission-free, so it can be shared; the permission check happens in
    api._get_module when the module is actually used."""
    cached = frappe.cache().get_value(MAP_CACHE_KEY)
    if cached:
        return cached
    out = {}
    for ws in _workspaces():
        try:
            doc = _workspace_doc(ws.name)
        except frappe.DoesNotExistError:
            continue
        for link in doc.links:
            if link.type == "Link" and link.link_type == "DocType" and link.link_to:
                out.setdefault(virtual_key(link.link_to), link.link_to)
    frappe.cache().set_value(MAP_CACHE_KEY, out, expires_in_sec=MAP_CACHE_TTL)
    return out


def clear_cache():
    frappe.cache().delete_value(MAP_CACHE_KEY)


def resolve_doctype(key):
    dt = _virtual_map().get(key)
    if dt:
        return dt
    # A DocType not linked from any workspace: still allowed if it exists
    # and the key is its own slug — the permission check follows anyway.
    for name in frappe.get_all("DocType", filters={"istable": 0, "issingle": 0}, pluck="name"):
        if virtual_key(name) == key:
            return name
    return None


def virtual_module(key):
    """An unsaved Shell Module for a "~<doctype>" key, or None."""
    from wajha.api import build_module_doc

    dt = resolve_doctype(key)
    if not dt or dt in SKIP_DOCTYPES:
        return None
    meta = frappe.get_meta(dt)
    if meta.istable or meta.issingle:
        return None
    doc = build_module_doc(dt, key, frappe._(dt))
    doc.name = key
    doc.enabled = 1
    doc.scope = "All"
    doc.auto_actions = 1
    doc.module_label_en = dt
    return doc


# --------------------------------------------------------------------------- tiles
TILES_CACHE_PREFIX = "wajha_tiles::"
TILES_CACHE_TTL = 300
FOLDER_PREFIX = GROUP_PREFIX + "="


def clear_tiles_cache():
    try:
        frappe.cache().delete_keys(TILES_CACHE_PREFIX)
    except Exception:
        pass


def _icon_rows():
    """Frappe 16 Desktop Icons this user could be shown: the standard ones
    plus the user's own — the same selection get_desktop_icons() makes."""
    fields = ["name", "label", "icon_type", "link_type", "link_to", "app", "icon",
              "logo_url", "link", "hidden", "bg_color", "parent_icon", "standard", "idx"]
    rows = frappe.get_all(
        "Desktop Icon", fields=fields,
        or_filters=[["standard", "=", 1], ["owner", "in", ["Administrator", frappe.session.user]]],
        order_by="idx asc, label asc",
    )
    roles = {}
    for r in frappe.get_all("Has Role", filters={"parenttype": "Desktop Icon",
                                                  "parent": ["in", [r.name for r in rows] or [""]]},
                            fields=["parent", "role"]):
        roles.setdefault(r.parent, set()).add(r.role)
    return rows, roles


def _app_permitted(icon):
    try:
        from frappe.desk.doctype.desktop_icon.desktop_icon import check_app_permission

        return bool(check_app_permission(icon.label, icon.app))
    except Exception:
        return True


def _icon_permitted(icon, roles, user_roles):
    if roles.get(icon.name) and not (roles[icon.name] & user_roles):
        return False
    kind = icon.icon_type or "Link"
    if kind == "Folder":
        return True
    if kind == "App":
        return _app_permitted(icon)
    ws = icon.link_to or icon.label
    return bool(frappe.db.exists("Workspace", ws) and workspace_sections(ws))


def _icon_tile(icon, children):
    label = icon.label or icon.name
    base = {
        "label": frappe._(label), "label_en": label, "icon": icon.icon,
        "logo_url": icon.logo_url, "bg_color": icon.bg_color, "app": icon.app, "count": len(children),
    }
    if children:
        base.update({"key": FOLDER_PREFIX + slug(label), "kind": "folder"})
        return base
    if (icon.icon_type or "Link") == "Link":
        ws = icon.link_to or label
        base.update({"key": group_key(ws), "kind": "group", "workspace": ws})
        return base
    if icon.link:
        base.update({"key": None, "kind": "link", "url": icon.link})
        return base
    return None


def _icon_tree():
    """Top-level tiles with their child tiles, mirroring the Desk home: a
    hidden parent's children are promoted; a visible parent with children
    becomes a folder tile carrying a count."""
    rows, roles = _icon_rows()
    user_roles = set(frappe.get_roles())
    by_label = {r.label: r for r in rows}
    permitted = {r.name: _icon_permitted(r, roles, user_roles) for r in rows}
    children = {}
    top = []
    for r in rows:
        if r.hidden or not permitted.get(r.name):
            continue
        parent = by_label.get(r.parent_icon) if r.parent_icon else None
        if parent and not parent.hidden and permitted.get(parent.name):
            children.setdefault(parent.label, []).append(r)
        else:
            top.append(r)
    out = []
    for r in top:
        kids = [c for c in children.get(r.label, []) if (c.icon_type or "Link") != "Folder" or children.get(c.label)]
        if (r.icon_type or "Link") == "Folder" and not kids:
            continue
        tile = _icon_tile(r, kids)
        if tile:
            tile["_children"] = [t for t in (_icon_tile(c, []) for c in kids) if t]
            out.append(tile)
    return out


def tiles():
    """Home-grid tiles for this user: Frappe 16 Desktop Icons when the site
    has them (the Desk home's own cards), else the public workspaces.
    Cached per user for a few minutes; cleared with the boot cache."""
    key = TILES_CACHE_PREFIX + frappe.session.user
    cached = frappe.cache().get_value(key)
    if cached is not None:
        return cached
    out = []
    if frappe.db.exists("DocType", "Desktop Icon"):
        out = [{k: v for k, v in t.items() if k != "_children"} for t in _icon_tree()]
    if not out:
        for ws in _workspaces():
            if ws.parent_page or not workspace_sections(ws.name):
                continue
            out.append({
                "key": group_key(ws.name), "kind": "group", "workspace": ws.name,
                "label": frappe._(ws.title or ws.name), "label_en": ws.title or ws.name,
                "icon": ws.icon, "logo_url": None, "bg_color": None, "app": ws.get("app"), "count": 0,
            })
    frappe.cache().set_value(key, out, expires_in_sec=TILES_CACHE_TTL)
    return out


def group(key):
    """What a tile opens: a folder's child tiles, or a workspace's DocTypes
    in its card sections."""
    if key.startswith(FOLDER_PREFIX):
        for t in _icon_tree():
            if t.get("key") == key:
                return {"key": key, "kind": "folder", "label": t["label"], "app": t.get("app"),
                        "tiles": t.get("_children", []), "sections": []}
        frappe.throw("مجموعة غير معروفة", frappe.DoesNotExistError)
    ws_slug = key[len(GROUP_PREFIX):]
    for ws in _workspaces():
        if slug(ws.name) == ws_slug:
            return {"key": key, "kind": "group", "label": frappe._(ws.title or ws.name),
                    "app": ws.get("app"), "tiles": [], "sections": workspace_sections(ws.name)}
    frappe.throw("مجموعة غير معروفة", frappe.DoesNotExistError)
