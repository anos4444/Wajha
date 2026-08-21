from frappe.model.document import Document

from wajha.boot import clear_boot_cache


class ShellTheme(Document):
    def on_update(self):
        clear_boot_cache()
