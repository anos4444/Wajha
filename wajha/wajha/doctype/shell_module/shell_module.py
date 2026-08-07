import frappe
from frappe.model.document import Document


class ShellModule(Document):
    def validate(self):
        self.module_key = (self.module_key or "").strip().lower().replace(" ", "_")
        if self.view_type == "List" and not self.ref_doctype:
            frappe.throw("اختر DocType للوحدة من نوع قائمة")
        if self.view_type == "Route Link" and not self.route:
            frappe.throw("أدخل المسار للوحدة من نوع رابط")

    def on_update(self):
        frappe.cache().delete_value("wajha_config")

    def on_trash(self):
        frappe.cache().delete_value("wajha_config")
