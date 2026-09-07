# Wajha — واجهة

**An Arabic-first, configuration-driven Desk shell for Frappe / ERPNext v16.**

Wajha turns a Frappe site into a branded, single-column application: a right-to-left sidebar of your own modules, a themed list experience with server-side filtering and pagination, a record card with the actions the user may take, an in-shell form for new records, a dashboard strip on every module, and a colour system you switch from the UI rather than from code. On a phone it is a real app: cards, a filter sheet, a bottom bar, and Add to Home Screen under the client's own name.

It is **configuration, not code**. Adding a module to the sidebar means creating a `Shell Module` record — no JavaScript edits, no rebuild. On a fresh install every workspace DocType of every installed app already has one.

Current release: **0.18.1**. `CHANGELOG.md` records each release and the reasoning behind it.

---

## Why it exists

Frappe's Desk is excellent for data work but always looks like Frappe. Public-sector and enterprise clients frequently need a system that looks like *their* system — their identity, their language, their vocabulary — while keeping everything that makes Frappe worth using: the permission model, workflows, validation, audit trail, and reports.

Wajha sits on top rather than replacing any of it. Browsing, navigation, the record card and the New form happen in the shell; every query and every action goes through Frappe's own permission and workflow machinery, so nothing about either is reimplemented. The standard Frappe form stays one link away, and so does the rest of the Desk.

## Highlights

- **Arabic and RTL first.** Every label carries an Arabic primary and an optional English secondary; layout, drawer direction and spacing are built for RTL and work in LTR. Every shell string ships with an Arabic translation.
- **Themes as data.** `Shell Theme` records hold the full token set — colours, font, radius, shadow, sidebar width. Four presets ship with the app; duplicate one and change it to match a client's brand. The theme is a site setting; a user's Light/Dark choice stays Frappe's own.
- **No build step.** Plain CSS and vanilla JavaScript: the Desk loads exactly two Wajha files, `wajha.css` and `wajha_boot.js`. Installs on any v16 bench, including servers with no Node toolchain, and works offline apart from the optional map tiles.
- **Permission-safe by construction.** The browser never names a DocType, a field or an operator. It names a *module key*; the server loads that module's saved configuration and builds the query from it, then Frappe's permission layer applies on top. A user cannot request data their roles forbid, even by editing the request.
- **Icons without a font.** Every module carries a Font Awesome Free glyph chosen for its DocType, or the emoji or `fa:` name an administrator typed. The glyphs ship as inline SVG path data with the modules that use them: no web font, no CDN, and they take the theme's colours.
- **Every app as modules, by default.** On install, on migrate, and whenever another app is installed later, Wajha creates a Shell Module record for every DocType the installed apps' workspaces link to, grouped by workspace and labelled in the site's language. Edit, disable or flag them for the phone bar; nothing is ever overwritten. Turn `seed_modules` off in Shell Settings to keep only hand-made modules.
- **Adapts to the site.** Home is a grid of every app and workspace the user may open, discovered from Frappe's own Desktop Icons and Workspaces; a tile opens the workspace's DocTypes as ready-made modules with cards, forms and actions. Install an app and it is there on the next load. Hand-made modules override any discovered one.
- **A real phone app.** Below 700px the list becomes cards (title, subtitle, status chip), filters live in a bottom sheet with a count badge, the list grows as you scroll, and up to four modules sit in a bottom bar within thumb reach. The drawer closes with ✕, a swipe, or a tap outside. Add to Home Screen installs the client's own name, logo and colours.
- **Record card with actions.** Tap a record and the shell shows only the fields that hold a value, grouped by the form's sections, plus child tables, attachments and comments — and the actions this user may take right now: workflow transitions, Submit/Cancel, Print, or actions you configure (set a field, call a whitelisted method, jump to a route). Desktop gets a side panel, phones the full screen.
- **Create from the shell.** New records use an in-shell form built from the DocType (or the module's `form_fields`): Link suggestions from Frappe's own search, child-table rows, Save, and Save & Submit only for users who hold submit permission — an employee saves a draft and the approver submits. The scope is filled server-side. A Link field whose DocType the user cannot read is shown disabled with a note naming that DocType, and the rest of the form stays usable.
- **A dashboard on every module.** Cards above each list: the record count, status counts that filter on tap, totals of numeric columns, app cards (leave balance with a progress bar, upcoming holidays, last check-in, last salary slip, expense claims by status) and any Frappe Number Card you pin to the module. All inside the user's scope and permissions.
- **Self-service out of the box.** With HRMS installed, employees get my leave, check in / out with location, salary slip PDFs, expense claims, attendance, advances, travel, shifts and their profile — each a "mine" module with an in-shell form, seeded automatically and editable as records. The same pack mechanism (`wajha/packs`) can dress any other app.
- **"Mine" modules.** A module scoped to the user's own records — by owner, by a user field, or by the Employee linked to the login — is a self-service app for employees with no extra code; an admin's browse module and an employee's "my leave" can point at the same DocType.
- **Open anything in a new tab.** Home tiles, sidebar entries, the phone tab bar and record cards are real links: a plain click routes in-page, Ctrl/⌘-click and middle-click open a second tab.
- **Responsive.** Persistent sidebar on desktop; off-canvas drawer with backdrop, Escape-to-close and 44px targets on tablets.
- **Optional map view.** Point any module at latitude/longitude fields and get a filtered map alongside the table.

## Requirements

- Frappe v16. Tested on 16.25 (self-hosted) and 16.33 (Frappe Cloud). Frappe v16 pins Python 3.14.
- ERPNext and HRMS are optional. The HRMS self-service pack and its dashboard cards appear only when HRMS is installed.
- No Node build step.

## Install

```bash
cd ~/frappe-bench
bench get-app https://github.com/anos4444/Wajha
bench --site <your-site> install-app wajha
bench --site <your-site> migrate
```

Installation seeds the theme presets, the default settings, the HRMS self-service modules when HRMS is present, and a module for every workspace DocType. On Frappe Cloud, add the app from the GitHub repository and let the bench update run the migrate.

Then open `/desk/wajha` (`/app/wajha` redirects there on v16). To make the shell the landing page for everyone, set the Wajha page as the Desk home page in Frappe (Desktop Settings, or the page's own "Set as Home Page"); the bare `/desk` URL then opens the shell.

### Updating a site

```bash
cd ~/frappe-bench/apps/wajha && git fetch origin main && git checkout -B main FETCH_HEAD && cd ../..
bench --site <your-site> migrate
bench restart
```

The restart matters: Wajha's assets are served under a content hash the backend computes at start-up, so a pull without a restart leaves browsers on the previous script. `migrate` is always safe to run; it also carries the clean-up patches for sites that had earlier releases installed.

## Configure in five minutes

1. **Shell Settings** — set the system name, the organisation subtitle, the logo, and pick an active theme. Leave `landing` on Home and `auto_modules` on to get the discovered apps grid; `seed_modules` controls the all-apps pack; `show_desk_link` keeps the "Frappe Desk" button at the foot of the drawer.
2. **Shell Module** — one record per sidebar item:
   - `module_key` — a latin slug, e.g. `assets`
   - `module_label` / `module_label_en` — what the user reads
   - `icon` — an emoji, or a Font Awesome Free glyph as `fa:coins` (the field offers the names); blank picks one for the DocType
   - `group` — a sidebar group; the field suggests the groups already in use
   - `view_type` — `List` (browse a DocType) or `Route Link` (jump to any page)
   - `ref_doctype`, then the **Columns** and **Filters** child tables
   - `scope` — `All`, or one of the `Mine` scopes with `scope_field` for a self-service module
   - `detail_fields` (optional) — the fields on the record card; blank shows every non-empty readable field by section
   - `show_in_mobile_bar` — pin the module to the phone's bottom bar
   - `form_fields` (optional) — the in-shell New form; blank offers the DocType's mandatory fields
   - `show_dashboard` and `number_cards` — the dashboard strip and any Frappe Number Cards pinned to it
   - **Actions** (optional) — buttons on the record card (Set Value, Server Method, Route, Print) or above the list (Create, e.g. check in / out); workflow transitions and Submit/Cancel appear on their own
   - optionally enable the map and name the lat/lon/label/colour fields
3. Open `/desk/wajha`.

To go faster, scaffold a module from an existing DocType — it copies the list-view columns and standard filters:

```python
frappe.call("wajha.api.scaffold_module_from_doctype", {"doctype": "Asset"})
```

## Moving between the shell and the Desk

- **Back to Frappe:** the drawer (☰ on desktop, **More** on a phone) ends with a **Frappe Desk** button that opens the Desk home. Switch it off with `show_desk_link` if the system should feel closed.
- **Search and workspaces** live in the Desk: Ctrl+K (⌘+K) or the search icon there opens Frappe's search, and the Desk sidebar lists the workspaces. The search box at the top of the shell's drawer filters modules only.
- **Direct addresses** work from anywhere: `/desk/wajha` for the shell, `/desk/wajha/<module_key>` for a module, `/desk/wajha/<module_key>/<name>` for a record, `/desk/home` or `/desk/<workspace>` for the Desk.
- The full Frappe form for any record is one link away from its card, and "Open the full form in Frappe" sits under every in-shell New form.
- **A user's own profile:** the name chip in the header opens the user's settings page in Frappe (photo, name, password, language). With HRMS, "My Profile" in the self-service group shows the employee record; "Open in Frappe" on it edits the record when the role may write, otherwise HR does.

## Theming

Every visual value is a CSS custom property (`--wj-primary`, `--wj-sidebar-bg`, `--wj-radius`, …) published at runtime from the active `Shell Theme`. Two switches in Shell Settings extend the theme beyond the shell:

- **apply_font_globally** — the theme font applies to Desk lists, forms and dialogs, so the whole site reads as one product.
- **apply_theme_globally** — the theme's colours are mapped onto Frappe's own variables, so a user landing on a standard form still feels inside your system. On by default: a fresh install comes up themed Desk-wide; turn it off to keep the colours inside the shell.

Outside those two switches Wajha leaves the Desk alone: no Desk-wide stylesheets of its own, no login-page override, no user-level theme fields. A ported theming module ("Swift Theme") shipped from 0.6.0 to 0.16.9 and was removed in 0.17.0; a migrate patch removes everything it left in a site's database.

For closed networks, leave `font_css_url` empty and ship the font files inside your own app; set only the family name in the theme.

## Consuming it from your app

Wajha owns presentation. Your app owns the domain: DocTypes, workflows, validation, reports. A typical consumer app declares Wajha as a dependency, then creates its `Shell Theme`, `Shell Settings` values and `Shell Module` records in its own `after_migrate` hook so a fresh install comes up fully dressed. A pack in the style of `wajha/packs/hrms.py` can seed modules and dashboard cards for any app, and packs never overwrite a record an administrator has edited.

## Security notes

- All read endpoints go through `frappe.get_list`, so row-level permissions, user permissions and field-level (permlevel) rules all apply unchanged. Dashboard counts and totals use the same path and the same scope.
- The client names module keys only. Filter fieldnames not declared in a module's Filters table are ignored rather than trusted; status chips filter through the module's own status field.
- `page_length` is capped server-side (500, ERPNext's own largest list page) regardless of what the client asks for.
- `scaffold_module_from_doctype` is restricted to System Manager and Shell Manager.
- The record card (`wajha.records`) loads through `frappe.get_doc` and `check_permission`, serialises only fields at a permlevel the user may read, and refuses a record outside a Mine module's scope with the same message as a missing one. Actions re-check submit/cancel/write permission server-side; Set Value also checks the field's permlevel; Server Method only calls whitelisted functions.
- Creating a record re-checks create permission, sets the scope field last so it cannot be overridden, and submits only when the user holds submit permission. Discovered (virtual) modules are permission-checked exactly like saved ones.

## Deployment notes worth knowing

Three Frappe behaviours cost real debugging time and are worth respecting in any project built on this app:

1. **Desk caches Page doclists.** Shipping a new `.js` does not invalidate that cache — bump the Page record's `modified`. Key that decision on a **content hash**, never on a timestamp comparison between machines; clock skew silently skips genuine deploys.
2. **Unversioned CSS paths served with far-future caching** keep browsers on the old stylesheet while the server serves the new one. Hash-version asset paths.
3. **Frappe navigates in-page.** Anything a page stamps on the document (a root colour, a body class, an inline `display`) outlives the route unless the page's own show/hide hooks undo it; a URL check at load time never fires again.

## Licence

MIT — see `license.txt`. The module icons are Font Awesome Free glyphs (https://fontawesome.com), used under CC BY 4.0; the attribution sits in `wajha/icons_data.py`.
