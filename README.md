# Wajha — واجهة

**An Arabic-first, configuration-driven Desk shell and theming layer for Frappe / ERPNext v16.**

Wajha turns a Frappe site into a branded, single-column application: a right-to-left sidebar of your own modules, a themed list experience with server-side filtering and pagination, an optional map view, and a colour system you switch from the UI rather than from code.

It is **configuration, not code**. Adding a module to the sidebar means creating a `Shell Module` record — no JavaScript edits, no rebuild. The same app can therefore dress an asset-management system, a licensing system, or a fleet system without forking.

---

## Why it exists

Frappe's Desk is excellent for data work but always looks like Frappe. Public-sector and enterprise clients frequently need a system that looks like *their* system — their identity, their language, their vocabulary — while keeping everything that makes Frappe worth using: the permission model, workflows, validation, audit trail, and reports.

Wajha sits on top rather than replacing any of it. Browsing, navigation and the record card happen in the shell; every query and every action goes through Frappe's own permission and workflow machinery, so nothing about either is reimplemented. The standard Frappe form stays one tap away for editing.

## Highlights

- **Arabic and RTL first.** Every label carries an Arabic primary and an optional English secondary; layout, drawer direction and spacing are built for RTL and work in LTR.
- **Themes as data.** `Shell Theme` records hold the full token set — colours, font, radius, shadow, sidebar width. Four presets ship with the app; duplicate one and change it to match a client's brand.
- **No build step.** Plain CSS and vanilla JavaScript. Installs on any v16 bench, including servers with no Node toolchain, and works offline apart from the optional map tiles.
- **Permission-safe by construction.** The browser never names a DocType, a field or an operator. It names a *module key*; the server loads that module's saved configuration and builds the query from it, then Frappe's permission layer applies on top. A user cannot request data their roles forbid, even by editing the request.
- **A real phone app.** Below 700px the list becomes cards (title, subtitle, status chip), filters live in a bottom sheet with a count badge, the list grows as you scroll, and up to four modules sit in a bottom bar within thumb reach. Add to Home Screen installs the client's own name, logo and colours.
- **Record card with actions.** Tap a record and the shell shows only the fields that hold a value, grouped by the form's sections, plus child tables, attachments and comments — and the actions this user may take right now: workflow transitions, Submit/Cancel, or actions you configure (set a field, call a whitelisted method, jump to a route). Desktop gets a side panel, phones the full screen.
- **Self-service out of the box.** With HRMS installed, employees get my leave, check in / out with location, salary slip PDFs, expense claims, attendance, advances, travel and more — each a "mine" module with an in-shell form, seeded automatically and editable as records. The same pack mechanism (`wajha/packs`) can dress any other app.
- **Create from the shell.** New records use an in-shell form built from the DocType (or the module's `form_fields`): Link suggestions from Frappe's own search, child-table rows, Save & Submit. The scope is filled server-side. Frappe's full form stays one link away.
- **"Mine" modules.** A module scoped to the user's own records — by owner, by a user field, or by the Employee linked to the login — is a self-service app for employees with no extra code; an admin's browse module and an employee's "my leave" can point at the same DocType.
- **Responsive.** Persistent sidebar on desktop; off-canvas drawer with backdrop, Escape-to-close and 44px targets on tablets.
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
   - `scope` — `All`, or one of the `Mine` scopes with `scope_field` for a self-service module
   - `detail_fields` (optional) — the fields on the record card; blank shows every non-empty readable field by section
   - `show_in_mobile_bar` — pin the module to the phone's bottom bar
   - `form_fields` (optional) — the in-shell New form; blank offers the DocType's mandatory fields
   - **Actions** (optional) — buttons on the record card (Set Value, Server Method, Route, Print) or above the list (Create, e.g. check in / out); workflow transitions and Submit/Cancel appear on their own
   - optionally enable the map and name the lat/lon/label/colour fields
3. Open `/app/wajha`.

To go faster, scaffold a module from an existing DocType — it copies the list-view columns and standard filters:

```python
frappe.call("wajha.api.scaffold_module_from_doctype", {"doctype": "Asset"})
```

## Theming

Every visual value is a CSS custom property (`--wj-primary`, `--wj-sidebar-bg`, `--wj-radius`, …) published at runtime from the active `Shell Theme`. Two switches in Shell Settings extend the theme beyond the shell:

- **apply_font_globally** — the theme font applies to Desk lists, forms and dialogs, so the whole site reads as one product.
- **apply_theme_globally** — the theme's colours are mapped onto Frappe's own variables, so a user landing on a standard form still feels inside your system. On by default since 0.10.0: a fresh install comes up themed Desk-wide; turn it off to keep the colours inside the shell.

For closed networks, leave `font_css_url` empty and ship the font files inside your own app; set only the family name in the theme.

## Consuming it from your app

Wajha owns presentation. Your app owns the domain: DocTypes, workflows, validation, reports. A typical consumer app declares Wajha as a dependency, then creates its `Shell Theme`, `Shell Settings` values and `Shell Module` records in its own `after_migrate` hook so a fresh install comes up fully dressed.

## Security notes

- All read endpoints go through `frappe.get_list`, so row-level permissions, user permissions and field-level (permlevel) rules all apply unchanged.
- Filter fieldnames not declared in a module's Filters table are ignored rather than trusted.
- `page_length` is capped server-side (500, ERPNext's own largest list page) regardless of what the client asks for.
- `scaffold_module_from_doctype` is restricted to System Manager and Shell Manager.
- The record card (`wajha.records`) loads through `frappe.get_doc` and `check_permission`, serialises only fields at a permlevel the user may read, and refuses a record outside a Mine module's scope with the same message as a missing one. Actions re-check submit/cancel/write permission server-side; Set Value also checks the field's permlevel; Server Method only calls whitelisted functions.

## Deployment notes worth knowing

Two Frappe behaviours cost real debugging time and are worth respecting in any project built on this app:

1. **Desk caches Page doclists.** Shipping a new `.js` does not invalidate that cache — bump the Page record's `modified`. Key that decision on a **content hash**, never on a timestamp comparison between machines; clock skew silently skips genuine deploys.
2. **Unversioned CSS paths served with far-future caching** keep browsers on the old stylesheet while the server serves the new one. Hash-version asset paths.

## Swift Theme module (0.6.0)

Wajha now ships the whole of
[Swift Theme](https://github.com/its-alikhokher/swift_theme) as a second
Frappe module, alongside the Shell system:

- **Twelve colour presets** (six light, six dark), per user, offered inside
  Frappe's own Switch Theme dialog — plus **Custom Colors**, which derives a
  full palette from a primary/secondary pair.
- **Themed, server-rendered login page** in three layouts, with every word of
  the brand panel editable from `Swift Theme Settings`.
- **Optional desk landing page** (eight designs) built on desktop icons and
  Number Cards, so Frappe's own permissions decide what appears.
- **Density, shape, font scale/family per user; glass, backdrops, styled
  scrollbar, toast and print theming, focus mode, per-event desk sounds** —
  each behind its own switch.

Configured from the `Swift Theme Settings` single; independent of the Shell,
so either feature set can be enabled without the other. The upstream
`.bundle.*` build files were replaced by individually hash-versioned plain
files, so the no-Node install rule above still holds. Do not install the
standalone `swift_theme` app on the same site — the module replaces it and
they share DocType names.

## Licence

MIT © AAA Consulting. The Swift Theme module is ported from
[its-alikhokher/swift_theme](https://github.com/its-alikhokher/swift_theme),
MIT © 2026 iamaliraza777@gmail.com.
