/* Wajha shell engine — renders entirely from Shell Settings / Shell Theme /
   Shell Module configuration. Contains no project-specific strings or fields. */

frappe.pages['wajha'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, single_column: true });
	$(page.main).parent().addClass('wj-page-root');
	new WajhaShell($(page.body), page);
};

// The Desk-chrome overrides in wajha.css (no Frappe sidebar, no breadcrumb
// bar) key on body.wj-route, which wajha_boot.js sets from the URL/router. On
// Frappe 16.25 the shell was seen with that chrome still showing, i.e. with
// no marker on <body> at that moment. This page's own show/hide hooks are the
// one place guaranteed to run whenever the shell is on screen, so set the
// marker here too, and hide this page's own .page-head directly with Frappe's
// .hide (display:none !important) rather than trust the selector chain.
// Removed again on hide so other Desk pages get their chrome back.
frappe.pages['wajha'].on_page_show = function (wrapper) {
	document.body.classList.add('wj-route');
	$(wrapper).find('.page-head').addClass('hide');
};
frappe.pages['wajha'].on_page_hide = function () {
	document.body.classList.remove('wj-route');
};

const PAGE_LENGTHS = [20, 50, 100, 200];

// The rows-per-page choice is a personal browsing preference, like a column
// width, so it lives in this browser rather than on the module record: one
// user reading 200 rows at a time must not change what everyone else sees.
// Anything outside the offered set (a stale or edited value) falls back to
// the default rather than reaching the server as a request it would clamp.
function saved_page_length() {
	try {
		const n = parseInt(window.localStorage.getItem('wajha:page_length'), 10);
		if (PAGE_LENGTHS.includes(n)) return n;
	} catch (e) { /* storage disabled or private mode: default is fine */ }
	return PAGE_LENGTHS[0];
}

class WajhaShell {
	constructor($root, page) {
		this.$root = $root.empty();
		this.page = page;
		this.state = { module: null, page_no: 1, page_length: saved_page_length(), filters: {}, search: '', sort: null, dir: null };
		window.wajha.get_config().then((cfg) => {
			this.cfg = cfg;
			if (!cfg || !cfg.enabled) return this.render_disabled();
			this.render_shell();
			this.route_initial();
		});
	}

	// ------------------------------------------------------------------ chrome
	render_disabled() {
		this.$root.html(`<div class="wj-empty">
			${__("The shell is not enabled. Enable it in Shell Settings.")}
		</div>`);
	}

	render_shell() {
		const b = this.cfg.brand || {};
		const layout = this.cfg.layout || {};
		this.$shell = $(`
			<div class="wj-shell">
				<div class="wj-backdrop" hidden></div>
				<aside class="wj-sidebar" role="navigation" aria-label="${__("Main navigation")}">
					<div class="wj-brand">
						${b.logo ? `<img src="${frappe.utils.escape_html(b.logo)}" alt="">` : ''}
						<div>
							<h1>${frappe.utils.escape_html(b.title || '')}</h1>
							${b.subtitle ? `<p>${frappe.utils.escape_html(b.subtitle)}</p>` : ''}
						</div>
					</div>
					<nav class="wj-nav"></nav>
					${b.footer_note ? `<div class="wj-foot">${frappe.utils.escape_html(b.footer_note)}</div>` : ''}
				</aside>
				<main class="wj-main">
					<div class="wj-head">
						<div style="display:flex;align-items:center;gap:10px">
							<button class="wj-burger" aria-expanded="false"
								aria-label="${__("Open navigation menu")}" aria-controls="wj-nav">☰</button>
							<h2 class="wj-title"></h2>
						</div>
						<div class="wj-chips"></div>
					</div>
					<div class="wj-body"></div>
				</main>
			</div>`).appendTo(this.$root);

		this.$nav = this.$shell.find('.wj-nav');
		this.$title = this.$shell.find('.wj-title');
		this.$body = this.$shell.find('.wj-body');

		this.render_nav();
		this.render_chips(layout);
		this.bind_drawer();
	}

	render_nav() {
		const groups = new Map();
		(this.cfg.modules || []).forEach((m) => {
			const g = m.group || '';
			if (!groups.has(g)) groups.set(g, []);
			groups.get(g).push(m);
		});
		// ungrouped first, then named groups
		[...groups.entries()]
			.sort((a, b) => (a[0] === '' ? -1 : b[0] === '' ? 1 : a[0].localeCompare(b[0], 'ar')))
			.forEach(([group, mods]) => {
				if (group) $(`<div class="wj-group-label">${frappe.utils.escape_html(group)}</div>`).appendTo(this.$nav);
				mods.forEach((m) => {
					$(`<button class="wj-link" data-key="${frappe.utils.escape_html(m.module_key)}">
						<span>${m.icon ? frappe.utils.escape_html(m.icon) + ' ' : ''}${frappe.utils.escape_html(m.module_label)}</span>
						${m.module_label_en ? `<span class="wj-en">${frappe.utils.escape_html(m.module_label_en)}</span>` : ''}
					</button>`)
						.on('click', () => this.open(m))
						.appendTo(this.$nav);
				});
			});
	}

	render_chips(layout) {
		const $c = this.$shell.find('.wj-chips').empty();
		if (layout.show_user_chip && this.cfg.user) {
			$(`<span class="wj-chip">${frappe.utils.escape_html(this.cfg.user.full_name || '')}</span>`).appendTo($c);
		}
		if (layout.show_clock) {
			const $clock = $('<span class="wj-chip"></span>').appendTo($c);
			const tick = () => $clock.text(frappe.datetime.now_datetime().replace('T', ' '));
			tick();
			this._clock = setInterval(tick, 1000);
			$(window).on('hashchange', () => clearInterval(this._clock));
		}
	}

	bind_drawer() {
		const $shell = this.$shell;
		const $burger = $shell.find('.wj-burger');
		const close = () => {
			$shell.removeClass('wj-open');
			$burger.attr('aria-expanded', 'false').attr('aria-label', __('Open navigation menu'));
		};
		const open = () => {
			$shell.addClass('wj-open');
			$burger.attr('aria-expanded', 'true').attr('aria-label', __('Close navigation menu'));
			$shell.find('.wj-link').first().focus();
		};
		$burger.on('click', () => ($shell.hasClass('wj-open') ? close() : open()));
		$shell.find('.wj-backdrop').on('click', close);
		$(document).on('keydown.wajha', (e) => {
			if (e.key === 'Escape') close();
		});
		this.close_drawer = close;
	}

	route_initial() {
		const mods = this.cfg.modules || [];
		if (!mods.length) {
			this.$body.html(`<div class="wj-card wj-empty">
				${__("No modules configured yet. Create Shell Module records, or scaffold one from an existing DocType.")}</div>`);
			return;
		}
		const preferred = (this.cfg.layout || {}).default_module;
		this.open(mods.find((m) => m.name === preferred) || mods[0]);
	}

	// ------------------------------------------------------------------ modules
	open(m) {
		this.close_drawer && this.close_drawer();
		this.$nav.find('.wj-link').removeAttr('aria-current');
		this.$nav.find(`.wj-link[data-key="${m.module_key}"]`).attr('aria-current', 'page');
		this.$title.text(m.module_label || '');
		this.state = { module: m, page_no: 1, page_length: saved_page_length(), filters: {}, search: '', sort: null, dir: null };

		if (m.view_type === 'Route Link') {
			this.$body.html(`<div class="wj-card wj-empty">${__("Opening…")}</div>`);
			frappe.set_route(m.route.replace(/^\/app\//, '').split('/'));
			return;
		}
		this.render_list_view(m);
	}

	render_list_view(m) {
		this.$body.html(`<div class="wj-card wj-empty">${__("Loading…")}</div>`);
		frappe.call('wajha.api.get_module_meta', { module_key: m.module_key })
			.then((r) => {
				this.meta = r.message;
				this.paint_list_frame();
				this.load_rows();
				if (this.meta.map && this.meta.map.enabled) this.load_map();
			})
			.catch(() => this.$body.html(`<div class="wj-card wj-empty">${__("Could not load this module.")}</div>`));
	}

	paint_list_frame() {
		const meta = this.meta;
		this.$body.empty();
		const $card = $('<div class="wj-card"></div>').appendTo(this.$body);
		const $tools = $('<div class="wj-toolbar"></div>').appendTo($card);

		// free-text search
		$(`<div class="wj-field"><label>${__("Search")}</label><input type="search" class="wj-search"></div>`)
			.appendTo($tools)
			.find('input')
			.on('input', frappe.utils.debounce(() => {
				this.state.search = this.$body.find('.wj-search').val();
				this.state.page_no = 1;
				this.load_rows();
				if (meta.map && meta.map.enabled) this.load_map();
			}, 350));

		(meta.filters || []).forEach((f) => {
			const $f = $(`<div class="wj-field"><label>${frappe.utils.escape_html(f.label)}</label></div>`)
				.appendTo($tools);
			const commit = () => {
				this.state.page_no = 1;
				this.load_rows();
				if (meta.map && meta.map.enabled) this.load_map();
			};

			if (f.control === 'Select') {
				const $input = $('<select><option value=""></option></select>');
				(f.options || []).forEach((o) => $input.append(`<option value="${frappe.utils.escape_html(o)}">${frappe.utils.escape_html(o)}</option>`));
				$input.appendTo($f).on('change', () => {
					this.state.filters[f.fieldname] = $input.val();
					commit();
				});
			} else if (f.control === 'MultiSelect') {
				const $input = $('<select multiple class="wj-multiselect"></select>');
				(f.options || []).forEach((o) => $input.append(`<option value="${frappe.utils.escape_html(o)}">${frappe.utils.escape_html(o)}</option>`));
				$input.appendTo($f).on('change', () => {
					this.state.filters[f.fieldname] = $input.val() || [];
					commit();
				});
			} else if (f.control === 'Number Range') {
				const $lo = $(`<input type="number" placeholder="${__("Min")}">`);
				const $hi = $(`<input type="number" placeholder="${__("Max")}">`);
				$('<div class="wj-range"></div>').append($lo).append($hi).appendTo($f);
				const update = () => {
					const lo = $lo.val(), hi = $hi.val();
					this.state.filters[f.fieldname] = (lo !== '' || hi !== '') ? [lo, hi] : '';
					commit();
				};
				$lo.on('change', update);
				$hi.on('change', update);
			} else if (f.control === 'Date Range' || f.control === 'Datetime Range') {
				const type = f.control === 'Datetime Range' ? 'datetime-local' : 'date';
				const $lo = $(`<input type="${type}">`);
				const $hi = $(`<input type="${type}">`);
				$('<div class="wj-range"></div>').append($lo).append($hi).appendTo($f);
				const update = () => {
					const lo = $lo.val(), hi = $hi.val();
					this.state.filters[f.fieldname] = (lo || hi) ? [lo, hi] : '';
					commit();
				};
				$lo.on('change', update);
				$hi.on('change', update);
			} else {
				// Text and Link both use a plain text box; Link matches on the
				// exact document name (server-side "=" once a value is set).
				// Applied as you type, like the free-text search, rather than on
				// Enter/blur: typing into a filter and seeing nothing happen read
				// as broken. Debounced so a fast typist costs one request, not one
				// per keystroke. The server matches Text and Link with "contains"
				// (see _build_filters), so a half-typed name already narrows the
				// list instead of emptying it until the exact value is complete.
				const $input = $('<input type="text">');
				$input.appendTo($f).on('input', frappe.utils.debounce(() => {
					this.state.filters[f.fieldname] = $input.val();
					commit();
				}, 350));
			}
		});

		$(`<button class="wj-btn wj-ghost">${__("Clear")}</button>`).appendTo($tools).on('click', () => {
			this.state.filters = {};
			this.state.search = '';
			this.paint_list_frame();
			this.load_rows();
		});

		if (meta.can_create) {
			$(`<button class="wj-btn">${__("New")}</button>`).appendTo($tools)
				.on('click', () => frappe.new_doc(meta.doctype));
		}

		// One pager above the table and one below, kept in step. The bottom-only
		// pager sat under a full page of rows, so Previous/Next were out of view
		// and the list looked like it stopped at the first page. The rows-per-page
		// choice mirrors ERPNext's list view; the server clamps it (200).
		const pager = (pos) => `<div class="wj-pager wj-pager-${pos}"><span class="wj-count"></span>
			<span class="wj-pager-controls">
			<label class="wj-pagesize">${__("Rows per page")}
			<select class="wj-page-length">${PAGE_LENGTHS.map((n) => `<option value="${n}">${n}</option>`).join('')}</select></label>
			<button class="wj-btn wj-ghost wj-prev">${__("Previous")}</button>
			<button class="wj-btn wj-ghost wj-next">${__("Next")}</button></span></div>`;
		$(pager('top')).appendTo($card);
		$(`<div class="wj-table-wrap"><table class="wj-table">
			<thead><tr></tr></thead><tbody></tbody></table></div>`).appendTo($card);
		$(pager('bottom')).appendTo($card);

		const $tr = $card.find('thead tr');
		if (meta.status_field) {
			$(`<th class="wj-status-col">${__("Status")}</th>`).appendTo($tr);
		}
		(meta.columns || []).forEach((c) => {
			$(`<th style="text-align:${c.align}${c.width ? ';width:' + c.width : ''}">${frappe.utils.escape_html(c.label)}</th>`)
				.appendTo($tr)
				.on('click', () => {
					this.state.dir = this.state.sort === c.fieldname && this.state.dir === 'ASC' ? 'DESC' : 'ASC';
					this.state.sort = c.fieldname;
					this.load_rows();
				});
		});

		$card.find('.wj-prev').on('click', () => {
			if (this.state.page_no > 1) { this.state.page_no--; this.load_rows(); }
		});
		$card.find('.wj-next').on('click', () => {
			this.state.page_no++;
			this.load_rows();
		});
		$card.find('.wj-page-length').val(String(this.state.page_length)).on('change', (e) => {
			const n = parseInt($(e.currentTarget).val(), 10);
			this.state.page_length = PAGE_LENGTHS.includes(n) ? n : PAGE_LENGTHS[0];
			$card.find('.wj-page-length').val(String(this.state.page_length));
			try { window.localStorage.setItem('wajha:page_length', String(this.state.page_length)); } catch (err) { /* ignore */ }
			this.state.page_no = 1;
			this.load_rows();
		});

		if (meta.map && meta.map.enabled) {
			$('<div class="wj-card"><div class="wj-map" id="wj-map"></div></div>').appendTo(this.$body);
		}
	}

	load_rows() {
		const meta = this.meta;
		frappe.call('wajha.api.get_module_data', {
			module_key: this.state.module.module_key,
			page: this.state.page_no,
			page_length: this.state.page_length,
			filters: JSON.stringify(this.state.filters || {}),
			search: this.state.search || '',
			sort_field: this.state.sort || '',
			sort_order: this.state.dir || '',
		}).then((r) => {
			const d = r.message || { rows: [], total: 0 };
			const $tb = this.$body.find('tbody').empty();
			const col_count = (meta.columns || []).length + (meta.status_field ? 1 : 0) || 1;
			if (!d.rows.length) {
				$tb.append(`<tr><td colspan="${col_count}">
					<div class="wj-empty">${__("No matching records.")}</div></td></tr>`);
			}
			d.rows.forEach((row) => {
				const $tr = $('<tr></tr>').on('click', () =>
					frappe.set_route('Form', d.doctype, row.name));
				if (meta.status_field) {
					$(`<td>${this.status_badge(row[meta.status_field])}</td>`).appendTo($tr);
				}
				(meta.columns || []).forEach((c) => {
					$(`<td style="text-align:${c.align}">${this.fmt(row[c.fieldname], c.format)}</td>`).appendTo($tr);
				});
				$tr.appendTo($tb);
			});
			const from = (d.page - 1) * d.page_length + (d.rows.length ? 1 : 0);
			const to = (d.page - 1) * d.page_length + d.rows.length;
			this.$body.find('.wj-count').text(`${from}–${to} ${__("of")} ${d.total}`);
			this.$body.find('.wj-prev').prop('disabled', d.page <= 1);
			this.$body.find('.wj-next').prop('disabled', to >= d.total);
		});
	}

	fmt(v, format) {
		if (v === null || v === undefined || v === '') return '';
		const esc = (x) => frappe.utils.escape_html(String(x));
		// frappe.format() returns markup for the numeric fieldtypes (Currency,
		// Percent and Int come back wrapped in an alignment <div>), so escaping
		// its output directly would print that markup as visible text. Take the
		// text content instead — <template> is inert, so nothing in the string
		// can load or execute while we unwrap it.
		const fmt_text = (value, fieldtype) => {
			const tpl = document.createElement('template');
			tpl.innerHTML = String(frappe.format(value, { fieldtype: fieldtype }));
			return esc(tpl.content.textContent || '');
		};
		switch (format) {
			case 'Badge': return `<span class="wj-badge">${esc(v)}</span>`;
			case 'Percent': return fmt_text(v, 'Percent');
			case 'Currency': return fmt_text(v, 'Currency');
			case 'Date': return esc(frappe.datetime.str_to_user(v));
			case 'Datetime': return esc(frappe.datetime.str_to_user(v));
			case 'Duration': return fmt_text(v, 'Duration');
			case 'Checkbox': return frappe.utils.cint(v) ? '✓' : '✗';
			case 'Rating': {
				const n = Math.round((frappe.utils.flt(v) || 0) * 5);
				return '★'.repeat(n) + '☆'.repeat(Math.max(0, 5 - n));
			}
			case 'Attachment':
				return `<a href="${esc(v)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${__("Open file")}</a>`;
			case 'Image':
				return `<img src="${esc(v)}" alt="" style="max-width:60px;max-height:40px;border-radius:4px;object-fit:cover">`;
			case 'MultiSelectBadge': {
				const parts = Array.isArray(v) ? v : String(v).split(',').map((s) => s.trim()).filter(Boolean);
				return parts.map((p) => `<span class="wj-badge">${esc(p)}</span>`).join('');
			}
			case 'JSON': {
				let text = v;
				try { text = typeof v === 'string' ? JSON.stringify(JSON.parse(v), null, 1) : JSON.stringify(v, null, 1); }
				catch (e) { text = String(v); }
				return `<code class="wj-json">${esc(text)}</code>`;
			}
			case 'Geolocation': return esc(__("(location)"));
			default: return esc(v);
		}
	}

	status_badge(value) {
		if (value === null || value === undefined || value === '') return '';
		const labels = this.meta.docstatus_labels;
		let text = String(value);
		let cls = '';
		if (labels && labels[String(value)] !== undefined) {
			text = __(labels[String(value)]);
			cls = String(value) === '1' ? 'wj-status-submitted'
				: String(value) === '2' ? 'wj-status-cancelled' : 'wj-status-draft';
		}
		return `<span class="wj-status-badge ${cls}">${frappe.utils.escape_html(text)}</span>`;
	}

	// ------------------------------------------------------------------ map
	load_map() {
		const conf = this.meta.map;
		this.ensure_leaflet().then(() => {
			frappe.call('wajha.api.get_map_points', {
				module_key: this.state.module.module_key,
				filters: JSON.stringify(this.state.filters || {}),
				search: this.state.search || '',
			}).then((r) => {
				const pts = r.message || [];
				const el = document.getElementById('wj-map');
				if (!el) return;
				if (this._map) { this._map.remove(); this._map = null; }
				const map = L.map(el).setView(conf.center, conf.zoom);
				this._map = map;
				L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
					maxZoom: 18, attribution: '© OpenStreetMap',
				}).addTo(map);
				const palette = ['--wj-primary', '--wj-accent', '--wj-info', '--wj-success', '--wj-warning', '--wj-danger']
					.map((t) => getComputedStyle(document.documentElement).getPropertyValue(t).trim() || '#555');
				const seen = new Map();
				pts.forEach((p) => {
					const key = conf.color ? p[conf.color] : '';
					if (key && !seen.has(key)) seen.set(key, palette[seen.size % palette.length]);
					const color = key ? seen.get(key) : palette[0];
					L.circleMarker([p[conf.lat], p[conf.lon]], {
						radius: 5, color, fillColor: color, fillOpacity: .85, weight: 1,
					}).bindPopup(`<b>${frappe.utils.escape_html(p[conf.label] || p.name)}</b>` +
						`<br><a href="/app/${frappe.router.slug(this.meta.doctype)}/${encodeURIComponent(p.name)}">${__("Open record")}</a>`)
						.addTo(map);
				});
			});
		}).catch(() => {
			$('#wj-map').html(`<div class="wj-empty">${__("The map library could not be loaded. Closed networks require a local tile server.")}</div>`);
		});
	}

	ensure_leaflet() {
		if (window.L) return Promise.resolve();
		return new Promise((resolve, reject) => {
			const css = document.createElement('link');
			css.rel = 'stylesheet';
			css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
			document.head.appendChild(css);
			const js = document.createElement('script');
			js.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
			js.onload = resolve;
			js.onerror = reject;
			setTimeout(reject, 10000);
			document.head.appendChild(js);
		});
	}
}
