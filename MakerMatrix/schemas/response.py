from typing import Optional, Generic, TypeVar
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar('T')


class ResponseSchema(GenericModel, Generic[T]):
    status: str
    message: str
    data: Optional[T] = None
