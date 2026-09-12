"""Strings that need translating but never appear in the source as literals,
declared here so Frappe's extractor puts them in ``locale/main.pot``.

Without this the entries would live only in the PO files, and the first
``bench update-po-files`` would mark them obsolete and drop them.

``_lt`` is Frappe's lazy translation marker: it is one of the keywords the
POT extractor recognises, and nothing here is evaluated at import time.
"""

from frappe import _lt

# Workspace titles the shell shows as sidebar groups. These belong to
# frappe / erpnext / hrms, which carry the msgid but leave the Arabic empty;
# translating them here fills that gap for every site running Wajha.
WORKSPACE_TITLES = [
    _lt("HR Setup"),  # hrms, HR: employees, HR reports, company/branch/department setup
    _lt("Invoicing"),  # erpnext, Accounts
    _lt("Recruitment"),  # hrms, HR: jobs, applicants, offers, interviews
    _lt("Tax & Benefits"),  # hrms, Payroll: benefit claims, tax slabs and exemptions
    _lt("Tenure"),  # hrms, HR: onboarding, training, grievances, daily work summaries
    _lt("Website"),  # frappe, Website
]

# Values Wajha writes into the database — theme names, the group the HRMS
# pack seeds, the default brand title. They are Arabic at the source, and
# the English is what a non-Arabic user reads.
SEEDED_VALUES = [
    _lt("الأخضر المؤسسي"),
    _lt("الأزرق الحكومي"),
    _lt("الرمادي المحايد"),
    _lt("العنابي"),
    _lt("نظام الإدارة"),
    _lt("الخدمة الذاتية"),
]

# Group names an administrator typed on a site rather than Wajha seeding
# them; kept here so both languages read the sidebar in their own.
SITE_GROUPS = [
    _lt("التطبيقات"),
    _lt("الإجازات والمطالبات"),
    _lt("الحضور والدوام"),
    _lt("الرواتب"),
    _lt("الموارد البشرية"),
    _lt("الموظفون"),
]

# Names the HR dashboard pack writes into Number Card, Dashboard Chart and
# Dashboard records; the Home page reads them back through frappe._.
HR_DASHBOARD = [
    _lt("HR Overview"),
    _lt("Active employees"),
    _lt("Pending leave approvals"),
    _lt("Pending expense claims"),
    _lt("Open job openings"),
    _lt("Employees per department"),
    _lt("Leave applications by status"),
    _lt("Joining trend"),
]
