"""HR overview dashboard for HR roles, built from Frappe's own blocks.

Number Cards for the KPI row, Dashboard Charts for the graphs, one Frappe
Dashboard tying them together, and two rows in Shell Settings mapping HR
Manager and HR User to it. Everything is a normal Frappe record afterwards:
an administrator changes a filter, a colour or a chart type in the Desk and
the shell's Home follows. The pack only creates what is missing; it never
edits or overwrites a record that exists, and it leaves the role table
alone once someone has filled it.
"""

import json

import frappe

DASHBOARD = "HR Overview"
ROLES = ["HR Manager", "HR User"]

# label, doctype, filters
CARDS = [
    ("Active Employees", "Employee", [["Employee", "status", "=", "Active"]]),
    ("Pending leave approvals", "Leave Application",
     [["Leave Application", "status", "=", "Open"], ["Leave Application", "docstatus", "=", 0]]),
    ("Pending expense claims", "Expense Claim",
     [["Expense Claim", "approval_status", "=", "Draft"], ["Expense Claim", "docstatus", "=", 0]]),
    ("Open job openings", "Job Opening", [["Job Opening", "status", "=", "Open"]]),
]

CHARTS = [
    {"chart_name": "Employees per department", "chart_type": "Group By", "document_type": "Employee",
     "group_by_based_on": "department", "group_by_type": "Count", "number_of_groups": 8, "type": "Bar",
     "filters_json": json.dumps([["Employee", "status", "=", "Active"]]), "width": "Half"},
    {"chart_name": "Leave applications by status", "chart_type": "Group By", "document_type": "Leave Application",
     "group_by_based_on": "status", "group_by_type": "Count", "number_of_groups": 6, "type": "Donut",
     "filters_json": "[]", "width": "Half"},
    {"chart_name": "Joining trend", "chart_type": "Count", "document_type": "Employee", "based_on": "date_of_joining",
     "timeseries": 1, "timespan": "Last Year", "time_interval": "Monthly", "type": "Line",
     "filters_json": "[]", "width": "Full"},
]


def installed():
    return "hrms" in frappe.get_installed_apps()


def seed(app_name=None):
    if not installed():
        return
    created = []
    card_names = [_card(label, dt, filters, created) for label, dt, filters in CARDS]
    chart_rows = [_chart(spec, created) for spec in CHARTS]
    card_names = [n for n in card_names if n]
    chart_rows = [r for r in chart_rows if r]
    if chart_rows and not frappe.db.exists("Dashboard", DASHBOARD):
        frappe.get_doc({
            "doctype": "Dashboard", "dashboard_name": DASHBOARD,
            "charts": chart_rows, "cards": [{"card": n} for n in card_names],
        }).insert(ignore_permissions=True)
        created.append(f"Dashboard {DASHBOARD}")
    _map_roles(created)
    if created:
        frappe.db.commit()
        from wajha.boot import clear_boot_cache
        clear_boot_cache()
        print(f"wajha: HR dashboard pack created {', '.join(created)}")


def _card(label, doctype, filters, created):
    if not frappe.db.exists("DocType", doctype):
        return None
    name = frappe.db.get_value("Number Card", {"label": label, "document_type": doctype}, "name")
    if name:
        return name
    doc = frappe.get_doc({
        "doctype": "Number Card", "label": label, "type": "Document Type", "document_type": doctype,
        "function": "Count", "filters_json": json.dumps(filters), "is_public": 1,
    }).insert(ignore_permissions=True)
    created.append(f"Number Card {label}")
    return doc.name


def _chart(spec, created):
    if not frappe.db.exists("DocType", spec["document_type"]):
        return None
    width = spec["width"]
    if not frappe.db.exists("Dashboard Chart", spec["chart_name"]):
        fields = {k: v for k, v in spec.items() if k != "width"}
        frappe.get_doc({"doctype": "Dashboard Chart", "is_public": 1, **fields}).insert(ignore_permissions=True)
        created.append(f"Dashboard Chart {spec['chart_name']}")
    return {"chart": spec["chart_name"], "width": width}


def _map_roles(created):
    """HR Manager and HR User → HR Overview, only while the table is empty."""
    if not frappe.db.exists("Dashboard", DASHBOARD):
        return
    frappe.clear_cache(doctype="Shell Settings")
    s = frappe.get_single("Shell Settings")
    if not s.meta.has_field("dashboards") or s.get("dashboards"):
        return
    rows = [r for r in ROLES if frappe.db.exists("Role", r)]
    if not rows:
        return
    for role in rows:
        s.append("dashboards", {"role": role, "dashboard": DASHBOARD})
    s.flags.ignore_permissions = True
    s.save()
    created.append("Shell Settings role mapping (" + ", ".join(rows) + ")")
