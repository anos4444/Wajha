import json

import frappe
from frappe.model.document import Document

# Filter controls whose queries are open-ended range scans (>=, <=) rather
# than exact matches. On a table with real row counts these are exactly the
# queries that degrade into a full table scan without a matching index --
# and the field picked for one of these controls is very often a custom or
# amount/date field that ERPNext's own standard-field indexes don't happen
# to cover (unlike e.g. `modified` or `transaction_date`, which usually are
# indexed already).
_INDEXABLE_CONTROLS = {"Number Range", "Date Range", "Datetime Range"}


class ShellModule(Document):
    def validate(self):
        self.module_key = (self.module_key or "").strip().lower().replace(" ", "_")
        if self.view_type == "List" and not self.ref_doctype:
            frappe.throw("اختر DocType للوحدة من نوع قائمة")
        if self.view_type == "Route Link" and not self.route:
            frappe.throw("أدخل المسار للوحدة من نوع رابط")
        self.status_field = (self.status_field or "").strip()
        self.scope_field = (self.scope_field or "").strip()
        if self.scope in ("Mine (User Field)", "Mine (Employee Field)") and not self.scope_field:
            frappe.throw("أدخل حقل النطاق للوحدة المقيّدة بالمستخدم")
        if self.scope == "Mine (Employee Field)" and not frappe.db.exists("DocType", "Employee"):
            frappe.throw("نطاق الموظف يتطلب تثبيت HRMS (DocType Employee)")
        self.detail_fields = ",".join(
            f.strip() for f in (self.detail_fields or "").replace("\n", ",").split(",") if f.strip()
        )
        self.form_fields = ",".join(
            f.strip() for f in (self.form_fields or "").replace("\n", ",").split(",") if f.strip()
        )
        for row in self.actions:
            row.value = (row.value or "").strip()
            # Print is the one type that may have no value (the default format).
            if row.action_type != "Print" and not row.value:
                frappe.throw(f"الإجراء {row.label}: أدخل القيمة")
            if row.action_type == "Set Value" and "=" not in row.value:
                frappe.throw(f"الإجراء {row.label}: القيمة يجب أن تكون بصيغة fieldname=value")
            if row.action_type == "Server Method" and "." not in row.value:
                frappe.throw(f"الإجراء {row.label}: أدخل المسار الكامل للدالة (app.module.function)")
            if row.action_type == "Create":
                try:
                    parsed = json.loads(row.value or "{}")
                except ValueError:
                    frappe.throw(f"الإجراء {row.label}: القيمة يجب أن تكون JSON")
                if not isinstance(parsed, dict):
                    frappe.throw(f"الإجراء {row.label}: القيمة يجب أن تكون كائن JSON")
                row.level = "Module" if not row.level else row.level
            if row.action_type == "Print" and (row.level or "Record") != "Record":
                frappe.throw(f"الإجراء {row.label}: الطباعة إجراء على مستوى السجل")
            if row.action_type in ("Set Value", "Server Method", "Route", "Print"):
                row.level = row.level or "Record"

    def on_update(self):
        self._clear_cache()
        self._queue_filter_indexes()

    def on_trash(self):
        self._clear_cache()

    def _clear_cache(self):
        # The module list is part of the boot payload, so adding, renaming or
        # disabling a module has to invalidate that too.
        from wajha.boot import clear_boot_cache

        clear_boot_cache()
        # Field allow-list is cached per module in wajha.api._allowed_fields();
        # drop it immediately so column/filter/status_field edits take effect
        # on the next request instead of waiting out the 5-minute TTL.
        frappe.cache().delete_value(f"wajha_fields_{self.name}")

    def _queue_filter_indexes(self):
        """Make sure range-filter fields are actually indexed.

        frappe.db.add_index() is idempotent -- it checks has_index() first
        and only issues the ALTER TABLE the first time a field is missing
        one -- so calling this on every save is cheap in the common case.
        It runs as a background job (queue="long") so a slow index build on
        an already-large table never blocks the Shell Module save itself.
        """
        if self.view_type != "List" or not self.ref_doctype:
            return
        fieldnames = sorted({
            f.fieldname for f in self.filters
            if f.control in _INDEXABLE_CONTROLS and f.fieldname
        })
        if not fieldnames:
            return
        frappe.enqueue(
            "wajha.wajha.doctype.shell_module.shell_module.add_filter_indexes",
            queue="long",
            job_name=f"wajha-add-filter-indexes-{self.name}",
            doctype=self.ref_doctype,
            fieldnames=fieldnames,
        )


def add_filter_indexes(doctype, fieldnames):
    """Background job body for ShellModule._queue_filter_indexes.

    Kept as a module-level function (rather than a method) because
    frappe.enqueue needs a plain importable dotted path.
    """
    meta = frappe.get_meta(doctype)
    real_fields = {df.fieldname for df in meta.fields}
    for fieldname in fieldnames:
        if fieldname not in real_fields:
            continue  # config referenced a field that no longer exists; skip quietly
        try:
            frappe.db.add_index(doctype, [fieldname])
        except Exception:
            frappe.log_error(
                title="Wajha: could not add filter index",
                message=frappe.get_traceback(),
            )
    frappe.db.commit()
