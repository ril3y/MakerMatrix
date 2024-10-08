import json
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, root_validator

from models.category_model import CategoryModel
from models.location_model import LocationModel


class UpdateQuantityRequest(BaseModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None
    new_quantity: int

    @root_validator(pre=True)
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

    @root_validator(pre=True)
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError('At least one of part_id, part_number, or manufacturer_pn must be provided.')
        return values


class PartModel(BaseModel):
    part_id: str
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None
    location: Optional[LocationModel] = None
    image_url: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = {}  # Add additional_properties
    categories: Optional[List[Union[str, CategoryModel]]] = None

    @root_validator
    def check_part_details(cls, values):
        part_number, part_name = values.get('part_number'), values.get('part_name')
        quantity = values.get('quantity')

        if part_number is None and part_name is None:
            raise ValueError('Either part_number or part_name must be provided')

        if quantity is not None and quantity <= 0:
            raise ValueError('Quantity must be a positive number')

        return values

    def to_json(self):
        return json.dumps(self.dict(), default=str)
