import frappe

from resharpening.utils.stock_entry_types import (
    OFFICE_TO_MANUFACTURING,
    MANUFACTURING_TO_READY,
)


PAGE_SIZE = 25


_NOTE_FIELD_VERIFIED = False
_SINV_FIELD_VERIFIED = False


def ensure_custom_note_field():
    """
    Ensure custom_resharpening_note field exists on Purchase Receipt.
    Cached after first verification.
    """
    global _NOTE_FIELD_VERIFIED
    if _NOTE_FIELD_VERIFIED:
        return

    if not frappe.db.has_column("Purchase Receipt", "custom_resharpening_note"):
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
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
    _NOTE_FIELD_VERIFIED = True


def ensure_sales_invoice_pr_field():
    """
    Ensure custom_resharpening_purchase_receipt field exists on Sales Invoice.
    Cached after first verification.
    """
    global _SINV_FIELD_VERIFIED
    if _SINV_FIELD_VERIFIED:
        return

    if not frappe.db.has_column("Sales Invoice", "custom_resharpening_purchase_receipt"):
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
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
    _SINV_FIELD_VERIFIED = True


# =============================================================
# GET RESHARPENING ORDERS
# =============================================================

@frappe.whitelist()
def get_resharpening_orders(
    supplier=None,
    status=None,
    from_date=None,
    to_date=None,
    page=1,
):
    """
    Return one page of Resharpening Purchase Receipts.

    Purchase Returns are NOT shown as separate dashboard orders.
    Their quantities are calculated against the original Purchase
    Receipt using Purchase Receipt.return_against.

    Closed Purchase Receipts remain visible and receive the
    dashboard status "Closed".
    """

    ensure_custom_note_field()
    ensure_sales_invoice_pr_field()

    page = max(int(page or 1), 1)

    offset = (
        page - 1
    ) * PAGE_SIZE


    # ---------------------------------------------------------
    # Filter conditions
    # ---------------------------------------------------------

    filter_conditions = [
        "pr.docstatus = 1",
        "pr.custom_operation_type = 'Resharpening'",
        "COALESCE(pr.is_return, 0) = 0",
    ]

    filter_values = []


    if supplier:

        filter_conditions.append(
            "pr.supplier = %s"
        )

        filter_values.append(
            supplier
        )


    if from_date:

        filter_conditions.append(
            "pr.posting_date >= %s"
        )

        filter_values.append(
            from_date
        )


    if to_date:

        filter_conditions.append(
            "pr.posting_date <= %s"
        )

        filter_values.append(
            to_date
        )


    filter_where = " AND ".join(
        filter_conditions
    )


    # ---------------------------------------------------------
    # Main query
    # ---------------------------------------------------------

    base_query = f"""
        SELECT

            pr.name AS purchase_receipt,

            pr.supplier,

            COALESCE(pr.supplier_name, pr.supplier) AS supplier_name,

            pr.posting_date AS receipt_date,

            pr.status AS purchase_receipt_status,

            pr.custom_resharpening_note AS note,


            COALESCE(
                received.received_qty,
                0
            ) AS received,


            COALESCE(
                sent.sent_qty,
                0
            ) AS sent,


            COALESCE(
                returned.returned_qty,
                0
            ) AS returned,


            GREATEST(
                COALESCE(received.received_qty, 0)
                - COALESCE(sent.sent_qty, 0),
                0
            ) AS not_sent,


            GREATEST(
                COALESCE(sent.sent_qty, 0)
                - COALESCE(ready.ready_qty, 0)
                - COALESCE(returned.returned_qty, 0),
                0
            ) AS in_manufacturing,


            COALESCE(
                invoiced.invoiced_qty,
                0
            ) AS invoiced,


            GREATEST(
                COALESCE(ready.ready_qty, 0)
                - COALESCE(invoiced.invoiced_qty, 0),
                0
            ) AS ready


        FROM `tabPurchase Receipt` pr


        # -----------------------------------------------------
        # Received quantities
        # -----------------------------------------------------

        LEFT JOIN (

            SELECT

                pri.parent AS purchase_receipt,

                SUM(pri.qty) AS received_qty


            FROM `tabPurchase Receipt Item` pri


            INNER JOIN `tabPurchase Receipt` original_pr

                ON original_pr.name = pri.parent


            WHERE

                original_pr.is_return = 0

                AND original_pr.docstatus = 1


            GROUP BY

                pri.parent

        ) received

            ON received.purchase_receipt = pr.name


        # -----------------------------------------------------
        # Office -> Manufacturing
        # -----------------------------------------------------

        LEFT JOIN (

            SELECT

                sed.custom_purchase_receipt
                    AS purchase_receipt,

                SUM(sed.qty) AS sent_qty


            FROM `tabStock Entry Detail` sed


            INNER JOIN `tabStock Entry` se

                ON se.name = sed.parent


            WHERE

                se.stock_entry_type = %s

                AND se.docstatus = 1


            GROUP BY

                sed.custom_purchase_receipt

        ) sent

            ON sent.purchase_receipt = pr.name


        # -----------------------------------------------------
        # Manufacturing -> Ready
        # -----------------------------------------------------

        LEFT JOIN (

            SELECT

                sed.custom_purchase_receipt
                    AS purchase_receipt,

                SUM(sed.qty) AS ready_qty


            FROM `tabStock Entry Detail` sed


            INNER JOIN `tabStock Entry` se

                ON se.name = sed.parent


            WHERE

                se.stock_entry_type = %s

                AND se.docstatus = 1


            GROUP BY

                sed.custom_purchase_receipt

        ) ready

            ON ready.purchase_receipt = pr.name


        # -----------------------------------------------------
        # Purchase Returns
        # -----------------------------------------------------

        LEFT JOIN (

            SELECT

                return_pr.return_against
                    AS purchase_receipt,


                ABS(
                    SUM(pri.qty)
                ) AS returned_qty


            FROM `tabPurchase Receipt` return_pr


            INNER JOIN `tabPurchase Receipt Item` pri

                ON pri.parent = return_pr.name


            WHERE

                return_pr.is_return = 1

                AND return_pr.docstatus = 1

                AND return_pr.return_against IS NOT NULL


            GROUP BY

                return_pr.return_against

        ) returned

            ON returned.purchase_receipt = pr.name


        # -----------------------------------------------------
        # Invoiced quantities (submitted Sales Invoices only)
        # -----------------------------------------------------

        LEFT JOIN (

            SELECT

                si.custom_resharpening_purchase_receipt
                    AS purchase_receipt,

                SUM(sii.qty) AS invoiced_qty


            FROM `tabSales Invoice` si

            INNER JOIN `tabSales Invoice Item` sii
                ON sii.parent = si.name


            WHERE

                si.custom_resharpening_purchase_receipt
                    IS NOT NULL

                AND si.custom_resharpening_purchase_receipt
                    != ''

                AND si.docstatus = 1


            GROUP BY

                si.custom_resharpening_purchase_receipt

        ) invoiced

            ON invoiced.purchase_receipt = pr.name


        WHERE

            {filter_where}
    """


    base_values = [

        OFFICE_TO_MANUFACTURING,

        MANUFACTURING_TO_READY,

        *filter_values,

    ]


    # ---------------------------------------------------------
    # Operational status
    # ---------------------------------------------------------

    status_case = """

        CASE

            # -------------------------------------------------
            # Invoiced (all received items invoiced or returned)
            # -------------------------------------------------

            WHEN (
                invoiced + returned >= received
                AND invoiced > 0
            )

                THEN 'Invoiced'


            # -------------------------------------------------
            # Closed
            # -------------------------------------------------

            WHEN purchase_receipt_status = 'Closed'

                THEN 'Closed'


            # -------------------------------------------------
            # Awaiting Manufacturing
            # -------------------------------------------------

            WHEN sent <= 0

                THEN 'Awaiting Manufacturing'


            # -------------------------------------------------
            # Ready / Partially Returned
            # -------------------------------------------------

            WHEN (

                ready + invoiced + returned >= received

                AND returned > 0

            )

                THEN 'Ready / Partially Returned'


            # -------------------------------------------------
            # Ready
            # -------------------------------------------------

            WHEN (

                ready + invoiced + returned >= received

                AND returned <= 0

            )

                THEN 'Ready'


            # -------------------------------------------------
            # Partially Ready
            # -------------------------------------------------

            WHEN ready > 0

                THEN 'Partially Ready'


            # -------------------------------------------------
            # In Manufacturing
            # -------------------------------------------------

            ELSE 'In Manufacturing'

        END

    """


    # ---------------------------------------------------------
    # Apply calculated status
    # ---------------------------------------------------------

    filtered_query = f"""

        SELECT

            *,

            {status_case} AS status


        FROM (

            {base_query}

        ) AS orders

    """


    filtered_values = base_values


    # ---------------------------------------------------------
    # Status filter
    # ---------------------------------------------------------

    if status == "Unable to Resharpen":

        filtered_query = f"""

            SELECT *

            FROM (

                {filtered_query}

            ) AS filtered_orders


            WHERE returned > 0

        """

    elif status:

        filtered_query = f"""

            SELECT *

            FROM (

                {filtered_query}

            ) AS filtered_orders


            WHERE status = %s

        """


        filtered_values = [

            *filtered_values,

            status,

        ]


    # ---------------------------------------------------------
    # Status counts & Total count (Single query execution)
    # ---------------------------------------------------------

    status_counts_rows = frappe.db.sql(
        f"""
            SELECT
                status,
                COUNT(*) AS count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'Invoiced' THEN invoiced
                            ELSE received
                        END
                    ), 0
                ) AS total_qty,
                COALESCE(SUM(returned), 0) AS returned_qty,
                COALESCE(SUM(CASE WHEN returned > 0 THEN 1 ELSE 0 END), 0) AS returned_count
            FROM (
                {filtered_query}
            ) AS status_orders
            GROUP BY
                status
        """,
        filtered_values,
        as_dict=True,
    )

    total_count = sum(row.count for row in status_counts_rows)
    total_returned_qty = sum(row.returned_qty for row in status_counts_rows)
    returned_orders_count = sum(row.returned_count for row in status_counts_rows)

    status_counts = {
        "Awaiting Manufacturing": {
            "count": 0,
            "total_qty": 0,
        },
        "In Manufacturing": {
            "count": 0,
            "total_qty": 0,
        },
        "Partially Ready": {
            "count": 0,
            "total_qty": 0,
        },
        "Ready / Partially Returned": {
            "count": 0,
            "total_qty": 0,
        },
        "Ready": {
            "count": 0,
            "total_qty": 0,
        },
        "Closed": {
            "count": 0,
            "total_qty": 0,
        },
        "Invoiced": {
            "count": 0,
            "total_qty": 0,
        },
        "Unable to Resharpen": {
            "count": returned_orders_count,
            "total_qty": total_returned_qty,
        },
    }

    for row in status_counts_rows:
        if row.status in status_counts and row.status != "Unable to Resharpen":
            status_counts[row.status] = {
                "count": row.count,
                "total_qty": row.total_qty,
            }


    # ---------------------------------------------------------
    # Pagination
    # ---------------------------------------------------------

    total_pages = (

        (total_count + PAGE_SIZE - 1)

        // PAGE_SIZE

    )


    if total_pages and page > total_pages:

        page = total_pages

        offset = (

            page - 1

        ) * PAGE_SIZE


    # ---------------------------------------------------------
    # Requested page
    # ---------------------------------------------------------

    paginated_query = f"""

        {filtered_query}


        ORDER BY

            receipt_date DESC,

            purchase_receipt DESC


        LIMIT {PAGE_SIZE}

        OFFSET {offset}

    """


    rows = frappe.db.sql(

        paginated_query,

        filtered_values,

        as_dict=True,

    )


    # ---------------------------------------------------------
    # Bulk fetch invoice counts for current page
    # ---------------------------------------------------------

    pr_names = [row.purchase_receipt for row in rows if row.purchase_receipt]
    invoice_counts_map = {}

    if pr_names:
        invoice_counts_data = frappe.db.sql(
            """
            SELECT
                custom_resharpening_purchase_receipt AS purchase_receipt,
                COUNT(*) AS invoice_count,
                MAX(name) AS latest_sales_invoice
            FROM `tabSales Invoice`
            WHERE
                custom_resharpening_purchase_receipt IN %s
                AND docstatus < 2
            GROUP BY
                custom_resharpening_purchase_receipt
            """,
            (tuple(pr_names),),
            as_dict=True,
        )
        invoice_counts_map = {
            row.purchase_receipt: {
                "invoice_count": row.invoice_count or 0,
                "sales_invoice": row.latest_sales_invoice or "",
            }
            for row in invoice_counts_data
        }


    # ---------------------------------------------------------
    # Build response
    # ---------------------------------------------------------

    orders = []


    for row in rows:

        inv_info = invoice_counts_map.get(row.purchase_receipt, {})
        invoice_count = inv_info.get("invoice_count", 0)
        sales_invoice = inv_info.get("sales_invoice", "")

        orders.append({

            "supplier":
                row.supplier,

            "supplier_name":
                getattr(row, "supplier_name", None) or row.supplier,

            "purchase_receipt":
                row.purchase_receipt,


            "receipt_date":
                row.receipt_date,


            "received":
                row.received or 0,


            "sent":
                row.sent or 0,


            "returned":
                row.returned or 0,


            "not_sent":
                row.not_sent or 0,


            "in_manufacturing":
                row.in_manufacturing or 0,


            "ready":
                row.ready or 0,


            "invoiced":
                row.invoiced or 0,


            "status":
                row.status,


            "purchase_receipt_status":
                row.purchase_receipt_status,

            "note":
                row.note or "",

            "has_sales_invoice":
                invoice_count > 0,

            "invoice_count":
                invoice_count,

            "sales_invoice":
                sales_invoice if invoice_count == 1 else "",

        })


    return {

        "orders":
            orders,

        "total_count":
            total_count,

        "page":
            page,

        "page_size":
            PAGE_SIZE,

        "total_pages":
            total_pages,

        "status_counts":
            status_counts,

    }


# =============================================================
# CLOSE RESHARPENING ORDER
# =============================================================

@frappe.whitelist()
def close_resharpening_order(
    purchase_receipt
):
    """
    Close a Resharpening Purchase Receipt.

    Only orders whose operational status is:

        Ready

    or:

        Ready / Partially Returned

    can be closed.
    """

    if not purchase_receipt:

        frappe.throw(
            "Purchase Receipt is required"
        )


    # ---------------------------------------------------------
    # Get Purchase Receipt
    # ---------------------------------------------------------

    receipt = frappe.get_doc(
        "Purchase Receipt",
        purchase_receipt
    )


    # ---------------------------------------------------------
    # Permission check
    # ---------------------------------------------------------

    if not frappe.has_permission(
        "Purchase Receipt",
        "write",
        receipt
    ):

        frappe.throw(
            "You do not have permission to close this Purchase Receipt."
        )


    # ---------------------------------------------------------
    # Basic validation
    # ---------------------------------------------------------

    if receipt.docstatus != 1:

        frappe.throw(
            "Only submitted Purchase Receipts can be closed."
        )


    if receipt.get("is_return"):

        frappe.throw(
            "A Purchase Return cannot be closed from the Resharpening Dashboard."
        )


    if receipt.get(
        "custom_operation_type"
    ) != "Resharpening":

        frappe.throw(
            "This Purchase Receipt is not a Resharpening order."
        )


    if receipt.status == "Closed":

        return {

            "success": True,

            "message":
                "Purchase Receipt is already closed.",

            "purchase_receipt":
                purchase_receipt,

        }


    # ---------------------------------------------------------
    # Calculate current quantities (Single consolidated query)
    # ---------------------------------------------------------

    qty_row = frappe.db.sql(
        """
        SELECT
            (
                SELECT COALESCE(SUM(qty), 0)
                FROM `tabPurchase Receipt Item`
                WHERE parent = %(pr)s
            ) AS received,

            (
                SELECT COALESCE(SUM(sed.qty), 0)
                FROM `tabStock Entry Detail` sed
                INNER JOIN `tabStock Entry` se
                    ON se.name = sed.parent
                WHERE
                    se.stock_entry_type = %(sent_type)s
                    AND se.docstatus = 1
                    AND sed.custom_purchase_receipt = %(pr)s
            ) AS sent,

            (
                SELECT COALESCE(SUM(sed.qty), 0)
                FROM `tabStock Entry Detail` sed
                INNER JOIN `tabStock Entry` se
                    ON se.name = sed.parent
                WHERE
                    se.stock_entry_type = %(ready_type)s
                    AND se.docstatus = 1
                    AND sed.custom_purchase_receipt = %(pr)s
            ) AS ready,

            (
                SELECT COALESCE(ABS(SUM(pri.qty)), 0)
                FROM `tabPurchase Receipt` return_pr
                INNER JOIN `tabPurchase Receipt Item` pri
                    ON pri.parent = return_pr.name
                WHERE
                    return_pr.is_return = 1
                    AND return_pr.docstatus = 1
                    AND return_pr.return_against = %(pr)s
            ) AS returned,

            (
                SELECT COALESCE(SUM(sii.qty), 0)
                FROM `tabSales Invoice` si
                INNER JOIN `tabSales Invoice Item` sii
                    ON sii.parent = si.name
                WHERE
                    si.custom_resharpening_purchase_receipt = %(pr)s
                    AND si.docstatus = 1
            ) AS invoiced
        """,
        {
            "pr": purchase_receipt,
            "sent_type": OFFICE_TO_MANUFACTURING,
            "ready_type": MANUFACTURING_TO_READY,
        },
        as_dict=True,
    )[0]

    received = qty_row.received or 0
    sent = qty_row.sent or 0
    ready = qty_row.ready or 0
    returned = qty_row.returned or 0
    invoiced = qty_row.invoiced or 0
    available_ready = max(ready - invoiced, 0)


    # ---------------------------------------------------------
    # Calculate operational status
    # ---------------------------------------------------------

    if (invoiced + returned >= received) and invoiced > 0:

        operational_status = "Invoiced"


    elif sent <= 0:

        operational_status = (
            "Awaiting Manufacturing"
        )


    elif (

        available_ready + invoiced + returned >= received

        and returned > 0

    ):

        operational_status = (
            "Ready / Partially Returned"
        )


    elif (

        available_ready + invoiced + returned >= received

        and returned <= 0

    ):

        operational_status = "Ready"


    elif available_ready > 0:

        operational_status = (
            "Partially Ready"
        )


    else:

        operational_status = (
            "In Manufacturing"
        )


    # ---------------------------------------------------------
    # Only Ready orders can be closed
    # ---------------------------------------------------------

    if operational_status not in (

        "Ready",

        "Ready / Partially Returned",

    ):

        frappe.throw(

            "This order cannot be closed. "
            f"Current status is: {operational_status}"

        )


    # ---------------------------------------------------------
    # Close Purchase Receipt
    # ---------------------------------------------------------

    frappe.db.set_value(

        "Purchase Receipt",

        purchase_receipt,

        "status",

        "Closed",

    )


    frappe.db.commit()

    # ---------------------------------------------------------
    # Trigger Closed WhatsApp Notification
    # ---------------------------------------------------------
    try:
        from resharpening.notifications.whatsapp import send_pr_closed_whatsapp_notification
        send_pr_closed_whatsapp_notification(purchase_receipt)
    except Exception:
        frappe.log_error(title="WhatsApp Close Notification Error", message=frappe.get_traceback())

    return {

        "success": True,

        "message":
            "Purchase Receipt closed successfully.",

        "purchase_receipt":
            purchase_receipt,

        "status":
            "Closed",

    }


# =============================================================
# ITEM-LEVEL DETAILS
# =============================================================

@frappe.whitelist()
def get_resharpening_order_details(
    purchase_receipt
):
    """
    Return item-level quantities for one
    Resharpening Purchase Receipt.

    Purchase Returns are linked through
    Purchase Receipt.return_against.
    """

    if not purchase_receipt:

        frappe.throw(
            "Purchase Receipt is required"
        )


    receipt = frappe.db.get_value(

        "Purchase Receipt",

        purchase_receipt,

        [

            "supplier",

            "posting_date",

            "is_return",

        ],

        as_dict=True,

    )


    if not receipt:

        frappe.throw(
            "Purchase Receipt not found"
        )


    # ---------------------------------------------------------
    # Safety:
    # Purchase Return itself cannot be an order.
    # ---------------------------------------------------------

    if receipt.is_return:

        frappe.throw(
            "Purchase Return cannot be used as a Resharpening order"
        )


    # ---------------------------------------------------------
    # Purchase Receipt items
    # ---------------------------------------------------------

    items = frappe.db.sql(

        """

        SELECT

            pri.item_code,

            pri.item_name,

            SUM(pri.qty) AS received_qty


        FROM `tabPurchase Receipt Item` pri


        WHERE

            pri.parent = %s


        GROUP BY

            pri.item_code,

            pri.item_name


        ORDER BY

            MIN(pri.idx)

        """,

        purchase_receipt,

        as_dict=True,

    )


    # ---------------------------------------------------------
    # Transferred to manufacturing
    # ---------------------------------------------------------

    transferred = frappe.db.sql(

        """

        SELECT

            sed.item_code,

            SUM(sed.qty) AS qty


        FROM `tabStock Entry Detail` sed


        INNER JOIN `tabStock Entry` se

            ON se.name = sed.parent


        WHERE

            se.stock_entry_type = %s

            AND se.docstatus = 1

            AND sed.custom_purchase_receipt = %s


        GROUP BY

            sed.item_code

        """,

        (

            OFFICE_TO_MANUFACTURING,

            purchase_receipt,

        ),

        as_dict=True,

    )


    # ---------------------------------------------------------
    # Manufacturing -> Ready
    # ---------------------------------------------------------

    ready_rows = frappe.db.sql(

        """

        SELECT

            sed.item_code,

            SUM(sed.qty) AS qty


        FROM `tabStock Entry Detail` sed


        INNER JOIN `tabStock Entry` se

            ON se.name = sed.parent


        WHERE

            se.stock_entry_type = %s

            AND se.docstatus = 1

            AND sed.custom_purchase_receipt = %s


        GROUP BY

            sed.item_code

        """,

        (

            MANUFACTURING_TO_READY,

            purchase_receipt,

        ),

        as_dict=True,

    )


    # ---------------------------------------------------------
    # Purchase Returns
    # ---------------------------------------------------------

    returned_rows = frappe.db.sql(

        """

        SELECT

            pri.item_code,

            ABS(
                SUM(pri.qty)
            ) AS qty


        FROM `tabPurchase Receipt` return_pr


        INNER JOIN `tabPurchase Receipt Item` pri

            ON pri.parent = return_pr.name


        WHERE

            return_pr.is_return = 1

            AND return_pr.docstatus = 1

            AND return_pr.return_against = %s


        GROUP BY

            pri.item_code

        """,

        purchase_receipt,

        as_dict=True,

    )


    # ---------------------------------------------------------
    # Invoiced quantities (submitted Sales Invoices only)
    # ---------------------------------------------------------

    invoiced_rows = frappe.db.sql(
        """
        SELECT
            sii.item_code,
            SUM(sii.qty) AS qty
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE
            si.custom_resharpening_purchase_receipt = %s
            AND si.docstatus = 1
        GROUP BY
            sii.item_code
        """,
        purchase_receipt,
        as_dict=True,
    )


    # ---------------------------------------------------------
    # Maps
    # ---------------------------------------------------------

    transferred_map = {

        row.item_code:
            row.qty or 0

        for row in transferred

    }


    ready_map = {

        row.item_code:
            row.qty or 0

        for row in ready_rows

    }


    returned_map = {

        row.item_code:
            row.qty or 0

        for row in returned_rows

    }


    invoiced_map = {

        row.item_code:
            row.qty or 0

        for row in invoiced_rows

    }


    # ---------------------------------------------------------
    # Build item-level result
    # ---------------------------------------------------------

    result = []


    for item in items:

        received_qty = (
            item.received_qty or 0
        )


        sent_qty = transferred_map.get(

            item.item_code,

            0,

        )


        total_ready_qty = ready_map.get(

            item.item_code,

            0,

        )


        returned_qty = returned_map.get(

            item.item_code,

            0,

        )


        invoiced_qty = invoiced_map.get(

            item.item_code,

            0,

        )


        available_ready_qty = max(

            total_ready_qty - invoiced_qty,

            0,

        )


        # -----------------------------------------------------
        # Important:
        #
        # Returned items WERE already sent to manufacturing.
        # -----------------------------------------------------

        not_sent_qty = max(

            received_qty
            - sent_qty,

            0,

        )


        in_manufacturing_qty = max(

            sent_qty
            - total_ready_qty
            - returned_qty,

            0,

        )


        result.append({

            "item_code":
                item.item_code,

            "item_name":
                item.item_name,

            "received":
                received_qty,

            "returned":
                returned_qty,

            "not_sent":
                not_sent_qty,

            "in_manufacturing":
                in_manufacturing_qty,

            "ready":
                available_ready_qty,

            "invoiced":
                invoiced_qty,

        })


    # ---------------------------------------------------------
    # Return response
    # ---------------------------------------------------------

    return {

        "purchase_receipt":
            purchase_receipt,

        "supplier":
            receipt.supplier,

        "receipt_date":
            receipt.posting_date,

        "items":
            result,

    }


# =============================================================
# SAVE RESHARPENING NOTE
# =============================================================

@frappe.whitelist()
def save_resharpening_note(purchase_receipt, note=None):
    """
    Save or update the custom_resharpening_note on a Purchase Receipt.
    """
    if not purchase_receipt:
        frappe.throw("Purchase Receipt is required")

    frappe.has_permission("Purchase Receipt", "write", throw=True)
    ensure_custom_note_field()

    note_val = (note or "").strip()
    frappe.db.set_value(
        "Purchase Receipt",
        purchase_receipt,
        "custom_resharpening_note",
        note_val
    )
    frappe.db.commit()

    return {
        "success": True,
        "purchase_receipt": purchase_receipt,
        "note": note_val
    }


# =============================================================
# CREATE RESHARPENING SALES INVOICE
# =============================================================

@frappe.whitelist()
def create_resharpening_sales_invoice(
    purchase_receipt
):
    """
    Prepare a new Sales Invoice for a closed Resharpening
    Purchase Receipt.

    Does NOT save or submit the invoice.

    Returns invoice field values so the frontend can open
    a new unsaved draft Sales Invoice form.

    If a Sales Invoice already exists for this Purchase
    Receipt, returns the existing invoice name instead.
    """

    if not purchase_receipt:

        frappe.throw(
            "Purchase Receipt is required"
        )


    # ---------------------------------------------------------
    # Permission check
    # ---------------------------------------------------------

    if not frappe.has_permission(
        "Sales Invoice",
        "create",
    ):

        frappe.throw(
            "You do not have permission to create Sales Invoices."
        )


    # ---------------------------------------------------------
    # Validate Purchase Receipt
    # ---------------------------------------------------------

    receipt = frappe.db.get_value(

        "Purchase Receipt",

        purchase_receipt,

        [
            "name",
            "supplier",
            "supplier_name",
            "status",
            "docstatus",
            "is_return",
            "custom_operation_type",
        ],

        as_dict=True,

    )


    if not receipt:

        frappe.throw(
            "Purchase Receipt not found"
        )


    if receipt.docstatus != 1:

        frappe.throw(
            "Only submitted Purchase Receipts can be invoiced."
        )


    if receipt.get("is_return"):

        frappe.throw(
            "A Purchase Return cannot be invoiced."
        )


    if receipt.get(
        "custom_operation_type"
    ) != "Resharpening":

        frappe.throw(
            "This Purchase Receipt is not a Resharpening order."
        )


    # ---------------------------------------------------------
    # Ensure custom field exists on Sales Invoice
    # ---------------------------------------------------------

    ensure_sales_invoice_pr_field()


    # ---------------------------------------------------------
    # Find matching Customer from Supplier
    # ---------------------------------------------------------

    supplier_id = receipt.supplier

    if not supplier_id:

        frappe.throw(
            "لا يوجد مورد مرتبط بإذن الاستلام هذا."
        )

    # Get the display/actual name of the supplier
    supplier_display_name = (
        receipt.get("supplier_name")
        or frappe.db.get_value("Supplier", supplier_id, "supplier_name")
        or supplier_id
    )

    # Match Customer by customer_name first, then fallback to ID/name
    customer_name = (
        frappe.db.get_value("Customer", {"customer_name": supplier_display_name}, "name")
        or frappe.db.get_value("Customer", {"customer_name": supplier_id}, "name")
        or frappe.db.get_value("Customer", supplier_id, "name")
    )

    if not customer_name:

        frappe.throw(
            f"لم يتم العثور على عميل مطابق للمورد: {supplier_display_name}\n\n"
            "يرجى إنشاء عميل بنفس الاسم أولاً."
        )


    # ---------------------------------------------------------
    # Calculate item-level available quantities
    # ---------------------------------------------------------

    company = (
        frappe.db.get_value("Purchase Receipt", purchase_receipt, "company")
        or frappe.defaults.get_user_default("Company")
        or "cnc"
    )

    # Purchase Receipt items
    items = frappe.db.sql(
        """
        SELECT
            pri.item_code,
            pri.item_name,
            pri.uom,
            pri.stock_uom,
            pri.conversion_factor,
            pri.description,
            SUM(pri.qty) AS received_qty
        FROM `tabPurchase Receipt Item` pri
        WHERE
            pri.parent = %s
        GROUP BY
            pri.item_code,
            pri.item_name,
            pri.uom,
            pri.stock_uom,
            pri.conversion_factor,
            pri.description
        ORDER BY
            MIN(pri.idx)
        """,
        purchase_receipt,
        as_dict=True,
    )

    # Manufacturing -> Ready
    ready_rows = frappe.db.sql(
        """
        SELECT
            sed.item_code,
            SUM(sed.qty) AS qty
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se
            ON se.name = sed.parent
        WHERE
            se.stock_entry_type = %s
            AND se.docstatus = 1
            AND sed.custom_purchase_receipt = %s
        GROUP BY
            sed.item_code
        """,
        (
            MANUFACTURING_TO_READY,
            purchase_receipt,
        ),
        as_dict=True,
    )

    # Submitted Sales Invoices for this PR
    invoiced_rows = frappe.db.sql(
        """
        SELECT
            sii.item_code,
            SUM(sii.qty) AS qty
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE
            si.custom_resharpening_purchase_receipt = %s
            AND si.docstatus = 1
        GROUP BY
            sii.item_code
        """,
        purchase_receipt,
        as_dict=True,
    )

    # Build maps
    ready_map = {
        row.item_code: row.qty or 0
        for row in ready_rows
    }

    invoiced_map = {
        row.item_code: row.qty or 0
        for row in invoiced_rows
    }

    # ---------------------------------------------------------
    # Build invoice items (only items with available_qty > 0)
    # ---------------------------------------------------------

    items_to_invoice = []
    for item in items:
        total_ready = ready_map.get(item.item_code, 0)
        already_invoiced = invoiced_map.get(item.item_code, 0)
        available_qty = max(total_ready - already_invoiced, 0)
        if available_qty > 0:
            items_to_invoice.append((item, available_qty))

    if not items_to_invoice:
        frappe.throw(
            "لا توجد كمية جاهزة متاحة للفوترة."
        )

    item_codes_tuple = tuple(set(item.item_code for item, _ in items_to_invoice))
    items_meta_rows = frappe.db.sql(
        """
        SELECT name, item_name, stock_uom, description
        FROM `tabItem`
        WHERE name IN %s
        """,
        (item_codes_tuple,),
        as_dict=True,
    )
    items_meta_map = {row.name: row for row in items_meta_rows}

    invoice_items = []

    for item, available_qty in items_to_invoice:
        item_doc = items_meta_map.get(item.item_code) or {}

        item_name = item.item_name or item_doc.get("item_name") or item.item_code
        uom = item.uom or item_doc.get("stock_uom") or "Nos"
        stock_uom = item.stock_uom or item_doc.get("stock_uom") or uom
        conversion_factor = item.conversion_factor or 1.0
        description = item.description or item_doc.get("description") or item_name

        row_data = {
            "item_code": item.item_code,
            "item_name": item_name,
            "qty": available_qty,
            "uom": uom,
            "stock_uom": stock_uom,
            "conversion_factor": conversion_factor,
            "description": description,
        }

        invoice_items.append(row_data)

    # ---------------------------------------------------------
    # Return invoice data for client-side form creation
    # ---------------------------------------------------------

    return {
        "success": True,
        "existing": False,
        "invoice_data": {
            "customer": customer_name,
            "company": company,
            "custom_resharpening_purchase_receipt": purchase_receipt,
            "items": invoice_items,
        },
    }


# =============================================================
# GET RESHARPENING SALES INVOICES (FOR VIEW DIALOG)
# =============================================================

@frappe.whitelist()
def get_resharpening_sales_invoices(
    purchase_receipt
):
    """
    Return all active Sales Invoices (draft and submitted) linked to a
    Purchase Receipt for the "عرض فواتير المبيعات" dialog.
    """

    if not purchase_receipt:
        frappe.throw("Purchase Receipt is required")

    invoices = frappe.db.sql(
        """
        SELECT
            si.name,
            si.posting_date,
            si.docstatus,
            si.status,
            COALESCE(SUM(sii.qty), 0) AS total_qty
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Invoice Item` sii
            ON sii.parent = si.name
        WHERE
            si.custom_resharpening_purchase_receipt = %s
            AND si.docstatus < 2
        GROUP BY
            si.name,
            si.posting_date,
            si.docstatus,
            si.status
        ORDER BY
            si.creation ASC
        """,
        purchase_receipt,
        as_dict=True,
    )

    return {
        "success": True,
        "invoices": invoices or [],
    }


