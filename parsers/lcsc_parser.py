import re
import requests
from bs4 import BeautifulSoup
from lib.required_input import RequiredInput
from parts.parts import Part
from parsers.parser import Parser
from api.easyeda import EasyedaApi
import base64
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

def parse_to_datetime(input_string):
    try:
        # Extract the date part (ignoring the first two characters and the last four)
        if input_string:
            date_part = input_string[2:8]
            parsed_date = datetime.strptime(date_part, '%y%m%d')
            # Format the date as a string in the desired format
            return parsed_date.strftime('%Y-%m-%d')  # e.g., "2023-03-15"
        else:
            return None
    except ValueError as ve:
        print(f"Error parsing date: {ve}")
        return None


class LcscParser(Parser):

    def __init__(self):
        super().__init__(pattern=re.compile(r"(\w+):([^,']+)"))
        self.api = EasyedaApi()

        self.part = Part(categories=['electronics'],
                         part_vendor="LCSC",
                         part_type="electronic component",
                         supplier="LCSC")

        # Define required inputs, you can remove / set them during enrich stage too.
        req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

        self.required_inputs = [req_part_name, req_part_type, req_part_quantity]

    def matches(self, data):
        match_data = self.decode_json_data(data)
        return bool(self.pattern.search(match_data))

    def enrich(self):
        # Specific to LCSC data enrichment

        # url = 'https://lcsc.com/product-detail/Multilayer-Ceramic-Capacitors-MLCC-SMD-SMT_SAMSUNG_CL10A106MQ8NNNC_10uF-106-20-6-3V_C1691.html'
        #
        # # Send a GET request to the URL
        # response = requests.get(url)
        #
        # # Parse the HTML content
        # soup = BeautifulSoup(response.text, 'html.parser')
        #
        # # Find the table by class name (adjust if needed)
        # table = soup.find('table', class_='info-table')
        #
        # # Initialize a dictionary to store key-value pairs
        # data = {}
        #
        # # Iterate through table rows and extract key-value pairs
        # if table:
        #     for row in table.find_all('tr'):
        #         # Extract columns: assume first column is key and second column is value
        #         cols = row.find_all('td')
        #         if len(cols) >= 2:
        #             key = cols[0].get_text(strip=True)
        #             value = cols[1].get_text(strip=True)
        #             data[key] = value
        #
        # # Output extracted data
        # for key, value in data.items():
        #     print(f"{key}: {value}")

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

            # new_order_number = data.get('pbn', '')
            #
            # if 'order_number' in self.part.additional_properties:
            #     if self.part.additional_properties['order_number'] is not None:
            #         # Check if the new order number is not already in the list
            #         if new_order_number not in self.part.additional_properties['order_number']:
            #             self.part.additional_properties['order_number'].append(new_order_number)
            #     else:
            #         # If the order_number is None, initialize it as a list with the new order number
            #         self.part.additional_properties['order_number'] = [new_order_number]
            # else:
            #     # If the order_number key doesn't exist, create it
            #     self.part.additional_properties['order_number'] = [new_order_number]

            # self.part_link = data.get('pl',
            self.set_property('part_number',data.get('pc', '').lower())
            self.set_property('manufacturer_part_number', data.get('pm', '').lower())
            self.part.additional_properties['order_date'] = parse_to_datetime(data.get('on', ''))
            self.part.order_date = parse_to_datetime(data.get('on', ''))

            if self.part.part_number.lower().startswith("c"):
                part_type = "capacitor"
            elif self.part.part_number.lower().startswith("r"):
                part_type = "resistor"
            elif self.part.part_number.lower().startswith("l"):
                part_type = "inductor"
            else:
                part_type = 'unknown'

            self.part_type = self.set_property('part_type',part_type)

        except Exception as e:
            print(f'Error parsing byte data: {e}')
            return None

    def submit(self):
        # Implementation for data submission specific to LcscParser
        pass

    # Implement other necessary methods or utilities as required
