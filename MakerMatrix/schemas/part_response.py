from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    """Category response schema that matches CategoryModel.to_dict() output"""
    id: Optional[str]
    name: str
    description: Optional[str] = None
    part_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class CategoriesListResponse(BaseModel):
    categories: List[CategoryResponse]

    model_config = ConfigDict(from_attributes=True)


class PartResponse(BaseModel):
    # === CORE PART DATA (always included) ===
    # Core identification
    id: Optional[str] = None
    part_name: Optional[str] = Field(default=None, max_length=255)
    part_number: Optional[str] = None
    
    # Part description  
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    component_type: Optional[str] = None
    
    # Current inventory
    quantity: Optional[int] = None
    location_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None  # Use generic dict for location data
    supplier: Optional[str] = None
    supplier_url: Optional[str] = None
    product_url: Optional[str] = None
    
    # Media
    image_url: Optional[str] = None
    emoji: Optional[str] = None

    # Part-specific properties (resistor values, screwdriver type, etc.)
    additional_properties: Optional[Dict[str, Any]] = {}
    
    # Core relationships (always included)
    categories: Optional[List[CategoryResponse]] = []
    projects: Optional[List[Dict[str, Any]]] = []  # Project assignments
    datasheets: Optional[List[Dict[str, Any]]] = []  # Always included (core part data)
    
    # Timestamps
    created_at: Optional[str] = None  # ISO datetime string
    updated_at: Optional[str] = None  # ISO datetime string
    
    # === OPTIONAL METADATA (populated when include parameter is used) ===
    # Pricing metadata (include=pricing)
    pricing_history: Optional[List[Dict[str, Any]]] = None
    current_pricing: Optional[Dict[str, Dict[str, Any]]] = None  # {supplier: {price, currency, stock}}
    
    # Enrichment metadata (include=enrichment)  
    enrichment_metadata: Optional[Dict[str, Any]] = None
    
    # System metadata (include=system)
    system_metadata: Optional[Dict[str, Any]] = None
    
    # Order relationships (include=orders)
    order_summary: Optional[Dict[str, Any]] = None
    order_history: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_categories(cls, orm_obj):
        # Convert the ORM model to a dictionary
        part_dict = orm_obj.model_dump()
        part_dict["categories"] = [
            {"id": cat.id, "name": cat.name, "description": cat.description}
            for cat in orm_obj.categories
        ]
        return cls(**part_dict)


class DeleteCategoriesResponse(BaseModel):
    deleted_count: int

    model_config = ConfigDict(from_attributes=True)
