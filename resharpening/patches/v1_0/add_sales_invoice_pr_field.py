import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Sales Invoice": [
            {
                "fieldname": "custom_resharpening_purchase_receipt",
                "label": "Resharpening Purchase Receipt",
                "fieldtype": "Link",
                "options": "Purchase Receipt",
                "insert_after": "customer",
                "no_copy": 1,
                "read_only": 1,
                "hidden": 1,
            }
        ]
    })
