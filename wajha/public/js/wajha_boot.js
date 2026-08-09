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

	window.wajha.get_config = function () {
		if (window.wajha._config_promise) return window.wajha._config_promise;
		window.wajha._config_promise = frappe.call('wajha.api.get_config')
			.then((r) => {
				window.wajha.config = r.message || { enabled: false };
				apply(window.wajha.config);
				return window.wajha.config;
			})
			.catch(() => ({ enabled: false }));
		return window.wajha._config_promise;
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

	mark_route();
	$(document).on('app_ready', function () {
		window.wajha.get_config();
		mark_route();
	});
	if (frappe.router && frappe.router.on) {
		frappe.router.on('change', mark_route);
	}
})();
