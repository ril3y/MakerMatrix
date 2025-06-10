from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    id: Optional[str]
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoriesListResponse(BaseModel):
    categories: List[CategoryResponse]

    model_config = ConfigDict(from_attributes=True)


class PartResponse(BaseModel):
    id: Optional[str]
    part_number: Optional[str]
    part_name: Optional[str]
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None
    location_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None  # Use generic dict for location data
    image_url: Optional[str] = None
    additional_properties: Optional[dict] = {}
    categories: Optional[List[CategoryResponse]] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_categories(cls, orm_obj):
        # Convert the ORM model to a dictionary
        part_dict = orm_obj.model_dump()
        part_dict["categories"] = [
            {"id": cat.id, "name": cat.name, "description": cat.description}
            for cat in orm_obj.categories
        ]
        return cls(**part_dict)


class DeleteCategoriesResponse(BaseModel):
    deleted_count: int

    model_config = ConfigDict(from_attributes=True)
