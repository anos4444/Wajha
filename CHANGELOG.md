# Changelog

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
