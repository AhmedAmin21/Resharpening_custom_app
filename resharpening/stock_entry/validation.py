import frappe

from resharpening.utils.quantities import (
    get_available_quantities,
)

from resharpening.utils.stock_entry_types import (
    MANUFACTURING_TO_READY,
)

from resharpening.utils.warehouses import (
    MANUFACTURING_WAREHOUSE,
    READY_WAREHOUSE,
)


def validate_resharpening_return(doc, method=None):
    """
    Validate Resharpening Manufacturing -> Ready Stock Entries.

    This validation runs before submission and makes sure that:

    1. The correct Stock Entry Type is used.
    2. Every row has a Purchase Receipt.
    3. Every row has a Supplier.
    4. Purchase Receipt belongs to the Supplier.
    5. Item exists on the Purchase Receipt.
    6. Source warehouse is Manufacturing.
    7. Target warehouse is Ready.
    8. Requested quantity does not exceed the
       currently available quantity.
    """

    # Only validate the Resharpening
    # Manufacturing -> Ready operation.
    if doc.stock_entry_type != MANUFACTURING_TO_READY:
        return

    if not doc.items:
        frappe.throw(
            "Resharpening return must contain at least one item."
        )

    # Keep track of quantities being returned
    # from the same Purchase Receipt + Item
    # inside this Stock Entry.
    requested_quantities = {}

    for row in doc.items:

        validate_row(
            doc,
            row,
            requested_quantities,
        )


def validate_row(
    doc,
    row,
    requested_quantities,
):
    """
    Validate one Stock Entry Detail row.
    """

    # ---------------------------------------------------------
    # 1. Required Purchase Receipt
    # ---------------------------------------------------------

    if not row.custom_purchase_receipt:
        frappe.throw(
            f"Purchase Receipt is required for item "
            f"<b>{row.item_code or 'Unknown'}</b>."
        )

    # ---------------------------------------------------------
    # 2. Required Supplier
    # ---------------------------------------------------------

    if not row.custom_supplier:
        frappe.throw(
            f"Supplier is required for item "
            f"<b>{row.item_code or 'Unknown'}</b>."
        )

    # ---------------------------------------------------------
    # 3. Validate Purchase Receipt
    # ---------------------------------------------------------

    purchase_receipt = frappe.db.get_value(
        "Purchase Receipt",
        row.custom_purchase_receipt,
        [
            "name",
            "supplier",
            "docstatus",
            "custom_operation_type",
            "status",
        ],
        as_dict=True,
    )

    if not purchase_receipt:
        frappe.throw(
            f"Purchase Receipt "
            f"<b>{row.custom_purchase_receipt}</b> "
            f"does not exist."
        )

    # ---------------------------------------------------------
    # 4. Purchase Receipt must be submitted
    # ---------------------------------------------------------

    if purchase_receipt.docstatus != 1:
        frappe.throw(
            f"Purchase Receipt "
            f"<b>{purchase_receipt.name}</b> "
            f"must be submitted before returning items."
        )

    # ---------------------------------------------------------
    # 5. Purchase Receipt must be Resharpening
    # ---------------------------------------------------------

    if purchase_receipt.custom_operation_type != "Resharpening":
        frappe.throw(
            f"Purchase Receipt "
            f"<b>{purchase_receipt.name}</b> "
            f"is not a Resharpening Purchase Receipt."
        )

    # ---------------------------------------------------------
    # 6. Supplier must match Purchase Receipt
    # ---------------------------------------------------------

    if purchase_receipt.supplier != row.custom_supplier:
        frappe.throw(
            f"Supplier mismatch for Purchase Receipt "
            f"<b>{purchase_receipt.name}</b>.<br><br>"
            f"Purchase Receipt supplier: "
            f"<b>{purchase_receipt.supplier}</b><br>"
            f"Selected supplier: "
            f"<b>{row.custom_supplier}</b>"
        )

    # ---------------------------------------------------------
    # 7. Validate source warehouse
    # ---------------------------------------------------------

    if row.s_warehouse != MANUFACTURING_WAREHOUSE:
        frappe.throw(
            f"Invalid source warehouse for item "
            f"<b>{row.item_code}</b>.<br><br>"
            f"Expected:<br>"
            f"<b>{MANUFACTURING_WAREHOUSE}</b>"
        )

    # ---------------------------------------------------------
    # 8. Validate target warehouse
    # ---------------------------------------------------------

    if row.t_warehouse != READY_WAREHOUSE:
        frappe.throw(
            f"Invalid target warehouse for item "
            f"<b>{row.item_code}</b>.<br><br>"
            f"Expected:<br>"
            f"<b>{READY_WAREHOUSE}</b>"
        )

    # ---------------------------------------------------------
    # 9. Validate item
    # ---------------------------------------------------------

    if not row.item_code:
        frappe.throw(
            "Item Code is required in every "
            "Resharpening return row."
        )

    item_exists = frappe.db.exists(
        "Item",
        row.item_code,
    )

    if not item_exists:
        frappe.throw(
            f"Item <b>{row.item_code}</b> does not exist."
        )

    # ---------------------------------------------------------
    # 10. Make sure item belongs to Purchase Receipt
    # ---------------------------------------------------------

    item_in_receipt = frappe.db.exists(
        "Purchase Receipt Item",
        {
            "parent": row.custom_purchase_receipt,
            "item_code": row.item_code,
        },
    )

    if not item_in_receipt:
        frappe.throw(
            f"Item <b>{row.item_code}</b> does not "
            f"belong to Purchase Receipt "
            f"<b>{row.custom_purchase_receipt}</b>."
        )

    # ---------------------------------------------------------
    # 11. Validate quantity
    # ---------------------------------------------------------

    if not row.qty or row.qty <= 0:
        frappe.throw(
            f"Return quantity for item "
            f"<b>{row.item_code}</b> must be greater than zero."
        )

    # ---------------------------------------------------------
    # 12. Group quantities in this Stock Entry
    # ---------------------------------------------------------

    key = (
        row.custom_purchase_receipt,
        row.item_code,
    )

    requested_quantities[key] = (
        requested_quantities.get(key, 0)
        + row.qty
    )

    # ---------------------------------------------------------
    # 13. Get current available quantity
    # ---------------------------------------------------------

    available_items = get_available_quantities(
        row.custom_purchase_receipt
    )

    available_map = {
        item["item_code"]: item["available_qty"]
        for item in available_items
    }

    available_qty = available_map.get(
        row.item_code,
        0,
    )

    requested_qty = requested_quantities[key]

    # ---------------------------------------------------------
    # 14. Prevent returning more than available
    # ---------------------------------------------------------

    if requested_qty > available_qty:
        frappe.throw(
            f"Not enough quantity available for "
            f"<b>{row.item_code}</b> "
            f"from Purchase Receipt "
            f"<b>{row.custom_purchase_receipt}</b>."
            f"<br><br>"
            f"Available in Manufacturing: "
            f"<b>{available_qty}</b>"
            f"<br>"
            f"Requested: "
            f"<b>{requested_qty}</b>"
        )
