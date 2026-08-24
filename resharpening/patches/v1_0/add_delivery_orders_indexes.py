"""Add database indexes on Purchase Invoice Delivery Orders child table.

Indexes on `sales_invoice` and `customer` columns speed up the LEFT JOIN
queries that Frappe generates when the list-view filters reference these
child-table fields.
"""

import frappe


def execute():
    frappe.db.add_index(
        "Purchase Invoice Delivery Orders", ["sales_invoice"]
    )
    frappe.db.add_index(
        "Purchase Invoice Delivery Orders", ["customer"]
    )
