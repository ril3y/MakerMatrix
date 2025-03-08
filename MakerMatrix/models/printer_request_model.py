from pydantic import BaseModel


class PrintRequest(BaseModel):
    image_path: str
    label: str = '29x90'
    rotate: str = '90'
