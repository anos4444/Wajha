"""One order for the apps, the way a business runs, not the alphabet.

Frappe's workspaces come with a `sequence_id` that reflects the order they
were created in, and the shell's sidebar and Home tiles used to fall back to
alphabetical order on top of that ("Accounting, Assets, Buying, …"). People
who run a company read their ERP in the order the money moves: win the
customer, sell, buy, stock, make, deliver, account for it, then the people
and the assets, then the tools and settings at the end.

`rank(title)` gives a workspace or module group its place in that order;
unknown groups (a custom app's workspace) land after the core business
areas and before the administrative ones, so nothing new is buried.
"""

import re

BUSINESS_ORDER = [
    # front office
    "Home", "CRM", "Selling", "Sales", "Point of Sale", "Retail",
    # supply
    "Buying", "Purchasing", "Stock", "Inventory", "Subcontracting", "Manufacturing", "Quality",
    # delivery
    "Projects", "Support", "Helpdesk",
    # money
    "Accounting", "Accounts", "Receivables", "Payables", "Invoicing", "Payments", "Financial Reports",
    "Tax Compliance", "Assets",
    # people
    "HR", "Human Resources", "Employee", "Employee Lifecycle", "Attendance", "Shift", "Leaves",
    "Recruitment", "Performance", "Expense Claims", "Payroll", "Salary", "Loans",
    # operations that custom apps usually add
    "Fleet", "Vehicle", "Cars", "Timesheet", "Fuel",
]

ADMIN_ORDER = [
    "Users", "Tools", "Website", "Integrations", "ERPNext Integrations",
    "ERPNext Settings", "Settings", "Build", "Utilities", "Developer",
]

UNKNOWN_RANK = 600
_words = re.compile(r"[a-z0-9]+")


def _norm(text):
    return " ".join(_words.findall(str(text or "").lower()))


def rank(title):
    """Position of a workspace title (or module group) in the business order.

    Exact title first, then the first business keyword the title contains as
    a whole word, then the administrative list; anything else sits at
    UNKNOWN_RANK, between the two."""
    t = _norm(title)
    if not t:
        return UNKNOWN_RANK
    for i, name in enumerate(BUSINESS_ORDER):
        if t == _norm(name):
            return i * 10
    for i, name in enumerate(ADMIN_ORDER):
        if t == _norm(name):
            return 1000 + i * 10
    words = set(t.split())
    for i, name in enumerate(BUSINESS_ORDER):
        n = _norm(name)
        if n in words or (" " in n and n in t):
            return i * 10 + 5
    for i, name in enumerate(ADMIN_ORDER):
        n = _norm(name)
        if n in words or (" " in n and n in t):
            return 1000 + i * 10 + 5
    return UNKNOWN_RANK
