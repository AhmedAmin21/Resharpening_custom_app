frappe.ui.form.on("Purchase Receipt", {
    refresh(frm) {
        // Only show for submitted Resharpening Purchase Receipts
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.custom_operation_type === "Resharpening" &&
            frm.doc.status !== "Closed"
        ) {
            frm.add_custom_button(
                __("Resharpening Transfer"),
                function () {
                    frappe.confirm(
                        __(
                            "Create a Resharpening Office → Manufacturing Stock Entry for this Purchase Receipt?"
                        ),
                        function () {
                            frappe.call({
                                method:
                                    "resharpening.purchase_receipt.transfer.create_resharpening_transfer",

                                args: {
                                    purchase_receipt: frm.doc.name,
                                },

                                freeze: true,

                                freeze_message: __(
                                    "Creating Resharpening Transfer..."
                                ),

                                callback: function (r) {
                                    if (r.message) {
                                        frappe.show_alert({
                                            message: __(
                                                "Stock Entry {0} created successfully.",
                                                [r.message]
                                            ),
                                            indicator: "green",
                                        });

                                        frappe.set_route(
                                            "Form",
                                            "Stock Entry",
                                            r.message
                                        );
                                    }
                                },
                            });
                        }
                    );
                },
                __("Create")
            );
        }
    },

    return_against(frm) {
        if (frm.doc.is_return && frm.doc.return_against && !frm.doc.custom_operation_type) {
            frappe.db.get_value("Purchase Receipt", frm.doc.return_against, "custom_operation_type", (r) => {
                if (r && r.custom_operation_type) {
                    frm.set_value("custom_operation_type", r.custom_operation_type);
                }
            });
        }
    },
});
