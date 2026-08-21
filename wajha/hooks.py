import hashlib
import os

app_name = "wajha"
app_title = "Wajha"
app_publisher = "AAA Consulting"
app_description = "واجهة — قشرة عربية قابلة للتهيئة وطبقة سمات لـ Frappe/ERPNext"
app_email = "a.abdulla@aaacons.com"
app_license = "MIT"

_PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")


def _versioned(url: str) -> str:
    """Append a short content hash to an asset URL: /assets/…/x.css?v=<hash>.

    /assets/* is served with far-future caching, so a bare path leaves browsers
    on the CSS/JS they downloaded before the update -- with no error anywhere,
    just a shell that looks half-deployed until someone hard-reloads.

    Hashed rather than a hand-bumped counter (which is only as reliable as
    remembering to bump it) or an mtime (which differs per machine, so a
    rebuilt-but-identical file reads as new and needlessly busts the cache).
    Unreadable file -> the bare path, because an asset that loads from cache is
    a far better failure than an asset that 404s.

    Read once per worker at import; the value is then frozen into the cached
    hooks, so a deploy still needs its usual `bench clear-cache` to be seen.
    """
    try:
        with open(os.path.join(_PUBLIC, *url.split("/assets/wajha/")[-1].split("/")), "rb") as f:
            return f"{url}?v={hashlib.md5(f.read()).hexdigest()[:10]}"
    except OSError:
        return url


# Plain CSS/JS — no bundler, so the app installs on any v16 bench without Node.
app_include_css = _versioned("/assets/wajha/css/wajha.css")
app_include_js = _versioned("/assets/wajha/js/wajha_boot.js")
web_include_css = _versioned("/assets/wajha/css/wajha.css")

# Ship the resolved shell config in Frappe's boot payload so the first paint
# needs no extra request. wajha_boot.js still falls back to the HTTP call.
boot_session = "wajha.boot.add_boot_data"

after_install = "wajha.install.after_install"
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
