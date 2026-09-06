"""Dashboard cards for the HRMS self-service modules.

Every figure comes from HRMS's own functions or from frappe.get_list inside
the module's scope, so what an employee sees here is exactly what the leave
form, the attendance list and the salary slip would tell them.
"""

import frappe
from frappe.utils import add_days, add_months, cint, flt, formatdate, get_first_day, nowdate

from wajha.api import _current_employee
from wajha.dashboard import register, stat


def _employee(module):
    scope = getattr(module, "scope", "All") or "All"
    if scope == "Mine (Employee Field)":
        return _current_employee()
    return None


# --------------------------------------------------------------------------- leave
def leave_cards(module, ctx):
    emp = _employee(module)
    cards = []
    if emp:
        # Balance per leave type, from HRMS's own leave-details function.
        try:
            from hrms.hr.doctype.leave_application.leave_application import get_leave_details

            details = get_leave_details(emp, nowdate()) or {}
            alloc = details.get("leave_allocation") or {}
            items = []
            for leave_type, d in alloc.items():
                total = flt(d.get("total_leaves"))
                remaining = flt(d.get("remaining_leaves"))
                taken = flt(d.get("leaves_taken"))
                pending = flt(d.get("leaves_pending_approval"))
                items.append({"label": frappe._(leave_type), "value": remaining, "total": total,
                              "hint": frappe._("{0} taken · {1} pending").format(taken, pending)})
            if items:
                cards.append({"kind": "progress", "label": frappe._("Leave balance"), "items": items})
        except Exception:
            frappe.log_error(title="wajha: leave balance card")
        # Upcoming holidays from the employee's holiday list.
        try:
            from hrms.hr.utils import get_holidays_for_employee

            holidays = get_holidays_for_employee(emp, nowdate(), add_days(nowdate(), 60), raise_exception=False) or []
            items = [{"label": frappe._(h.get("description") or ""), "hint": formatdate(h.get("holiday_date"))}
                     for h in holidays if not cint(h.get("weekly_off"))][:5]
            if items:
                cards.append({"kind": "list", "label": frappe._("Upcoming holidays"), "items": items})
        except Exception:
            frappe.log_error(title="wajha: holidays card")
    # Pending approval, for the employee and for the approver alike.
    pending = frappe.get_list("Leave Application", fields=[{"COUNT": "*"}], as_list=True, limit_page_length=1,
                              filters=ctx["scope"] + [["docstatus", "=", 0], ["status", "=", "Open"]])
    n = cint(pending[0][0]) if pending else 0
    if n:
        cards.append(stat(frappe._("Awaiting approval"), str(n), icon="⏳", tone="warning",
                          filter={"field": "status", "value": "Open"}))
    return cards


# --------------------------------------------------------------------------- attendance
def attendance_cards(module, ctx):
    start = get_first_day(nowdate())
    rows = frappe.get_list("Attendance", fields=["status", {"COUNT": "*"}], group_by="status", as_list=True,
                           filters=ctx["scope"] + [["attendance_date", ">=", start], ["docstatus", "=", 1]],
                           limit_page_length=10)
    counts = {r[0]: cint(r[1]) for r in rows if r[0]}
    if not counts:
        return []
    tone = {"Present": "success", "Absent": "danger", "On Leave": "info", "Half Day": "warning", "Work From Home": "info"}
    return [stat(frappe._(k), str(v), hint=frappe._("This month"), tone=tone.get(k)) for k, v in counts.items()]


# --------------------------------------------------------------------------- check-ins
def checkin_cards(module, ctx):
    today = nowdate()
    rows = frappe.get_list("Employee Checkin", fields=["log_type", "time"], order_by="time desc", limit_page_length=1,
                           filters=ctx["scope"] + [["time", ">=", today]])
    if not rows:
        return [stat(frappe._("Today"), frappe._("Not checked in"), icon="🕒", tone="warning")]
    last = rows[0]
    label = frappe._("Checked in") if last.log_type == "IN" else frappe._("Checked out")
    return [stat(frappe._("Today"), label, hint=frappe.utils.format_datetime(last.time, "HH:mm"),
                 icon="🟢" if last.log_type == "IN" else "🔴", tone="success" if last.log_type == "IN" else None)]


# --------------------------------------------------------------------------- salary
def salary_cards(module, ctx):
    rows = frappe.get_list("Salary Slip", fields=["net_pay", "gross_pay", "end_date", "currency"],
                           order_by="end_date desc", limit_page_length=1,
                           filters=ctx["scope"] + [["docstatus", "=", 1]])
    if not rows:
        return []
    r = rows[0]
    cur = {"fieldtype": "Currency", "options": "currency"}
    doc = frappe._dict(currency=r.currency)
    return [stat(frappe._("Last net pay"), frappe.format_value(r.net_pay, cur, doc), hint=formatdate(r.end_date), icon="💵", tone="success"),
            stat(frappe._("Gross"), frappe.format_value(r.gross_pay, cur, doc), hint=formatdate(r.end_date))]


# --------------------------------------------------------------------------- expenses
def expense_cards(module, ctx):
    since = add_months(nowdate(), -12)
    rows = frappe.get_list("Expense Claim", fields=["approval_status", {"SUM": "total_claimed_amount"}, {"COUNT": "*"}],
                           group_by="approval_status", as_list=True, limit_page_length=10,
                           filters=ctx["scope"] + [["posting_date", ">=", since], ["docstatus", "<", 2]])
    out = []
    tone = {"Approved": "success", "Rejected": "danger", "Draft": "warning"}
    for status, amount, count in rows:
        if not status:
            continue
        out.append(stat(frappe._(status), frappe.format_value(flt(amount), {"fieldtype": "Currency"}),
                        hint=frappe._("{0} claims, last 12 months").format(cint(count)), tone=tone.get(status),
                        filter={"field": "approval_status", "value": status}))
    return out


register("Leave Application", leave_cards)
register("Attendance", attendance_cards)
register("Employee Checkin", checkin_cards)
register("Salary Slip", salary_cards)
register("Expense Claim", expense_cards)
