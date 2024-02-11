from typing import Optional
from pydantic import BaseModel


class LocationModel(BaseModel):
    id: Optional[str]
    name: Optional[str]
    description: Optional[str]
    parent_id: Optional[str] = None