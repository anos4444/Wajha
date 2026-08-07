from frappe.model.document import Document


class ShellTheme(Document):
    def on_update(self):
        import frappe
        frappe.cache().delete_value('wajha_config')
