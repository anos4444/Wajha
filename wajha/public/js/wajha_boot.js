/* Wajha boot: publish the active theme as CSS custom properties, optionally
   applying the font/colours to the whole Desk.
   Runs on every Desk page (app_include_js), so themed Frappe list/form surfaces
   stay consistent with the shell — and so anything that throws in here takes an
   unrelated Desk page down with it. Keep every branch guarded. */
(function () {
	const TOKEN_MAP = {
		primary: '--wj-primary',
		primary_dark: '--wj-primary-dark',
		accent: '--wj-accent',
		sidebar_bg: '--wj-sidebar-bg',
		sidebar_ink: '--wj-sidebar-ink',
		sidebar_active_bg: '--wj-sidebar-active-bg',
		sidebar_active_ink: '--wj-sidebar-active-ink',
		page_bg: '--wj-page-bg',
		surface_bg: '--wj-surface-bg',
		ink: '--wj-ink',
		muted_ink: '--wj-muted-ink',
		border: '--wj-border',
		danger: '--wj-danger',
		warning: '--wj-warning',
		success: '--wj-success',
		info: '--wj-info',
		radius: '--wj-radius',
		card_shadow: '--wj-shadow',
		sidebar_width: '--wj-sidebar-width',
		font_family: '--wj-font',
		base_font_size: '--wj-font-size',
	};

	// Bump the suffix when the cached shape changes, so an old browser copy is
	// ignored rather than half-read.
	const CACHE_KEY = 'wj_theme_v1';
	const SHELL_ROUTE = /^\/(app|desk)\/wajha(\/|$)/;

	/* ------------------------------------------------------ token application */

	function apply_tokens(t) {
		const root = document.documentElement;
		if (!root || !t) return;
		Object.keys(TOKEN_MAP).forEach((k) => {
			if (t[k]) root.style.setProperty(TOKEN_MAP[k], t[k]);
		});
	}

	function apply_layout(t, layout) {
		t = t || {};
		layout = layout || {};

		if (t.font_css_url && !document.getElementById('wj-font-link')) {
			const l = document.createElement('link');
			l.id = 'wj-font-link';
			l.rel = 'stylesheet';
			l.href = t.font_css_url;
			(document.head || document.documentElement).appendChild(l);
		}

		if (layout.apply_font_globally && t.font_family) {
			set_style('wj-global-font',
				`:root { --font-stack: ${css(t.font_family, 'inherit')}; }
				body, .navbar, .page-head, .form-control, .btn, input, select, textarea {
					font-family: ${css(t.font_family, 'inherit')} !important;
				}`);
		}
		if (layout.apply_theme_globally) {
			set_style('wj-global-theme', desk_theme_css(t));
		}
	}

	// Token values are authored in Shell Theme records, i.e. by an admin rather
	// than by anyone who can reach this page -- but they are interpolated raw
	// into a stylesheet, so one stray brace or semicolon would silently break
	// every rule after it. Anything outside the shape a colour/length/font
	// stack takes is dropped in favour of the fallback.
	function css(value, fallback) {
		if (typeof value !== 'string') return fallback;
		const v = value.trim();
		if (!v || /[;{}<>\\]|url\s*\(|@import|expression\s*\(/i.test(v)) return fallback;
		return v;
	}

	// Re-declare Frappe's own custom properties so the whole Desk follows the
	// active Shell Theme -- list views, forms, modals, the awesomebar -- without
	// patching core. This stylesheet is appended at runtime, so it lands after
	// frappe's and erpnext's bundles and wins on cascade order at equal
	// specificity. Every property below was confirmed to exist on a live
	// Frappe 16.31.0 Desk; core derives further variables from --primary
	// (--progress-bar-bg among them), which is why the list is shorter than the
	// number of surfaces it repaints.
	//
	// Scoped away from dark mode on purpose. Frappe's dark palette is defined
	// on [data-theme="dark"] at the same specificity, so an unscoped :root
	// block would override it -- and every Shell Theme preset is a light
	// palette, so the result is dark chrome wearing light-mode inks. Dark mode
	// therefore keeps Frappe's own colours until Shell Theme can express a dark
	// variant.
	function desk_theme_css(t) {
		const primary = css(t.primary, '#013D28');
		const ink = css(t.ink, '#182620');
		const muted = css(t.muted_ink, '#6B7C74');
		const border = css(t.border, '#E2E6E0');
		const surface = css(t.surface_bg, '#FFFFFF');
		const page = css(t.page_bg, '#F2F3F1');

		return `:root:not([data-theme="dark"]) {
			--primary: ${primary};
			--primary-color: ${primary};
			--btn-primary: ${primary};
			--progress-bar-bg: ${primary};

			--text-color: ${ink};
			--heading-color: ${ink};
			--icon-stroke: ${ink};
			--text-muted: ${muted};
			--scrollbar-thumb-color: ${muted};

			--border-color: ${border};
			--dark-border-color: ${border};
			--divider-color: ${border};
			--table-border-color: ${border};
			--sidebar-border-color: ${border};
			--control-bg-on-gray: ${border};
			--btn-default-hover-bg: ${border};
			--switch-bg: ${border};
			--scrollbar-track-color: ${border};
			--focus-default: 0px 0px 0px 2px ${border};

			--fg-color: ${surface};
			--card-bg: ${surface};
			--surface-white: ${surface};
			--surface-modal: ${surface};
			--modal-bg: ${surface};
			--popover-bg: ${surface};
			--toast-bg: ${surface};
			--awesomebar-focus-bg: ${surface};
			--sidebar-active-color: ${surface};

			--subtle-fg: ${page};
			--subtle-accent: ${page};
			--surface-menu-bar: ${page};
			--highlight-color: ${page};
			--control-bg: ${page};
			--fg-hover-color: ${page};
			--btn-default-bg: ${page};
			--sidebar-hover-color: ${page};
			--sidebar-select-color: ${page};
		}
		:root:not([data-theme="dark"]) .btn-primary {
			background: ${primary};
			border-color: ${primary};
		}`;
	}

	// The shell paints its own background from --wj-page-bg, but only once
	// wajha.css has been parsed and .wj-shell exists in the DOM. Until then the
	// browser shows its default white, which reads as a flash against any dark
	// theme. Stamping the root element covers that gap.
	//
	// Deliberately scoped to the shell route, unlike the tokens above: this
	// script runs on every Desk page, and tinting the root background of pages
	// that are not ours is exactly the kind of global side effect that has
	// broken unrelated Desk pages before.
	function stamp_page_bg(t) {
		if (!t || !t.page_bg) return;
		if (!SHELL_ROUTE.test(window.location.pathname)) return;
		document.documentElement.style.backgroundColor = t.page_bg;
	}

	function clear_applied() {
		const root = document.documentElement;
		if (!root) return;
		Object.keys(TOKEN_MAP).forEach((k) => root.style.removeProperty(TOKEN_MAP[k]));
		root.style.backgroundColor = '';
		['wj-global-font', 'wj-global-theme'].forEach((id) => {
			const el = document.getElementById(id);
			if (el) el.textContent = '';
		});
	}

	function set_style(id, css) {
		let el = document.getElementById(id);
		if (!el) {
			el = document.createElement('style');
			el.id = id;
			(document.head || document.documentElement).appendChild(el);
		}
		el.textContent = css;
	}

	/* ------------------------------------------------- last-known-good cache */

	function cookie(name) {
		try {
			const m = ('; ' + document.cookie).match('; ' + name + '=([^;]*)');
			if (!m) return '';
			return decodeURIComponent(m[1].replace(/^"|"$/g, ''));
		} catch (e) {
			return '';
		}
	}

	function read_cache() {
		try {
			const raw = window.localStorage.getItem(CACHE_KEY);
			if (!raw) return null;
			const c = JSON.parse(raw);
			if (!c || !c.tokens) return null;
			// On a shared browser the previous user's theme must not paint for
			// the next one. frappe.boot is not available this early, but the
			// user_id cookie is, and it changes on login/logout.
			if (c.user !== cookie('user_id')) return null;
			return c;
		} catch (e) {
			// disabled storage, private mode, or a corrupt value — painting
			// nothing is a worse first frame, never a broken page
			return null;
		}
	}

	function write_cache(cfg) {
		try {
			window.localStorage.setItem(CACHE_KEY, JSON.stringify({
				user: cookie('user_id'),
				tokens: cfg.tokens || {},
				layout: cfg.layout || {},
			}));
		} catch (e) {
			// quota or private mode: this load is still themed from the boot
			// payload, only the next one loses its head start
		}
	}

	function clear_cache() {
		try {
			window.localStorage.removeItem(CACHE_KEY);
		} catch (e) {
			/* nothing to do */
		}
	}

	/* -------------------------------------------------------- paint-critical */

	// Everything above the `frappe` guard runs without frappe, without a body,
	// and must not throw.
	//
	// The boot payload (wajha/boot.py) themes the first paint with no request,
	// but only when boot actually carried it: a boot that failed soft, a Guest
	// session, or a page where this script is evaluated before frappe.boot is
	// assigned all fall through to the HTTP call, which lands after first paint
	// — a visible flash of unthemed Desk on every load. The last-known-good
	// theme closes that window. It is overwritten by the authoritative config
	// further down in this same script, so a stale copy survives at most the
	// span between two synchronous statements.
	const cached = read_cache();
	if (cached) {
		apply_tokens(cached.tokens);
		apply_layout(cached.tokens, cached.layout);
		stamp_page_bg(cached.tokens);
	}

	if (typeof frappe === 'undefined') return;

	window.wajha = window.wajha || {};

	// The config normally arrives in the boot payload (see wajha/boot.py), so the
	// theme can be published before first paint with no request at all. The HTTP
	// call is kept as a fallback for the cases boot cannot cover: a boot that
	// failed soft, and re-reading the config after settings change in-session.
	function boot_config() {
		return (window.frappe && frappe.boot && frappe.boot.wajha_config) || null;
	}

	window.wajha.get_config = function () {
		if (window.wajha._config_promise) return window.wajha._config_promise;
		const booted = boot_config();
		if (booted) {
			window.wajha.config = booted;
			apply(booted);
			window.wajha._config_promise = Promise.resolve(booted);
			return window.wajha._config_promise;
		}
		window.wajha._config_promise = frappe.call('wajha.api.get_config')
			.then((r) => {
				window.wajha.config = r.message || { enabled: false };
				apply(window.wajha.config);
				return window.wajha.config;
			})
			.catch(() => ({ enabled: false }));
		return window.wajha._config_promise;
	};

	// Drop the memoised config so the next get_config() re-fetches over HTTP.
	// Needed after Shell Settings or Shell Theme change within a session, since
	// the boot payload is only rebuilt on a full page load.
	window.wajha.refresh_config = function () {
		window.wajha._config_promise = null;
		if (window.frappe && frappe.boot) frappe.boot.wajha_config = null;
		return window.wajha.get_config();
	};

	function apply(cfg) {
		if (!cfg || !cfg.enabled) {
			// The shell was disabled, or this user lost access to it, since the
			// last load. The cached theme has already painted by this point, so
			// undo it and drop the copy — otherwise a disabled shell keeps
			// repainting its old colours on every load indefinitely.
			if (cached) clear_applied();
			clear_cache();
			return;
		}
		const t = cfg.tokens || {};
		apply_tokens(t);
		apply_layout(t, cfg.layout);
		stamp_page_bg(t);
		write_cache(cfg);
	}

	// Mark the shell route so scoped Desk-chrome overrides apply only there.
	//
	// Reads frappe.router.current_route directly instead of going through
	// frappe.get_route_str()/frappe.get_route() -- both do
	// `frappe.router.current_route.join("/")` with no null guard in Frappe
	// core, and current_route is genuinely null on a hard load (this script
	// calls mark_route() before the router has resolved anything) and for a
	// moment during some route transitions. The uncaught TypeError killed
	// this whole IIFE, so get_config was never even registered and the page
	// rendered blank -- reported live on Shell Settings.
	function is_shell_route() {
		const route = frappe.router && frappe.router.current_route;
		if (Array.isArray(route) && route.length) return route[0] === 'wajha';
		// On a hard load the router has often not resolved the route yet by the
		// time app_ready fires, and if it resolved before this listener was
		// registered no 'change' event follows either — so the class would never
		// be set and Frappe's app rail would keep squeezing the shell. Fall back
		// to the URL, which is already correct at that point.
		return SHELL_ROUTE.test(window.location.pathname);
	}

	function mark_route() {
		if (!document.body) return;
		document.body.classList.toggle('wj-route', is_shell_route());
	}

	// Publish the theme as early as this script runs. With the config already in
	// the boot payload this is synchronous, so the custom properties are set
	// before the browser paints and there is no flash of unthemed Desk. Without
	// it, fall through to app_ready and the HTTP call as before.
	if (boot_config()) window.wajha.get_config();

	mark_route();
	// This script is included in <head>, so on a hard load there is no body to
	// class yet and the chrome overrides would wait for app_ready. Catching
	// DOMContentLoaded applies them as soon as the body exists instead.
	if (!document.body) {
		document.addEventListener('DOMContentLoaded', mark_route, { once: true });
	}
	$(document).on('app_ready', function () {
		window.wajha.get_config();
		mark_route();
	});
	if (frappe.router && frappe.router.on) {
		frappe.router.on('change', mark_route);
	}
})();
