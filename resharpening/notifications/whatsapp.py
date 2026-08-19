import frappe
import requests
import re
import base64

def get_whatsapp_settings():
    return frappe.get_doc("Resharpening WhatsApp Settings")

def get_supplier_mobile(supplier):
    if not supplier:
        return None
        
    # 1. Look for Primary Contact with mobile_no or phone
    contacts = frappe.db.sql("""
        SELECT c.mobile_no, c.phone, c.is_primary_contact
        FROM `tabContact` c
        INNER JOIN `tabDynamic Link` dl ON dl.parent = c.name
        WHERE dl.link_doctype = 'Supplier' AND dl.link_name = %s
        ORDER BY c.is_primary_contact DESC, c.modified DESC
    """, supplier, as_dict=True)
    
    for c in contacts:
        phone = c.mobile_no or c.phone
        if phone:
            return phone
            
    # 2. Fallback to Supplier's direct mobile_no if field exists
    if frappe.db.has_column("Supplier", "mobile_no"):
        phone = frappe.db.get_value("Supplier", supplier, "mobile_no")
        if phone:
            return phone
            
    return None

def clean_phone_number(phone):
    if not phone:
        return ""
    clean_phone = re.sub(r'\D', '', str(phone))
    if not clean_phone:
        return ""
    # Auto-add Egypt country code (20) for local numbers starting with 0
    if clean_phone.startswith('0'):
        clean_phone = '20' + clean_phone[1:]
    return clean_phone

def create_whatsapp_log(event_type, event_reference, purchase_receipt, supplier, phone, message):
    try:
        log = frappe.get_doc({
            "doctype": "Resharpening WhatsApp Log",
            "event_type": event_type,
            "event_reference": event_reference,
            "purchase_receipt": purchase_receipt,
            "supplier": supplier,
            "phone": phone,
            "message": message,
            "status": "Pending",
            "sent_at": frappe.utils.now_datetime()
        })
        log.insert(ignore_permissions=True, ignore_links=True)
        frappe.db.commit()
        return log.name
    except Exception:
        frappe.log_error(title="WhatsApp Log Creation Error", message=frappe.get_traceback())
        return None

def update_whatsapp_log(log_name, status, error_message=None):
    if not log_name:
        return
    try:
        frappe.db.set_value("Resharpening WhatsApp Log", log_name, {
            "status": status,
            "error_message": error_message or "",
            "sent_at": frappe.utils.now_datetime()
        })
        frappe.db.commit()
    except Exception:
        frappe.log_error(title="WhatsApp Log Update Error", message=frappe.get_traceback())

def is_duplicate_event(event_type, event_reference):
    if not event_reference:
        return False
    return bool(frappe.db.exists("Resharpening WhatsApp Log", {
        "event_type": event_type,
        "event_reference": event_reference,
        "status": "Sent"
    }))

def get_resharpening_order_progress(purchase_receipt):
    """
    Calculate the current progress and operational status of a Resharpening Purchase Receipt.
    Uses the exact same calculation rules as api/dashboard.py.
    """
    if not purchase_receipt:
        return {
            "received_qty": 0,
            "sent_qty": 0,
            "ready_qty": 0,
            "returned_qty": 0,
            "remaining_qty": 0,
            "order_status": "",
            "return_count": 0
        }
        
    from resharpening.utils.stock_entry_types import (
        OFFICE_TO_MANUFACTURING,
        MANUFACTURING_TO_READY,
    )
    
    # 1. Received quantity (original PR items)
    received = frappe.db.sql("""
        SELECT COALESCE(SUM(qty), 0) AS qty
        FROM `tabPurchase Receipt Item`
        WHERE parent = %s
    """, purchase_receipt, as_dict=True)[0].qty or 0
    
    # 2. Sent to Factory (Office -> Manufacturing)
    sent = frappe.db.sql("""
        SELECT COALESCE(SUM(sed.qty), 0) AS qty
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.stock_entry_type = %s
          AND se.docstatus = 1
          AND sed.custom_purchase_receipt = %s
    """, (OFFICE_TO_MANUFACTURING, purchase_receipt), as_dict=True)[0].qty or 0
    
    # 3. Ready in Office (Manufacturing -> Ready)
    ready = frappe.db.sql("""
        SELECT COALESCE(SUM(sed.qty), 0) AS qty
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.stock_entry_type = %s
          AND se.docstatus = 1
          AND sed.custom_purchase_receipt = %s
    """, (MANUFACTURING_TO_READY, purchase_receipt), as_dict=True)[0].qty or 0
    
    # 4. Returned to Supplier (Purchase Return)
    returned = frappe.db.sql("""
        SELECT COALESCE(ABS(SUM(pri.qty)), 0) AS qty
        FROM `tabPurchase Receipt` return_pr
        INNER JOIN `tabPurchase Receipt Item` pri ON pri.parent = return_pr.name
        WHERE return_pr.is_return = 1
          AND return_pr.docstatus = 1
          AND return_pr.return_against = %s
    """, purchase_receipt, as_dict=True)[0].qty or 0
    
    # 5. Return count (number of Factory -> Office Stock Entries)
    return_count_res = frappe.db.sql("""
        SELECT COUNT(DISTINCT se.name) AS count
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.stock_entry_type = %s
          AND se.docstatus = 1
          AND sed.custom_purchase_receipt = %s
    """, (MANUFACTURING_TO_READY, purchase_receipt), as_dict=True)
    return_count = return_count_res[0].count if return_count_res else 0
    
    # Check if PR itself is closed
    pr_status = frappe.db.get_value("Purchase Receipt", purchase_receipt, "status")
    
    # 6. Operational Status
    if pr_status == "Closed":
        operational_status = "Closed"
    elif sent <= 0:
        operational_status = "Awaiting Manufacturing"
    elif (ready + returned >= received) and returned > 0:
        operational_status = "Ready / Partially Returned"
    elif (ready >= received) and returned <= 0:
        operational_status = "Ready"
    elif ready > 0:
        operational_status = "Partially Ready"
    else:
        operational_status = "In Manufacturing"
        
    remaining = max(received - ready - returned, 0)
    
    def _clean_num(val):
        flt_val = frappe.utils.flt(val)
        return int(flt_val) if flt_val.is_integer() else flt_val

    return {
        "received_qty": _clean_num(received),
        "sent_qty": _clean_num(sent),
        "ready_qty": _clean_num(ready),
        "returned_qty": _clean_num(returned),
        "remaining_qty": _clean_num(remaining),
        "order_status": operational_status,
        "return_count": return_count
    }

def format_message(template, doc=None, items=None, **kwargs):
    if not template:
        return ""
    
    # 1. Extract item list safely for CURRENT EVENT
    items_formatted = []
    items_to_process = items if items is not None else (doc.items if doc and hasattr(doc, "items") else [])
    
    total_event_qty = 0.0
    item_count = 0
    
    if items_to_process:
        for item in items_to_process:
            raw_qty = getattr(item, "qty", 0) or getattr(item, "transfer_qty", 0) or getattr(item, "stock_qty", 0) or 0
            qty = abs(frappe.utils.flt(raw_qty))
            code = getattr(item, "item_code", "") or getattr(item, "item_name", "")
            if qty > 0 and code:
                qty_str = int(qty) if qty.is_integer() else qty
                items_formatted.append(f"{qty_str}x {code}")
                total_event_qty += qty
                item_count += 1
                
    item_list = ", ".join(items_formatted)
    clean_total_qty = int(total_event_qty) if total_event_qty.is_integer() else total_event_qty
    
    # 2. Resolve Purchase Receipt reference for progress calculation
    pr_name = kwargs.get("purchase_receipt") or ""
    if not pr_name and doc:
        if getattr(doc, "doctype", None) == "Purchase Receipt":
            pr_name = getattr(doc, "return_against", None) or doc.name
        elif getattr(doc, "doctype", None) == "Stock Entry" and hasattr(doc, "items") and doc.items:
            pr_name = getattr(doc.items[0], "custom_purchase_receipt", "") or ""
            
    # 3. Fetch Order Progress
    progress = {}
    if pr_name:
        progress = get_resharpening_order_progress(pr_name)
        
    return_number = kwargs.get("return_number")
    if return_number is None:
        return_number = progress.get("return_count", "") if progress else ""
    
    context = {
        # General
        "supplier_name": kwargs.get("supplier_name") or "",
        "purchase_receipt": pr_name,
        "stock_entry": kwargs.get("stock_entry") or (doc.name if doc and hasattr(doc, "name") and getattr(doc, "doctype", None) == "Stock Entry" else ""),
        "date": frappe.utils.today(),
        
        # Current Event Items
        "item_list": item_list,
        "items_list": item_list,
        "items": item_list,
        "item": item_list,
        "item_code": item_list,
        "item_name": item_list,
        
        # Quantity
        "total_qty": clean_total_qty,
        "item_count": item_count,
        
        # Order Progress
        "received_qty": progress.get("received_qty", ""),
        "ready_qty": progress.get("ready_qty", ""),
        "remaining_qty": progress.get("remaining_qty", ""),
        
        # Factory Return
        "return_number": return_number,
        
        # Purchase Return
        "return_reason": kwargs.get("return_reason") or (getattr(doc, "custom_resharp_return_reason", "") if doc else "") or "",
        "resharp_return_reason": kwargs.get("return_reason") or (getattr(doc, "custom_resharp_return_reason", "") if doc else "") or "",
        "reason": kwargs.get("return_reason") or (getattr(doc, "custom_resharp_return_reason", "") if doc else "") or "",

        # Status
        "order_status": progress.get("order_status", "")
    }
    
    # Replace placeholders
    for key, value in context.items():
        template = template.replace(f"{{{key}}}", str(value))
        
    return template

def send_message(phone, text, settings, log_id=None):
    if not phone or not text:
        if log_id:
            update_whatsapp_log(log_id, "Failed", "Missing phone number or message text")
        return
        
    clean_phone = clean_phone_number(phone)
    if not clean_phone:
        if log_id:
            update_whatsapp_log(log_id, "Failed", f"Invalid phone number: {phone}")
        return
        
    url = settings.evoapi_url.rstrip('/') if settings.evoapi_url else ""
    if not url:
        if log_id:
            update_whatsapp_log(log_id, "Failed", "EvoAPI URL is not configured in settings")
        return
        
    instance_id = settings.evoapi_instance_id
    if instance_id and not url.endswith(f"/message/sendText/{instance_id}"):
        if "message/sendText" not in url:
            url = f"{url}/message/sendText/{instance_id}"
            
    api_token = settings.get_password("evoapi_token")
    headers = {
        "apikey": api_token,
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    payload = {
        "number": clean_phone,
        "text": text
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        if log_id:
            update_whatsapp_log(log_id, "Sent")
    except Exception as e:
        resp_text = getattr(e.response, 'text', str(e))
        clean_error_msg = f"URL: {url}\nResponse: {resp_text}"
        frappe.log_error(title="WhatsApp Text API Error", message=clean_error_msg)
        if log_id:
            update_whatsapp_log(log_id, "Failed", resp_text)

def send_document(phone, document_base64, filename, caption, settings, log_id=None):
    if not phone or not document_base64:
        if log_id:
            update_whatsapp_log(log_id, "Failed", "Missing phone number or document")
        return
        
    clean_phone = clean_phone_number(phone)
    if not clean_phone:
        if log_id:
            update_whatsapp_log(log_id, "Failed", f"Invalid phone number: {phone}")
        return
        
    url = settings.evoapi_url.rstrip('/') if settings.evoapi_url else ""
    if not url:
        if log_id:
            update_whatsapp_log(log_id, "Failed", "EvoAPI URL is not configured in settings")
        return
        
    instance_id = settings.evoapi_instance_id
    if instance_id:
        if "message/sendMedia" not in url:
            base_url = re.sub(r'/message/send.*', '', url)
            url = f"{base_url}/message/sendMedia/{instance_id}"
            
    api_token = settings.get_password("evoapi_token")
    headers = {
        "apikey": api_token,
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    payload = {
        "number": clean_phone,
        "mediatype": "document",
        "mimetype": "application/pdf",
        "caption": caption or filename,
        "media": document_base64,
        "fileName": filename
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        response.raise_for_status()
        if log_id:
            update_whatsapp_log(log_id, "Sent")
    except Exception as e:
        resp_text = getattr(e.response, 'text', str(e))
        clean_error_msg = f"URL: {url}\nResponse: {resp_text}"
        frappe.log_error(title="WhatsApp PDF Document API Error", message=clean_error_msg)
        if log_id:
            update_whatsapp_log(log_id, "Failed", resp_text)

def process_receipt_notification(doc_name):
    """
    Executes in the background worker queue to avoid slowing down document submission.
    """
    try:
        doc = frappe.get_doc("Purchase Receipt", doc_name)
    except Exception:
        return
        
    settings = get_whatsapp_settings()
    if not settings.enable_whatsapp_notifications:
        return
        
    is_return = getattr(doc, "is_return", 0) == 1
    
    if is_return:
        if not getattr(settings, "send_item_return_message", 1):
            return
        template = getattr(settings, "item_return_template", None)
        event_type = "Purchase Return"
        event_ref = doc.name
        send_pdf = False
    else:
        if not getattr(settings, "send_receive_message", 1):
            return
        template = getattr(settings, "receipt_message_template", None)
        event_type = "Receive"
        event_ref = doc.name
        send_pdf = bool(getattr(settings, "send_receipt_pdf", 1))
        
    if not template or is_duplicate_event(event_type, event_ref):
        return
        
    phone = get_supplier_mobile(doc.supplier)
    if not phone:
        return
        
    supplier_name = frappe.db.get_value("Supplier", doc.supplier, "supplier_name") or doc.supplier
    original_pr = getattr(doc, "return_against", None) or doc.name
    
    message = format_message(
        template, 
        doc=doc, 
        supplier_name=supplier_name,
        purchase_receipt=original_pr
    )
    
    log_id = create_whatsapp_log(event_type, event_ref, original_pr, doc.supplier, phone, message)
    
    if send_pdf:
        try:
            print_format = getattr(settings, "receipt_print_format", None)
            pdf_bytes = frappe.get_print("Purchase Receipt", doc.name, print_format=print_format, as_pdf=True)
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            filename = f"{doc.name}.pdf"
            send_document(
                phone=phone,
                document_base64=pdf_b64,
                filename=filename,
                caption=message,
                settings=settings,
                log_id=log_id
            )
        except Exception:
            frappe.log_error(title="WhatsApp PDF Generation Error", message=frappe.get_traceback())
            send_message(phone=phone, text=message, settings=settings, log_id=log_id)
    else:
        send_message(phone=phone, text=message, settings=settings, log_id=log_id)

def send_receipt_message(doc, method=None):
    if doc.docstatus != 1:
        return
        
    # Check if Resharpening Purchase Receipt or Return against one
    is_resharpening = getattr(doc, "custom_operation_type", None) == "Resharpening"
    if not is_resharpening and getattr(doc, "is_return", 0) and getattr(doc, "return_against", None):
        parent_op = frappe.db.get_value("Purchase Receipt", doc.return_against, "custom_operation_type")
        if parent_op == "Resharpening":
            is_resharpening = True
            
    if not is_resharpening:
        return
        
    # Offload entirely to background queue so Purchase Receipt submission is instant (no lag)
    frappe.enqueue(process_receipt_notification, doc_name=doc.name, queue="short")

def send_pr_closed_whatsapp_notification(purchase_receipt):
    """
    Explicitly triggered when a Resharpening Purchase Receipt is closed.
    """
    if not purchase_receipt:
        return
        
    settings = get_whatsapp_settings()
    if not settings.enable_whatsapp_notifications or not getattr(settings, "send_closed_message", 1):
        return
        
    event_type = "Closed"
    event_ref = purchase_receipt
    
    if is_duplicate_event(event_type, event_ref):
        return
        
    template = getattr(settings, "ready_message_template", None)
    if not template:
        return
        
    receipt = frappe.get_doc("Purchase Receipt", purchase_receipt)
    if getattr(receipt, "custom_operation_type", None) != "Resharpening":
        return
        
    phone = get_supplier_mobile(receipt.supplier)
    if not phone:
        return
        
    supplier_name = frappe.db.get_value("Supplier", receipt.supplier, "supplier_name") or receipt.supplier
    
    message = format_message(
        template, 
        doc=receipt, 
        supplier_name=supplier_name,
        purchase_receipt=receipt.name
    )
    
    log_id = create_whatsapp_log(event_type, event_ref, receipt.name, receipt.supplier, phone, message)
    frappe.enqueue(send_message, phone=phone, text=message, settings=settings, log_id=log_id)

def send_stock_entry_message(doc, method=None):
    if doc.docstatus != 1:
        return
        
    from resharpening.utils.stock_entry_types import OFFICE_TO_MANUFACTURING, MANUFACTURING_TO_READY
    
    settings = get_whatsapp_settings()
    if not settings.enable_whatsapp_notifications:
        return
        
    if doc.stock_entry_type == OFFICE_TO_MANUFACTURING:
        if not getattr(settings, "send_factory_transfer_message", 1):
            return
        template = getattr(settings, "factory_transfer_template", None)
        event_type = "Factory Transfer"
    elif doc.stock_entry_type == MANUFACTURING_TO_READY:
        if not getattr(settings, "send_factory_return_message", 1):
            return
        template = getattr(settings, "factory_return_template", None) or getattr(settings, "item_return_template", None)
        event_type = "Factory Return"
    else:
        return
        
    if not template:
        return
        
    # Group items by (custom_supplier, custom_purchase_receipt) to safely handle multi-order stock entries
    grouped_orders = {}
    if doc.items:
        for item in doc.items:
            supplier = getattr(item, "custom_supplier", None)
            pr = getattr(item, "custom_purchase_receipt", None)
            if not supplier:
                continue
                
            key = (supplier, pr)
            if key not in grouped_orders:
                grouped_orders[key] = []
            grouped_orders[key].append(item)
            
    for (supplier, pr), items in grouped_orders.items():
        # Phase 8: Duplicate Protection per Stock Entry / Order group
        event_ref = f"{doc.name}-{supplier}-{pr}" if len(grouped_orders) > 1 else doc.name
        if is_duplicate_event(event_type, event_ref):
            continue
            
        phone = get_supplier_mobile(supplier)
        if not phone:
            continue
            
        supplier_name = frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier
        
        # Calculate return sequence number for Factory Return
        return_number = None
        if event_type == "Factory Return" and pr:
            # Count distinct submitted stock entries of type MANUFACTURING_TO_READY for this PR
            count_res = frappe.db.sql("""
                SELECT COUNT(DISTINCT se.name) AS cnt
                FROM `tabStock Entry Detail` sed
                INNER JOIN `tabStock Entry` se ON se.name = sed.parent
                WHERE se.stock_entry_type = %s
                  AND se.docstatus = 1
                  AND sed.custom_purchase_receipt = %s
            """, (MANUFACTURING_TO_READY, pr), as_dict=True)
            return_number = count_res[0].cnt if count_res else 1
        
        message = format_message(
            template, 
            doc=doc,
            items=items,
            supplier_name=supplier_name,
            purchase_receipt=pr or "",
            stock_entry=doc.name,
            return_number=return_number
        )
        
        log_id = create_whatsapp_log(event_type, event_ref, pr or "", supplier, phone, message)
        frappe.enqueue(send_message, phone=phone, text=message, settings=settings, log_id=log_id)
