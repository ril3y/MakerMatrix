from typing import Dict, Any

from pydantic import BaseModel


class PrinterConfig(BaseModel):
    backend: str
    driver: str
    printer_identifier: str
    dpi: int
    model: str
    scaling_factor: float = 1.0
    additional_settings: Dict[str, Any] = {}
