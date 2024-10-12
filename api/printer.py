class Printer:
    def __init__(self, name):
        self.name = name

    def connect(self):
        return f"Connected to printer: {self.name}"

    def print_id_card(self, id_card_info):
        return f"Printing ID card with info: {id_card_info}"

printers = [Printer("Magicard"), Printer("PVC Evolis")]

def get_connected_printers():
    return [printer.connect() for printer in printers]
