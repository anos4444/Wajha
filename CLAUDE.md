# Wajha — instructions for Claude Code

Wajha (واجهة) is an Arabic-first, configuration-driven Desk shell and theming
layer for Frappe / ERPNext v16. It turns a Frappe site into a branded,
single-column application — RTL sidebar, themed list views with server-side
search/filter/pagination, an optional map view — configured entirely through
Frappe records (`Shell Settings`, `Shell Theme`, `Shell Module`), not code.
It is a **reusable platform app**, not tied to any one client's DocTypes.
Read `README.md` first for the product pitch; this file is for working on
the codebase itself.

## Architecture, in one paragraph

The browser never names a DocType, field, or query operator — only a
`module_key`. `wajha/api.py` resolves that key to a `Shell Module` record
server-side, builds the `frappe.get_list()` call from the module's saved
Columns/Filters child tables, and Frappe's own permission layer applies on
top exactly as it would for any other query. This is the core security
invariant of the app: a client cannot request data its roles forbid, even by
hand-editing the request, because the server decides what fields/filters are
even legal for a given module before touching the DocType.

## Key files

- `wajha/api.py` (~550 lines) — every whitelisted endpoint. `get_config()`
  (theme tokens + module list for the sidebar), `get_module_data()` (the
  list-view query, paginated/filtered/searched), `get_module_meta()`
  (column/filter definitions for the frontend to render controls from),
  `get_map_points()`, `scaffold_module_from_doctype()` (generates a Shell
  Module from an existing DocType's list-view config). Field/count caching
  lives here (`_allowed_fields`, `_cached_count`).
- `wajha/boot.py` — attaches the resolved `get_config()` payload to Frappe's
  own boot response (`boot_session` hook) so the shell is themed before
  first paint, no HTTP round trip. Fails soft (never breaks Desk boot on a
  half-migrated Shell Settings). `clear_boot_cache()` drops the per-user
  cached bootinfo; called from `on_update()` on Shell Settings/Shell Theme,
  and from Shell Module's own `_clear_cache()`.
- `wajha/install.py` — idempotent seeding (4 theme presets, `Shell Manager`
  role, default `Shell Settings`). Registered on **both** `after_install`
  and `after_migrate` — `bench install-app` does not run migrate hooks, so
  after_install-only seeding left fresh installs unthemed (see git history,
  commit `219bfde`).
- `wajha/public/js/wajha_boot.js` — loads globally on **every** Desk page
  via `app_include_js`, not just `/app/wajha`. Publishes theme tokens as CSS
  custom properties, optionally applies font/colors Desk-wide. Because it's
  global, a bug here can break unrelated Desk pages (see Known sharp edges).
- `wajha/wajha/page/wajha/wajha.js` + `wajha/public/css/wajha.css` — the
  actual shell page: sidebar, list view, filters, map. No build step —
  plain JS/CSS, so the app installs on any v16 bench without Node.
- `wajha/wajha/wajha/doctype/shell_module/shell_module.py` — on save,
  clears caches AND enqueues a background job (`add_filter_indexes`) that
  adds a DB index to any field used by a Number/Date/Datetime Range filter.
- DocTypes: `Shell Settings` (single), `Shell Theme`, `Shell Module` +
  `Shell Module Column` / `Shell Module Filter` (child tables).

## Testing discipline — read this before trusting a green result

**A check that can only pass is not a check.** Every functional test in this
project pairs a positive assertion with a negative control that proves the
check can actually fail (e.g. "impossible filter bound → 0 rows", "restricted
user's role set is exactly the narrow test role, not accidentally broad").
When you write or evaluate a test here, ask: what would make this fail, and
have I actually triggered that condition once? If a test only ever exercises
the success path, it isn't proving what it looks like it's proving.

This app has genuinely burned people on green-but-wrong results before —
e.g. an app-level `Shell Manager` permission that in practice covered every
DocType, or a "fresh install" that had never actually been tested unmigrated
until it broke on `hub.tawasulcloud.com`. Prefer testing against something
close to a real fresh site/dataset over trusting that static review caught
everything.

## Known sharp edges (do not reintroduce)

- **`frappe.get_route_str()` / `frappe.get_route()` are unsafe.** Frappe
  core does `frappe.router.current_route.join("/")` with no null guard, and
  `current_route` is genuinely `null` for a moment during some route
  transitions. Since `wajha_boot.js` runs on every Desk page, calling either
  of these unguarded can throw an uncaught `TypeError` that blanks out
  whatever page happens to be transitioning at that moment. Read
  `frappe.router.current_route` directly inside a try/catch instead (see
  `mark_route()` in `wajha_boot.js`, fixed in `13742a3`).
- **Desk caches Page doclists** — shipping a new `wajha.js` does not
  invalidate it; the Page record's `modified` timestamp has to change. Key
  that on a content hash, not a timestamp comparison across machines (clock
  skew silently skips real deploys).
- **Unversioned CSS paths with far-future caching** keep browsers on stale
  styles after a deploy. Hash-version the asset path.
- **`inset-inline-end` in RTL** resolves to the *left* edge, not the right —
  bit the mobile drawer once (docked opposite the sidebar). Use physical
  `left`/`right` per direction instead of logical properties for anything
  that has to match the RTL sidebar's side.
- **`frappe.format()` for Currency/Percent returns an alignment-wrapped
  `<div>`**, not a bare string — escaping it directly prints the markup as
  text. Unwrap through an inert `<template>` first, then escape the text
  node.
- **`bench install-app` does not run `after_migrate`** — anything that must
  exist on a genuinely fresh site (theme presets, roles, default settings)
  needs to fire from `after_install` too. Test against a real fresh
  `install-app`, not a bench that's already been migrated once — the bug
  stays invisible otherwise (see `219bfde`).
- **v16 rejects backticked `order_by` and string SQL functions in SELECT**
  in some contexts that v15 tolerated — already fixed once (`2ce8757`), keep
  an eye out for the same class of issue in new query-building code.

## Environment / deployment facts

- Requires Frappe v16, which pins **Python 3.14 exactly**.
- No Node build step — plain CSS/JS by design; don't introduce a bundler
  without strong justification, since "installs on any v16 bench, even ones
  with no Node toolchain" is a stated feature, not an accident.
- Repo: `https://github.com/anos4444/Wajha.git`, branch `main`. Local repo
  at `~/apps-src/wajha` on Anas's Mac.
- Live test target: `odoojo.frappe.cloud` (frappe 16.30.0 / erpnext
  16.31.1) — several real defects have only ever surfaced there, not in
  synthetic testing, so treat it as the source of truth when the two
  disagree.
- `CHANGELOG.md` is kept current per release; check it for the fullest
  up-to-date account of what shipped and why before assuming a feature
  doesn't exist yet.

## Commit style

Look at recent `git log` messages before writing your own — this repo's
convention is a `type: short summary` subject line, then a body that states
what broke (with a concrete repro/measurement where possible), the root
cause, the fix, and how it was verified. Not a changelog restatement — the
reasoning that justifies the change.
