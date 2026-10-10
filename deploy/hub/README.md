# Deploying Wajha with a baked Docker image

For a Frappe site running as a **split Docker Compose stack** — separate
backend, queue, scheduler, websocket and frontend containers all sharing
one image, behind a proxy, with MariaDB alongside.

Placeholders used throughout: `<HOST>` the server, `<SITE>` the Frappe site
name, `<IMAGE>` the stack's image tag, and `<backend>` / `<frontend>` /
`<queue-*>` / `<scheduler>` the container names.

Two independent paths follow. The first is the one to use.

## 1. Rebuild the image (persistent)

Apps are baked into `<IMAGE>`, so every container in the stack gets them
and a `docker compose up -d` cannot undo it.

Files in this folder:

- `apps.json` — the app set: erpnext and hrms on `version-16`, wajha on
  `main`. All public.
- `Containerfile` — the layered build. Its header carries the exact build
  command.

Steps:

1. On a machine with Docker and network access, run the build command from
   `Containerfile`'s header. It produces `<IMAGE>:v16-next`.
2. **Back up first:**
   `docker exec -u frappe <backend> bench --site <SITE> backup --with-files`
3. Point the compose file's image tag at `:v16-next` and bring the stack up.
   The `sites` and `logs` volumes persist, so the database and site files
   carry over; only the code layer changes.
4. Migrate onto the new code:
   `docker exec -u frappe <backend> bench --site <SITE> migrate`,
   then `bench --site <SITE> install-app wajha` (first time only) and
   `bench --site <SITE> clear-cache`.

`install-app wajha` fires `after_install`; `migrate` fires `after_migrate`.
Both seed the Shell Theme presets, the `Shell Manager` role and the default
`Shell Settings`, and both compile the translation catalogue. They are
idempotent and safe to repeat. Wajha needs **both** hooks because
`bench install-app` does not run migrate hooks.

> **Upgrade note.** `version-16` is a moving branch, so two builds a week
> apart are not the same image. Pin `FRAPPE_BRANCH` and the branches in
> `apps.json` to matching release tags for a reproducible upgrade, and read
> ERPNext's release notes for manual migration steps between your current
> release and the target.

## 2. Install into the running container (preview only)

Shows Wajha on the live site immediately, but it is **lost when the
container is recreated**, because it writes into the container layer rather
than the image — and only the container you touched gets it, so the queues
and scheduler run without the app. Database changes (DocTypes, custom
fields, settings) do persist on the `sites` volume. Use this to preview
before committing to an image rebuild, not as a deploy.

1. Get the source into `<backend>:/home/frappe/frappe-bench/apps/wajha`
   (`bench get-app`, or copy a checkout in).
2. `bench setup requirements --python` — installs wajha into the env.
3. Link the assets. Wajha ships plain CSS/JS with no build step:
   `ln -sfn apps/wajha/wajha/public sites/assets/wajha`
4. `bench --site <SITE> install-app wajha`
5. `bench --site <SITE> clear-cache`, then restart the backend and workers
   so the new hooks load.

If the frontend is a separate container, copy `wajha/public` into its
`assets/wajha` too, or it will serve the old CSS and JS.

## Verify

- `https://<HOST>/desk/wajha` renders the shell: sidebar, Home tiles and
  the dashboard strip. Frappe 16 serves the Desk at `/desk`; `/app`
  redirects there, and the bare `/wajha` is a website route that 404s.
- Sidebar module entries draw real icons, not empty boxes. If every glyph
  is missing, check the sprite is served:
  `curl -I https://<HOST>/assets/wajha/icons/fa.svg`
- Shell Theme presets exist and `Shell Settings` has an active theme — if
  the shell renders untokenised, seeding did not run.
- Translations resolve. In an English session the sidebar group headings
  read English, not their stored Arabic source. Frappe only reads compiled
  `.mo` files, so if they are untranslated the catalogue was not compiled:
  check `sites/assets/locale/<lang>/LC_MESSAGES/wajha.mo` exists.
- A Desk page outside the shell still looks normal — `wajha_boot.js` loads
  on every Desk page, so a fault there is visible away from `/desk/wajha`.
