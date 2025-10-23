"""
Standardized Enrichment Response Schemas

These Pydantic schemas define the exact structure that all supplier enrichment
methods must return, ensuring consistency across all supplier integrations.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class EnrichmentStatus(str, Enum):
    """Enrichment operation status"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class EnrichmentSource(BaseModel):
    """Information about the enrichment data source"""

    supplier: str = Field(..., description="Supplier name (e.g., 'LCSC', 'DigiKey')")
    api_endpoint: Optional[str] = Field(None, description="Specific API endpoint used")
    api_version: Optional[str] = Field(None, description="API version used")
    enriched_at: datetime = Field(default_factory=datetime.now, description="When enrichment was performed")


class BaseEnrichmentResponse(BaseModel):
    """Base response schema for all enrichment operations"""

    success: bool = Field(..., description="Whether the enrichment was successful")
    status: EnrichmentStatus = Field(..., description="Detailed status of the operation")
    source: EnrichmentSource = Field(..., description="Source information")
    part_number: str = Field(..., description="Part number that was enriched")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Any warnings during enrichment")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator("status", pre=True, always=True)
    def set_status_from_success(cls, v, values):
        if v is None:
            return EnrichmentStatus.SUCCESS if values.get("success") else EnrichmentStatus.FAILED
        return v


class ImageInfo(BaseModel):
    """Information about a component image"""

    url: str = Field(..., description="Direct URL to the image")
    type: str = Field(default="product", description="Type of image (product, schematic, etc.)")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    format: Optional[str] = Field(None, description="Image format (png, jpg, etc.)")
    size_bytes: Optional[int] = Field(None, description="Image file size in bytes")
    thumbnail_url: Optional[str] = Field(None, description="URL to thumbnail version")


class DatasheetEnrichmentResponse(BaseEnrichmentResponse):
    """Response schema for datasheet enrichment"""

    datasheet_url: Optional[str] = Field(None, description="Direct URL to the datasheet PDF")
    datasheet_filename: Optional[str] = Field(None, description="Original filename of the datasheet")
    datasheet_size_bytes: Optional[int] = Field(None, description="Size of the datasheet file")
    datasheet_pages: Optional[int] = Field(None, description="Number of pages in the datasheet")
    download_verified: bool = Field(default=False, description="Whether the URL was verified to work")


class ImageEnrichmentResponse(BaseEnrichmentResponse):
    """Response schema for image enrichment"""

    images: List[ImageInfo] = Field(default_factory=list, description="List of available images")
    primary_image_url: Optional[str] = Field(None, description="URL to the primary/main image")

    @validator("primary_image_url", pre=True, always=True)
    def set_primary_from_images(cls, v, values):
        if v is None and values.get("images"):
            return values["images"][0].url if values["images"] else None
        return v


class PriceBreak(BaseModel):
    """Price break information"""

    quantity: int = Field(..., description="Minimum quantity for this price")
    unit_price: float = Field(..., description="Price per unit at this quantity")
    currency: str = Field(default="USD", description="Currency code")
    price_type: str = Field(default="list", description="Type of price (list, distributor, etc.)")


class PricingEnrichmentResponse(BaseEnrichmentResponse):
    """Response schema for pricing enrichment"""

    unit_price: Optional[float] = Field(None, description="Current unit price")
    currency: str = Field(default="USD", description="Currency code")
    price_breaks: List[PriceBreak] = Field(default_factory=list, description="Quantity-based pricing")
    minimum_order_quantity: Optional[int] = Field(None, description="Minimum order quantity")
    price_valid_until: Optional[datetime] = Field(None, description="When pricing expires")
    price_source: Optional[str] = Field(None, description="Source of pricing (list, real-time, etc.)")


class StockEnrichmentResponse(BaseEnrichmentResponse):
    """Response schema for stock/availability enrichment"""

    quantity_available: Optional[int] = Field(None, description="Current stock quantity")
    availability_status: Optional[str] = Field(None, description="Availability status text")
    lead_time_days: Optional[int] = Field(None, description="Lead time in days")
    last_updated: Optional[datetime] = Field(None, description="When stock info was last updated")
    warehouse_locations: List[str] = Field(default_factory=list, description="Available warehouse locations")
    backorder_allowed: bool = Field(default=False, description="Whether backorders are accepted")
    lifecycle_status: Optional[str] = Field(None, description="Product lifecycle status")


class SpecificationAttribute(BaseModel):
    """A single specification attribute"""

    name: str = Field(..., description="Attribute name")
    value: str = Field(..., description="Attribute value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    attribute_type: Optional[str] = Field(None, description="Type of attribute")


class DetailsEnrichmentResponse(BaseEnrichmentResponse):
    """Response schema for detailed component information"""

    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    manufacturer_part_number: Optional[str] = Field(None, description="Manufacturer's part number")
    product_description: Optional[str] = Field(None, description="Product description")
    detailed_description: Optional[str] = Field(None, description="Detailed description")
    category: Optional[str] = Field(None, description="Product category")
    subcategory: Optional[str] = Field(None, description="Product subcategory")
    package_type: Optional[str] = Field(None, description="Package/case type")
    series: Optional[str] = Field(None, description="Product series")
    specifications: List[SpecificationAttribute] = Field(default_factory=list, description="Technical specifications")
    rohs_compliant: Optional[bool] = Field(None, description="RoHS compliance status")
    operating_temperature_min: Optional[float] = Field(None, description="Minimum operating temperature (°C)")
    operating_temperature_max: Optional[float] = Field(None, description="Maximum operating temperature (°C)")


class SpecificationsEnrichmentResponse(BaseEnrichmentResponse):
    """Response schema for technical specifications enrichment"""

    specifications: List[SpecificationAttribute] = Field(default_factory=list, description="Technical specifications")
    electrical_characteristics: Dict[str, Any] = Field(default_factory=dict, description="Electrical characteristics")
    mechanical_characteristics: Dict[str, Any] = Field(default_factory=dict, description="Mechanical characteristics")
    environmental_characteristics: Dict[str, Any] = Field(
        default_factory=dict, description="Environmental characteristics"
    )
    certifications: List[str] = Field(default_factory=list, description="Product certifications")


class BulkEnrichmentItem(BaseModel):
    """Single item in a bulk enrichment operation"""

    part_number: str = Field(..., description="Part number that was processed")
    success: bool = Field(..., description="Whether this item was successful")
    capabilities_completed: List[str] = Field(default_factory=list, description="Successfully completed capabilities")
    capabilities_failed: List[str] = Field(default_factory=list, description="Failed capabilities")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    enrichment_data: Dict[str, Any] = Field(default_factory=dict, description="Enriched data for this part")


class BulkEnrichmentResponse(BaseModel):
    """Response schema for bulk enrichment operations"""

    total_parts: int = Field(..., description="Total number of parts processed")
    successful_parts: int = Field(..., description="Number of successfully enriched parts")
    failed_parts: int = Field(..., description="Number of failed parts")
    processing_time_seconds: float = Field(..., description="Total processing time")
    source: EnrichmentSource = Field(..., description="Source information")
    items: List[BulkEnrichmentItem] = Field(..., description="Individual item results")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")


# Union type for all enrichment responses
EnrichmentResponse = Union[
    DatasheetEnrichmentResponse,
    ImageEnrichmentResponse,
    PricingEnrichmentResponse,
    StockEnrichmentResponse,
    DetailsEnrichmentResponse,
    SpecificationsEnrichmentResponse,
]


# Capability to Response Schema Mapping
CAPABILITY_SCHEMA_MAPPING = {
    "fetch_datasheet": DatasheetEnrichmentResponse,
    "fetch_image": ImageEnrichmentResponse,
    "fetch_pricing": PricingEnrichmentResponse,
    "fetch_stock": StockEnrichmentResponse,
    "fetch_details": DetailsEnrichmentResponse,
    "fetch_specifications": SpecificationsEnrichmentResponse,
}


def get_schema_for_capability(capability: str) -> BaseEnrichmentResponse:
    """
    Get the appropriate response schema for a given capability

    Args:
        capability: The enrichment capability name

    Returns:
        The corresponding response schema class
    """
    return CAPABILITY_SCHEMA_MAPPING.get(capability, BaseEnrichmentResponse)


def validate_enrichment_response(capability: str, response_data: Dict[str, Any]) -> BaseEnrichmentResponse:
    """
    Validate an enrichment response against the appropriate schema

    Args:
        capability: The enrichment capability name
        response_data: The response data to validate

    Returns:
        Validated response object

    Raises:
        ValidationError: If the response doesn't match the schema
    """
    schema_class = get_schema_for_capability(capability)
    return schema_class(**response_data)
