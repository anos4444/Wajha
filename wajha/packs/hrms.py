"""HRMS self-service pack.

When HRMS is on the site, every employee-facing DocType gets a "mine" module
out of the box — my leave, my expense claims, my attendance, my check-ins,
my salary slips, my profile — each with an in-shell form, the record card,
and the actions an employee expects (check in / out with location, salary
slip PDF). Seeded on install, on migrate, and when HRMS is installed later
(after_app_install), so a site adapts without anyone creating records.

Idempotent and non-destructive: a module that exists is left alone except
that blank fields are filled; an admin's edits are never overwritten, and
disabling a module keeps it disabled.
"""

import json

import frappe

from wajha.api import build_module_doc

GROUP = "الخدمة الذاتية"
GROUP_EN = "Self Service"

# (module_key, label, label_en, icon, doctype, sequence, scope, scope_field,
#  {columns, form_fields, detail_fields, mobile_bar, actions, page_length})
MODULES = [
    ("my_leaves", "إجازاتي", "My Leave", "🌴", "Leave Application", 1,
     "Mine (Employee Field)", "employee", {
         "columns": ["leave_type", "from_date", "to_date", "total_leave_days", "status"],
         "form_fields": ["leave_type", "from_date", "to_date", "half_day", "half_day_date", "description"],
         "detail_fields": ["employee_name", "leave_type", "from_date", "to_date", "total_leave_days",
                           "half_day", "description", "status", "leave_approver_name", "leave_balance"],
         "mobile_bar": 1,
     }),
    ("my_checkins", "تسجيل الحضور", "Check In / Out", "📍", "Employee Checkin", 2,
     "Mine (Employee Field)", "employee", {
         "columns": ["log_type", "time", "shift"],
         "form_fields": ["log_type", "time"],
         "mobile_bar": 1,
         "page_length": 20,
         "actions": [
             {"label": "تسجيل دخول", "label_en": "Check in", "action_type": "Create", "level": "Module",
              "style": "Primary", "confirm": 1, "icon": "🟢",
              "value": {"log_type": "IN", "time": "{now}", "latitude": "{lat}", "longitude": "{lon}", "device_id": "wajha-shell"}},
             {"label": "تسجيل خروج", "label_en": "Check out", "action_type": "Create", "level": "Module",
              "style": "Danger", "confirm": 1, "icon": "🔴",
              "value": {"log_type": "OUT", "time": "{now}", "latitude": "{lat}", "longitude": "{lon}", "device_id": "wajha-shell"}},
         ],
     }),
    ("my_salary_slips", "قسائم راتبي", "My Salary Slips", "💵", "Salary Slip", 3,
     "Mine (Employee Field)", "employee", {
         "columns": ["start_date", "end_date", "gross_pay", "net_pay"],
         "form_fields": [],
         "detail_fields": ["employee_name", "start_date", "end_date", "posting_date", "total_working_days",
                           "payment_days", "gross_pay", "total_deduction", "net_pay", "currency"],
         "mobile_bar": 1,
         "actions": [
             {"label": "تنزيل PDF", "label_en": "Download PDF", "action_type": "Print", "level": "Record",
              "style": "Primary", "confirm": 0, "icon": "📄", "value": ""},
         ],
     }),
    ("my_expenses", "مطالباتي", "My Expense Claims", "🧾", "Expense Claim", 4,
     "Mine (Employee Field)", "employee", {
         "columns": ["posting_date", "total_claimed_amount", "total_sanctioned_amount", "status"],
         "form_fields": ["expenses", "remark"],
         "mobile_bar": 1,
     }),
    ("my_attendance", "حضوري", "My Attendance", "🕒", "Attendance", 5,
     "Mine (Employee Field)", "employee", {
         "columns": ["attendance_date", "status", "shift", "working_hours"],
         "form_fields": [],
     }),
    ("my_attendance_requests", "طلبات الحضور", "Attendance Requests", "📝", "Attendance Request", 6,
     "Mine (Employee Field)", "employee", {
         "columns": ["from_date", "to_date", "reason"],
         "form_fields": ["from_date", "to_date", "reason", "explanation"],
     }),
    ("my_comp_leave", "الإجازة التعويضية", "Compensatory Leave", "⏱️", "Compensatory Leave Request", 7,
     "Mine (Employee Field)", "employee", {
         "columns": ["work_from_date", "work_end_date", "leave_type"],
         "form_fields": ["work_from_date", "work_end_date", "half_day", "reason"],
     }),
    ("my_advances", "سلفي", "My Advances", "💳", "Employee Advance", 8,
     "Mine (Employee Field)", "employee", {
         "columns": ["posting_date", "purpose", "advance_amount", "status"],
         "form_fields": ["purpose", "advance_amount", "advance_account", "mode_of_payment"],
     }),
    ("my_travel", "طلبات السفر", "Travel Requests", "✈️", "Travel Request", 9,
     "Mine (Employee Field)", "employee", {
         "columns": ["travel_type", "purpose_of_travel", "travel_funding"],
         "form_fields": ["travel_type", "purpose_of_travel", "travel_funding", "description"],
     }),
    ("my_shift_requests", "طلبات الوردية", "Shift Requests", "🔁", "Shift Request", 10,
     "Mine (Employee Field)", "employee", {
         "columns": ["shift_type", "from_date", "to_date", "status"],
         "form_fields": ["shift_type", "from_date", "to_date"],
     }),
    ("my_shifts", "ورديتي", "My Shifts", "📅", "Shift Assignment", 11,
     "Mine (Employee Field)", "employee", {
         "columns": ["shift_type", "start_date", "end_date", "status"],
         "form_fields": [],
     }),
    ("my_profile", "ملفي", "My Profile", "👤", "Employee", 12,
     "Mine (User Field)", "user_id", {
         "columns": ["employee_name", "designation", "department", "company"],
         "form_fields": [],
         "detail_fields": ["employee_name", "employee", "designation", "department", "branch", "company",
                           "date_of_joining", "employment_type", "reports_to", "cell_number",
                           "company_email", "personal_email"],
     }),
]


def installed():
    return "hrms" in frappe.get_installed_apps()


def seed(app_name=None):
    """Runs from after_install, after_migrate and after_app_install."""
    # Any app arriving changes what Home can show: drop the discovery caches.
    try:
        from wajha.boot import clear_boot_cache

        clear_boot_cache()
    except Exception:
        pass
    if app_name and app_name not in ("hrms", "wajha"):
        return
    if not installed() or not frappe.db.exists("DocType", "Shell Module"):
        return
    frappe.clear_cache(doctype="Shell Module")
    frappe.clear_cache(doctype="Shell Module Action")
    created, filled = [], []
    for key, label, label_en, icon, doctype, seq, scope, scope_field, conf in MODULES:
        if not frappe.db.exists("DocType", doctype):
            continue
        # One module that fails to validate (a field renamed upstream, say)
        # must not take the other eleven down with it — nor migrate.
        try:
            _seed_one(key, label, label_en, icon, doctype, seq, scope, scope_field, conf, created, filled)
        except Exception:
            frappe.log_error(title=f"wajha: HRMS pack could not seed {key}", message=frappe.get_traceback())
            print(f"wajha: HRMS pack skipped {key}: {frappe.get_traceback().strip().splitlines()[-1]}")
    if created or filled:
        print(f"wajha: HRMS self-service pack — created {created or 'none'}, filled {filled or 'none'}")


def _seed_one(key, label, label_en, icon, doctype, seq, scope, scope_field, conf, created, filled):
    meta = frappe.get_meta(doctype)
    real = {df.fieldname for df in meta.fields}
    columns = [c for c in conf.get("columns", []) if c in real]
    if frappe.db.exists("Shell Module", key):
        if _fill_blanks(key, conf, real):
            filled.append(key)
        return
    doc = build_module_doc(doctype, key, label, field_include=columns or None)
    doc.module_label_en = label_en
    doc.icon = icon
    doc.group = GROUP
    doc.sequence = seq
    doc.scope = scope
    doc.scope_field = scope_field
    doc.form_fields = ",".join(f for f in conf.get("form_fields", []) if f in real)
    doc.detail_fields = ",".join(f for f in conf.get("detail_fields", []) if f in real)
    doc.show_in_mobile_bar = conf.get("mobile_bar", 0)
    doc.auto_generated = 1
    if conf.get("page_length"):
        doc.page_length = conf["page_length"]
    doc.sort_field = "modified"
    for a in conf.get("actions", []):
        row = dict(a)
        if isinstance(row.get("value"), dict):
            row["value"] = json.dumps(row["value"], ensure_ascii=False)
        doc.append("actions", row)
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    created.append(key)


def _fill_blanks(key, conf, real):
    """Fill only what is blank on an existing module (e.g. form_fields on a
    module made before this pack existed). Never overwrites."""
    doc = frappe.get_doc("Shell Module", key)
    changed = False
    for field, values in (("form_fields", conf.get("form_fields", [])),
                          ("detail_fields", conf.get("detail_fields", []))):
        if not doc.get(field) and values:
            doc.set(field, ",".join(f for f in values if f in real))
            changed = True
    if not doc.actions and conf.get("actions"):
        for a in conf["actions"]:
            row = dict(a)
            if isinstance(row.get("value"), dict):
                row["value"] = json.dumps(row["value"], ensure_ascii=False)
            doc.append("actions", row)
        changed = True
    if changed:
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
    return changed
