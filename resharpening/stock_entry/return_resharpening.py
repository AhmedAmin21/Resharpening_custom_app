import frappe

from resharpening.utils.quantities import get_available_quantities
from resharpening.utils.warehouses import (
    MANUFACTURING_WAREHOUSE,
    READY_WAREHOUSE,
)


@frappe.whitelist()
def get_resharpening_orders():
    """
    Return all open Resharpening Purchase Receipts that
    currently have items available in the manufacturing warehouse.

    Warehouses are returned in the same response so the
    frontend only needs one server request.
    """

    purchase_receipts = frappe.get_all(
        "Purchase Receipt",
        filters={
            "docstatus": 1,
            "custom_operation_type": "Resharpening",
            "status": ["!=", "Closed"],
        },
        fields=[
            "name",
            "supplier",
            "posting_date",
            "status",
        ],
        order_by="posting_date desc",
    )

    orders = []

    for pr in purchase_receipts:
        available_items = get_available_quantities(pr.name)

        # Don't show receipts that currently have
        # nothing available to return.
        if not available_items:
            continue

        orders.append({
            "purchase_receipt": pr.name,
            "supplier": pr.supplier,
            "posting_date": pr.posting_date,
            "status": pr.status,
            "items": available_items,
        })

    return {
        "orders": orders,

        "warehouses": {
            "source_warehouse": MANUFACTURING_WAREHOUSE,
            "target_warehouse": READY_WAREHOUSE,
        },
    }
