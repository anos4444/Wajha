/* Wajha boot: fetch the active theme once per session and publish it as CSS
   custom properties, optionally applying the font/colours to the whole Desk.
   Runs on every Desk page, so themed Frappe list/form surfaces stay consistent
   with the shell. */
(function () {
	if (typeof frappe === 'undefined') return;

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
		if (!cfg || !cfg.enabled) return;
		const root = document.documentElement;
		const t = cfg.tokens || {};
		Object.keys(TOKEN_MAP).forEach((k) => {
			if (t[k]) root.style.setProperty(TOKEN_MAP[k], t[k]);
		});

		if (t.font_css_url && !document.getElementById('wj-font-link')) {
			const l = document.createElement('link');
			l.id = 'wj-font-link';
			l.rel = 'stylesheet';
			l.href = t.font_css_url;
			document.head.appendChild(l);
		}

		const layout = cfg.layout || {};
		if (layout.apply_font_globally && t.font_family) {
			set_style('wj-global-font',
				`:root, body, .navbar, .page-head, .form-control, .btn, input, select, textarea {
					font-family: ${t.font_family} !important;
				}`);
		}
		if (layout.apply_theme_globally) {
			set_style('wj-global-theme',
				`:root {
					--primary: ${t.primary || '#013D28'};
					--primary-color: ${t.primary || '#013D28'};
					--text-color: ${t.ink || '#182620'};
					--border-color: ${t.border || '#E2E6E0'};
					--card-bg: ${t.surface_bg || '#fff'};
					--fg-color: ${t.surface_bg || '#fff'};
					--subtle-fg: ${t.page_bg || '#F2F3F1'};
				}
				.btn-primary { background: ${t.primary}; border-color: ${t.primary}; }`);
		}
	}

	function set_style(id, css) {
		let el = document.getElementById(id);
		if (!el) {
			el = document.createElement('style');
			el.id = id;
			document.head.appendChild(el);
		}
		el.textContent = css;
	}

	// Mark the shell route so scoped Desk-chrome overrides apply only there.
	function is_shell_route() {
		const route = (frappe.get_route_str && frappe.get_route_str()) || '';
		if (route) return route.startsWith('wajha');
		// On a hard load the router has often not resolved the route yet by the
		// time app_ready fires, and if it resolved before this listener was
		// registered no 'change' event follows either — so the class would never
		// be set and Frappe's app rail would keep squeezing the shell. Fall back
		// to the URL, which is already correct at that point.
		return /^\/(app|desk)\/wajha(\/|$)/.test(window.location.pathname);
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
	$(document).on('app_ready', function () {
		window.wajha.get_config();
		mark_route();
	});
	if (frappe.router && frappe.router.on) {
		frappe.router.on('change', mark_route);
	}
})();
