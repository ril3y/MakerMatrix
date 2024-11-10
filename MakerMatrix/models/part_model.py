import json
import uuid
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, model_validator

from MakerMatrix.models.category_model import CategoryModel
from MakerMatrix.models.location_model import LocationModel


class UpdateQuantityRequest(BaseModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None
    new_quantity: int

    @model_validator(mode='before')
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")
        return values


class GenericPartQuery(BaseModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None

    @model_validator(mode='before')
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError('At least one of part_id, part_number, or manufacturer_pn must be provided.')
        return values


class PartModel(BaseModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None
    location: Optional[LocationModel] = None
    image_url: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = {}  # Add additional_properties
    categories: Optional[List[Union[str, CategoryModel]]] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.part_id:
            self.part_id = str(uuid.uuid4())

    @model_validator(mode='before')
    def check_part_details(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        part_name = values.get('part_name')
        quantity = values.get('quantity')

        # Allow the use of part_id as a unique identifier for updates
        if not part_id and not (part_number or part_name):
            raise ValueError('Either part_id, part_number, or part_name must be provided.')

        if quantity is not None and quantity <= 0:
            raise ValueError('Quantity must be a positive number')

        additional_properties = values.get('additional_properties', {})
        if additional_properties:
            # Check for blank values and duplicate keys
            for key, value in additional_properties.items():
                if not key or value is None or value == "":
                    raise ValueError(f"Additional property '{key}' has a blank value.")
            if len(additional_properties) != len(set(additional_properties.keys())):
                raise ValueError("Duplicate keys found in additional properties.")

        return values

    @model_validator(mode='before')
    def check_unique_part_name(cls, values):
        part_name = values.get("part_name")
        part_id = values.get("part_id")

        if part_name:
            # Import PartService here to avoid circular import issues
            from MakerMatrix.services.part_service import PartService

            # Check if there is any part with the same name, excluding the current part by ID
            if not PartService.part_repo.is_part_name_unique(part_name, part_id):
                raise ValueError(f"Part name '{part_name}' must be unique.")

        return values

    def to_json(self):
        return json.dumps(self.dict(), default=str)
