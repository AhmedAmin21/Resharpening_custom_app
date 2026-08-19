import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Purchase Receipt": [
            {
                "fieldname": "custom_resharp_return_reason",
                "label": "Resharp Return Reason",
                "fieldtype": "Small Text",
                "insert_after": "return_against",
                "depends_on": "eval:doc.is_return && doc.custom_operation_type == 'Resharpening'",
                "no_copy": 1,
            }
        ]
    })
