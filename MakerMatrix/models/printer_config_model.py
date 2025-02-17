# Pydantic models for input validation
from pydantic import BaseModel


class PrinterConfig(BaseModel):
    model: str
    driver: str
    backend: str
    printer_identifier: str
    dpi: int
    scaling_factor: float
