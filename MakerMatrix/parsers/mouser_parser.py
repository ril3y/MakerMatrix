import os
import re
from datetime import datetime

from mouser.api import MouserPartSearchRequest

from MakerMatrix.lib.required_input import RequiredInput
from MakerMatrix.parsers.parser import Parser
from MakerMatrix.parts.parts import Part


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


def _extract_quantity(quantity_string):
    qn = next((x for x in quantity_string if x.startswith("Q")), None)
    return int(qn[1:] if qn is not None else None)


def _extract_part_vendor(part_vendor):
    vendor = next((x for x in part_vendor if x.startswith("1V")), None)
    return vendor[2:] if vendor is not None else None


def _extract_pn(pn_string):
    pn = next((x for x in pn_string if "1P" in x), None)
    result = pn[2:] if pn is not None else None
    return result


class Mouser(Parser):

    def __init__(self):
        self.mouser_version = ""
        self.required_inputs = []
        super().__init__(pattern=[
            {'current': '[)>\x1e06\x1d'},
            {'legacy': '>[)>06\x1d'}
        ])

        self.part = Part(categories=['electronics'],
                         part_vendor="Mouser",
                         part_type="electronic component",
                         supplier="Mouser")

        # Define required inputs, you can remove / set them during enrich stage too.
        # req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        # req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        # req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

    def _extract_categories(self, category):
        cats = None
        if "-" in category:
            cats = category.split("-")
        elif "/" in category:
            cats = category.split("/")
        else:
            self.part.categories.append(category.lstrip().rstrip().lower())

        if cats is not None:
            for c in cats:
                if c not in self.part.categories:
                    self.part.categories.append(c)

    def submit(self):
        # Implementation for data submission specific to LcscParser
        pass

    def _process_description(self, description_string):
        description = [word.lower() for word in description_string.split()]
        description_string = description_string.lower()

        if "resistor" in description_string or "resistance" in description_string:
            pattern_tolerance = r'(\d+(\.\d+)?%)'
            # resistance_pattern = r'(\d+(?:\.\d+)?[a-zA-Z]?)\sOhms'
            resistance_pattern = r'(\d+(?:\.\d+)?)\s?[Oo]hms?'

            self.part.categories.append('resistors')

            if "ohm" in description_string:
                resistance_match = re.search(resistance_pattern, description_string, re.IGNORECASE)
                if resistance_match:
                    resistance = resistance_match.group(1)
                    self.part.add_additional_property('resistance', resistance + "Ω")

            if "%" in description_string:
                tolerance_match = re.search(pattern_tolerance, description_string)
                self.part.add_additional_property('tolerance', tolerance_match.group(1))

            # Sometimes we can't get the regex to match due to things being different
            # So we need to add the required inputs for missing data.
            if "resistance" not in self.part.additional_properties.keys():
                # Parsing the resistance did not work manually add this
                self.part.part_type = "resistor"

                self.required_inputs.append(
                    RequiredInput(field_name="value", data_type="string", prompt="Enter the resistance value"))

                self.add_required_input(field_name="package", data_type="string", prompt="Enter the package. IE: 0402")

        elif "capacitance" in description_string or "capacitor" in description_string:
            self.part.categories.append('capacitors')
            self.add_required_input(field_name="value", data_type="string", prompt="Enter the capacitance value. IE: "
                                                                                   "22pf")
            self.add_required_input(field_name="package", data_type="string", prompt="Enter the package. IE: 0402")

            if 'SMD' in description_string:
                self.part.add_additional_property('type', 'smd')
                self.part.part_type = "capacitor"
                self.part.categories.append('smd')

        elif " ic " in description_string.lower():
            self.part.part_type = "integrated circuit"
            self.add_optional_input(field_name="ic_type", data_type="string", prompt="Enter the type of IC.")
            self.add_required_input(field_name="package", data_type="string", prompt="Enter the package type.")

    def _parse_legacy(self, qr_data):
        fields = qr_data.split('\x1d')
        self.part.quantity = int(fields[4].lstrip("Q"))
        self.part.part_number = fields[3].lstrip("1P")

    def _parse_current(self, qr_data):
        records = qr_data.split('\x1e')
        fields = records[1].split('\x1d')

        self.part.part_number = _extract_pn(fields)
        self.part.quantity = _extract_quantity(fields)
        self.part.vendor = _extract_part_vendor(fields)

    def enrich(self):
        args = []
        request = MouserPartSearchRequest('partnumber', None, *args)
        search = request.part_search(self.part.part_number)

        if search:
            results = request.get_clean_response()
            self.part.description = results.get('Description')
            self._extract_categories(results.get('Category'))
            self.part.manufacturer = results.get('Manufacturer')
            self.part.add_additional_property("datasheet_url", results.get('DataSheetUrl'))
            self.part.image_url = results.get('ImagePath')
            self.part.manufacturer_part_number = results.get('ManufacturerPartNumber')
            self._process_description(self.part.description)

    def parse(self, data):
        qr_data = self.decode_json_data(data)
        self.part.categories.append("electronics")  # Set default categories
        self.part.categories.append("components")
        match self.mouser_version:
            case 'current':
                self._parse_current(qr_data)
                # self.enrich()

            case 'legacy':
                self._parse_legacy(qr_data)
                # self.enrich()

    def matches(self, data):
        if os.getenv("MOUSER_PART_API_KEY") is not None:
            match_data = self.decode_json_data(data)

        for pat in self.pattern:
            for key, value in pat.items():
                if match_data.startswith(value):
                    self.mouser_version = key
                    return True

        return False
