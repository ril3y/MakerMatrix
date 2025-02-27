from typing import Optional, Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")

class ResponseSchema(BaseModel, Generic[T]):
    status: str
    message: str
    data: Optional[T] = None
    page: Optional[int] = None  # For pagination
    page_size: Optional[int] = None  # For pagination
    total_parts: Optional[int] = None  # Total count for pagination
