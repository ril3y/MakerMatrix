from typing import Optional, List

from pydantic import BaseModel, model_validator


class PartCreate(BaseModel):
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int] = None  # Fixed: field is now optional, not just type
    description: Optional[str] = None
    supplier: Optional[str] = None
    supplier_url: Optional[str] = None
    product_url: Optional[str] = None
    supplier_part_number: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    location_id: Optional[str] = None
    image_url: Optional[str] = None
    emoji: Optional[str] = None
    additional_properties: Optional[dict] = {}
    category_names: Optional[List[str]] = []

    # Enrichment parameters
    auto_enrich: Optional[bool] = False
    enrichment_supplier: Optional[str] = None
    enrichment_capabilities: Optional[List[str]] = []

    @model_validator(mode='before')
    def check_part_identifiers(cls, values):
        if not values.get('part_name') and not values.get('part_number'):
            raise ValueError('Either part_name or part_number must be provided')
        return values

    class Config:
        from_attributes = True


class PartUpdate(BaseModel):
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    supplier: Optional[str] = None
    supplier_url: Optional[str] = None
    product_url: Optional[str] = None
    supplier_part_number: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    location_id: Optional[str] = None
    image_url: Optional[str] = None
    emoji: Optional[str] = None
    additional_properties: Optional[dict] = {}
    category_names: Optional[List[str]] = []

    class Config:
        from_attributes = True
