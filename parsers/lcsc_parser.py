import os, re
from lib.required_input import RequiredInput
from parts.parts import Part
from parsers.parser import Parser
from api.easyeda import EasyedaApi

def get_nested_value(data, keys, default=""):
    """Safely extract a value from nested dictionaries.

    Args:
        data (dict): The dictionary to extract the value from.
        keys (list): A list of keys representing the path to the desired value.
        default (str, optional): The default value to return if the key is not found. Defaults to "".

    Returns:
        The extracted value or the default value.
    """
    for key in keys:
        data = data.get(key, {})
        if not data:
            return default
    return data if data != default else default


class LcscParser(Parser):

    def __init__(self):
        super().__init__(pattern=re.compile(r"(\w+):([^,']+)"))
        self.api = EasyedaApi()

        self.part = Part(categories=['electronics'],
                         part_vendor="LCSC",
                         part_type="electronic component",
                         supplier="LCSC")

        # Define required inputs, you can remove / set them during enrich stage too.
        #req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

        self.required_inputs = [req_part_type, req_part_quantity]

    def matches(self, data):
        if 'MOUSER_PART_API_KEY' in os.environ:
            print("Mouser API key exists")

            match_data = self.decode_json_data(data)
            return bool(self.pattern.search(match_data))
        return False

    def enrich(self):
        # Specific to LCSC data enrichment
        try:
            lcsc_data = self.api.get_info_from_easyeda_api(lcsc_id=self.part.part_number.upper()) # This is cases sensitive on lcsc servers side
            if lcsc_data != {}:
                # self.part.additional_properties['value'] = lcsc_data['result']['dataStr']['head']['c_para']['Value'], ""
                # self.part.additional_properties['package'] = lcsc_data['result']['dataStr']['head']['c_para']['package'], ""
                # self.part.additional_properties['manufacturer'] = lcsc_data['result']['dataStr']['head']['c_para']['Manufacturer'], ""
                #self.set_property('image_url', lcsc_data['result']['szlcsc']['image']) # This seems to be denied on the server, perhaps it needs the right useragent
                self.set_property('part_name', f" {self.part.manufacturer_part_number}")
                # self.part.additional_properties['datasheet_url'] = \
                #     lcsc_data['result']['packageDetail']['dataStr']['head']['c_para']['link']
                # self.part.additional_properties['url'] = lcsc_data['result']['szlcsc']['url']


                # Using the function to set additional properties
                self.part.additional_properties['value'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'Value'])

                self.part.additional_properties['package'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'package'])

                self.part.additional_properties['manufacturer'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'Manufacturer'])

                self.part.additional_properties['datasheet_url'] = get_nested_value(
                    lcsc_data, ['result', 'packageDetail', 'dataStr', 'head', 'c_para', 'link'])

                self.part.additional_properties['url'] = get_nested_value(
                    lcsc_data, ['result', 'szlcsc', 'url'])

                # Check if 'datasheet_url' exists in additional_properties and is not empty
                if 'datasheet_url' in self.part.additional_properties and self.part.additional_properties[
                    'datasheet_url']:
                    # Process the datasheet_url and set the 'description' property
                    description = self.part.additional_properties['datasheet_url'].strip(
                        "https://lcsc.com/product-detail").replace("-", ", ").rstrip(".html")
                    self.set_property('description', description)
                else:
                    # Handle the case where 'datasheet_url' is not available or empty
                    # For example, set 'description' to an empty string or a default value
                    self.set_property('description', "")

        except Exception as e:
            print(f'Error enriching data: {e}')
            return None

    def parse(self, json_data):
        try:
            decoded_data = self.decode_json_data(json_data)
            # Parsing logic specific to LCSC data
            key_value_pairs = re.findall(r"(\w+):([^,']+)", decoded_data)
            data = {key: value for key, value in key_value_pairs}

            self.set_property("quantity", int(data.get('qty')))
            self.set_property('part_number',data.get('pc', '').lower())
            self.set_property('manufacturer_part_number', data.get('pm', '').lower())
            # self.part.additional_properties['order_date'] = parse_to_datetime(data.get('on', ''))
            # self.part.order_date = parse_to_datetime(data.get('on', ''))
            #
            #
            # self.part_type = self.set_property('part_type',part_type)

        except Exception as e:
            print(f'Error parsing byte data: {e}')
            return None

    def submit(self):
        # Implementation for data submission specific to LcscParser
        pass

