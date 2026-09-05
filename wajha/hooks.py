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
#
# The swift-* files are the Swift Theme module (ported from
# its-alikhokher/swift_theme, MIT). Upstream shipped them as .bundle.scss /
# .bundle.js import lists purely for cache busting; here each file is listed
# individually and _versioned() provides the hash, keeping the no-Node rule.
# ORDER IS LOAD-BEARING: it reproduces the upstream bundle order — several of
# these stylesheets deliberately settle cascade ties by coming later, and
# swift-boot.js must run first among the scripts because it writes the theme
# attributes onto <html> before Frappe paints.
app_include_css = [
    _versioned("/assets/wajha/css/wajha.css"),
    _versioned("/assets/wajha/css/swift-fonts.css"),
    _versioned("/assets/wajha/css/swift-base.css"),
    _versioned("/assets/wajha/css/swift-preset-base.css"),
    _versioned("/assets/wajha/css/swift-backdrops.css"),
    _versioned("/assets/wajha/css/swift-layout.css"),
    _versioned("/assets/wajha/css/swift-density.css"),
    _versioned("/assets/wajha/css/swift-desk.css"),
    _versioned("/assets/wajha/css/swift-sidebar.css"),
    _versioned("/assets/wajha/css/swift-home.css"),
    _versioned("/assets/wajha/css/swift-preset-accents.css"),
    _versioned("/assets/wajha/css/swift-glass.css"),
    _versioned("/assets/wajha/css/swift-scrollbar.css"),
    _versioned("/assets/wajha/css/swift-toast.css"),
    _versioned("/assets/wajha/css/swift-perf.css"),
]
app_include_js = [
    _versioned("/assets/wajha/js/wajha_boot.js"),
    _versioned("/assets/wajha/js/swift-boot.js"),
    _versioned("/assets/wajha/js/swift-mode-observer.js"),
    _versioned("/assets/wajha/js/swift-theme-dialog.js"),
    _versioned("/assets/wajha/js/swift-palette.js"),
    _versioned("/assets/wajha/js/swift-sidebar.js"),
    _versioned("/assets/wajha/js/swift-focus.js"),
    _versioned("/assets/wajha/js/swift-perf.js"),
    _versioned("/assets/wajha/js/swift-sounds.js"),
]
web_include_css = [
    _versioned("/assets/wajha/css/wajha.css"),
    _versioned("/assets/wajha/css/swift-fonts.css"),
    _versioned("/assets/wajha/css/swift-base.css"),
    _versioned("/assets/wajha/css/swift-preset-base.css"),
    _versioned("/assets/wajha/css/swift-backdrops.css"),
    _versioned("/assets/wajha/css/swift-glass.css"),
    _versioned("/assets/wajha/css/swift-website.css"),
    _versioned("/assets/wajha/css/swift-login.css"),
    _versioned("/assets/wajha/css/swift-scrollbar.css"),
]
web_include_js = [
    _versioned("/assets/wajha/js/swift-boot.js"),
    _versioned("/assets/wajha/js/swift-website.js"),
]

# The Swift theme fields this app adds to User are only editable when the
# server would accept a change; the script keeps the form honest about that.
doctype_js = {"User": "public/js/user_form.js"}

# Ship the resolved shell config in Frappe's boot payload so the first paint
# needs no extra request. wajha_boot.js still falls back to the HTTP call.
boot_session = "wajha.boot.add_boot_data"

# Swift Theme preferences ride in bootinfo too, under their own key
# (frappe.boot.swift_theme). extend_bootinfo alone is enough; also registering
# boot_session for it would compute the same preferences twice per desk load.
extend_bootinfo = "wajha.swift.boot.extend_bootinfo"

after_install = [
    "wajha.install.after_install",
    "wajha.swift.install.after_install",
    "wajha.packs.hrms.seed",
    "wajha.packs.apps.seed",
]
after_migrate = [
    "wajha.install.after_migrate",
    "wajha.swift.install.after_migrate",
    "wajha.packs.hrms.seed",
    "wajha.packs.apps.seed",
]
# Fires in every installed app when another app is installed on the site:
# HRMS arriving after Wajha still gets its self-service modules.
after_app_install = ["wajha.packs.hrms.seed", "wajha.packs.apps.seed"]

add_to_apps_screen = [
    {
        "name": "wajha",
        "logo": "/assets/wajha/images/wajha.svg",
        "title": "Wajha",
        "route": "/app/wajha",
        "has_permission": "wajha.api.has_app_permission",
    }
]
