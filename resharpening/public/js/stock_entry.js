frappe.ui.form.on("Stock Entry", {
    refresh(frm) {
        add_resharpening_button(frm);
    },

    stock_entry_type(frm) {
        add_resharpening_button(frm);
    },
});


function add_resharpening_button(frm) {
    // Only show for draft Stock Entries
    if (
        frm.doc.docstatus !== 0 ||
        frm.doc.stock_entry_type !==
            "Resharpening Factory To Office"
    ) {
        return;
    }

    // Prevent duplicate button
    if (frm.custom_buttons?.["Return Resharpening"]) {
        return;
    }

    const button = frm.add_custom_button(
        __("Return Resharpening"),
        function () {
            show_resharpening_return_dialog(frm);
        }
    );

    button.addClass(
        "btn-resharpening-return"
    );
}


function show_resharpening_return_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Return Resharpening"),
        size: "large",

        fields: [
            {
                fieldname: "supplier",
                fieldtype: "Link",
                label: __("Supplier"),
                options: "Supplier",
            },

            {
                fieldname: "purchase_receipt",
                fieldtype: "Select",
                label: __("Purchase Receipt"),
                options: [],
                reqd: 1,
            },

            {
                fieldname: "available_items",
                fieldtype: "HTML",
            },
        ],

        primary_action_label: __("Add to Return"),

        primary_action() {
            add_selected_items_to_stock_entry(
                dialog,
                frm
            );
        },
    });

    dialog.show();

    /*
     * Supplier filtering happens locally.
     * No server request.
     */
    dialog.fields_dict.supplier.df.onchange =
        function () {
            const supplier =
                dialog.get_value("supplier");

        update_purchase_receipt_options(
            dialog,
            supplier
        );
    };

    /*
     * Purchase Receipt selection happens locally.
     * No server request.
     */
    dialog.fields_dict.purchase_receipt.$input.on(
        "change",
        function () {
            const selected_label =
                dialog.get_value(
                    "purchase_receipt"
                );

            if (!selected_label) {
                clear_available_items(dialog);
                return;
            }

            const purchase_receipt =
                dialog.purchase_receipt_map?.[
                    selected_label
                ];

            if (!purchase_receipt) {
                clear_available_items(dialog);
                return;
            }

            load_resharpening_items(
                dialog,
                purchase_receipt
            );
        }
    );

    /*
     * ONE server request.
     *
     * It returns:
     * - Purchase Receipts
     * - Suppliers
     * - Dates
     * - Available quantities
     * - Source warehouse
     * - Target warehouse
     */
    load_resharpening_data(dialog);
}


function load_resharpening_data(dialog) {
    frappe.call({
        method:
            "resharpening.stock_entry.return_resharpening.get_resharpening_orders",

        freeze: true,

        freeze_message: __(
            "Loading resharpening orders..."
        ),

        callback(r) {
            if (!r.message) {
                return;
            }

            /*
             * Store everything in memory.
             * No more server requests are needed
             * while using this dialog.
             */
            dialog.resharpening_orders =
                r.message.orders || [];

            dialog.resharpening_warehouses =
                r.message.warehouses || {};

            update_purchase_receipt_options(
                dialog,
                null
            );
        },
    });
}


function update_purchase_receipt_options(
    dialog,
    supplier
) {
    const orders =
        dialog.resharpening_orders || [];

    /*
     * Supplier filtering is performed
     * entirely in the browser.
     */
    const filtered_orders = supplier
        ? orders.filter(
              order =>
                  order.supplier === supplier
          )
        : orders;

    /*
     * Map the visible label to the actual
     * Purchase Receipt name.
     *
     * Example:
     *
     * Display:
     * PR-00042 — 08-08-2026
     *
     * Actual value:
     * PR-00042
     */
    dialog.purchase_receipt_map = {};

    const options = filtered_orders.map(
        order => {
            const formatted_date =
                frappe.datetime.str_to_user(
                    order.posting_date
                );

            const label =
                `${order.purchase_receipt} — ${formatted_date}`;

            dialog.purchase_receipt_map[
                label
            ] = order.purchase_receipt;

            return label;
        }
    );

    dialog.set_df_property(
        "purchase_receipt",
        "options",
        options.join("\n")
    );

    dialog.set_value(
        "purchase_receipt",
        ""
    );

    clear_available_items(dialog);
}


function clear_available_items(dialog) {
    dialog.fields_dict.available_items.$wrapper.empty();

    dialog.current_order = null;
}


function load_resharpening_items(
    dialog,
    purchase_receipt
) {
    /*
     * Find the Purchase Receipt from
     * data already loaded into memory.
     *
     * ZERO server requests.
     */
    const order =
        (dialog.resharpening_orders || []).find(
            item =>
                item.purchase_receipt ===
                purchase_receipt
        );

    if (!order) {
        frappe.msgprint(
            __("Purchase Receipt not found.")
        );

        return;
    }

    dialog.current_order = order;

    let html = `
        <div style="margin-top: 15px;">
            <h5>
                ${__("Available Items")}
            </h5>

            <table
                class="table table-bordered"
                style="margin-bottom: 0;"
            >
                <thead>
                    <tr>
                        <th>
                            ${__("Item")}
                        </th>

                        <th>
                            ${__("Available")}
                        </th>

                        <th style="width: 150px;">
                            ${__("Return Qty")}
                        </th>
                    </tr>
                </thead>

                <tbody>
    `;

    order.items.forEach(
        (item, index) => {
            html += `
                <tr
                    data-item-index="${index}"
                >
                    <td>
                        <strong>
                            ${frappe.utils.escape_html(
                                item.item_code
                            )}
                        </strong>

                        ${
                            item.item_name
                                ? `
                                    <br>

                                    <small
                                        class="text-muted"
                                    >
                                        ${frappe.utils.escape_html(
                                            item.item_name
                                        )}
                                    </small>
                                  `
                                : ""
                        }
                    </td>

                    <td>
                        ${item.available_qty}
                    </td>

                    <td>
                        <input
                            type="number"
                            class="form-control return-qty-input"
                            data-item-index="${index}"
                            min="0"
                            max="${item.available_qty}"
                            step="any"
                            value="0"
                        >
                    </td>
                </tr>
            `;
        }
    );

    html += `
                </tbody>
            </table>
        </div>
    `;

    const wrapper =
        dialog.fields_dict
            .available_items
            .$wrapper;

    wrapper.html(html);

    /*
     * Quantity validation is completely
     * client-side.
     */
    wrapper
        .find(".return-qty-input")
        .on(
            "input",
            function () {
                const index =
                    Number(
                        $(this).attr(
                            "data-item-index"
                        )
                    );

                const item =
                    dialog.current_order
                        .items[index];

                let value =
                    parseFloat(
                        $(this).val()
                    ) || 0;

                if (value < 0) {
                    value = 0;
                }

                if (
                    value >
                    item.available_qty
                ) {
                    value =
                        item.available_qty;

                    frappe.show_alert({
                        message:
                            __(
                                "Return quantity cannot exceed available quantity."
                            ),

                        indicator:
                            "orange",
                    });
                }

                $(this).val(value);
            }
        );
}


function add_selected_items_to_stock_entry(
    dialog,
    frm
) {
    const order =
        dialog.current_order;

    if (!order) {
        frappe.msgprint(
            __(
                "Please select a Purchase Receipt first."
            )
        );

        return;
    }

    const warehouses =
        dialog.resharpening_warehouses;

    if (
        !warehouses ||
        !warehouses.source_warehouse ||
        !warehouses.target_warehouse
    ) {
        frappe.msgprint(
            __(
                "Resharpening warehouses are not available."
            )
        );

        return;
    }

    const wrapper =
        dialog.fields_dict
            .available_items
            .$wrapper;

    const selected_items = [];

    let invalid_quantity = false;

    wrapper
        .find(".return-qty-input")
        .each(
            function () {
                const index =
                    Number(
                        $(this).attr(
                            "data-item-index"
                        )
                    );

                const qty =
                    parseFloat(
                        $(this).val()
                    ) || 0;

                if (qty <= 0) {
                    return;
                }

                const item =
                    order.items[index];

                /*
                 * Final client-side validation.
                 */
                if (
                    qty >
                    item.available_qty
                ) {
                    frappe.msgprint({
                        title:
                            __(
                                "Invalid Quantity"
                            ),

                        message:
                            __(
                                "Return quantity for {0} cannot exceed the available quantity of {1}.",
                                [
                                    item.item_code,
                                    item.available_qty,
                                ]
                            ),

                        indicator:
                            "red",
                    });

                    invalid_quantity = true;

                    return false;
                }

                selected_items.push({
                    item_code:
                        item.item_code,

                    item_name:
                        item.item_name,

                    qty:
                        qty,

                    uom:
                        item.stock_uom,

                    purchase_receipt:
                        order.purchase_receipt,

                    supplier:
                        order.supplier,
                });
            }
        );

    if (invalid_quantity) {
        return;
    }

    if (!selected_items.length) {
        frappe.msgprint(
            __(
                "Please enter a return quantity for at least one item."
            )
        );

        return;
    }

    /*
     * Add the selected items.
     *
     * Reuse Frappe's initial empty row
     * when possible.
     */
    selected_items.forEach(
        (item, index) => {
            let row;

            if (
                index === 0 &&
                frm.doc.items &&
                frm.doc.items.length === 1 &&
                is_empty_stock_entry_row(
                    frm.doc.items[0]
                )
            ) {
                row =
                    frm.doc.items[0];
            } else {
                row =
                    frm.add_child(
                        "items"
                    );
            }

            row.item_code =
                item.item_code;

            row.qty =
                item.qty;

            row.uom =
                item.uom;
            row.conversion_factor = 1;
            /*
             * Manufacturing -> Ready
             */
            row.s_warehouse =
                warehouses.source_warehouse;

            row.t_warehouse =
                warehouses.target_warehouse;

            row.custom_purchase_receipt =
                item.purchase_receipt;

            row.custom_supplier =
                item.supplier;
        }
    );

    /*
     * Only refresh the child table.
     *
     * This does NOT reload the document
     * and does NOT make a server request.
     */
    frm.refresh_field(
        "items"
    );

    dialog.hide();

    frappe.show_alert({
        message:
            __(
                "{0} item(s) added to the Stock Entry.",
                [
                    selected_items.length,
                ]
            ),

        indicator:
            "green",
    });
}


function is_empty_stock_entry_row(
    row
) {
    return (
        !row.item_code &&
        !row.qty &&
        !row.s_warehouse &&
        !row.t_warehouse &&
        !row.custom_purchase_receipt &&
        !row.custom_supplier
    );
}
