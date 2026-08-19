import frappe

def setup():
    setup_settings()
    setup_log_doctype()

def setup_settings():
    doctype_name = "Resharpening WhatsApp Settings"
    fields = [
        # SECTION 1: EvoAPI Configuration & Notification Toggles
        {
            "fieldname": "api_section",
            "fieldtype": "Section Break",
            "label": "EvoAPI Configuration & Settings"
        },
        {
            "fieldname": "evoapi_url",
            "fieldtype": "Data",
            "label": "EvoAPI URL",
            "description": "Example: https://evoapi.ens-ala.com/"
        },
        {
            "fieldname": "evoapi_instance_id",
            "fieldtype": "Data",
            "label": "Instance ID"
        },
        {
            "fieldname": "evoapi_token",
            "fieldtype": "Password",
            "label": "API Token"
        },
        {
            "fieldname": "receipt_print_format",
            "fieldtype": "Link",
            "options": "Print Format",
            "label": "Purchase Receipt Print Format",
            "description": "Optional: Select the Print Format used to generate the PDF. Leave blank to use the standard default format."
        },
        {
            "fieldname": "cb_config",
            "fieldtype": "Column Break"
        },
        {
            "fieldname": "enable_whatsapp_notifications",
            "fieldtype": "Check",
            "label": "Enable WhatsApp Notifications (Master Switch)",
            "default": "1"
        },
        {
            "fieldname": "send_receive_message",
            "fieldtype": "Check",
            "label": "ارسال رسالة الاستلام",
            "default": "1"
        },
        {
            "fieldname": "send_receipt_pdf",
            "fieldtype": "Check",
            "label": "Attach Purchase Receipt PDF (Message will be PDF Caption)",
            "default": "1"
        },
        {
            "fieldname": "send_factory_transfer_message",
            "fieldtype": "Check",
            "label": "ارسال رسالة النقل الى المصنع",
            "default": "1"
        },
        {
            "fieldname": "send_factory_return_message",
            "fieldtype": "Check",
            "label": "ارسال رسالة النقل من المصنع الى المكتب",
            "default": "1"
        },
        {
            "fieldname": "send_item_return_message",
            "fieldtype": "Check",
            "label": "ارسال رسالة المرتجع (غير قابل للسن)",
            "default": "1"
        },
        {
            "fieldname": "send_closed_message",
            "fieldtype": "Check",
            "label": "ارسال رسالة انتهاء الطلب بالكامل",
            "default": "1"
        },

        # SECTION 2: Placeholder Reference Guide
        {
            "fieldname": "placeholders_section",
            "fieldtype": "Section Break",
            "label": "Available Placeholders & Guide",
            "collapsible": 1
        },
        {
            "fieldname": "placeholders_guide",
            "fieldtype": "HTML",
            "label": "Placeholder Guide",
            "options": """
            <div style="background-color: var(--bg-light-gray, #f8f9fa); border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; padding: 15px; font-size: 13px;">
                <h5 style="margin-top: 0; margin-bottom: 10px; color: var(--text-color, #1f272e);">Available Dynamic Keywords / Placeholders:</h5>
                <table class="table table-bordered table-sm" style="background: white; margin-bottom: 16px;">
                    <thead class="thead-light">
                        <tr>
                            <th style="width: 25%;">Placeholder</th>
                            <th style="width: 45%;">Description</th>
                            <th style="width: 30%;">Example Output</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><code>{supplier_name}</code></td><td>Supplier / Customer Name</td><td>CNC Tech Corp</td></tr>
                        <tr><td><code>{purchase_receipt}</code></td><td>Purchase Receipt Reference ID</td><td>PRE-00045</td></tr>
                        <tr><td><code>{stock_entry}</code></td><td>Stock Entry Reference ID (for transfers &amp; returns)</td><td>STE-00027</td></tr>
                        <tr><td><code>{item_list}</code> (or <code>{items}</code>, <code>{item}</code>)</td><td>Formatted list of items in the current event</td><td>6x D6 End Mill, 2x D10 End Mill</td></tr>
                        <tr><td><code>{total_qty}</code></td><td>Total quantity of items in current event</td><td>8</td></tr>
                        <tr><td><code>{item_count}</code></td><td>Number of distinct item lines in current event</td><td>2</td></tr>
                        <tr><td><code>{received_qty}</code></td><td>Total received quantity in original order</td><td>20</td></tr>
                        <tr><td><code>{ready_qty}</code></td><td>Total quantity completed &amp; ready in office</td><td>14</td></tr>
                        <tr><td><code>{remaining_qty}</code></td><td>Remaining quantity still in factory</td><td>6</td></tr>
                        <tr><td><code>{return_number}</code></td><td>Sequence return number (1, 2, 3...)</td><td>2</td></tr>
                        <tr><td><code>{return_reason}</code></td><td>Return reason (from Resharp Return Reason)</td><td>غير قابل للسن / تلف في السلاح</td></tr>
                        <tr><td><code>{order_status}</code></td><td>Current operational status of the order</td><td>Partially Ready</td></tr>
                        <tr><td><code>{date}</code></td><td>Current date</td><td>2026-08-15</td></tr>
                    </tbody>
                </table>

                <h5 style="margin-top: 0; margin-bottom: 10px; color: var(--text-color, #1f272e);">WhatsApp Text Formatting:</h5>
                <table class="table table-bordered table-sm" style="background: white; margin-bottom: 0;">
                    <thead class="thead-light">
                        <tr>
                            <th style="width: 25%;">Syntax</th>
                            <th style="width: 30%;">Formatting</th>
                            <th style="width: 45%;">Example</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>*text*</code></td>
                            <td><strong>Bold</strong></td>
                            <td><code>*مرحباً*</code> → <strong>مرحباً</strong></td>
                        </tr>
                        <tr>
                            <td><code>_text_</code></td>
                            <td><em>Italic</em></td>
                            <td><code>_مرحباً_</code> → <em>مرحباً</em></td>
                        </tr>
                        <tr>
                            <td><code>~text~</code></td>
                            <td><s>Strikethrough</s></td>
                            <td><code>~مرحباً~</code> → <s>مرحباً</s></td>
                        </tr>
                        <tr>
                            <td><code>```text```</code></td>
                            <td><span style="font-family: monospace;">Monospace</span></td>
                            <td><code>```PRE-00045```</code> → <span style="font-family: monospace;">PRE-00045</span></td>
                        </tr>
                        <tr>
                            <td><code>*_text_*</code></td>
                            <td><strong><em>Bold + Italic</em></strong></td>
                            <td><code>*_مرحباً_*</code> → <strong><em>مرحباً</em></strong></td>
                        </tr>
                        <tr>
                            <td>(new line in template)</td>
                            <td>Line break in WhatsApp</td>
                            <td>Press Enter in the template text box</td>
                        </tr>
                    </tbody>
                </table>
                <p style="margin-top: 8px; margin-bottom: 0; color: var(--text-muted, #8d99a6); font-size: 12px;">
                    💡 You can combine placeholders with formatting, e.g.: <code>*الطلب:* {purchase_receipt}</code>
                </p>
            </div>
            """
        },

        # SECTION 3: Message Templates
        {
            "fieldname": "templates_section",
            "fieldtype": "Section Break",
            "label": "Message Templates"
        },
        {
            "fieldname": "receipt_message_template",
            "fieldtype": "Text",
            "label": "رسالة الاستلام",
            "description": "Sent when items are received via Purchase Receipt. (If PDF attachment is enabled, this text is sent as the single message PDF caption)."
        },
        {
            "fieldname": "factory_transfer_template",
            "fieldtype": "Text",
            "label": "رسالة النقل الى المصنع",
            "description": "Sent when items are transferred Office → Factory."
        },
        {
            "fieldname": "factory_return_template",
            "fieldtype": "Text",
            "label": "رسالة النقل من المصنع الى المكتب",
            "description": "Sent every time items return Factory → Office."
        },
        {
            "fieldname": "ready_message_template",
            "fieldtype": "Text",
            "label": "رسالة انتهاء الطلب بالكامل",
            "description": "Sent when the order is closed via the Resharpening Dashboard."
        },
        {
            "fieldname": "item_return_template",
            "fieldtype": "Text",
            "label": "رسالة المرتجع (غير قابل للسن)",
            "description": "Sent when a Purchase Return is submitted for rejected/returned items."
        }
    ]

    if not frappe.db.exists("DocType", doctype_name):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": doctype_name,
            "module": "Resharpening",
            "custom": 1,
            "issingle": 1,
            "fields": fields,
            "permissions": [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1
                }
            ]
        })
        doc.insert()
        frappe.db.commit()
        print(f"Created DocType {doctype_name}")
    else:
        doc = frappe.get_doc("DocType", doctype_name)
        doc.set("fields", [])
        for f in fields:
            doc.append("fields", f)
        doc.save()
        frappe.db.commit()
        print(f"Updated DocType {doctype_name} schema and field layout successfully.")

def setup_log_doctype():
    doctype_name = "Resharpening WhatsApp Log"
    fields = [
        {
            "fieldname": "event_type",
            "fieldtype": "Select",
            "label": "Event Type",
            "options": "Receive\nFactory Transfer\nFactory Return\nPurchase Return\nClosed",
            "in_list_view": 1,
            "reqd": 1
        },
        {
            "fieldname": "event_reference",
            "fieldtype": "Data",
            "label": "Event Reference",
            "in_list_view": 1,
            "reqd": 1
        },
        {
            "fieldname": "purchase_receipt",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "label": "Purchase Receipt",
            "in_list_view": 1
        },
        {
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "label": "Supplier",
            "in_list_view": 1
        },
        {
            "fieldname": "cb_log",
            "fieldtype": "Column Break"
        },
        {
            "fieldname": "phone",
            "fieldtype": "Data",
            "label": "Phone",
            "in_list_view": 1
        },
        {
            "fieldname": "status",
            "fieldtype": "Select",
            "options": "Sent\nFailed\nPending",
            "label": "Status",
            "in_list_view": 1,
            "default": "Pending"
        },
        {
            "fieldname": "sent_at",
            "fieldtype": "Datetime",
            "label": "Sent At",
            "in_list_view": 1
        },
        {
            "fieldname": "details_section",
            "fieldtype": "Section Break",
            "label": "Message Details"
        },
        {
            "fieldname": "message",
            "fieldtype": "Text",
            "label": "Message Content"
        },
        {
            "fieldname": "error_message",
            "fieldtype": "Text",
            "label": "Error Message"
        }
    ]

    if not frappe.db.exists("DocType", doctype_name):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": doctype_name,
            "module": "Resharpening",
            "custom": 1,
            "autoname": "format:WA-LOG-{YYYY}-{MM}-{#####}",
            "fields": fields,
            "permissions": [
                {
                    "role": "System Manager",
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1
                }
            ]
        })
        doc.insert()
        frappe.db.commit()
        print(f"Created DocType {doctype_name}")
    else:
        print(f"DocType {doctype_name} already exists.")
