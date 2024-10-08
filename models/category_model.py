from typing import Optional
from pydantic import BaseModel, Field
import uuid


class CategoryModel(BaseModel):
    id: Optional[str] = None  # Will be set automatically when adding to the database
    name: Optional[str]
    description: Optional[str] = None
    parent_id: Optional[str] = None
