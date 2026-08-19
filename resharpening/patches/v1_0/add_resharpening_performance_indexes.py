import frappe


def execute():
    """
    Add database indexes for Resharpening performance optimization.
    Idempotent and safe across fresh installations and upgrades.
    """
    indexes_to_add = [
        {
            "doctype": "Stock Entry Detail",
            "field": "custom_purchase_receipt",
            "index_name": "idx_resharp_purchase_receipt",
        },
        {
            "doctype": "Sales Invoice",
            "field": "custom_resharpening_purchase_receipt",
            "index_name": "idx_resharp_sales_invoice_pr",
        },
        {
            "doctype": "Purchase Receipt",
            "field": "custom_operation_type",
            "index_name": "idx_resharp_operation_type",
        },
    ]

    for item in indexes_to_add:
        doctype = item["doctype"]
        field = item["field"]
        index_name = item["index_name"]

        # 1. Verify table has column
        if not frappe.db.has_column(doctype, field):
            continue

        table_name = f"`tab{doctype}`"

        # 2. Check if index already exists on column or with the same name
        existing_indexes = frappe.db.sql(
            f"""
            SHOW INDEX FROM {table_name}
            WHERE Column_name = %s OR Key_name = %s
            """,
            (field, index_name),
            as_dict=True,
        )

        if not existing_indexes:
            try:
                frappe.db.add_index(doctype, [field], index_name)
            except Exception as e:
                # Fallback to direct SQL if add_index fails
                try:
                    frappe.db.sql(
                        f"ALTER TABLE {table_name} ADD INDEX `{index_name}` (`{field}`)"
                    )
                except Exception as inner_e:
                    frappe.log_error(
                        title=f"Index Creation Failed for {doctype}.{field}",
                        message=f"{e}\n{inner_e}",
                    )
