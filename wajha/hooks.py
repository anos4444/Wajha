app_name = "wajha"
app_title = "Wajha"
app_publisher = "AAA Consulting"
app_description = "واجهة — قشرة عربية قابلة للتهيئة وطبقة سمات لـ Frappe/ERPNext"
app_email = "a.abdulla@aaacons.com"
app_license = "MIT"

# Plain CSS/JS — no bundler, so the app installs on any v16 bench without Node.
app_include_css = "/assets/wajha/css/wajha.css"
app_include_js = "/assets/wajha/js/wajha_boot.js"
web_include_css = "/assets/wajha/css/wajha.css"

# Ship the resolved shell config in Frappe's boot payload so the first paint
# needs no extra request. wajha_boot.js still falls back to the HTTP call.
boot_session = "wajha.boot.add_boot_data"

after_migrate = ["wajha.install.after_migrate"]

add_to_apps_screen = [
    {
        "name": "wajha",
        "logo": "/assets/wajha/images/wajha.svg",
        "title": "Wajha",
        "route": "/app/wajha",
        "has_permission": "wajha.api.has_app_permission",
    }
]
