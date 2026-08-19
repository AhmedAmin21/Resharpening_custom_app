from resharpening.notifications.whatsapp import format_message

class DummyItem:
    def __init__(self, qty, item_code):
        self.qty = qty
        self.item_code = item_code

class DummyDoc:
    def __init__(self, name, items):
        self.name = name
        self.items = items

def test():
    doc = DummyDoc("PR-0001", [DummyItem(5, "Blade-A"), DummyItem(0, "Blade-B"), DummyItem(2, "Cutter-X")])
    template = "Hello {supplier_name}, we received {item_list} from receipt {purchase_receipt} on {date}."
    
    result = format_message(template, doc, supplier_name="Acme Corp")
    print("FORMAT RESULT:", result)
