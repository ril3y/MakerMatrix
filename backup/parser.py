from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
import json
from parts.parts import Part


class Parser(ABC):
    supplier: str
    quantity: int
    manufacturer_pn: str
    supplier_pn: str
    part_link: str
    part_location: dict
    value: str
    foot_print: str
    compressed_data: List[bytes]

    def to_dict(self) -> dict:
        # Create a new dictionary for representation
        json_dict = {}

        # Iterate over all attributes of the class
        for key, value in self.__dict__.items():
            # Check if the attribute is a datetime instance
            if isinstance(value, datetime):
                # Convert datetime to ISO 8601 formatted string
                json_dict[key] = value.isoformat()
            elif key == 'part' and isinstance(value, Part):
                # If it's the 'part' attribute and an instance of Part class, convert it to a dictionary
                json_dict[key] = value.to_dict()
            else:
                # For other types, use the value as it is
                json_dict[key] = value

        return json_dict

    def to_json(self) -> str:
        # Create a new dictionary for JSON representation
        json_dict = {}

        # Iterate over all attributes of the class
        for key, value in self.__dict__.items():
            # Check if the attribute is a datetime instance
            if isinstance(value, datetime):
                # Convert datetime to ISO 8601 formatted string
                json_dict[key] = value.isoformat()
            elif isinstance(value, Part):
                # For attributes that are instances of Part or its subclasses, use their to_json method
                json_dict[key] = value.to_json()
            else:
                # For other types, use the value as it is
                json_dict[key] = value

        # Convert dictionary to JSON string
        return json.dumps(json_dict)

    @abstractmethod
    def check(self, data) -> bool:
        pass

    @abstractmethod
    def parse(self, fields):
        pass

    @abstractmethod
    def lookup(self):
        pass

    @abstractmethod
    def submit(self):
        pass
