/* Wajha shell engine — renders entirely from Shell Settings / Shell Theme /
   Shell Module configuration. Contains no project-specific strings or fields. */

frappe.pages['wajha'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, single_column: true });
	$(page.main).parent().addClass('wj-page-root');
	new WajhaShell($(page.body), page);
};

class WajhaShell {
	constructor($root, page) {
		this.$root = $root.empty();
		this.page = page;
		this.state = { module: null, page_no: 1, filters: {}, search: '', sort: null, dir: null };
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
			الواجهة غير مفعّلة. فعّلها من <b>إعدادات الواجهة (Shell Settings)</b>.
		</div>`);
	}

	render_shell() {
		const b = this.cfg.brand || {};
		const layout = this.cfg.layout || {};
		this.$shell = $(`
			<div class="wj-shell">
				<div class="wj-backdrop" hidden></div>
				<aside class="wj-sidebar" role="navigation" aria-label="التنقل الرئيسي">
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
								aria-label="فتح قائمة التنقل" aria-controls="wj-nav">☰</button>
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
			$burger.attr('aria-expanded', 'false').attr('aria-label', 'فتح قائمة التنقل');
		};
		const open = () => {
			$shell.addClass('wj-open');
			$burger.attr('aria-expanded', 'true').attr('aria-label', 'إغلاق قائمة التنقل');
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
				لا توجد وحدات مُهيّأة بعد. أنشئ وحدات من <b>Shell Module</b>،
				أو استخدم أداة التهيئة السريعة من DocType موجود.</div>`);
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
		this.state = { module: m, page_no: 1, filters: {}, search: '', sort: null, dir: null };

		if (m.view_type === 'Route Link') {
			this.$body.html(`<div class="wj-card wj-empty">جارٍ الفتح…</div>`);
			frappe.set_route(m.route.replace(/^\/app\//, '').split('/'));
			return;
		}
		this.render_list_view(m);
	}

	render_list_view(m) {
		this.$body.html('<div class="wj-card wj-empty">جارٍ التحميل…</div>');
		frappe.call('wajha.api.get_module_meta', { module_key: m.module_key })
			.then((r) => {
				this.meta = r.message;
				this.paint_list_frame();
				this.load_rows();
				if (this.meta.map && this.meta.map.enabled) this.load_map();
			})
			.catch(() => this.$body.html('<div class="wj-card wj-empty">تعذّر تحميل الوحدة.</div>'));
	}

	paint_list_frame() {
		const meta = this.meta;
		this.$body.empty();
		const $card = $('<div class="wj-card"></div>').appendTo(this.$body);
		const $tools = $('<div class="wj-toolbar"></div>').appendTo($card);

		// free-text search
		$(`<div class="wj-field"><label>بحث</label><input type="search" class="wj-search"></div>`)
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
			let $input;
			if (f.control === 'Select') {
				$input = $('<select><option value=""></option></select>');
				(f.options || []).forEach((o) => $input.append(`<option value="${frappe.utils.escape_html(o)}">${frappe.utils.escape_html(o)}</option>`));
			} else {
				$input = $('<input type="text">');
			}
			$input.appendTo($f).on('change', () => {
				this.state.filters[f.fieldname] = $input.val();
				this.state.page_no = 1;
				this.load_rows();
				if (meta.map && meta.map.enabled) this.load_map();
			});
		});

		$('<button class="wj-btn wj-ghost">تفريغ</button>').appendTo($tools).on('click', () => {
			this.state.filters = {};
			this.state.search = '';
			this.paint_list_frame();
			this.load_rows();
		});

		if (meta.can_create) {
			$('<button class="wj-btn">جديد</button>').appendTo($tools)
				.on('click', () => frappe.new_doc(meta.doctype));
		}

		$(`<div class="wj-table-wrap"><table class="wj-table">
			<thead><tr></tr></thead><tbody></tbody></table></div>
			<div class="wj-pager"><span class="wj-count"></span>
			<span><button class="wj-btn wj-ghost wj-prev">السابق</button>
			<button class="wj-btn wj-ghost wj-next">التالي</button></span></div>`).appendTo($card);

		const $tr = $card.find('thead tr');
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

		if (meta.map && meta.map.enabled) {
			$('<div class="wj-card"><div class="wj-map" id="wj-map"></div></div>').appendTo(this.$body);
		}
	}

	load_rows() {
		const meta = this.meta;
		frappe.call('wajha.api.get_module_data', {
			module_key: this.state.module.module_key,
			page: this.state.page_no,
			filters: JSON.stringify(this.state.filters || {}),
			search: this.state.search || '',
			sort_field: this.state.sort || '',
			sort_order: this.state.dir || '',
		}).then((r) => {
			const d = r.message || { rows: [], total: 0 };
			const $tb = this.$body.find('tbody').empty();
			if (!d.rows.length) {
				$tb.append(`<tr><td colspan="${(meta.columns || []).length || 1}">
					<div class="wj-empty">لا توجد سجلات مطابقة.</div></td></tr>`);
			}
			d.rows.forEach((row) => {
				const $tr = $('<tr></tr>').on('click', () =>
					frappe.set_route('Form', d.doctype, row.name));
				(meta.columns || []).forEach((c) => {
					$(`<td style="text-align:${c.align}">${this.fmt(row[c.fieldname], c.format)}</td>`).appendTo($tr);
				});
				$tr.appendTo($tb);
			});
			const from = (d.page - 1) * d.page_length + (d.rows.length ? 1 : 0);
			const to = (d.page - 1) * d.page_length + d.rows.length;
			this.$body.find('.wj-count').text(`${from}–${to} من ${d.total}`);
			this.$body.find('.wj-prev').prop('disabled', d.page <= 1);
			this.$body.find('.wj-next').prop('disabled', to >= d.total);
		});
	}

	fmt(v, format) {
		if (v === null || v === undefined || v === '') return '';
		const esc = (x) => frappe.utils.escape_html(String(x));
		switch (format) {
			case 'Badge': return `<span class="wj-badge">${esc(v)}</span>`;
			case 'Percent': return esc(frappe.format(v, { fieldtype: 'Percent' }));
			case 'Currency': return esc(frappe.format(v, { fieldtype: 'Currency' }));
			case 'Date': return esc(frappe.datetime.str_to_user(v));
			case 'Datetime': return esc(frappe.datetime.str_to_user(v));
			default: return esc(v);
		}
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
						`<br><a href="/app/${frappe.router.slug(this.meta.doctype)}/${encodeURIComponent(p.name)}">فتح السجل</a>`)
						.addTo(map);
				});
			});
		}).catch(() => {
			$('#wj-map').html(`<div class="wj-empty">تعذّر تحميل مكتبة الخرائط.
				داخل الشبكات المغلقة يلزم خادم خرائط محلي.</div>`);
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
