import frappe
from frappe.model.document import Document


class ShellSettings(Document):
    def on_update(self):
        frappe.cache().delete_value('wajha_config')
