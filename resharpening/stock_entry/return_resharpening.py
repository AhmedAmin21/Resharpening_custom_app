import frappe

from resharpening.utils.stock_entry_types import (
    OFFICE_TO_MANUFACTURING,
    MANUFACTURING_TO_READY,
)
from resharpening.utils.warehouses import (
    MANUFACTURING_WAREHOUSE,
    READY_WAREHOUSE,
)


@frappe.whitelist()
def get_resharpening_orders():
    """
    Return all open Resharpening Purchase Receipts that
    currently have items available in the manufacturing warehouse.

    Optimized to fetch all quantities in bulk using 4 total queries
    instead of 3*N queries per open Purchase Receipt.

    Warehouses are returned in the same response so the
    frontend only needs one server request.
    """

    open_prs = frappe.db.sql(
        """
        SELECT name, supplier, posting_date, status
        FROM `tabPurchase Receipt`
        WHERE docstatus = 1
          AND custom_operation_type = 'Resharpening'
          AND COALESCE(is_return, 0) = 0
          AND status != 'Closed'
        ORDER BY posting_date DESC
        """,
        as_dict=True,
    )

    if not open_prs:
        return {
            "orders": [],
            "warehouses": {
                "source_warehouse": MANUFACTURING_WAREHOUSE,
                "target_warehouse": READY_WAREHOUSE,
            },
        }

    pr_names = tuple(pr.name for pr in open_prs)

    # 1. Transferred from Office to Factory (Stock Entry)
    transferred_rows = frappe.db.sql(
        """
        SELECT
            sed.custom_purchase_receipt AS pr,
            sed.item_code,
            SUM(sed.qty) AS qty
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se
            ON se.name = sed.parent
        WHERE
            se.stock_entry_type = %s
            AND se.docstatus = 1
            AND sed.custom_purchase_receipt IN %s
        GROUP BY sed.custom_purchase_receipt, sed.item_code
        """,
        (OFFICE_TO_MANUFACTURING, pr_names),
        as_dict=True,
    )

    # 2. Returned from Factory to Ready (Stock Entry)
    ready_rows = frappe.db.sql(
        """
        SELECT
            sed.custom_purchase_receipt AS pr,
            sed.item_code,
            SUM(sed.qty) AS qty
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se
            ON se.name = sed.parent
        WHERE
            se.stock_entry_type = %s
            AND se.docstatus = 1
            AND sed.custom_purchase_receipt IN %s
        GROUP BY sed.custom_purchase_receipt, sed.item_code
        """,
        (MANUFACTURING_TO_READY, pr_names),
        as_dict=True,
    )

    # 3. Purchase returns against these PRs
    pr_return_rows = frappe.db.sql(
        """
        SELECT
            pr.return_against AS pr,
            pri.item_code,
            ABS(SUM(pri.qty)) AS qty
        FROM `tabPurchase Receipt Item` pri
        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
        WHERE
            pr.is_return = 1
            AND pr.docstatus = 1
            AND pr.return_against IN %s
        GROUP BY pr.return_against, pri.item_code
        """,
        (pr_names,),
        as_dict=True,
    )

    transferred_map = {(r.pr, r.item_code): r.qty for r in transferred_rows}
    ready_map = {(r.pr, r.item_code): r.qty for r in ready_rows}
    pr_return_map = {(r.pr, r.item_code): r.qty for r in pr_return_rows}

    all_keys = set(transferred_map) | set(ready_map) | set(pr_return_map)

    # Group positive available quantities by PR
    positive_items_by_pr = {}
    all_positive_item_codes = set()

    for pr, item_code in all_keys:
        t_qty = transferred_map.get((pr, item_code), 0)
        r_qty = ready_map.get((pr, item_code), 0)
        ret_qty = pr_return_map.get((pr, item_code), 0)
        avail_qty = t_qty - r_qty - ret_qty

        if avail_qty > 0:
            if pr not in positive_items_by_pr:
                positive_items_by_pr[pr] = []
            positive_items_by_pr[pr].append({
                "item_code": item_code,
                "transferred_qty": t_qty,
                "returned_qty": r_qty,
                "purchase_returned_qty": ret_qty,
                "available_qty": avail_qty,
            })
            all_positive_item_codes.add(item_code)

    # 4. Fetch Item metadata in a single bulk query
    items_meta_map = {}
    if all_positive_item_codes:
        meta_rows = frappe.db.sql(
            """
            SELECT name, item_name, stock_uom
            FROM `tabItem`
            WHERE name IN %s
            """,
            (tuple(all_positive_item_codes),),
            as_dict=True,
        )
        items_meta_map = {r.name: r for r in meta_rows}

    orders = []
    for pr in open_prs:
        if pr.name in positive_items_by_pr:
            pr_items = []
            for item in sorted(positive_items_by_pr[pr.name], key=lambda x: x["item_code"]):
                meta = items_meta_map.get(item["item_code"]) or {}
                pr_items.append({
                    "item_code": item["item_code"],
                    "item_name": meta.get("item_name") or item["item_code"],
                    "transferred_qty": item["transferred_qty"],
                    "returned_qty": item["returned_qty"],
                    "purchase_returned_qty": item["purchase_returned_qty"],
                    "available_qty": item["available_qty"],
                    "stock_uom": meta.get("stock_uom") or "Nos",
                })

            orders.append({
                "purchase_receipt": pr.name,
                "supplier": pr.supplier,
                "posting_date": pr.posting_date,
                "status": pr.status,
                "items": pr_items,
            })

    return {
        "orders": orders,
        "warehouses": {
            "source_warehouse": MANUFACTURING_WAREHOUSE,
            "target_warehouse": READY_WAREHOUSE,
        },
    }
