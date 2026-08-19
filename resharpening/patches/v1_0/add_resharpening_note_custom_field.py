import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Purchase Receipt": [
            {
                "fieldname": "custom_resharpening_note",
                "label": "Resharpening Note",
                "fieldtype": "Small Text",
                "insert_after": "status",
                "no_copy": 1,
            }
        ]
    })
