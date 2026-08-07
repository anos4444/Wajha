# Changelog

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
