"""Boot transport for the shell configuration.

The client used to fetch `wajha.api.get_config` over HTTP on every Desk page
load, which cost a round trip before anything could be themed and left a
visible flash of unstyled Desk. The same payload now rides along in Frappe's
own boot response, so the theme is already in hand when the first line of
wajha_boot.js runs.

This also removes a race rather than papering over one: the shell no longer has
to guess, at `app_ready` time, whether its configuration has arrived yet.
"""

import frappe


def add_boot_data(bootinfo):
    """Attach the resolved shell config to the boot payload.

    Fails soft on purpose. A broken or half-migrated Shell Settings must never
    take the whole Desk down with it — the client falls back to fetching the
    config over HTTP when `wajha_config` is missing, which is exactly the old
    behaviour.
    """
    if frappe.session.user in ("Guest", None):
        return

    try:
        from wajha.api import get_config

        bootinfo.wajha_config = get_config()
    except Exception:
        frappe.log_error("wajha: boot config failed")


def clear_boot_cache():
    """Drop cached boot payloads after a settings/theme/module change.

    Frappe caches bootinfo per user, so without this a theme edit would keep
    serving the old colours until that cache happened to turn over. Falls back
    to a full cache clear if the bootinfo key cannot be dropped on its own —
    correctness matters more here than the cost of a rare settings save.
    """
    try:
        frappe.cache().delete_key("bootinfo")
    except Exception:
        frappe.clear_cache()
    try:
        from wajha import discovery

        discovery.clear_tiles_cache()
        discovery.clear_cache()
    except Exception:
        pass
