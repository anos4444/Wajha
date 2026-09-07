"""Icons for modules: an emoji the administrator typed, or a Font Awesome
Free glyph named ``fa:<name>``.

The glyphs are shipped as inline SVG path data (``icons_data.GLYPHS``),
not as a web font: nothing to download from a CDN, nothing to break on a
closed network, and the glyph takes the tile's colour through
``currentColor``. Only the glyphs a response actually uses travel with
it — ``table()`` picks them out — so a page never pays for the whole set.

A DocType with no icon of its own gets one from ``DOCTYPE_ICONS`` or,
failing that, from the first keyword of its name that ``KEYWORDS`` knows.
"""

from wajha.icons_data import GLYPHS

PREFIX = "fa:"
DEFAULT = "file-lines"

DOCTYPE_ICONS = {
    # Accounts
    "Account": "book-open", "Accounting Dimension": "layer-group", "Accounting Period": "calendar",
    "Bank": "building-columns", "Bank Account": "building-columns", "Bank Transaction": "right-left",
    "Bank Reconciliation Tool": "scale-balanced", "Budget": "chart-pie", "Cost Center": "sitemap",
    "Cost Center Allocation": "sitemap", "Currency": "coins", "Currency Exchange": "arrow-right-arrow-left",
    "Exchange Rate Revaluation": "arrows-rotate", "Finance Book": "book", "Fiscal Year": "calendar",
    "Journal Entry": "book", "Monthly Distribution": "calendar-days", "Mode of Payment": "credit-card",
    "Payment Entry": "money-bill-transfer", "Payment Order": "paper-plane", "Payment Request": "hand-holding-dollar",
    "Payment Terms Template": "file-contract", "Period Closing Voucher": "calendar-check",
    "Purchase Invoice": "file-invoice", "Sales Invoice": "file-invoice-dollar", "Share Transfer": "share-nodes",
    "Shareholder": "people-group", "Subscription": "repeat", "Subscription Plan": "clipboard-list",
    "POS Invoice": "cash-register", "POS Profile": "cash-register", "POS Opening Entry": "cash-register",
    "POS Closing Entry": "cash-register", "Pricing Rule": "tags", "Price List": "tag", "Item Price": "tag",
    "Loyalty Program": "star", "Dunning": "triangle-exclamation", "Cheque Print Template": "print",
    "Process Statement Of Accounts": "file-lines", "Opening Invoice Creation Tool": "file-circle-check",
    "Loan": "hand-holding-dollar", "Loan Application": "file-signature",
    # Selling, buying, CRM
    "Customer": "user-tie", "Customer Group": "users", "Supplier": "truck", "Supplier Group": "users",
    "Quotation": "file-signature", "Sales Order": "cart-shopping", "Purchase Order": "bag-shopping",
    "Supplier Quotation": "file-contract", "Request for Quotation": "comments", "Material Request": "clipboard-list",
    "Sales Partner": "handshake", "Sales Person": "user", "Territory": "map", "Lead": "user-plus",
    "Opportunity": "star", "Campaign": "bullhorn", "Prospect": "user-plus", "Contact": "address-book",
    "Address": "location-dot", "Contract": "file-contract", "Appointment": "calendar-check",
    "Installation Note": "screwdriver-wrench", "Blanket Order": "file-lines", "Product Bundle": "boxes-stacked",
    "Terms and Conditions": "file-contract", "Company": "building",
    # Stock, assets
    "Item": "cube", "Item Group": "cubes", "Brand": "tag", "Warehouse": "warehouse", "Stock Entry": "dolly",
    "Delivery Note": "truck-fast", "Purchase Receipt": "box-open", "Stock Reconciliation": "scale-balanced",
    "Batch": "barcode", "Serial No": "qrcode", "Landed Cost Voucher": "truck", "Pick List": "list-check",
    "Packing Slip": "box", "Shipment": "truck", "Quality Inspection": "clipboard-check", "Delivery Trip": "car",
    "Stock Ledger Entry": "book", "Bin": "box", "UOM": "ruler", "Item Attribute": "sliders",
    "Putaway Rule": "warehouse", "Asset": "boxes-stacked", "Asset Category": "layer-group",
    "Asset Movement": "dolly", "Asset Repair": "screwdriver-wrench", "Asset Maintenance": "wrench",
    "Asset Depreciation Schedule": "chart-line", "Asset Value Adjustment": "sliders",
    "Asset Capitalization": "money-bills", "Location": "location-dot",
    # Manufacturing, projects, support, quality
    "BOM": "sitemap", "Work Order": "industry", "Job Card": "clipboard-list", "Production Plan": "calendar-days",
    "Workstation": "gears", "Operation": "gear", "Routing": "diagram-project", "Downtime Entry": "triangle-exclamation",
    "Subcontracting Order": "handshake", "Subcontracting Receipt": "box-open",
    "Project": "diagram-project", "Task": "list-check", "Timesheet": "stopwatch", "Project Type": "layer-group",
    "Activity Type": "clock", "Project Template": "file-lines", "Project Update": "comment",
    "Issue": "triangle-exclamation", "Warranty Claim": "shield-halved", "Service Level Agreement": "file-contract",
    "Quality Goal": "trophy", "Quality Procedure": "clipboard-list", "Quality Review": "clipboard-check",
    "Quality Action": "bolt", "Quality Feedback": "comment", "Non Conformance": "triangle-exclamation",
    "Quality Meeting": "users",
    # HR and payroll
    "Employee": "user", "Department": "sitemap", "Designation": "id-badge", "Branch": "building",
    "Employment Type": "briefcase", "Employee Grade": "ranking-star", "Employee Group": "users",
    "Leave Application": "calendar-minus", "Leave Type": "tags", "Leave Allocation": "calendar-plus",
    "Leave Period": "calendar", "Leave Policy": "file-contract", "Leave Policy Assignment": "file-signature",
    "Holiday List": "umbrella-beach", "Compensatory Leave Request": "calendar-plus", "Leave Encashment": "money-bill-wave",
    "Attendance": "calendar-check", "Attendance Request": "calendar-check", "Employee Checkin": "clock",
    "Shift Type": "clock", "Shift Assignment": "calendar-days", "Shift Request": "calendar-plus",
    "Employee Attendance Tool": "list-check", "Upload Attendance": "upload", "Expense Claim": "receipt",
    "Expense Claim Type": "tags", "Employee Advance": "hand-holding-dollar", "Travel Request": "plane",
    "Vehicle": "car", "Vehicle Log": "car", "Salary Slip": "money-check-dollar", "Salary Structure": "sitemap",
    "Salary Structure Assignment": "file-signature", "Salary Component": "coins", "Payroll Entry": "money-bills",
    "Additional Salary": "money-bill-wave", "Employee Incentive": "award", "Retention Bonus": "medal",
    "Employee Benefit Application": "heart", "Employee Benefit Claim": "receipt",
    "Employee Tax Exemption Declaration": "percent", "Income Tax Slab": "percent", "Payroll Period": "calendar",
    "Job Opening": "briefcase", "Job Applicant": "user-plus", "Job Offer": "file-signature", "Interview": "comments",
    "Interview Round": "list", "Interview Type": "tags", "Interview Feedback": "comment",
    "Appointment Letter": "file-lines", "Staffing Plan": "chart-bar", "Employee Onboarding": "person-walking",
    "Employee Separation": "person-walking", "Employee Promotion": "ranking-star", "Employee Transfer": "right-left",
    "Employee Grievance": "triangle-exclamation", "Training Event": "person-chalkboard",
    "Training Program": "graduation-cap", "Training Result": "award", "Training Feedback": "comment",
    "Appraisal": "star", "Appraisal Cycle": "calendar", "Appraisal Template": "file-lines", "Goal": "trophy",
    "Employee Skill Map": "graduation-cap", "Skill": "star", "Exit Interview": "comments",
    "Full and Final Statement": "file-invoice-dollar", "Gratuity": "sack-dollar", "Daily Work Summary": "newspaper",
    "Employee Referral": "user-plus",
    # Frappe
    "User": "user", "Role": "shield-halved", "Role Profile": "shield-halved", "Module Profile": "layer-group",
    "User Permission": "key", "Print Format": "print", "Letter Head": "file-lines", "Email Account": "envelope",
    "Email Template": "envelope", "Notification": "bell", "Newsletter": "newspaper", "Communication": "comments",
    "ToDo": "list-check", "Event": "calendar", "Note": "pen-to-square", "File": "paperclip", "Report": "chart-bar",
    "Dashboard": "chart-simple", "Dashboard Chart": "chart-line", "Number Card": "chart-simple",
    "Workflow": "diagram-project", "Webhook": "link", "Integration Request": "server", "Data Import": "upload",
    "Data Export": "download", "Web Page": "globe", "Web Form": "file-pen", "Blog Post": "newspaper",
    "Translation": "language", "Language": "language", "Country": "globe", "Naming Series": "barcode",
    "Auto Repeat": "repeat", "Assignment Rule": "user-gear", "Scheduled Job Type": "clock",
    "Error Log": "triangle-exclamation", "Activity Log": "list", "Access Log": "key", "Package": "box",
    "Shell Module": "sliders", "Shell Theme": "sliders", "Shell Settings": "gear",
}

# First keyword found in the DocType name wins; order matters.
KEYWORDS = [
    ("settings", "gear"), ("invoice", "file-invoice"), ("payment", "money-bill-transfer"),
    ("salary", "money-check-dollar"), ("payroll", "money-check-dollar"), ("tax", "percent"),
    ("leave", "calendar-minus"), ("attendance", "calendar-check"), ("shift", "clock"), ("holiday", "umbrella-beach"),
    ("employee", "user"), ("customer", "user-tie"), ("supplier", "truck"), ("item", "cube"),
    ("warehouse", "warehouse"), ("stock", "warehouse"), ("asset", "boxes-stacked"), ("project", "diagram-project"),
    ("task", "list-check"), ("quality", "clipboard-check"), ("bank", "building-columns"), ("currency", "coins"),
    ("budget", "chart-pie"), ("report", "chart-bar"), ("dashboard", "chart-simple"), ("template", "file-lines"),
    ("training", "graduation-cap"), ("interview", "comments"), ("job", "briefcase"), ("loan", "hand-holding-dollar"),
    ("advance", "hand-holding-dollar"), ("expense", "receipt"), ("vehicle", "car"), ("travel", "plane"),
    ("website", "globe"), ("web ", "globe"), ("letter", "file-lines"), ("contract", "file-contract"),
    ("agreement", "file-contract"), ("address", "location-dot"), ("location", "location-dot"),
    ("contact", "address-book"), ("email", "envelope"), ("mail", "envelope"), ("print", "print"),
    ("user", "user"), ("role", "shield-halved"), ("permission", "key"), ("category", "tags"), ("type", "tags"),
    ("group", "tags"), ("rule", "sliders"), ("request", "paper-plane"), ("order", "cart-shopping"),
    ("entry", "pen-to-square"), ("log", "list"), ("tool", "screwdriver-wrench"), ("period", "calendar"),
    ("year", "calendar"), ("calendar", "calendar"), ("plan", "clipboard-list"), ("script", "code"),
]


def icon_for(doctype):
    """``fa:<name>`` for a DocType that has no icon of its own."""
    if not doctype:
        return PREFIX + DEFAULT
    name = DOCTYPE_ICONS.get(doctype)
    if not name:
        low = doctype.lower()
        for word, candidate in KEYWORDS:
            if word in low:
                name = candidate
                break
    return PREFIX + (name if name in GLYPHS else DEFAULT)


def normalize(spec, doctype=None):
    """What the client should draw: the emoji as typed, a known ``fa:``
    name as typed, an unknown one as the default glyph, nothing as the
    DocType's own icon."""
    spec = (spec or "").strip()
    if not spec:
        return icon_for(doctype)
    if spec.startswith(PREFIX):
        return spec if spec[len(PREFIX):] in GLYPHS else PREFIX + DEFAULT
    return spec


def attach(module):
    """Fill ``module["icon"]`` in place (a dict from get_all or a summary)."""
    module["icon"] = normalize(module.get("icon"), module.get("ref_doctype"))
    return module


def table(specs):
    """Path data for the ``fa:`` names among ``specs``, keyed by name."""
    out = {}
    for spec in specs:
        if spec and spec.startswith(PREFIX):
            name = spec[len(PREFIX):]
            if name in GLYPHS:
                out[name] = list(GLYPHS[name])
    return out


def names():
    """Every glyph name, for the Shell Module icon picker."""
    return sorted(GLYPHS)
