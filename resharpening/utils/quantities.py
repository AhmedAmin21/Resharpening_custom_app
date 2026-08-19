import frappe

from resharpening.utils.stock_entry_types import (
    OFFICE_TO_MANUFACTURING,
    MANUFACTURING_TO_READY,
)


def get_transferred_quantities(purchase_receipt):
    """
    Get quantities transferred from the receiving warehouse
    to the manufacturing warehouse for a Purchase Receipt.
    """

    rows = frappe.db.sql(
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
        (OFFICE_TO_MANUFACTURING, purchase_receipt),
        as_dict=True,
    )

    return {
        row.item_code: row.transferred_qty
        for row in rows
    }


def get_returned_quantities(purchase_receipt):
    """
    Get quantities transferred from the manufacturing warehouse
    to the ready warehouse for a Purchase Receipt.
    """

    rows = frappe.db.sql(
        """
        SELECT
            sed.item_code,
            SUM(sed.qty) AS returned_qty
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se
            ON se.name = sed.parent
        WHERE
            se.stock_entry_type = %s
            AND se.docstatus = 1
            AND sed.custom_purchase_receipt = %s
        GROUP BY sed.item_code
        """,
        (MANUFACTURING_TO_READY, purchase_receipt),
        as_dict=True,
    )

    return {
        row.item_code: row.returned_qty
        for row in rows
    }


def get_purchase_returned_quantities(purchase_receipt):
    """
    Get quantities returned to the supplier via Purchase Returns
    (Purchase Receipt with is_return=1) against this Purchase Receipt.

    Purchase Return items have negative qty values, so we use ABS().
    """

    rows = frappe.db.sql(
        """
        SELECT
            pri.item_code,
            ABS(SUM(pri.qty)) AS purchase_returned_qty
        FROM `tabPurchase Receipt Item` pri
        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
        WHERE
            pr.is_return = 1
            AND pr.docstatus = 1
            AND pr.return_against = %s
        GROUP BY pri.item_code
        """,
        (purchase_receipt,),
        as_dict=True,
    )

    return {
        row.item_code: row.purchase_returned_qty
        for row in rows
    }


def get_available_quantities(purchase_receipt):
    """
    Calculate how many units of each item are currently
    available in the manufacturing warehouse.

    Available = Transferred to Factory
              - Returned to Ready (Stock Entry)
              - Returned to Supplier (Purchase Return)
    """

    transferred_quantities = get_transferred_quantities(
        purchase_receipt
    )

    returned_quantities = get_returned_quantities(
        purchase_receipt
    )

    purchase_returned_quantities = get_purchase_returned_quantities(
        purchase_receipt
    )

    available = []

    item_codes = (
        set(transferred_quantities)
        | set(returned_quantities)
        | set(purchase_returned_quantities)
    )

    for item_code in item_codes:

        transferred_qty = transferred_quantities.get(
            item_code, 0
        )

        returned_qty = returned_quantities.get(
            item_code, 0
        )

        purchase_returned_qty = purchase_returned_quantities.get(
            item_code, 0
        )

        available_qty = (
            transferred_qty
            - returned_qty
            - purchase_returned_qty
        )

        if available_qty > 0:

            item_name = frappe.db.get_value(
                "Item",
                item_code,
                "item_name"
            )

            stock_uom = frappe.db.get_value(
                "Item",
                item_code,
                "stock_uom"
            )

            available.append({
                "item_code": item_code,
                "item_name": item_name,
                "transferred_qty": transferred_qty,
                "returned_qty": returned_qty,
                "purchase_returned_qty": purchase_returned_qty,
                "available_qty": available_qty,
                "stock_uom": stock_uom,
            })

    return available
