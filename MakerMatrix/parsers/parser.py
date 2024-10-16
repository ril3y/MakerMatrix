from abc import ABC, abstractmethod

from MakerMatrix.lib.optional_input import OptionalInput
from MakerMatrix.parts.parts import Part
from MakerMatrix.lib.required_input import RequiredInput
import json

import base64


# Assuming the Part class is defined elsewhere
# from parts.parts import Part

class Parser(ABC):
    def __init__(self, pattern):
        self.optional_inputs = []
        self.pattern = pattern
        self.part = Part
        self.required_inputs = []

    @staticmethod
    def create_question_dict(event, question_type, question_text, positive_text, negative_text):
        data = {
            "event": event,
            "data": {
                "questionType": question_type,
                "questionText": question_text,
                "positiveResponseText": positive_text,
                "negativeResponseText": negative_text
            }
        }
        return data

    # Example usage
    # nfc_question_dict = create_question_dict(
    #     "question",
    #     "regular",
    #     "Do you want to write the part number to an NFC tag?",
    #     "Yes",
    #     "No"
    # )

    def validate(self, json_string):
        try:
            data = json.loads(json_string)

            # Extract required inputs and part number from the JSON data
            required_inputs = data.get('required_inputs', [])
            part_number = data.get('part_number')

            for input in required_inputs:
                field_name = input.get('field_name')
                data_type = input.get('data_type')
                value = input.get('value')

                # Perform type validation
                if data_type == "string":
                    if not isinstance(value, str):
                        return False, f"Invalid type for field {field_name}. Expected string."
                elif data_type == "int":
                    try:
                        int_value = int(value)  # Attempt to convert to int
                        value = int_value  # Update value with converted int
                    except ValueError:
                        return False, f"Invalid type for field {field_name}. Expected integer."

                # Dynamically update the fields on parser.part based on field_name
                setattr(self.part, field_name, value)

            # # Update part number if necessary
            # if part_number:
            #     self.part.part_number = part_number

            return True, "Validation successful and data updated."

        except json.JSONDecodeError as e:
            return False, f"JSON decoding error: {e}"

    def add_required_input(self, field_name, data_type, prompt):
        self.required_inputs.append(RequiredInput(field_name, data_type, prompt))

    def add_optional_input(self, field_name, data_type, prompt):
        self.optional_inputs.append(OptionalInput(field_name, data_type, prompt))

    def remove_required_input(self, field_name):
        for r in self.required_inputs:
            if r.field_name == field_name:
                print(f"Removed requirement: {r}")
                self.required_inputs.remove(r)

    def get_required_inputs_json(self):
        return json.dumps([input_field.to_dict() for input_field in self.required_inputs], indent=4)

    def decode_data(self, json_data):
        _data = json.loads(json_data)
        return _data

    def set_property(self, property_name, value):
        # Initialize a variable to keep track of whether the property was successfully set
        property_set_successfully = False

        # Try to set the property
        try:
            # Check if the property exists in the Part object or in the class itself
            target = self.part if hasattr(self.part, property_name) else self if hasattr(self, property_name) else None

            if target is not None:
                # Set the property
                setattr(target, property_name, value)
                property_set_successfully = True
        except Exception as e:
            # Handle any exceptions that might occur
            print(f"Error setting property: {e}")

        # If the property was not set successfully, set it to an empty string
        if not property_set_successfully:
            if hasattr(self.part, property_name):
                setattr(self.part, property_name, "")
            elif hasattr(self, property_name):
                setattr(self, property_name, "")

        # The rest of your code for handling the required inputs
        if property_set_successfully:
            should_remove_input = False
            if isinstance(value, str) and value.strip():
                should_remove_input = True
            elif value is not None:
                should_remove_input = True
            if should_remove_input:
                self.required_inputs = [req for req in self.required_inputs if req.field_name != property_name]

    def decode_json_data(self, json_data):
        byte_data = self.decode_data(json_data)
        _data = base64.b64decode(byte_data['qrData'])
        decoded_data = _data.decode('utf-8')
        return decoded_data

    def to_dict(self, obj=None):
        """
        Converts the object's attributes to a dictionary, excluding methods,
        and removes leading underscores from attribute names. If no object is
        provided, it converts the attributes of the current instance.
        """
        if obj is None:
            obj = self

        attr_dict = {}
        for attr in dir(obj):
            if not callable(getattr(obj, attr)) and not attr.startswith("_"):
                # Remove leading underscore from attribute names
                key = attr.lstrip('_')
                attr_dict[key] = getattr(obj, attr)
        return attr_dict

    def format_required_data(self, requirements, clientId, part_number):
        obj = self.to_dict(requirements)
        obj['client_id'] = clientId
        obj['required_inputs'] = requirements
        obj['part_number'] = part_number
        return self.to_json(obj)

    def append_event(self, event_type):
        """
        Appends an event type to the object's attributes.
        """
        obj = self.to_dict()
        obj['event'] = event_type
        return self.to_json(obj)

    def to_json(self, obj=None):
        """
        Converts the given object's attributes to a JSON string.
        If no object is provided, converts the current object's attributes.
        """

        def serialize(obj_to_serialize):
            if hasattr(obj_to_serialize, '__dict__'):
                return {k.lstrip('_'): v for k, v in obj_to_serialize.__dict__.items()}
            # elif isinstance(obj_to_serialize, (datetime, date)):
            #     return obj_to_serialize.isoformat()
            return str(obj_to_serialize)  # Fallback to string representation

        # Use the provided object or self if no object is provided
        obj_to_convert = obj if obj is not None else self

        return json.dumps(obj_to_convert, default=serialize)

    @abstractmethod
    def parse(self, fields):
        pass

    @abstractmethod
    def submit(self):
        pass
