from abc import abstractmethod
from datetime import datetime
import uuid


class Part():

    def __init__(self, **kwargs):
        self._manufacturer = None
        self._part_number = kwargs.get('part_number', None)
        self._manufacturer_part_number = kwargs.get('manufacturer_part_number', None)
        self._part_url = kwargs.get('part_url', None)
        self._quantity = kwargs.get('quantity', None)
        # self._value = kwargs.get('value', None)
        self._part_name = kwargs.get('part_name', None)
        self._part_vendor = kwargs.get('part_vendor', None)
        self._part_type = kwargs.get('part_type', None)
        self._image_url = kwargs.get('image_url', "")
        self._description = kwargs.get('description', "")
        self._categories = kwargs.get('categories', [])
        self._sub_category = kwargs.get('sub_category', None)
        self.additional_properties = kwargs.get('additional_properties', {})
        self._supplier = kwargs.get('supplier', None)
        self._part_location = kwargs.get('part_location', {})
        # self._package = kwargs.get('package', {})
        self._part_id = ""

    def apply_required_data(self, user_data):
        pass

    @abstractmethod
    def parse(self, data):
        pass

    @property
    def part_id(self):
        """Getter for UUID. UUIDs are read-only."""
        return self._part_id

    @part_id.setter
    def part_id(self, value):
        self._part_id = value

    def generate_part_id(self):
        self._part_id = str(uuid.uuid4())

    @property
    def manufacturer(self):
        return self._manufacturer

    @manufacturer.setter
    def manufacturer(self, value):
        self._manufacturer = value

    @property
    def manufacturer_part_number(self):
        return self._manufacturer_part_number

    @manufacturer_part_number.setter
    def manufacturer_part_number(self, value):
        self._manufacturer_part_number = value
    @property
    def part_location(self):
        return self._part_location

    @part_location.setter
    def part_location(self, value):
        self._part_location = value

    @property
    def supplier(self):
        return self._supplier

    @supplier.setter
    def supplier(self, value):
        self._supplier = value

    @property
    def sub_category(self):
        return self._sub_category

    @sub_category.setter
    def sub_category(self, value):
        self._sub_category = value

    # Getters and Setters
    @property
    def part_number(self):
        return self._part_number

    @part_number.setter
    def part_number(self, value):
        self._part_number = value

    @property
    def part_url(self):
        return self._part_url

    @part_url.setter
    def part_url(self, value):
        self._part_url = value

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        self._quantity = value

    @property
    def part_name(self):
        return self._part_name

    @part_name.setter
    def part_name(self, value):
        self._part_name = value

    @property
    def part_vendor(self):
        return self._part_vendor

    @part_vendor.setter
    def part_vendor(self, value):
        self._part_vendor = value

    @property
    def part_type(self):
        return self._part_type

    @part_type.setter
    def part_type(self, value):
        self._part_type = value

    @property
    def image_url(self):
        return self._image_url

    @image_url.setter
    def image_url(self, value):
        self._image_url = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def categories(self):
        return self._categories

    @categories.setter
    def categories(self, value):
        if isinstance(value, list):
            self._categories = value
        else:
            raise TypeError("Categories must be a list")

    @property
    def additional_properties(self):
        return self._additional_properties

    @additional_properties.setter
    def additional_properties(self, value):
        if isinstance(value, dict):
            self._additional_properties = value
        else:
            raise TypeError("Additional properties must be a dictionary")

    def add_additional_property(self, key, value):
        """Adds or updates an entry in the additional_properties dictionary.

        Args:
            key (str): The key for the property to add or update.
            value: The value to set for the given key.
        """
        if not isinstance(key, str):
            raise TypeError("Key must be a string")
        # You can add additional validation for the value here if necessary.

        self.additional_properties[key] = value

    @staticmethod
    def decode_hex(hex_string):
        try:
            if len(hex_string) % 2 != 0:
                raise ValueError("Hex string must have an even number of characters.")
            return bytes.fromhex(hex_string).decode()
        except ValueError as e:
            print(f"Error decoding hex string: {e}")
            return ""  # Return an empty string or handle it as per your application's requirement

    def dict(self):
        attributes = {}
        for attr in dir(self):
            # Filter out private attributes and methods
            if not attr.startswith("__") and not attr.startswith("_") and not callable(getattr(self, attr)):
                value = getattr(self, attr)
                # Optionally, you can skip None values
                # if value is not None:
                attributes[attr] = value
        return attributes



    def __repr__(self):
        return f"BarcodeParser(part_number={self._part_number}, part_url={self._part_url}, ...)"
