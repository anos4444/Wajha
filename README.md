# Wajha — واجهة

**An Arabic-first, configuration-driven Desk shell and theming layer for Frappe / ERPNext v16.**

Wajha turns a Frappe site into a branded, single-column application: a right-to-left sidebar of your own modules, a themed list experience with server-side filtering and pagination, an optional map view, and a colour system you switch from the UI rather than from code.

It is **configuration, not code**. Adding a module to the sidebar means creating a `Shell Module` record — no JavaScript edits, no rebuild. The same app can therefore dress an asset-management system, a licensing system, or a fleet system without forking.

---

## Why it exists

Frappe's Desk is excellent for data work but always looks like Frappe. Public-sector and enterprise clients frequently need a system that looks like *their* system — their identity, their language, their vocabulary — while keeping everything that makes Frappe worth using: the permission model, workflows, validation, audit trail, and reports.

Wajha sits on top rather than replacing any of it. Browsing and navigation happen in the shell; opening a record hands you to the standard Frappe form, so nothing about permissions or workflow is reimplemented.

## Highlights

- **Arabic and RTL first.** Every label carries an Arabic primary and an optional English secondary; layout, drawer direction and spacing are built for RTL and work in LTR.
- **Themes as data.** `Shell Theme` records hold the full token set — colours, font, radius, shadow, sidebar width. Four presets ship with the app; duplicate one and change it to match a client's brand.
- **No build step.** Plain CSS and vanilla JavaScript. Installs on any v16 bench, including servers with no Node toolchain, and works offline apart from the optional map tiles.
- **Permission-safe by construction.** The browser never names a DocType, a field or an operator. It names a *module key*; the server loads that module's saved configuration and builds the query from it, then Frappe's permission layer applies on top. A user cannot request data their roles forbid, even by editing the request.
- **Responsive.** Persistent sidebar on desktop; off-canvas drawer with backdrop, Escape-to-close and 44px targets on phones and tablets.
- **Optional map view.** Point any module at latitude/longitude fields and get a filtered map alongside the table.

## Install

```bash
cd ~/frappe-bench
bench get-app https://github.com/<your-org>/wajha
bench --site <your-site> install-app wajha
bench --site <your-site> migrate
```

Requires Frappe v16 (Python 3.14). No Node build step is needed.

## Configure in five minutes

1. **Shell Settings** — set the system name, the authority/organisation subtitle, the logo, and pick an active theme.
2. **Shell Module** — one record per sidebar item:
   - `module_key` — a latin slug, e.g. `assets`
   - `module_label` / `module_label_en` — what the user reads
   - `view_type` — `List` (browse a DocType) or `Route Link` (jump to any page)
   - `ref_doctype`, then the **Columns** and **Filters** child tables
   - optionally enable the map and name the lat/lon/label/colour fields
3. Open `/app/wajha`.

To go faster, scaffold a module from an existing DocType — it copies the list-view columns and standard filters:

```python
frappe.call("wajha.api.scaffold_module_from_doctype", {"doctype": "Asset"})
```

## Theming

Every visual value is a CSS custom property (`--wj-primary`, `--wj-sidebar-bg`, `--wj-radius`, …) published at runtime from the active `Shell Theme`. Two switches in Shell Settings extend the theme beyond the shell:

- **apply_font_globally** — the theme font applies to Desk lists, forms and dialogs, so the whole site reads as one product.
- **apply_theme_globally** — the theme's colours are mapped onto Frappe's own variables, so a user landing on a standard form still feels inside your system.

For closed networks, leave `font_css_url` empty and ship the font files inside your own app; set only the family name in the theme.

## Consuming it from your app

Wajha owns presentation. Your app owns the domain: DocTypes, workflows, validation, reports. A typical consumer app declares Wajha as a dependency, then creates its `Shell Theme`, `Shell Settings` values and `Shell Module` records in its own `after_migrate` hook so a fresh install comes up fully dressed.

## Security notes

- All read endpoints go through `frappe.get_list`, so row-level permissions, user permissions and field-level (permlevel) rules all apply unchanged.
- Filter fieldnames not declared in a module's Filters table are ignored rather than trusted.
- `page_length` is capped server-side (200) regardless of what the client asks for.
- `scaffold_module_from_doctype` is restricted to System Manager and Shell Manager.

## Deployment notes worth knowing

Two Frappe behaviours cost real debugging time and are worth respecting in any project built on this app:

1. **Desk caches Page doclists.** Shipping a new `.js` does not invalidate that cache — bump the Page record's `modified`. Key that decision on a **content hash**, never on a timestamp comparison between machines; clock skew silently skips genuine deploys.
2. **Unversioned CSS paths served with far-future caching** keep browsers on the old stylesheet while the server serves the new one. Hash-version asset paths.

## Licence

MIT © AAA Consulting.
