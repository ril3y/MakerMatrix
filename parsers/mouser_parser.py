import os

from datetime import datetime
from mouser.api import MouserPartSearchRequest
from lib.required_input import RequiredInput
from parsers.parser import Parser
from parts.parts import Part
import json

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


class Mouser(Parser):

    def __init__(self):
        super().__init__(pattern='[)>\x1e06\x1d')

        self.part = Part(categories=['electronics'],
                         part_vendor="Mouser",
                         part_type="electronic component",
                         supplier="Mouser")

        # Define required inputs, you can remove / set them during enrich stage too.
        # req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        # req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        # req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

        self.required_inputs = []

    def _extract_pn(self, pn_string):
        pn = next((x for x in pn_string if "1P" in x), None)
        result = pn[2:] if pn is not None else None
        return result

    def _extract_quantity(self, quantity_string):
        qn = next((x for x in quantity_string if x.startswith("Q")), None)
        return int(qn[1:] if qn is not None else None)

    def _extract_part_vendor(self, part_vendor):
        vendor = next((x for x in part_vendor if x.startswith("1V")), None)
        return vendor[2:] if vendor is not None else None

    def _extract_categories(self, category):
        cats = category.split("/")
        for c in cats:
            if c not in self.part.categories:
                self.part.categories.append(c)
    def submit(self):
        # Implementation for data submission specific to LcscParser
        pass

    def parse(self, data):
        qr_data = self.decode_json_data(data)
        records = qr_data.split('\x1e')
        fields = records[1].split('\x1d')
        # records = qr_data.split('\x1e')
        self.part.part_number = self._extract_pn(fields)
        self.part.quantity = self._extract_quantity(fields)
        self.part.vendor = self._extract_part_vendor(fields)
        args = []
        request = MouserPartSearchRequest('partnumber', None, *args)
        search = request.part_search(self.part.part_number)

        if search:
            results = request.get_clean_response()
            self.part.description = results.get('Description')
            self.part.image = results.get('ImagePath')
            self._extract_categories(results.get('Category'))
            self.part.manufacturer = results.get('Manufacturer')
        print("Done")

    def matches(self, data):
        if os.getenv("MOUSER_PART_API_KEY") is not None:
            match_data = self.decode_json_data(data)
        return match_data.startswith(self.pattern)

    def enrich(self):
        pass
