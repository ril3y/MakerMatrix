from typing import Optional, List

from pydantic import BaseModel


class PartCreate(BaseModel):
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
        orm_mode = True


class PartUpdate(BaseModel):
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    supplier: Optional[str] = None
    location_id: Optional[str] = None
    image_url: Optional[str] = None
    additional_properties: Optional[dict] = {}
    category_names: Optional[List[str]] = []

    class Config:
        orm_mode = True
