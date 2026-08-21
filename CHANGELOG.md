# Changelog

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
