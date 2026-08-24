/**
 * Purchase Invoice List View – Delivery Order sidebar filters
 *
 * Adds "Sales Invoice" and "Customer" Link filters to the list-view
 * sidebar so users can search Purchase Invoices by child-table values
 * from the "Purchase Invoice Delivery Orders" table.
 *
 * Frappe's DatabaseQuery already handles the LEFT JOIN + GROUP BY
 * automatically when filters reference a child DocType, so no
 * server-side changes are needed.
 */

(function () {
	// Preserve ERPNext's own listview_settings (loaded first).
	const existing = frappe.listview_settings["Purchase Invoice"] || {};
	const _original_onload = existing.onload;

	existing.onload = function (listview) {
		// Execute ERPNext's original onload first.
		if (_original_onload) {
			_original_onload.call(this, listview);
		}

		// Guard against re-adding on route change / re-render.
		if (listview._delivery_order_filters_added) return;
		listview._delivery_order_filters_added = true;

		setup_delivery_order_sidebar(listview);
	};

	frappe.listview_settings["Purchase Invoice"] = existing;

	/* ------------------------------------------------------------------ */
	/*  Sidebar section                                                    */
	/* ------------------------------------------------------------------ */

	function setup_delivery_order_sidebar(listview) {
		let retries = 0;
		const max_retries = 10;

		const attach = () => {
			const route = frappe.get_route();
			// Stop if user navigated away from Purchase Invoice list view
			if (!route || route[0] !== "List" || route[1] !== "Purchase Invoice") {
				return;
			}

			const $sidebar = listview.page && listview.page.sidebar;
			if (!$sidebar || !$sidebar.length) {
				if (++retries < max_retries) {
					setTimeout(attach, 300);
				}
				return;
			}

			const $list_sidebar = $sidebar.find(".list-sidebar");
			if (!$list_sidebar.length) {
				if (++retries < max_retries) {
					setTimeout(attach, 300);
				}
				return;
			}

			// Avoid duplicate section insertion
			if ($list_sidebar.find(".delivery-order-filters").length) return;

			// Build a new sidebar section matching Frappe's existing style.
			const $section = $(`
				<div class="sidebar-section delivery-order-filters">
					<li class="sidebar-label">
						${__("Delivery Orders")}
					</li>
					<div class="do-si-filter" style="padding: 4px 0;"></div>
					<div class="do-cust-filter" style="padding: 4px 0;"></div>
				</div>
			`);

			// Insert before the "Save Filter" section so it sits
			// alongside the other "Filter By" controls.
			const $save_section = $list_sidebar.find(".save-filter-section");
			if ($save_section.length) {
				$section.insertBefore($save_section);
			} else {
				$list_sidebar.append($section);
			}

			const controls = [];

			// --- Sales Invoice filter ---
			controls.push(
				make_sidebar_filter(listview, {
					wrapper: $section.find(".do-si-filter"),
					fieldtype: "Link",
					options: "Sales Invoice",
					label: __("Sales Invoice"),
					fieldname: "do_sales_invoice",
					child_fieldname: "sales_invoice",
				})
			);

			// --- Customer filter ---
			controls.push(
				make_sidebar_filter(listview, {
					wrapper: $section.find(".do-cust-filter"),
					fieldtype: "Link",
					options: "Customer",
					label: __("Customer"),
					fieldname: "do_customer",
					child_fieldname: "customer",
				})
			);

			// Hook into on_filter_change for two-way synchronization
			const _original_on_filter_change = listview.on_filter_change;
			listview.on_filter_change = function () {
				if (_original_on_filter_change) {
					_original_on_filter_change.call(this);
				}
				controls.forEach((c) => c.sync_from_filter_area());
			};
		};

		attach();
	}

	/* ------------------------------------------------------------------ */
	/*  Helper: create one sidebar Link control                            */
	/* ------------------------------------------------------------------ */

	function make_sidebar_filter(listview, opts) {
		let is_syncing = false;

		const control = frappe.ui.form.make_control({
			df: {
				fieldtype: opts.fieldtype,
				options: opts.options,
				label: opts.label,
				fieldname: opts.fieldname,
				placeholder: opts.label,
				input_class: "input-xs",
			},
			parent: opts.wrapper,
			render_input: true,
		});
		control.refresh();

		const apply = frappe.utils.debounce(() => {
			if (is_syncing) return;
			const value = control.get_value();

			// Remove any previous filter for this child field.
			remove_child_filter(listview, opts.child_fieldname);

			if (value) {
				listview.filter_area.add(
					"Purchase Invoice Delivery Orders",
					opts.child_fieldname,
					"=",
					value
				);
			} else {
				listview.refresh();
			}
		}, 300);

		control.$input.on("change", apply);
		control.$input.on("awesomplete-selectcomplete", apply);

		const sync_from_filter_area = () => {
			if (!listview.filter_area) return;
			const filters = listview.filter_area.get() || [];
			const match = filters.find(
				(f) =>
					f[0] === "Purchase Invoice Delivery Orders" &&
					f[1] === opts.child_fieldname
			);
			const active_val = match ? match[3] : "";
			if (control.get_value() !== active_val) {
				is_syncing = true;
				const res = control.set_value(active_val);
				if (res && res.then) {
					res.then(() => {
						is_syncing = false;
					}).catch(() => {
						is_syncing = false;
					});
				} else {
					is_syncing = false;
				}
			}
		};

		return {
			control,
			sync_from_filter_area,
		};
	}

	/* ------------------------------------------------------------------ */
	/*  Helper: remove a child-table filter from the FilterGroup           */
	/* ------------------------------------------------------------------ */

	function remove_child_filter(listview, child_fieldname) {
		if (!listview.filter_area || !listview.filter_area.filter_list) return;

		const filters = listview.filter_area.filter_list.filters || [];
		for (let i = filters.length - 1; i >= 0; i--) {
			const f = filters[i];
			if (!f.field) continue;
			const val = f.get_value();
			if (
				val &&
				val[0] === "Purchase Invoice Delivery Orders" &&
				val[1] === child_fieldname
			) {
				f.remove();
			}
		}
	}
})();
