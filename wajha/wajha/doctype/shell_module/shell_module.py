import frappe
from frappe.model.document import Document


class ShellModule(Document):
    def validate(self):
        self.module_key = (self.module_key or "").strip().lower().replace(" ", "_")
        if self.view_type == "List" and not self.ref_doctype:
            frappe.throw("اختر DocType للوحدة من نوع قائمة")
        if self.view_type == "Route Link" and not self.route:
            frappe.throw("أدخل المسار للوحدة من نوع رابط")
        self.status_field = (self.status_field or "").strip()

    def on_update(self):
        self._clear_cache()

    def on_trash(self):
        self._clear_cache()

    def _clear_cache(self):
        frappe.cache().delete_value("wajha_config")
        # Field allow-list is cached per module in wajha.api._allowed_fields();
        # drop it immediately so column/filter/status_field edits take effect
        # on the next request instead of waiting out the 5-minute TTL.
        frappe.cache().delete_value(f"wajha_fields_{self.name}")
