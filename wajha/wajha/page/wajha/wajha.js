/* Wajha shell engine — renders entirely from Shell Settings / Shell Theme /
   Shell Module configuration. Contains no project-specific strings or fields.

   Routes (all handled by this one Desk page):
     /app/wajha                      default module
     /app/wajha/<module_key>         a module's list
     /app/wajha/<module_key>/<name>  a record card over that list
   The record card is a route on purpose: a phone's back gesture and the
   browser's back button must close the card, not leave the app. */

frappe.pages['wajha'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, single_column: true });
	$(page.main).parent().addClass('wj-page-root');
	wrapper.wajha_shell = new WajhaShell($(page.body), page);
};

// The Desk-chrome overrides in wajha.css (no Frappe sidebar, no breadcrumb
// bar) key on body.wj-route, which wajha_boot.js sets from the URL/router. On
// Frappe 16.25 the shell was seen with that chrome still showing, i.e. with
// no marker on <body> at that moment. This page's own show/hide hooks are the
// one place guaranteed to run whenever the shell is on screen, so set the
// marker here too, and hide this page's own .page-head directly with Frappe's
// .hide (display:none !important) rather than trust the selector chain.
// Removed again on hide so other Desk pages get their chrome back.
//
// on_page_show also fires on every route change within the page, which is
// how sub-routes reach the shell. frappe.router.current_route is read
// directly (never frappe.get_route(): see CLAUDE.md) and null-checked.
frappe.pages['wajha'].on_page_show = function (wrapper) {
	document.body.classList.add('wj-route');
	$(wrapper).find('.page-head').addClass('hide');
	const route = frappe.router && frappe.router.current_route;
	if (wrapper.wajha_shell) wrapper.wajha_shell.on_route(Array.isArray(route) ? route.slice() : []);
};
frappe.pages['wajha'].on_page_hide = function () {
	document.body.classList.remove('wj-route');
};

// ERPNext's own list-view sizes, so the shell paginates the way the rest of
// the Desk does; the server clamps at MAX_PAGE_LENGTH (500), the same ceiling.
const PAGE_LENGTHS = [20, 100, 500];

// Below this width the list is a stack of cards, filters live in a bottom
// sheet and the modules sit in a bottom bar. Kept apart from the 900px drawer
// breakpoint: a tablet in portrait still reads a table comfortably.
const PHONE = window.matchMedia('(max-width: 700px)');
const MOBILE_BAR_MAX = 4;

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

const esc = (x) => frappe.utils.escape_html(String(x === null || x === undefined ? '' : x));

// Chevron pointing "forward" in the reading direction; CSS mirrors it in LTR.
const CHEVRON = '<svg class="wj-chev" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M15 6l-6 6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

class WajhaShell {
	constructor($root, page) {
		this.$root = $root.empty();
		this.page = page;
		this.reset_state(null);
		this.pending_route = null;
		window.wajha.get_config().then((cfg) => {
			this.cfg = cfg;
			if (!cfg || !cfg.enabled) return this.render_disabled();
			this.render_shell();
			this.apply_route(this.pending_route || []);
		});
		// Crossing the phone breakpoint (rotation, window resize) swaps the
		// table for cards or back; the rows already in hand are just repainted.
		const on_media = () => { if (this.meta) this.render_rows(); };
		if (PHONE.addEventListener) PHONE.addEventListener('change', on_media);
		else if (PHONE.addListener) PHONE.addListener(on_media);
	}

	reset_state(module) {
		this.state = {
			module, page_no: 1, page_length: saved_page_length(),
			filters: {}, search: '', sort: null, dir: null, rows: [], total: 0, loading: false,
		};
	}

	is_phone() { return PHONE.matches; }

	// ------------------------------------------------------------------ routing
	on_route(route) {
		if (!this.cfg) { this.pending_route = route; return; }
		this.apply_route(route);
	}

	apply_route(route) {
		const mods = this.cfg.modules || [];
		if (!mods.length) {
			this.$body.html(`<div class="wj-card wj-empty">
				${__("No modules configured yet. Create Shell Module records, or scaffold one from an existing DocType.")}</div>`);
			return;
		}
		const key = route[1] || '';
		const name = route.slice(2).join('/');
		let m = key ? mods.find((x) => x.module_key === key) : null;
		if (!m) {
			const preferred = (this.cfg.layout || {}).default_module;
			m = mods.find((x) => x.name === preferred) || mods[0];
			if (m.view_type !== 'List') m = mods.find((x) => x.view_type === 'List') || m;
		}
		if (m.view_type === 'Route Link') {
			frappe.set_route(m.route.replace(/^\/app\//, '').split('/'));
			return;
		}
		const same = this.state.module && this.state.module.module_key === m.module_key;
		if (!same) {
			this.open(m).then(() => { if (name) this.show_detail(name); });
		} else if (name) {
			this.show_detail(name);
		} else {
			this.close_detail(false);
		}
	}

	go(m) {
		this.close_drawer && this.close_drawer();
		if (m.view_type === 'Route Link') {
			frappe.set_route(m.route.replace(/^\/app\//, '').split('/'));
			return;
		}
		frappe.set_route('wajha', m.module_key);
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
						${b.logo ? `<img src="${esc(b.logo)}" alt="">` : ''}
						<div>
							<h1>${esc(b.title || '')}</h1>
							${b.subtitle ? `<p>${esc(b.subtitle)}</p>` : ''}
						</div>
					</div>
					<nav class="wj-nav" id="wj-nav"></nav>
					${layout.show_desk_link ? `<button class="wj-desk-link" type="button">
						<span>↩ ${__("العودة إلى Frappe")}</span><span class="wj-en">Frappe Desk</span>
					</button>` : ''}
					${b.footer_note ? `<div class="wj-foot">${esc(b.footer_note)}</div>` : ''}
				</aside>
				<main class="wj-main">
					<div class="wj-head">
						<div class="wj-head-start">
							<button class="wj-burger" aria-expanded="false"
								aria-label="${__("Open navigation menu")}" aria-controls="wj-nav">☰</button>
							<h2 class="wj-title"></h2>
						</div>
						<div class="wj-chips"></div>
					</div>
					<div class="wj-body"></div>
				</main>
				<nav class="wj-tabbar" aria-label="${__("Modules")}"></nav>
			</div>`).appendTo(this.$root);

		this.$nav = this.$shell.find('.wj-nav');
		this.$tabbar = this.$shell.find('.wj-tabbar');
		this.$title = this.$shell.find('.wj-title');
		this.$body = this.$shell.find('.wj-body');

		this.render_nav();
		this.render_tabbar();
		this.render_chips(layout);
		this.bind_drawer();
		// The shell hides Frappe's own sidebar and app switcher on its route, so
		// without this a user has no visible way to reach the other apps; the
		// Home workspace brings the full Desk (and its switcher) back.
		this.$shell.find('.wj-desk-link').on('click', () => frappe.set_route('home'));
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
				if (group) $(`<div class="wj-group-label">${esc(group)}</div>`).appendTo(this.$nav);
				mods.forEach((m) => {
					$(`<button class="wj-link" data-key="${esc(m.module_key)}">
						<span>${m.icon ? esc(m.icon) + ' ' : ''}${esc(m.module_label)}</span>
						${m.module_label_en ? `<span class="wj-en">${esc(m.module_label_en)}</span>` : ''}
					</button>`)
						.on('click', () => this.go(m))
						.appendTo(this.$nav);
				});
			});
	}

	// Phone bottom bar: the modules flagged for it (first four), else the
	// first four, plus "More" for the drawer. Thumb reach beats a burger at
	// the top of the screen.
	render_tabbar() {
		const mods = this.cfg.modules || [];
		let bar = mods.filter((m) => frappe.utils.cint(m.show_in_mobile_bar));
		if (!bar.length) bar = mods.slice(0, MOBILE_BAR_MAX);
		bar = bar.slice(0, MOBILE_BAR_MAX);
		this.$tabbar.empty();
		bar.forEach((m) => {
			$(`<button class="wj-tab" type="button" data-key="${esc(m.module_key)}">
				<span class="wj-tab-icon" aria-hidden="true">${esc(m.icon || '•')}</span>
				<span class="wj-tab-label">${esc(m.module_label)}</span>
			</button>`).on('click', () => this.go(m)).appendTo(this.$tabbar);
		});
		$(`<button class="wj-tab wj-tab-more" type="button" aria-controls="wj-nav">
			<span class="wj-tab-icon" aria-hidden="true">☰</span>
			<span class="wj-tab-label">${__("More")}</span>
		</button>`).on('click', () => this.open_drawer && this.open_drawer()).appendTo(this.$tabbar);
	}

	render_chips(layout) {
		const $c = this.$shell.find('.wj-chips').empty();
		if (layout.show_user_chip && this.cfg.user) {
			$(`<span class="wj-chip">${esc(this.cfg.user.full_name || '')}</span>`).appendTo($c);
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
			$shell.removeClass('wj-open wj-sheet-open');
			$burger.attr('aria-expanded', 'false').attr('aria-label', __('Open navigation menu'));
			$shell.find('.wj-filter-btn').attr('aria-expanded', 'false');
		};
		const open = () => {
			$shell.removeClass('wj-sheet-open').addClass('wj-open');
			$burger.attr('aria-expanded', 'true').attr('aria-label', __('Close navigation menu'));
			$shell.find('.wj-link').first().focus();
		};
		$burger.on('click', () => ($shell.hasClass('wj-open') ? close() : open()));
		$shell.find('.wj-backdrop').on('click', close);
		$(document).on('keydown.wajha', (e) => {
			if (e.key !== 'Escape') return;
			if ($shell.hasClass('wj-open') || $shell.hasClass('wj-sheet-open')) close();
			else if (this.$detail) this.close_detail(true);
		});
		this.close_drawer = close;
		this.open_drawer = open;
	}

	// ------------------------------------------------------------------ modules
	open(m) {
		this.close_drawer && this.close_drawer();
		this.$nav.find('.wj-link').removeAttr('aria-current');
		this.$nav.find(`.wj-link[data-key="${m.module_key}"]`).attr('aria-current', 'page');
		this.$tabbar.find('.wj-tab').removeAttr('aria-current');
		this.$tabbar.find(`.wj-tab[data-key="${m.module_key}"]`).attr('aria-current', 'page');
		this.$title.text(m.module_label || '');
		this.reset_state(m);
		if (this.$detail) { this.$detail.remove(); this.$detail = null; }
		this.$shell.removeClass('wj-detail-open');
		return this.render_list_view(m);
	}

	render_list_view(m) {
		this.$body.html(`<div class="wj-card wj-empty">${__("Loading…")}</div>`);
		return frappe.call('wajha.api.get_module_meta', { module_key: m.module_key })
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
		const $card = $('<div class="wj-card wj-list-card"></div>').appendTo(this.$body);
		const $tools = $('<div class="wj-toolbar"></div>').appendTo($card);
		const is_set = (v) => !(v === '' || v === null || v === undefined
			|| (Array.isArray(v) && v.every((x) => x === '' || x === null)));
		const active_count = () => Object.values(this.state.filters).filter(is_set).length;

		// Search stays on screen at every width; on a phone it is the whole
		// toolbar, with the filters behind one button carrying a count.
		const $search_row = $('<div class="wj-search-row"></div>').appendTo($tools);
		$(`<div class="wj-field wj-search-field"><label>${__("Search")}</label>
			<input type="search" class="wj-search" placeholder="${__("Search")}…" enterkeyhint="search"></div>`)
			.appendTo($search_row)
			.find('input').val(this.state.search || '')
			.on('input', frappe.utils.debounce(() => {
				this.state.search = this.$body.find('.wj-search').val();
				this.state.page_no = 1;
				this.load_rows();
				if (meta.map && meta.map.enabled) this.load_map();
			}, 350));
		const $filter_btn = $(`<button type="button" class="wj-btn wj-ghost wj-filter-btn" aria-controls="wj-filters" aria-expanded="false">
			<span>${__("Filter")}</span><span class="wj-filter-count" hidden></span></button>`)
			.appendTo($search_row)
			.on('click', () => {
				const open = !this.$shell.hasClass('wj-sheet-open');
				this.$shell.removeClass('wj-open').toggleClass('wj-sheet-open', open);
				$filter_btn.attr('aria-expanded', String(open));
			});
		if (!(meta.filters || []).length) $filter_btn.hide();
		if (meta.can_create) {
			$(`<button class="wj-btn wj-new">＋ ${__("New")}</button>`).appendTo($search_row)
				.on('click', () => frappe.new_doc(meta.doctype, meta.new_defaults || {}));
		}

		const $filters = $(`<div class="wj-filters" id="wj-filters">
			<div class="wj-sheet-head"><strong>${__("Filter")}</strong>
				<button type="button" class="wj-btn wj-sheet-done">${__("Done")}</button></div>
			<div class="wj-filter-fields"></div></div>`).appendTo($tools);
		const $ff = $filters.find('.wj-filter-fields');
		$filters.find('.wj-sheet-done').on('click', () => this.close_drawer());
		const $active = $('<div class="wj-active"></div>').appendTo($card);

		const sync_badges = () => {
			const n = active_count();
			$filter_btn.find('.wj-filter-count').text(n).prop('hidden', !n);
			$filter_btn.toggleClass('wj-has-filters', n > 0);
			$active.empty();
			(meta.filters || []).forEach((f) => {
				const v = this.state.filters[f.fieldname];
				if (!is_set(v)) return;
				const text = Array.isArray(v) ? v.filter(Boolean).join(' – ') : v;
				$(`<button type="button" class="wj-chip wj-active-chip">${esc(f.label)}: ${esc(text)} <span aria-hidden="true">✕</span></button>`)
					.on('click', () => { this.state.filters[f.fieldname] = ''; this.state.page_no = 1; this.paint_list_frame(); this.load_rows(); })
					.appendTo($active);
			});
		};

		(meta.filters || []).forEach((f) => {
			const current = this.state.filters[f.fieldname];
			const $f = $(`<div class="wj-field"><label>${esc(f.label)}</label></div>`).appendTo($ff);
			const commit = () => {
				this.state.page_no = 1;
				sync_badges();
				this.load_rows();
				if (meta.map && meta.map.enabled) this.load_map();
			};

			if (f.control === 'Select') {
				const $input = $('<select><option value=""></option></select>');
				(f.options || []).forEach((o) => $input.append(`<option value="${esc(o)}">${esc(o)}</option>`));
				$input.val(current || '');
				$input.appendTo($f).on('change', () => {
					this.state.filters[f.fieldname] = $input.val();
					commit();
				});
			} else if (f.control === 'MultiSelect') {
				const $input = $('<select multiple class="wj-multiselect"></select>');
				(f.options || []).forEach((o) => $input.append(`<option value="${esc(o)}">${esc(o)}</option>`));
				if (Array.isArray(current)) $input.val(current);
				$input.appendTo($f).on('change', () => {
					this.state.filters[f.fieldname] = $input.val() || [];
					commit();
				});
			} else if (f.control === 'Number Range') {
				const $lo = $(`<input type="number" inputmode="decimal" placeholder="${__("Min")}">`);
				const $hi = $(`<input type="number" inputmode="decimal" placeholder="${__("Max")}">`);
				if (Array.isArray(current)) { $lo.val(current[0] || ''); $hi.val(current[1] || ''); }
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
				if (Array.isArray(current)) { $lo.val(current[0] || ''); $hi.val(current[1] || ''); }
				$('<div class="wj-range"></div>').append($lo).append($hi).appendTo($f);
				const update = () => {
					const lo = $lo.val(), hi = $hi.val();
					this.state.filters[f.fieldname] = (lo || hi) ? [lo, hi] : '';
					commit();
				};
				$lo.on('change', update);
				$hi.on('change', update);
			} else {
				// Text and Link both use a plain text box. Applied as you type,
				// like the free-text search, rather than on Enter/blur: typing
				// into a filter and seeing nothing happen read as broken.
				// Debounced so a fast typist costs one request, not one per
				// keystroke. The server matches Text and Link with "contains"
				// (see _build_filters), so a half-typed name already narrows the
				// list instead of emptying it until the exact value is complete.
				const $input = $('<input type="text">').val(current || '');
				$input.appendTo($f).on('input', frappe.utils.debounce(() => {
					this.state.filters[f.fieldname] = $input.val();
					commit();
				}, 350));
			}
		});

		$(`<button class="wj-btn wj-ghost wj-clear">${__("Clear")}</button>`).appendTo($ff).on('click', () => {
			this.state.filters = {};
			this.state.search = '';
			this.state.page_no = 1;
			this.paint_list_frame();
			this.load_rows();
		});
		sync_badges();

		// One pager above the table and one below, kept in step. The bottom-only
		// pager sat under a full page of rows, so Previous/Next were out of view
		// and the list looked like it stopped at the first page.
		// ERPNext's list-view controls: the 20 / 100 / 500 page-size buttons and
		// a Load More that appends the next page, plus Previous/Next to jump
		// between pages when a table is long. On a phone only the count and a
		// Load More survive (see CSS); the list also grows on its own as the
		// user reaches the end.
		const pager = (pos) => `<div class="wj-pager wj-pager-${pos}"><span class="wj-count"></span>
			<span class="wj-pager-controls">
			<span class="wj-pagesize" role="group" aria-label="${__("Rows per page")}">${PAGE_LENGTHS.map((n) =>
				`<button type="button" class="wj-btn wj-ghost wj-page-length" data-n="${n}">${n}</button>`).join('')}</span>
			<button type="button" class="wj-btn wj-ghost wj-more">${__("Load More")}</button>
			<button type="button" class="wj-btn wj-ghost wj-prev">${__("Previous")}</button>
			<button type="button" class="wj-btn wj-ghost wj-next">${__("Next")}</button></span></div>`;
		$(pager('top')).appendTo($card);
		$(`<div class="wj-table-wrap"><table class="wj-table">
			<thead><tr></tr></thead><tbody></tbody></table></div>`).appendTo($card);
		$('<div class="wj-cards" role="list"></div>').appendTo($card);
		$('<div class="wj-sentinel" aria-hidden="true"></div>').appendTo($card);
		$(pager('bottom')).appendTo($card);

		const $tr = $card.find('thead tr');
		if (meta.status_field) {
			$(`<th class="wj-status-col">${__("Status")}</th>`).appendTo($tr);
		}
		(meta.columns || []).forEach((c) => {
			$(`<th style="text-align:${c.align}${c.width ? ';width:' + c.width : ''}">${esc(c.label)}</th>`)
				.appendTo($tr)
				.on('click', () => {
					this.state.dir = this.state.sort === c.fieldname && this.state.dir === 'ASC' ? 'DESC' : 'ASC';
					this.state.sort = c.fieldname;
					this.state.page_no = 1;
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
		const mark_size = () => $card.find('.wj-page-length').each((_, b) =>
			$(b).toggleClass('active', parseInt(b.dataset.n, 10) === this.state.page_length));
		mark_size();
		$card.find('.wj-page-length').on('click', (e) => {
			const n = parseInt(e.currentTarget.dataset.n, 10);
			this.state.page_length = PAGE_LENGTHS.includes(n) ? n : PAGE_LENGTHS[0];
			mark_size();
			try { window.localStorage.setItem('wajha:page_length', String(this.state.page_length)); } catch (err) { /* ignore */ }
			this.state.page_no = 1;
			this.load_rows();
		});
		$card.find('.wj-more').on('click', () => this.load_more());

		// Infinite scroll for phones: the sentinel under the cards asks for the
		// next page as it scrolls into view. Desktop keeps explicit paging.
		if (this._observer) this._observer.disconnect();
		if ('IntersectionObserver' in window) {
			this._observer = new IntersectionObserver((entries) => {
				if (!entries.some((e) => e.isIntersecting)) return;
				if (!this.is_phone() || this.state.loading) return;
				this.load_more();
			}, { rootMargin: '240px 0px' });
			this._observer.observe($card.find('.wj-sentinel')[0]);
		}

		if (meta.map && meta.map.enabled) {
			$('<div class="wj-card"><div class="wj-map" id="wj-map"></div></div>').appendTo(this.$body);
		}
	}

	load_more() {
		if (this.state.loading || this.state.rows.length >= this.state.total) return;
		this.state.page_no++;
		this.load_rows(true);
	}

	// append=true is Load More: keep what is on screen and add the next page
	// under it, the way ERPNext's list grows; the count then reads from row 1.
	load_rows(append = false) {
		const req_module = this.state.module.module_key;
		this.state.loading = true;
		if (!append && !this.state.rows.length) this.$body.find('.wj-cards').addClass('wj-skeleton');
		return frappe.call('wajha.api.get_module_data', {
			module_key: req_module,
			page: this.state.page_no,
			page_length: this.state.page_length,
			filters: JSON.stringify(this.state.filters || {}),
			search: this.state.search || '',
			sort_field: this.state.sort || '',
			sort_order: this.state.dir || '',
		}).then((r) => {
			if (!this.state.module || this.state.module.module_key !== req_module) return;
			const d = r.message || { rows: [], total: 0, page: 1, page_length: this.state.page_length };
			this.state.rows = append ? this.state.rows.concat(d.rows) : d.rows;
			this.state.total = d.total;
			this.state.page = d.page;
			this.state.page_length = d.page_length;
			this.state.first_row = append ? 1 : (d.page - 1) * d.page_length + 1;
			this.render_rows();
		}).always(() => {
			this.state.loading = false;
			this.$body.find('.wj-cards').removeClass('wj-skeleton');
		});
	}

	render_rows() {
		const meta = this.meta;
		const s = this.state;
		const $tb = this.$body.find('tbody').empty();
		const $cards = this.$body.find('.wj-cards').empty();
		const col_count = (meta.columns || []).length + (meta.status_field ? 1 : 0) || 1;
		if (!s.rows.length) {
			const empty = `<div class="wj-empty">${__("No matching records.")}</div>`;
			$tb.append(`<tr><td colspan="${col_count}">${empty}</td></tr>`);
			$cards.append(empty);
		}
		const open = (row) => {
			this._detail_via_list = true;
			frappe.set_route('wajha', s.module.module_key, row.name);
		};
		if (this.is_phone()) {
			const card = meta.card || {};
			const subtitle = card.subtitle || [];
			s.rows.forEach((row) => {
				const title = row[card.title] || row.name;
				const sub = subtitle.map((f) => {
					const col = (meta.columns || []).find((c) => c.fieldname === f);
					return this.fmt(row[f], col ? col.format : 'Text');
				}).filter(Boolean);
				$(`<button type="button" class="wj-rowcard" role="listitem">
					<span class="wj-rowcard-main">
						<span class="wj-rowcard-title">${esc(title)}</span>
						${sub.length ? `<span class="wj-rowcard-sub">${sub.join(' <i>·</i> ')}</span>` : ''}
					</span>
					${meta.status_field ? `<span class="wj-rowcard-status">${this.status_badge(row[meta.status_field])}</span>` : ''}
					${CHEVRON}
				</button>`).on('click', () => open(row)).appendTo($cards);
			});
		} else {
			s.rows.forEach((row) => {
				const $tr = $('<tr class="wj-row"></tr>').on('click', () => open(row));
				if (meta.status_field) {
					$(`<td>${this.status_badge(row[meta.status_field])}</td>`).appendTo($tr);
				}
				(meta.columns || []).forEach((c) => {
					$(`<td style="text-align:${c.align}">${this.fmt(row[c.fieldname], c.format)}</td>`).appendTo($tr);
				});
				$tr.appendTo($tb);
			});
		}
		const from = s.rows.length ? s.first_row : 0;
		const to = s.rows.length ? s.first_row + s.rows.length - 1 : 0;
		this.$body.find('.wj-count').text(`${from}–${to} ${__("of")} ${s.total}`);
		this.$body.find('.wj-prev').prop('disabled', (s.page || 1) <= 1);
		this.$body.find('.wj-next, .wj-more').prop('disabled', to >= s.total);
	}

	// After an action on the card, keep the list truthful without refetching
	// every loaded page: patch the one row's status and repaint.
	refresh_row(record) {
		const meta = this.meta;
		const row = this.state.rows.find((r) => r.name === record.name);
		if (!row || !meta.status_field || !record.status) return;
		row[meta.status_field] = record.status.value;
		this.render_rows();
	}

	fmt(v, format) {
		if (v === null || v === undefined || v === '') return '';
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
		return `<span class="wj-status-badge ${cls}">${esc(text)}</span>`;
	}

	// ------------------------------------------------------------------ record card
	show_detail(name) {
		if (this.$detail && this.$detail.data('name') === name) return;
		if (this.$detail) this.$detail.remove();
		const m = this.state.module;
		this.$detail = $(`<div class="wj-detail" role="dialog" aria-modal="true" aria-label="${esc(name)}">
			<div class="wj-detail-head">
				<button type="button" class="wj-back" aria-label="${__("Back")}">${CHEVRON}</button>
				<div class="wj-detail-title"><h3>${esc(name)}</h3><small></small></div>
				<span class="wj-detail-status"></span>
			</div>
			<div class="wj-detail-body"><div class="wj-empty">${__("Loading…")}</div></div>
			<div class="wj-detail-actions"></div>
		</div>`).data('name', name).appendTo(this.$shell);
		this.$shell.addClass('wj-detail-open');
		this.$detail.find('.wj-back').on('click', () => this.close_detail(true));
		this.$shell.find('.wj-backdrop').off('click.detail').on('click.detail', () => {
			if (this.$detail && !this.$shell.hasClass('wj-open') && !this.$shell.hasClass('wj-sheet-open')) this.close_detail(true);
		});
		frappe.call('wajha.records.get_record', { module_key: m.module_key, name })
			.then((r) => this.render_detail(r.message))
			.catch(() => {
				if (!this.$detail) return;
				this.$detail.find('.wj-detail-body').html(`<div class="wj-empty">${__("Could not load this record.")}</div>`);
			});
	}

	// navigate=true means the user closed it (back button, backdrop, Escape):
	// step the history back when the card was opened from the list, so the
	// phone's back gesture and this button do the same thing; otherwise route
	// to the list. navigate=false is the route handler telling us the URL
	// already moved on.
	close_detail(navigate) {
		if (!this.$detail) return;
		this.$detail.remove();
		this.$detail = null;
		this.$shell.removeClass('wj-detail-open');
		if (!navigate) return;
		if (this._detail_via_list) {
			this._detail_via_list = false;
			window.history.back();
		} else {
			frappe.set_route('wajha', this.state.module.module_key);
		}
	}

	render_detail(rec) {
		if (!this.$detail || !rec) return;
		const $d = this.$detail;
		$d.find('.wj-detail-title h3').text(rec.title || rec.name);
		$d.find('.wj-detail-title small').text(rec.title && rec.title !== rec.name
			? `${rec.name} · ${rec.modified}` : rec.modified);
		$d.find('.wj-detail-status').html(rec.status ? this.detail_status(rec) : '');

		const $b = $d.find('.wj-detail-body').empty();
		(rec.sections || []).forEach((sec) => {
			const $s = $('<section class="wj-dsec"></section>').appendTo($b);
			if (sec.label) $(`<h4>${esc(sec.label)}</h4>`).appendTo($s);
			const $dl = $('<dl class="wj-dl"></dl>').appendTo($s);
			sec.fields.forEach((f) => {
				const wide = ['html', 'code', 'image'].includes(f.kind) || ['Small Text', 'Long Text', 'Text'].includes(f.fieldtype);
				$(`<div class="wj-dl-row${wide ? ' wj-wide' : ''}"><dt>${esc(f.label)}</dt><dd>${this.detail_value(f)}</dd></div>`).appendTo($dl);
			});
		});
		if (!(rec.sections || []).length) $b.append(`<div class="wj-empty">${__("Nothing to show.")}</div>`);

		(rec.tables || []).forEach((t) => {
			const $s = $(`<section class="wj-dsec"><h4>${esc(t.label)} <span class="wj-muted">(${t.total})</span></h4></section>`).appendTo($b);
			const $t = $('<div class="wj-table-wrap"><table class="wj-table wj-subtable"><thead><tr></tr></thead><tbody></tbody></table></div>').appendTo($s);
			t.columns.forEach((c) => $t.find('thead tr').append(`<th>${esc(c.label)}</th>`));
			t.rows.forEach((row) => {
				const $tr = $('<tr></tr>');
				t.columns.forEach((c) => $tr.append(`<td>${esc(row[c.fieldname])}</td>`));
				$t.find('tbody').append($tr);
			});
			if (t.total > t.rows.length) $s.append(`<div class="wj-muted">${__("Showing the first {0} rows", [t.rows.length])}</div>`);
		});

		if ((rec.attachments || []).length) {
			const $s = $(`<section class="wj-dsec"><h4>${__("Attachments")}</h4><ul class="wj-files"></ul></section>`).appendTo($b);
			rec.attachments.forEach((a) => $s.find('ul').append(
				`<li><a href="${esc(a.file_url)}" target="_blank" rel="noopener">📎 ${esc(a.file_name || a.file_url)}</a></li>`));
		}

		const $c = $(`<section class="wj-dsec wj-comments"><h4>${__("Comments")}</h4><ul class="wj-comment-list"></ul>
			<div class="wj-comment-box"><textarea rows="2" placeholder="${__("Add a comment")}…"></textarea>
			<button type="button" class="wj-btn wj-ghost">${__("Send")}</button></div></section>`).appendTo($b);
		this.render_comments($c.find('ul'), rec.comments || []);
		$c.find('button').on('click', () => {
			const text = $c.find('textarea').val().trim();
			if (!text) return;
			$c.find('button').prop('disabled', true);
			frappe.call('wajha.records.add_comment', { module_key: this.state.module.module_key, name: rec.name, text })
				.then((r) => { $c.find('textarea').val(''); this.render_comments($c.find('ul'), r.message || []); })
				.always(() => $c.find('button').prop('disabled', false));
		});

		this.render_actions(rec);
		$d.find('.wj-detail-body')[0].scrollTop = 0;
	}

	render_comments($ul, comments) {
		$ul.empty();
		if (!comments.length) { $ul.append(`<li class="wj-muted">${__("No comments yet.")}</li>`); return; }
		comments.forEach((c) => $ul.append(
			`<li><div class="wj-comment-meta"><b>${esc(c.by)}</b> <span>${esc(c.when)}</span></div><div>${esc(c.text)}</div></li>`));
	}

	detail_status(rec) {
		const v = String(rec.status.value);
		const cls = v === '1' ? 'wj-status-submitted' : v === '2' ? 'wj-status-cancelled' : v === '0' ? 'wj-status-draft' : '';
		return `<span class="wj-status-badge ${cls}">${esc(rec.status.label)}</span>`;
	}

	detail_value(f) {
		switch (f.kind) {
			case 'check': return f.value ? '✓' : '✗';
			case 'html': return `<div class="wj-rich">${f.value}</div>`; // sanitised server-side
			case 'image': return `<img class="wj-dimg" src="${esc(f.value)}" alt="">`;
			case 'file': return `<a href="${esc(f.value)}" target="_blank" rel="noopener">${__("Open file")}</a>`;
			case 'code': return `<code class="wj-json">${esc(f.value)}</code>`;
			case 'color': return `<span class="wj-swatch" style="background:${esc(f.value)}"></span> ${esc(f.value)}`;
			case 'rating': {
				const n = Math.round((frappe.utils.flt(f.value) || 0) * 5);
				return '★'.repeat(n) + '☆'.repeat(Math.max(0, 5 - n));
			}
			case 'link': return f.doctype
				? `<a href="/app/${esc(frappe.router.slug(f.doctype))}/${encodeURIComponent(f.value)}">${esc(f.value)}</a>`
				: esc(f.value);
			default: return esc(f.value);
		}
	}

	render_actions(rec) {
		const $a = this.$detail.find('.wj-detail-actions').empty();
		const m = this.state.module;
		(rec.actions || []).forEach((a) => {
			const label = a.label || '';
			const cls = a.style === 'Primary' ? '' : a.style === 'Danger' ? 'wj-danger' : 'wj-ghost';
			const $btn = $(`<button type="button" class="wj-btn ${cls}">${a.icon ? esc(a.icon) + ' ' : ''}${esc(label)}</button>`)
				.attr('title', a.hint || '')
				.appendTo($a);
			$btn.on('click', () => {
				if (a.kind === 'custom' && a.type === 'Route') {
					const route = String(a.value || '').replace(/\{name\}/g, rec.name).replace(/^\/app\//, '');
					frappe.set_route(route.split('/'));
					return;
				}
				const run = () => {
					$a.find('button').prop('disabled', true);
					frappe.call('wajha.records.run_action', {
						module_key: m.module_key, name: rec.name,
						action: JSON.stringify({ kind: a.kind, value: a.value, idx: a.idx }),
					}).then((r) => {
						frappe.show_alert({ message: __("Done"), indicator: 'green' });
						this.render_detail(r.message);
						this.refresh_row(r.message);
					}).catch(() => $a.find('button').prop('disabled', false));
				};
				if (a.confirm) frappe.confirm(`${esc(label)}${a.hint ? ' ← ' + esc(a.hint) : ''}؟`, run);
				else run();
			});
		});
		$(`<button type="button" class="wj-btn wj-ghost wj-open-desk">${__("Open in Frappe")}</button>`)
			.on('click', () => frappe.set_route('Form', rec.doctype, rec.name))
			.appendTo($a);
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
					}).bindPopup(`<b>${esc(p[conf.label] || p.name)}</b>` +
						`<br><a href="/app/wajha/${encodeURIComponent(this.state.module.module_key)}/${encodeURIComponent(p.name)}">${__("Open record")}</a>`)
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
