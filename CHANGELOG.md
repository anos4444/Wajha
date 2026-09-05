# Changelog

## 0.15.0 — 2026-09-05

**Every app's modules exist as records by default.** A fresh install had no
Shell Module records beyond the HRMS self-service pack; the other apps were
reachable only through the discovered Home tiles. The new **all-apps pack**
(`wajha/packs/apps.py`) creates a Shell Module record for every DocType the
installed apps' workspaces link to — columns, filters and search from the
DocType's list view, grouped by workspace, labelled in the site's language —
on install, on migrate and whenever an app is installed later (Frappe 16's
`after_app_install`). Switched by the new Shell Settings `seed_modules`
(default on). Rules as before: create only what is missing, never overwrite,
skip DocTypes that already have an All-scope module. Pack seeding does not
queue filter-index jobs (a fresh install must not ALTER live tables).

- **Sidebar** copes with hundreds of modules: a filter box, and collapsible
  workspace groups — hand-made groups open, pack groups closed until asked
  and remembered per browser; the active module's group opens itself.
- Quick access on Home and the bottom bar prefer flagged or hand-made
  modules over pack-seeded ones.

## 0.14.1 — 2026-09-05

**Headings were nearly invisible on the hub.** The shell's page title,
greeting, group and card headings inherited the Desk's `--heading-color`,
which a Desk-wide theme can set to a near-white; seen in real phone
screenshots on hub.tawasulcloud.com. Every shell heading now carries an
explicit ink colour from the theme tokens.

## 0.14.0 — 2026-09-05

**Home: the apps grid, discovered from Frappe, adapting to whatever is
installed.** The shell now lands on a Home page: a greeting, the hand-made
modules as quick access, and one tile per app or workspace this user may
open — taken from Frappe 16's own Desktop Icons (the cards the Desk home
shows: folders with a count, workspaces, app links), or from the public
Workspaces on a Desk without them. A tile opens the workspace's DocTypes in
its own card sections; each DocType is a **virtual module** (`~doctype`)
built on the fly from its list view, exactly as the scaffold would build a
Shell Module record, with the record card, actions and forms — nothing is
written, and a hand-made module for the same DocType takes precedence.
Install an app and its tiles and modules appear on the next load; nobody
creates records.

- Shell Settings: `landing` (Home / Default module) and `auto_modules`
  (default on). Home is also at `wajha/home`; groups at `wajha/@…`.
- Sidebar and bottom bar gain a Home entry.
- Permission: Desktop Icon roles and app permission are honoured; a
  workspace shows only DocTypes the user may read; a virtual module is
  resolved server-side and permission-checked like a saved one.
- Drawer: narrower (82vw, max 300px) so the tap-outside strip is real.

## 0.13.1 — 2026-09-05

**The HRMS pack did not seed on the hub.** Shell Module Action's `value`
was mandatory, the pack's salary-slip Print action has none (blank = the
default print format), and the resulting MandatoryError aborted the whole
seeding step in `after_migrate` — zero self-service modules. `value` is now
optional for Print only (validate() still requires it for every other
type), and each pack module is seeded on its own with a logged skip, so
one bad definition can never block the rest. The form's fallback field
list also skips mandatory fields the DocType already fills (series,
posting date, default status).

## 0.13.0 — 2026-09-05

**Employee self-service, complete, without Frappe's form.**

- **HRMS pack** (`wajha/packs/hrms.py`). When HRMS is on the site, twelve
  "mine" modules are seeded — my leave, check in / out, my salary slips,
  my expense claims, my attendance, attendance requests, compensatory
  leave, advances, travel, shift requests, my shifts, my profile — each
  scoped to the Employee behind the login (my profile by `user_id`), with
  list columns, an in-shell form, a card field list and actions. Seeded on
  install, on migrate and on `after_app_install` (HRMS arriving later still
  gets them). Idempotent: existing modules keep every admin edit; only
  blanks are filled.
- **In-shell New form** (`wajha.records.get_form` / `create_record`). The
  fields the module names in `form_fields` (or the DocType's mandatory
  ones), the DocType's own defaults, Link fields with live suggestions from
  Frappe's link search, child-table rows, Save and Save & Submit. The scope
  field is written by the server after the request's values, so a request
  cannot be filed for someone else. Validation is the DocType's own.
  Phones get a full-screen form; the empty list offers a New button.
- **Module-level actions.** Shell Module Action gains `level` (Record /
  Module) and two types: **Create** (a JSON template with `{employee}`,
  `{user}`, `{now}`, `{today}`, `{lat}`, `{lon}`; `"__submit": 1` submits)
  and **Print** (opens the PDF through Frappe's own download endpoint, which
  re-checks the permission). Check in / check out are Create actions above
  the check-ins list, sending the device location when it is granted.
- **Drawer.** A ✕ button in the drawer header and swipe-towards-the-edge
  close it; the drawer and the record panel now follow the shell's own
  direction rather than the document's, so an English-language Desk no
  longer opens the drawer on the opposite side from the desktop sidebar.

## 0.12.1 — 2026-09-05

**0.12.0 rendered an empty shell on Frappe 16 — phones and desktops alike.**
`render_tabbar` called `frappe.utils.cint`, which does not exist (Frappe
ships `cint`/`flt` as bare globals), so the page script threw halfway
through `render_shell`: the sidebar was on screen, the body never was.
The local Playwright harness missed it because its Frappe shim *defined*
`frappe.utils.cint`. The script now uses its own `wj_int`/`wj_num`
helpers, and the harness shim exposes only what Frappe really has — run
against the 0.12.0 script it now reproduces the hub error exactly.

Also: Frappe 16 serves the Desk at `/desk` (and 301s `/app` there), so the
manifest's `start_url`/`scope`, the record card's Desk link and the
Route action / Route Link prefix stripping now follow the running version.

## 0.12.0 — 2026-09-05

**The shell on a phone is a product, not the desktop squeezed.** Until now a
390px screen got the same six-column table in a horizontal scroller, a stack
of filter inputs above the first record, a six-control pager, and a tap that
handed the user to Frappe's form. Every part of that is replaced:

- **Cards below 700px.** One record per full-width row: the first column as
  the title, the next two as a one-line subtitle, the status chip, a
  chevron. No horizontal scroll. The card fields come from the columns the
  module already orders, so nobody maintains a second list for phones.
- **Search stays; filters move into a bottom sheet** behind one button
  carrying the count of active filters, with removable chips under the
  search box. Inputs are 16px on phones so iOS stops zooming on focus.
- **The list grows as you scroll** (an IntersectionObserver on a sentinel)
  with a Load More fallback; the 20/100/500 and Previous/Next controls are
  desktop-only.
- **A bottom bar** of up to four modules (flag them with the new
  `show_in_mobile_bar`, else the first four) plus More for the drawer —
  thumb reach instead of a burger at the top of the screen.
- **A record card inside the shell** (`wajha.records.get_record`), on
  desktop too: a side panel at the inline end, full screen on phones. It
  shows only the fields that hold a value, grouped by the form's own
  sections (or the module's `detail_fields` list), child tables, attachments
  and comments, with an actions bar pinned at the bottom. "Open in Frappe"
  remains as the escape hatch, never the default.
- **Actions from the card.** Automatic: the workflow transitions Frappe says
  this user may take (`frappe.model.workflow.get_transitions`), or Submit /
  Cancel where there is no workflow. Configured: a new Actions table on
  Shell Module — Set Value, a whitelisted Server Method, or a Route.
  Every action re-checks Frappe's permission on the server; Set Value also
  checks the field's permlevel and Server Method refuses anything not
  whitelisted. The list patches the row's status in place afterwards.
- **Mine modules.** `scope` on Shell Module: All, Mine (Owner), Mine (User
  Field) or Mine (Employee Field) with `scope_field`. A Mine module adds
  the user's own identity to every query server-side before saved filters
  are read; opening someone else's record by name answers exactly like a
  missing record; New starts inside the scope (the employee's own leave).
  A user with no Employee record sees nothing, not everyone.
- **Routes.** `/app/wajha/<module_key>` and `/app/wajha/<module_key>/<name>`
  — the record card is a route so the phone's back gesture closes the card
  rather than leaving the app.
- **Install as the client's app.** On the shell route the page advertises a
  web-app manifest generated from Shell Settings (`wajha.api.manifest`: name,
  logo, theme and background colours, standalone display, RTL) and sets
  `theme-color`, so Add to Home Screen installs *their* system.

## 0.11.0 — 2026-09-05

**Paging works exactly like ERPNext's list view.** 0.8.0 added a rows-per-page
dropdown (20/50/100/200) and Previous/Next; the ask was ERPNext's model. The
pager now carries ERPNext's own **20 / 100 / 500** page-size buttons and a
**Load More** that appends the next page under the rows already on screen
(the count then reads from row 1), alongside Previous/Next for jumping.
`MAX_PAGE_LENGTH` rises from 200 to 500 to match ERPNext's largest page —
still a hard server-side ceiling. Clear now also returns to page 1.

## 0.10.1 — 2026-09-05

**The 0.10.0 seeding probe crashed `after_migrate`.** `never_stored()` read
the `tabSingles` row through `frappe.db.get_value("Singles", {...})`, which
appends its default `ORDER BY creation` — and `tabSingles` has no `creation`
column. On v16 that raised `(1054, "Unknown column 'creation' in 'ORDER BY'")`
from inside the migrate hook on hub.tawasulcloud.com (existing rows were
untouched; only the seeding step died). Both seeders now read the row with a
plain `select … limit 1`, which cannot be reordered.

## 0.10.0 — 2026-09-05

**A themed Desk out of the box.** A fresh install already enabled the shell,
picked the first preset and applied the font Desk-wide — but
`apply_theme_globally` had no default, so a new site's forms, lists and
dialogs stayed on Frappe's stock palette until someone found the switch.
It now defaults on: install Wajha and the whole Desk carries the active
theme; turn it off in Shell Settings to keep the colours inside the shell.

The seeding also stops depending on the DocType defaults, which only reach a
site with no Settings row at all. Every switch a fresh install should carry
(`enabled`, `apply_font_globally`, `apply_theme_globally`,
`hide_desk_sidebar`, `show_clock`, `show_user_chip`, `show_desk_link`) is now
seeded through one loop that reads the stored row — never set → the
default, an explicit 0 stays — so a site upgraded from an earlier release
gets the same out-of-the-box state without overriding anyone's choice.

The "never set" probe itself was wrong until now. 0.7.1 and 0.9.0 used
`frappe.db.get_single_value(dt, field) is None`, but on v16 that call casts a
missing Check to 0 — seen on hub.tawasulcloud.com, where `show_desk_link` had
no `tabSingles` row and the probe still said 0, so the seed took it for
"turned off" and the new Desk link stayed hidden (and the 0.7.1 Swift switch
guard had never actually fired). Both seeds now read the raw `tabSingles`
row (`never_stored()`), which is the only place the two cases differ.

## 0.9.0 — 2026-09-05

**A way back to the rest of the Desk.** The shell hides Frappe's own sidebar
and its app switcher on its route (by design), which left an admin with no
visible route to any other app — only a Route Link someone had happened to
configure, or a typed URL. The sidebar now ends with a **↩ العودة إلى Frappe
/ Frappe Desk** button that opens the Home workspace, where the full Desk and
its switcher are back. Governed by a new `Shell Settings.show_desk_link`
(on by default; seeded on for existing sites by reading the stored row, so an
unset Check is not mistaken for "off"; an absent field — a site not yet
migrated — also counts as on, because the exit must never vanish by
accident). Turn it off for a deployment that should look closed on the
shell. Bumps the Page `modified` so the new script reaches browsers.

## 0.8.1 — 2026-09-05

**The shell sets its own Desk-chrome marker.** 0.7.2 keyed the chrome-hiding
rules on `body[data-route="wajha"]` as well as `body.wj-route`, and the v16
sidebar went — but the breadcrumb bar (`.page-head`) was still seen on the
shell, which means neither marker was on `<body>` at that moment (v16 puts
every breadcrumb in the page's own `.page-head`, which the rule targets). The
page's `on_page_show` is the one hook guaranteed to run whenever the shell is
on screen, so it now adds `wj-route` itself and hides its own `.page-head`
with Frappe's `.hide`; `on_page_hide` removes the marker so other pages keep
their chrome. Also bumps the Page record's `modified`, which had never moved
since 0.1 — Desk caches the Page script keyed on it, so the 0.8.0 filter and
paging changes could otherwise be served stale.

## 0.8.0 — 2026-09-05

**Filters apply as you type, and paging works like ERPNext's list.** Two
things asked for after the first real session on hub.tawasulcloud.com:

- The free-text Search already filtered as you typed, but the per-field
  filter boxes (Company, Full Name, Branch…) only committed on Enter/blur,
  so typing into one and seeing nothing happen read as broken. Text and Link
  filter inputs now apply on `input`, debounced 350 ms like the search box.
  Link filters match by *contains* server-side instead of the exact document
  name — with an exact match, a list would empty on every keystroke until the
  full name was in. (A list value from a multi-value client still means an
  exact set.)
- The only pager sat *below* a full page of rows, so Previous/Next were out
  of view and the list looked like it stopped at the first page. There is
  now a pager above the table as well as below, kept in step, and both carry
  a **rows per page** choice (20 / 50 / 100 / 200), mirroring ERPNext's list
  view. The choice is a personal browsing preference, so it lives in the
  browser (`localStorage`), not on the module record; the server clamps any
  request at `MAX_PAGE_LENGTH` (200) as before, so a hand-edited request
  still cannot pull a whole table. `get_module_data` gains an optional
  `page_length` argument; the module's own setting remains the default.

## 0.7.2 — 2026-09-04

**Frappe's desk sidebar no longer sits beside the shell on v16.** On
hub.tawasulcloud.com (frappe 16.25) `/app/wajha` showed two navigation
columns: the v16 desk sidebar (app switcher, ⌘K search, workspace items) on
the left and the shell's own on the right, with the breadcrumb bar still on
top. The chrome-hiding rules keyed only on `body.wj-route`, the class our own
`wajha_boot.js` sets, and targeted `.body-sidebar` — but v16 wraps the panel
in `.body-sidebar-container`, whose `.body-sidebar-placeholder` reserves the
220px even when the panel is hidden, and the marker was not in effect on that
load. The rules now also key on `body[data-route="wajha"]`, which Frappe's
own `views/container.js` stamps on every page change (hard load included), so
they hold without depending on our script having run; they hide the whole
container and `.page-head`. v15 selectors are kept.

## 0.7.1 — 2026-09-04

**Upgrading to 0.7.0 no longer switches Swift Theme off.** The new `enabled`
field was seeded by the same "fill what is still None/empty" loop as every
other default — but Frappe initialises an unset Check to 0 when a document
loads, so a site that had never stored the field read exactly like one that
had turned the theme off, and the loop left it at 0. Seen on the first upgrade
of hub.tawasulcloud.com (`enabled before: 0`); that site was being switched
off deliberately, so nothing was lost there, but any other site would have
come up unthemed until someone ticked the box. The seed now reads the stored
row directly (`get_single_value`, None when absent) for this one field, so
"never set" is seeded on while an explicit 0 is respected.

## 0.7.0 — 2026-09-04

**A master switch for the Swift Theme module.** Upstream never had one:
`swift-boot.js` paints whenever a preset *or* a custom colour exists, and it
keeps a last-known-good copy in localStorage that it repaints before the boot
payload arrives — so a site had no way to see the plain Frappe Desk (or the
Wajha Shell on its own) again short of uninstalling. Needed the moment both
layers were live on the same site and someone asked to see "Wajha only".

`Swift Theme Settings` gains **Enable Swift Theme** (on by default; the
seeding backfills it, and an absent value counts as on so a half-migrated
site is never switched off by accident). Off means:

- `get_effective_prefs()` returns a *disabling* payload, not an empty one —
  blank colour identifiers, every feature flag at 0, no presets, no sounds, no
  landing. The desk's `applyAll` then removes the preset stylesheet and
  `data-swift-themed`, strips every `data-swift-*` attribute, and blanks the
  stored copies. The bootstrap that runs before `frappe.boot` honours an
  explicit `enabled: 0` over the cache for the same reason, so the theme
  cannot flash back for one paint on the first disabled load.
- The Switch Theme dialog shows Frappe's own three cards only.
- The desk landing hands back whatever home page the site had before
  (`_apply_home_page` now reacts to the switch as well as to
  *Enable Home Page*, and restores when either turns it off).
- `/login` renders as stock Frappe: same markup (it *is* Frappe's template,
  wrapped), none of the Swift classes or inline variables.

Per-user picks (`swift_preset` etc.) are left in place, so turning the switch
back on returns everyone to where they were. Contract suite: +7 checks
including two negative controls (an absent switch still paints the cache;
`enabled: 1` paints the server preset), 65/65 passing.

## 0.6.1 — 2026-09-04

**Swift Theme Settings now seeds on the first migrate.** On a first install
where one `bench migrate` both creates the `Swift Theme Settings` DocType and
runs `wajha.swift.install.after_migrate`, the doctype's meta could still be the
empty pre-creation copy cached earlier in the same request. `_seed_settings`
gates every default on `settings.meta.has_field(...)`, so with a stale meta it
skipped all of them, marked nothing changed, and never saved — the single came
up blank (no `active_preset`, switcher off, login layout unset) until a second
migrate happened to run with a warm meta. Found deploying 0.6.0 onto the
hub.tawasulcloud.com bench: the Shell presets seeded but Swift Theme Settings
stayed empty until seeded by hand. `_seed_settings` now drops the doctype's
cached meta (`frappe.clear_cache(doctype="Swift Theme Settings")`) before
reading the single, so the `has_field` guards see the fields migrate just
synced. Idempotent; no effect on a site whose settings are already populated.

## 0.6.0 — 2026-09-04

**The whole of Swift Theme, as a module of Wajha.** Ported from
[its-alikhokher/swift_theme](https://github.com/its-alikhokher/swift_theme)
(MIT; attribution in `license.txt`) under a new `Swift Theme` Frappe module,
alongside — not replacing — Wajha's own Shell system. Everything the upstream
app does now installs with Wajha:

- **Twelve colour presets** (six light, six dark), each a hand-tuned role
  palette with its own backdrop, offered inside Frappe's own Switch Theme
  dialog per user, plus **Custom Colors**: a primary/secondary pair expanded
  into a full palette by the shared `derive_roles` maths (Python and JS copies
  kept in step by a parity test).
- **Server-rendered themed login page** in three layouts (Split, Centered,
  Minimal), with every word on the brand panel editable from Settings.
- **Optional desk landing page** (`swift-home`, eight designs) built on
  `frappe.boot.desktop_icons` and Number Cards, so permissions narrow it with
  nothing re-implemented.
- **Density, shape, font scale and family per user; navbar/sidebar variants,
  glass, styled scrollbar, toast and print theming, focus mode, Alt+B sidebar
  toggle, per-event desk sounds** — each behind its own switch in the new
  `Swift Theme Settings` single.

Mechanics of the port, where it deliberately differs from upstream:

- Upstream's `.bundle.scss`/`.bundle.js` files existed only for cache busting
  and would have put Node back into the install path. The files are instead
  listed individually in `hooks.py`, in the exact bundle order (which is
  load-bearing), each through the existing `_versioned()` content hash — the
  same cache-busting result with no build step.
- Python packages land as `wajha.swift` (boot/home/colour/install — upstream's
  `api/` name collides with `wajha/api.py`) and `wajha.swift_theme` (the
  doctypes and the `swift-home` page). Whitelisted method paths change
  accordingly (`wajha.swift.boot.*`, `wajha.swift.home.*`); the bootinfo key
  (`frappe.boot.swift_theme`), the realtime event (`swift_theme_updated`) and
  the localStorage keys are unchanged, so the ported JS needed only the
  method-path and `/assets/wajha/` rewrites.
- Upstream's `patches/v1_0/*` migrate *old swift_theme installs* and are not
  ported: on a Wajha site the module arrives fresh, and the idempotent
  install/migrate seeding (`wajha.swift.install`) produces the end state those
  patches converge on.
- Upstream's 3.7k-line bench integration suite is not ported yet (it asserts
  the bundle structure this port replaces); the two Node-run contract suites
  are, live under `wajha/tests/`, and pass against the ported files.

## 0.5.0 — 2026-08-21

Closes the two remaining first-paint and stale-asset gaps, both borrowed from
Solvronix-Desk and independently confirmed by Aurora's appearance layer.

**Flash-free theming without the boot payload.** 0.4.2 made the first paint
themed *when the boot payload carried the config*. It does not always: a boot
that failed soft, a Guest session, or any page where `wajha_boot.js` is
evaluated before `frappe.boot` is assigned all fall through to the HTTP call,
which lands after first paint — a visible flash of unthemed Desk on every one
of those loads. `wajha_boot.js` now keeps a last-known-good copy of the tokens
in `localStorage` and applies it synchronously at the top of the IIFE, above
the `typeof frappe` guard, so it does not depend on frappe existing yet. The
authoritative config still overwrites it further down the same script, so a
stale copy survives at most the span between two synchronous statements.

The cached copy is stamped with the `user_id` cookie and ignored when that
cookie no longer matches, so a shared browser never paints the previous user's
theme. When the authoritative config comes back disabled, the applied
properties are removed and the cache dropped — otherwise a shell that had been
turned off would keep repainting its old colours on every load. On the shell
route only, `<html>`'s background is stamped from `page_bg`, covering the gap
before `.wj-shell` exists in the DOM; it is deliberately not stamped on other
Desk pages, since this script loads on all of them.

Verified by running the real shipped file under JavaScriptCore in a stubbed
browser: 26 checks including negative controls for cache-absent (nothing
paints early), a cache belonging to a different user (nothing paints),
`localStorage` throwing as it does in private mode (no exception escapes), and
a non-shell route (tokens still published, background *not* stamped). The
0.4.1 null-`current_route` crash is covered in the same suite against a
faithful copy of core's unguarded `get_route_str`. As a control the previous
file was run through the identical harness: it fails exactly the 8 checks that
describe the new behaviour and passes the other 18.

**Whole-Desk theming that actually reaches the Desk.** `apply_theme_globally`
mapped seven of Frappe's custom properties, which left list views, forms,
modals, menus, controls and the awesomebar on core's default palette: turning
it on branded the primary colour and little else. It now re-declares 37
properties, confirmed present on a live Frappe 16.31.0 Desk, so the whole
product follows the active Shell Theme without patching core — the stylesheet
is appended at runtime and therefore lands after frappe's and erpnext's own
bundles, winning on cascade order at equal specificity. Core derives further
variables from `--primary` (`--progress-bar-bg` among them), so the repaint
reaches more surfaces than the list length suggests. `apply_font_globally` now
also publishes `--font-stack` rather than relying only on an `!important`
selector list.

The override is scoped to `:root:not([data-theme="dark"])`. Frappe's dark
palette is declared on `[data-theme="dark"]` at the same specificity, so the
previous unscoped `:root` block overrode it — dark chrome wearing light-mode
inks. Every Shell Theme preset is a light palette, so dark mode is left to
Frappe until Shell Theme can express a dark variant.

Token values are now filtered before interpolation: they are admin-authored
rather than attacker-supplied, but a stray brace or semicolon in one field
would silently kill every rule after it, so anything outside the shape a
colour, length or font stack takes falls back to the default.

Verified on the live odoojo Desk by injecting the generated stylesheet into a
real logged-in session: the primary action button moved from `rgb(23,23,23)`
to `rgb(91,31,51)` and muted text from `#525252` to the theme's `#7A6B70`,
with 7 of 8 watched core variables changing (the eighth, `--card-bg`, was
already white in both). As a negative control the same page was flipped to
`data-theme="dark"` with the stylesheet still installed: none of the overrides
applied, while the *old* seven-property block was observed still bleeding into
dark mode — the bug the new scoping fixes. The tab was restored afterwards and
nothing was changed server-side.

**Hash-versioned asset URLs.** `app_include_css`/`app_include_js`/
`web_include_css` were bare paths under far-future caching, so browsers kept
serving the CSS and JS they downloaded before an update — no error, just a
shell that looks half-deployed until a hard reload. `hooks.py` now appends a
short content hash (`?v=…`). Hashed rather than a hand-bumped counter, which
is only as reliable as remembering to bump it, or an mtime, which differs per
machine so a rebuilt-but-identical file would needlessly bust every cache.
An unreadable file falls back to the bare path. Verified with 8 checks, 4 of
them negative: editing the CSS moves its `?v=` while the untouched JS keeps
its own, and a missing file degrades to the bare path instead of raising.

## 0.4.2 — 2026-08-11

Restores the boot-payload client reader that 0.4.1 accidentally reverted,
and corrects three errors in the newly added `CLAUDE.md`.

The 0.4.1 hotfix was prepared against a stale copy of `wajha_boot.js` that
predated the boot-transport work, so shipping it silently dropped the
`frappe.boot.wajha_config` reader and `wajha.refresh_config()` — the server
kept building the payload on every boot while nothing consumed it, and
`get_config()` fell back to the HTTP round trip the boot transport existed
to remove. This release re-applies the null-route fix to the *current* file
instead: `is_shell_route()` reads `frappe.router.current_route` directly
(null-checked, with the URL-pathname fallback for the unresolved-router
hard-load case) and never calls Frappe core's unguarded
`frappe.get_route_str()`.

Verified by running the real shipped file in a stubbed browser/frappe
harness whose `get_route_str` is a faithful copy of core's unguarded
implementation: 11/11 checks — the reported null-`current_route` hard-load
no longer throws and the IIFE survives, URL fallback resolves the shell
route both ways, boot config applies synchronously with zero HTTP requests,
absence of boot config falls back to exactly one memoised HTTP call, and
`refresh_config()` clears the boot copy and re-fetches. As a control, the
pre-fix file was run through the same harness and crashes with the exact
reported error.

`CLAUDE.md` corrections: the install-seeding rationale was inverted (the
`219bfde` bug was after_migrate-only registration, not after_install-only),
a doctype path had an extra directory level, and the Python-version note now
attributes the 3.14 pin to Frappe's own pyproject rather than implying
wajha requires it (wajha declares `>=3.10`).

## 0.4.1 — 2026-08-11

Hotfix: `wajha_boot.js` — which loads globally on every Desk page via
`app_include_js`, not just on the `/app/wajha` shell — could throw an
uncaught `TypeError: Cannot read properties of null (reading 'join')`
from inside Frappe core's own `router.js` (`frappe.get_route_str()` calls
`frappe.router.current_route.join("/")` with no null guard), because
`current_route` is genuinely `null` for a moment during some route
transitions. Since this ran unguarded on `app_ready`/every router change,
it could blank out ANY Desk page it fired on mid-transition — reported
live as the Shell Settings single doctype rendering blank after install.

Fixed by no longer calling `frappe.get_route_str()`/`frappe.get_route()`
at all; `mark_route()` now reads `frappe.router.current_route` directly
inside a try/catch and treats anything that isn't a proper route array as
"not the shell route" instead of crashing. Verified against the exact
reported failure mode (`current_route === null`, and `undefined` for good
measure) plus positive/negative route-detection controls — 5/5 checks
passed, including first confirming the *old* code really does throw the
identical error message under the same condition (so the test is proven
capable of catching the bug, not just capable of passing).

## 0.4.0 — 2026-08-08

Extensibility pass on `scaffold_module_from_doctype` — the one-shot generator
that turns an existing native ERPNext DocType into a working Shell Module.
Live-validated with 10 checks (4 negative controls) against real DocTypes,
including a throwaway custom "Wajha Geo Test" DocType built specifically to
exercise the map auto-detect path.

- **`field_include` / `field_exclude`**: new optional params (list or comma-separated string) to control exactly which fields become columns/filters, instead of only whatever the source DocType's own `in_list_view`/`in_standard_filter` flags happen to be. Useful when a native DocType's list-view config doesn't match what should actually show in the Wajha shell. `field_exclude` is applied last, so it can also trim an explicit `field_include` list.
- **Map auto-detect**: scaffolding a DocType that has a conventional latitude/longitude field pair (`latitude`/`longitude`, `lat`/`lng`, `lat`/`lon`, `gps_latitude`/`gps_longitude`) now automatically sets `map_lat_field`, `map_lon_field` and enables `show_map` — map setup used to be a mandatory manual step after every scaffold even when the coordinates were right there. Excluding either half of the pair via `field_exclude` correctly suppresses auto-detect.
- **Smarter default filters**: if the source DocType defines no `in_standard_filter` fields at all (common on custom DocTypes never wired up for the native list view), the scaffold now falls back to Select fields with a manageable option count (≤15) and Date/Datetime fields, so a scaffolded module isn't left with zero filters. DocTypes that DO define standard filters are untouched — the fallback only fires when there's nothing to use.

## 0.3.0 — 2026-08-08

Performance & scalability pass. Measured live against a 100,000-row Sales Order
table (random dates over the last 365 days, random amounts, mixed docstatus)
and 84 concurrently-configured Shell Modules — not estimated.

- **Auto-indexing for range filters**: saving a Shell Module now enqueues a background job (`queue="long"`, so it never blocks the save) that adds a DB index to any field used by a `Number Range`, `Date Range` or `Datetime Range` filter, via Frappe's own idempotent `frappe.db.add_index()`. Measured effect: sorting 100k rows by a previously-unindexed amount field dropped from 51.8ms to 1.7ms (~30x). A broad Date Range filter that matches most of the table is unaffected either way, which is correct — MariaDB rightly prefers a full scan over an index lookup at that selectivity, so this isn't something an index can fix.
- **Pagination COUNT(*) caching**: the total-row-count query that powers the pager is now cached for 20 seconds per unique (module, filters) combination — long enough to absorb a user clicking through pages of the same filtered view, short enough that a newly added/edited record shows up in the count almost immediately. Measured effect: a filtered `get_module_data` call went from 122.5ms (cache miss) to ~51-54ms on repeat calls (cache hit) — the count query alone had been costing ~70ms on the 100k-row table.
- **Verified**: full 18-check functional suite + 6-check permission-boundary suite re-run clean against the 100k-row dataset after these changes; the auto-index job was triggered directly (no RQ worker running in the validation environment) and confirmed via `SHOW INDEX` to actually create the index, and confirmed idempotent (re-running it a second time did not create a duplicate).

## 0.2.0 — 2026-08-08

Native ERPNext DocType compatibility pass.

- **Status badges**: submittable DocTypes (Sales Order, Purchase Invoice, Journal Entry, …) now render a Draft/Submitted/Cancelled badge automatically via `docstatus`, with no per-module configuration required. Non-submittable DocTypes can opt in via the new `status_field` option on Shell Module.
- **Fixed range filters**: `Number Range` and `Date Range` were declared as filter controls since 0.1.0 but the list-view toolbar only ever rendered a single text box for them, so they silently never worked. They now render two linked inputs. Added `Datetime Range` alongside them, plus a new `MultiSelect` control (renders as a multi-select box, sent to the server as an `in` filter).
- **Child-table safety**: a column accidentally pointed at a Table/Table MultiSelect field is now dropped server-side instead of breaking the row renderer.
- **Wider field-type coverage**: `Checkbox`, `Rating`, `Attachment`, `Image`, `Geolocation`, `MultiSelectBadge`, `JSON` and `Duration` column formats, so `scaffold_module_from_doctype` produces a usable module straight away on more native DocTypes instead of falling back to plain text everywhere.
- **Performance**: the per-module allowed-field computation is now cached (5 min TTL, invalidated immediately on Shell Module save) instead of being recomputed on every `get_module_data`/`get_module_meta`/`get_map_points` call.
- No schema-breaking changes: existing Shell Module records keep working unchanged; `status_field` defaults to empty (auto-resolves to `docstatus` for submittable DocTypes only).

## 0.1.0 — 2026-08-07

First release.

- `Shell Settings` (single), `Shell Theme`, `Shell Module` + column/filter child tables — the whole shell is configured as data.
- Four Arabic theme presets: الأخضر المؤسسي، الأزرق الحكومي، الرمادي المحايد، العنابي.
- RTL-first shell page at `/app/wajha`: sidebar with grouped modules, themed list view with server-side search, filtering, sorting and pagination, optional Leaflet map view.
- Permission-safe API keyed on module (never on a client-supplied DocType or field); `page_length` capped at 200 server-side.
- `scaffold_module_from_doctype` to generate a module from an existing DocType's list-view fields.
- Runtime CSS custom-property injection, with optional global font and global colour application across the Desk.
- Responsive: off-canvas drawer with backdrop, Escape-to-close, 44px targets below the configured breakpoint.
- No build step — plain CSS/JS, installs on benches without Node.
