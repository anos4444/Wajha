# Deploying Wajha on hub.tawasulcloud.com

The hub runs as a Docker Compose stack on `151.243.198.59`
(`hub-backend-1`, `hub-queue-*`, `hub-scheduler-1`, `hub-websocket-1`,
`hub-frontend-1`, `hub-proxy-1` = traefik, `hub-db-1` = mariadb 11.8). The
Frappe apps are **baked into the `hub-erpnext-hrms:v16` image** — the
containers have no `.git`, and `hub-backend-1` has **no node/yarn** (build
tooling lives elsewhere in a split image). Current baseline: **frappe
16.25.0 / erpnext 16.26.2**, apps `frappe erpnext hrms`, one site
`hub.tawasulcloud.com`.

There are two independent things here:

## 1. Persistent deploy — rebuild the image (recommended, includes latest ERPNext)

Files in this folder:

- `apps.json` — the app set for the new image: erpnext + hrms on
  `version-16` (public), wajha on `main` (private).
- `Containerfile` — a frappe_docker layered build that clones those apps,
  builds assets, and produces a production image. Header comments carry the
  exact build command.

Steps:

1. On a machine with Docker and network access, put a **fine-grained,
   read-only GitHub token** for `anos4444/Wajha` (Contents: Read) in
   `WAJHA_TOKEN`.
2. Run the build command from `Containerfile`'s header → produces
   `hub-erpnext-hrms:v16-next`.
3. **Back up first:** `docker exec -u frappe hub-backend-1 bench --site
   hub.tawasulcloud.com backup --with-files`.
4. Point the compose file's image tag at `:v16-next` and
   `docker compose up -d` the hub stack. Volumes (`sites`, `logs`) persist,
   so the DB and site files carry over; only the code layer changes.
5. Migrate onto the new code:
   `docker exec -u frappe hub-backend-1 bench --site hub.tawasulcloud.com
   migrate`
   then `bench --site hub.tawasulcloud.com install-app wajha` (first time
   only), and `bench --site hub.tawasulcloud.com clear-cache`.

`install-app wajha` fires `after_install` (seeds the four Shell Theme
presets + `Shell Settings`, the nine `swift_*` User custom fields, and
`Swift Theme Settings` with the Iron Man preset and all defaults);
`migrate` fires `after_migrate` (idempotent, safe to repeat).

> **ERPNext upgrade note.** `version-16` is a moving branch. Pin
> `FRAPPE_BRANCH` and the erpnext/hrms branches in `apps.json` to matching
> release **tags** if you want a reproducible upgrade rather than "latest at
> build time", and read ERPNext's release notes for any manual migration
> steps between 16.26.2 and the target.

## 2. Live preview — install Wajha into the running container (non-persistent)

Shows Wajha on the live site immediately, but is **lost when the container
is recreated** (a compose pull/redeploy), because it writes into the
container layer, not the image. The DB changes it makes (doctypes, custom
fields, settings) do persist on the `sites` volume. Use this only to
preview before the image rebuild.

Because `hub-backend-1` cannot authenticate to the private repo and has no
node, the sequence is:

1. Get the wajha source into `hub-backend-1:/home/frappe/frappe-bench/apps/wajha`
   (a token-authenticated `bench get-app`, or copy a checkout in).
2. `bench setup requirements --python` (installs wajha into the env).
3. Create the asset symlink (no build step needed — wajha ships plain
   CSS/JS): `ln -sfn apps/wajha/wajha/public sites/assets/wajha`.
4. `bench --site hub.tawasulcloud.com install-app wajha`
5. `bench --site hub.tawasulcloud.com clear-cache` and restart the backend +
   workers so the new hooks load.

## Verify (either path)

- `Swift Theme Settings` opens seeded (Iron Man, not blank).
- User menu → **Toggle Theme** shows the twelve preset cards.
- `/login` renders the themed Split layout server-side.
- A normal list view still themes correctly with the Shell's
  `apply_theme_globally` — the one Shell↔Swift interaction to eyeball.

## Housekeeping spotted during recon

`hub-backend-1` has an **orphaned `bench --site wajha-fresh.localhost serve
--port 8099`** process (pid 108438, started Aug 10) pinning ~30% CPU for
weeks, serving a site that no longer exists in `sites/`. Safe to kill
(`kill 108438`) to reclaim the CPU; unrelated to this deploy.
