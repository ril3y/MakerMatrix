from backup.parser import Parser
from api.easyeda import EasyedaApi
api = EasyedaApi()

class MouserParser(Parser):
    def __init__(self):
        self.manufacturer: str
        self.package: str

    def barcode_parse(self, data_string):
        # data_string = data_string.decode('utf-8')
        fields = data_string.split('\x1d')
        # key_value_pairs = re.findall(r"(\w+):([^,']+)", data_string)
        # data = {key: value for key, value in key_value_pairs}
        # We got a valid resonse
        # ['{pbn:PICK2310310072', 'on:GB2310311110', 'pc:C1691', 'pm:CL10A106MQ8NNNC', 'qty:1000', 'mc:', 'cc:1', 'pdi:95279765', 'hp:0', 'wc:ZH}']
        # self.quantity = int(data.get('qty', 0))
        # self.order_number = data.get('{pbn', '')
        # # self.part_link = data.get('pl', '')
        # self.supplier_pn = data.get('pc', '')
        # self.manufacturer_pn = data.get('pm', '')
        # self.order_date = self.parse_to_datetime(data.get('on', ''))

    # def parse_to_datetime(self, input_string):
    #     try:
    #         # Extract the date part (ignoring the first two characters and the last four)
    #         if input_string:
    #             date_part = input_string[2:8]
    #             return datetime.strptime(date_part, '%y%m%d')
    #         else:
    #             return None
    #     except ValueError as ve:
    #         print(f"Error parsing date: {ve}")
    #         return None

    def process(self, data_string):
        try:
            # Parse the data string and set the attribute values

            self.supplier = "LCSC"
            self.barcode_parse(data_string)

            lcsc_data = api.get_info_from_easyeda_api(lcsc_id=self.supplier_pn)
            if len(lcsc_data) != 0:
                self.parse_lscs_response(lcsc_data)
                self.supplier_icon = f"http:{lcsc_data['result']['packageDetail']['owner']['avatar']}"
            else:
                print(f"Supplier Part {self.supplier_pn} not found.")

            print(f"Data: {lcsc_data}")

        except Exception as e:
            print(f"Error processing data: {e}")


    def parse_footprint(self, mc_value):
        try:
            # Extract the footprint from the 'mc' field
            # Assuming the footprint is after 'k'
            footprint = mc_value.split('k')[1].strip()
            return footprint if footprint else ''
        except IndexError as ie:
            print(f"Error parsing footprint: {ie}")
            return ''

    # def choose_parser(data) -> ParserMeta:
    #     if data.encode().startswith(b'>[)>06'):
    #         # Data starts with the specified bytes
    #
    #         # Decode bytes to string
    #         qr_data_str = data.decode("utf-8", "ignore")
    #
    #         # Split the data by Group Separator (0x1D)
    #         fields = qr_data_str.split('\x1d')
    #
    #         # Display the fields\
    #         print("MOUSER")
    #         print(fields)


    def check(self, data) -> bool:
        try:
            if data.encode().startswith(b'>[)>06'):
                print(f"Matched {self.__class__.__name__}")
                return True
        except Exception as e:
            print(f"Error checking data: {e}")
        return False

    def parse(self, fields):
        try:
            # Implement the parse method specific to LcscParser
            pass
        except Exception as e:
            print(f"Error parsing fields: {e}")

    def lookup(self):
        try:
            # Implement the lookup method specific to LcscParser
            pass
        except Exception as e:
            print(f"Error looking up data: {e}")

    def submit(self):
        try:
            # Implement the submit method specific to LcscParser
            pass
        except Exception as e:
            print(f"Error submitting data: {e}")
