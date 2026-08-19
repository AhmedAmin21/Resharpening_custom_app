import frappe

from resharpening.utils.warehouses import (
    RECEIVING_WAREHOUSE,
    MANUFACTURING_WAREHOUSE,
)

from resharpening.utils.stock_entry_types import (
    OFFICE_TO_MANUFACTURING,
)

@frappe.whitelist()
def create_resharpening_transfer(purchase_receipt):
    """
    Create the Office -> Manufacturing Stock Entry
    for a Resharpening Purchase Receipt.
    """

    # ------------------------------------------------------------------
    # Get Purchase Receipt
    # ------------------------------------------------------------------

    pr = frappe.get_doc("Purchase Receipt", purchase_receipt)

    # ------------------------------------------------------------------
    # Validate Purchase Receipt
    # ------------------------------------------------------------------

    if pr.docstatus != 1:
        frappe.throw(
            "Purchase Receipt must be submitted before creating "
            "a resharpening transfer."
        )

    if pr.custom_operation_type != "Resharpening":
        frappe.throw(
            "This Purchase Receipt is not marked as Resharpening."
        )

    if pr.status == "Closed":
        frappe.throw(
            "This Purchase Receipt is already closed."
        )



    # ------------------------------------------------------------------
    # Check whether this Purchase Receipt was already transferred
    # ------------------------------------------------------------------

    existing_items = frappe.db.sql(
        """
        SELECT
            sed.item_code,
            SUM(sed.qty) AS transferred_qty
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se
            ON se.name = sed.parent
        WHERE
            se.stock_entry_type = %s
            AND se.docstatus = 1
            AND sed.custom_purchase_receipt = %s
        GROUP BY sed.item_code
        """,
        (OFFICE_TO_MANUFACTURING, pr.name),
        as_dict=True,
    )

    transferred_map = {
        row.item_code: row.transferred_qty
        for row in existing_items
    }

    # ------------------------------------------------------------------
    # Create Stock Entry
    # ------------------------------------------------------------------

    stock_entry = frappe.new_doc("Stock Entry")

    stock_entry.stock_entry_type = OFFICE_TO_MANUFACTURING

    # ------------------------------------------------------------------
    # Add Purchase Receipt items
    # ------------------------------------------------------------------

    for item in pr.items:

        if not item.qty:
            continue

        already_transferred = transferred_map.get(
            item.item_code, 0
        )

        remaining_qty = item.qty - already_transferred

        if remaining_qty <= 0:
            continue

        stock_entry.append(
            "items",
            {
                "item_code": item.item_code,
                "qty": remaining_qty,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor or 1,

                "s_warehouse": RECEIVING_WAREHOUSE,
                "t_warehouse": MANUFACTURING_WAREHOUSE,

                "custom_purchase_receipt": pr.name,
                "custom_supplier": pr.supplier,
            },
        )

    # ------------------------------------------------------------------
    # Validate that there are items to transfer
    # ------------------------------------------------------------------

    if not stock_entry.items:
        frappe.throw(
            "All items from this Purchase Receipt have already "
            "been transferred to Manufacturing."
        )

    # ------------------------------------------------------------------
    # Insert Stock Entry
    # ------------------------------------------------------------------

    stock_entry.insert()

    return stock_entry.name
@frappe.whitelist()
def get_available_resharpening_items(purchase_receipt):
    from resharpening.utils.quantities import get_available_quantities

    return get_available_quantities(purchase_receipt)
