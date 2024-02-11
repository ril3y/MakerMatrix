import json
from typing import Optional
from pydantic import BaseModel, root_validator
from lib.models.location_model import LocationModel


class PartModel(BaseModel):
    part_id: str
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None  # Also make parent_id not required
    location: Optional[LocationModel] = None
    image_url: Optional[str] = None

    @root_validator
    def check_part_details(cls, values):
        part_number, part_name = values.get('part_number'), values.get('part_name')
        if part_number is None and part_name is None:
            raise ValueError('Either part_number or part_name must be provided')
        return values

    def to_json(self):
        return json.dumps(self.dict(), default=str)