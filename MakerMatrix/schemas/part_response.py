from typing import Optional, List
from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: Optional[str]
    name: Optional[str]
    description: Optional[str] = None

    class Config:
        from_attributes = True


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
    categories: Optional[List[CategoryResponse]] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_categories(cls, orm_obj):
        part_dict = orm_obj.dict()
        part_dict["categories"] = [
            CategoryResponse.from_orm(category) for category in orm_obj.categories
        ]
        return cls(**part_dict)
