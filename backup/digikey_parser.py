from parser import Parser

class DigikeyParser(Parser):

    def check(self, data) -> bool:
        """
        Checks to see if the data matches this parser signature
        :return: boolean
        """
        if data.startswith(b'[)>\x1e06\x1d'):
            print(f"Matched {self.__class__.__name__}")
            return True


    def parse(self, fields):
        self.supplier_pn = fields[1].replace('P', '', 1)
        self.manufacturer_pn = fields[2].replace('P', '', 1)
        self.quantity = fields[8].replace('Q', '', 1)


    def lookup(self):
        print("Example lookup")

    def submit(self):
        print("Example submit")

    def process(self, data):
        if data.encode().startswith(b'[)>\x1e06\x1d'):
            # Split the data by Record Separator
            records = data.split('\x1e')

            fields = records[1].split('\x1d')
            self.parse(fields)
            # Display the fields
            print(self)

    def __repr__(self):
        return str(f"{self.__class__.__name__}, Supplier Part Number: {self.supplier_pn} Manufacturer PN: {self.manufacturer_pn} Quantity: {self.quantity}")
