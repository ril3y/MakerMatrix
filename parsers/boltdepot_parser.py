import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from parsers.parser import Parser
from parts.parts import Part
from lib.required_input import RequiredInput
import base64


class BoltDepotParser(Parser):



    def submit(self):
        pass

    def __init__(self):
        self._pattern = re.compile(r"http://boltdepot.com/Product-Details.aspx\?product=")
        self.part = Part(categories=['hardware'],
                         part_vendor="bolt depot",
                         part_type="hardware",
                         supplier="bolt depot")
        # Required Inputs
        req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

        # Set the required inputs
        self.required_inputs = [req_part_name, req_part_quantity]

    def decode_json_data(self, json_data):
        byte_data = self.decode_data(json_data)
        _data = base64.b64decode(byte_data['qrData'])
        decoded_data = _data.decode('utf-8')
        return decoded_data

    def matches(self, data):
        decoded_data = self.decode_json_data(data)
        return bool(self._pattern.search(decoded_data))

    # Specific to bolt depot parsing
    def _extract_properties(self, document):
        for element in document.select('.product-details-table .property-name'):
            key = element.get_text().strip().lower()  # Convert key to lowercase
            value_element = element.find_next_sibling()
            if value_element and value_element.span:
                value = value_element.span.get_text().strip()
                value = value.replace('"', '').lower()  # Remove double quotes and convert value to lowercase

                if key == 'category':
                    self.part.categories.append(value)
                else:
                    self.part.additional_properties[key] = value

    def enrich(self):
        try:
            url = f'https://www.boltdepot.com/Product-Details.aspx?product={self.part.part_number}'
            response = requests.get(url)

            if response.status_code == 200:
                document = BeautifulSoup(response.text, 'html.parser')
                self.part.part_url = url
                self.part.description = document.select_one('.header-title h1').get_text()
                self.part.image_url = "https://www.boltdepot.com/" + \
                                      document.select_one('#ctl00_ctl00_Body_Body__ctrl_0_CatalogImage')['src']
                self._extract_properties(document)
                return self
            else:
                raise Exception('Failed to load product page')

        except Exception as e:
            print(f'Error enriching data: {e}')
            return None

    def parse(self, json_data):
        try:
            decoded_data = self.decode_json_data(json_data)
            uri = urlparse(decoded_data)
            self.part.part_number = parse_qs(uri.query)['product'][0]
            self.part.part_vendor = "Bolt Depot"
            return self

        except Exception as e:
            print(f'Error parsing byte data: {e}')
            return None
