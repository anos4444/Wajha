from frappe.model.document import Document

from wajha.boot import clear_boot_cache


class ShellSettings(Document):
    def on_update(self):
        # The config rides in the boot payload, so that is what has to be
        # invalidated for an edit here to reach open sessions on next load.
        clear_boot_cache()
