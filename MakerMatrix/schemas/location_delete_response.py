from typing import List, Optional
from pydantic import BaseModel


class LocationDeleteResponse(BaseModel):
    location_ids_to_delete: List[str]
    affected_parts_count: int
    affected_locations_count: int
    location_hierarchy: dict

    class Config:
        from_attributes = True
