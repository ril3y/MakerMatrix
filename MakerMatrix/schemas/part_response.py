from typing import Optional, List
from pydantic import BaseModel

class PartResponse(BaseModel):
    id: Optional[str]
    part_number: Optional[str]
    part_name: Optional[str]
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None
    location_id: Optional[str] = None
    image_url: Optional[str] = None
    additional_properties: Optional[dict] = {}
    category_names: Optional[List[str]] = []

    class Config:
        from_attributes = True
