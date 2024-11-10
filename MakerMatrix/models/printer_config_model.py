# Pydantic models for input validation
from pydantic import BaseModel


class PrinterConfig(BaseModel):
    model: str
    backend: str
    printer_identifier: str
    dpi: int
