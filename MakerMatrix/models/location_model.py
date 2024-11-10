import uuid
from typing import Optional

from pydantic import BaseModel, root_validator, validator, Field


class LocationModel(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str]
    description: Optional[str] = None
    parent_id: Optional[str] = None

    # @validator('name')
    # def check_unique_name(cls, value):
    #     if value:
    #         # Import LocationService here to avoid circular import issues
    #         from services.location_service import LocationService
    #         if not LocationService.location_repo.is_location_name_unique(value):
    #             raise ValueError(f"Location name '{value}' must be unique.")
    #     return value

    @root_validator(pre=True)
    def auto_generate_id(cls, values):
        if not values.get('id'):
            values['id'] = str(uuid.uuid4())
        return values


class LocationQueryModel(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
