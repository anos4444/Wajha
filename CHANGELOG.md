# Changelog

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
