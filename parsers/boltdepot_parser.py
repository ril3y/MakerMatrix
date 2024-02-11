import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from parsers.parser import Parser
from parts.parts import Part
from lib.required_input import RequiredInput


class BoltDepotParser(Parser):

    def submit(self):
        pass

    def __init__(self):
        self._pattern = re.compile(r"http://boltdepot.com/Product-Details.aspx\?product=")
        self.part = Part(categories=['hardware'],
                         part_vendor="bolt depot",
                         part_type="hardware",
                         supplier="bolt depot")
        self.required_inputs = []
        # Required Inputs
        # req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        # req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

        # Set the required inputs
        self.add_required_input(field_name="quantity", data_type="int", prompt="Enter the quantity.")

    def matches(self, data):
        decoded_data = self.decode_json_data(data)
        new_part_data = self._pattern.search(decoded_data)
        # if new_part_data:
        #     self.part = Part(categories=['hardware'])
        return new_part_data

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
                table = document.find('table', class_='product-details-table')
                names_values = {}

                # Iterate through rows in the table
                # Inside your loop that iterates through table rows
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        property_name = cells[0].text.strip()
                        # Check for 'value-message' within the second cell
                        value_message = cells[1].find('div', class_='value-message')
                        if value_message and property_name.lower() != "category":
                            # If 'value-message' exists, use its text
                            property_value = value_message.text.strip()
                        else:
                            # Otherwise, use the text directly from the cell
                            property_value = cells[1].text.strip()
                        names_values[property_name] = property_value

                # Print the extracted names and values
                for name, value in names_values.items():
                    if name.lower() == "category":
                        self.part.categories.append(value.lower())
                    else:
                        self.part.add_additional_property(name, value.replace("\r\n"," "))


                # # Extract the description
                content_main = document.find('div', id='content-main')
                if content_main:
                    description = content_main.find('h1').text
                    self.part.description = description

                if not description:
                    self.add_required_input(field_name="description", data_type="string",
                                                    prompt="Enter the description.")


            else:
                raise Exception('Failed to load product page')

        except Exception as e:
            print(f'Error enriching data: {e}')
            return None

    def parse(self, json_data):
        try:
            decoded_data = self.decode_json_data(json_data)
            uri = urlparse(decoded_data)
            _pn = parse_qs(uri.query)['product'][0]
            self.part.part_number = _pn
            self.set_property("part.manufacturer_part_number", _pn)
            self.set_property("part_vendor", "Bolt Depot")
            self.part.categories.append("hardware")

            return self

        except Exception as e:
            print(f'Error parsing byte data: {e}')
            return None
