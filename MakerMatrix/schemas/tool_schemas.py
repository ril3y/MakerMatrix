"""
Tool Schemas Module

Contains Pydantic schemas for tool-related API request/response models.
These schemas handle validation and serialization for tool operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ToolCreateRequest(BaseModel):
    """Request schema for creating a new tool"""
    tool_name: str = Field(..., min_length=1, max_length=255, description="Unique tool name")
    tool_number: Optional[str] = Field(None, max_length=100, description="Internal tool tracking number")
    description: Optional[str] = Field(None, description="Tool description and notes")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Tool manufacturer")
    model_number: Optional[str] = Field(None, max_length=255, description="Manufacturer's model number")
    tool_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Tool category: hand_tool, power_tool, measuring_instrument, consumable, etc."
    )

    supplier: Optional[str] = Field(None, max_length=255, description="Primary/preferred supplier")
    supplier_part_number: Optional[str] = Field(None, max_length=255, description="Supplier's part number")
    supplier_url: Optional[str] = Field(None, description="URL to supplier homepage")
    product_url: Optional[str] = Field(None, description="URL to specific product page")

    image_url: Optional[str] = Field(None, description="URL to tool image")
    emoji: Optional[str] = Field(None, max_length=50, description="Unicode emoji or shortcode")

    additional_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Tool-specific properties as flat key-value pairs"
    )

    condition: Optional[str] = Field(
        "good",
        description="Tool condition: excellent, good, fair, poor, needs_repair, out_of_service"
    )
    is_checkable: Optional[bool] = Field(True, description="Can be checked out (False for large/stationary equipment)")
    is_calibrated_tool: Optional[bool] = Field(False, description="Requires regular calibration")
    is_consumable: Optional[bool] = Field(False, description="Consumable item (bits, blades, etc.)")

    purchase_date: Optional[datetime] = Field(None, description="Date tool was purchased")
    purchase_price: Optional[float] = Field(None, ge=0, description="Original purchase price")

    # Initial location and quantity
    location_id: Optional[str] = Field(None, description="Initial storage location ID")
    quantity: int = Field(1, ge=1, description="Initial quantity (typically 1)")

    category_ids: Optional[List[str]] = Field(default_factory=list, description="Category IDs to assign")

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        valid_conditions = ['excellent', 'good', 'fair', 'poor', 'needs_repair', 'out_of_service']
        if v and v not in valid_conditions:
            raise ValueError(f"Condition must be one of: {', '.join(valid_conditions)}")
        return v


class ToolUpdateRequest(BaseModel):
    """Request schema for updating an existing tool"""
    tool_name: Optional[str] = Field(None, min_length=1, max_length=255)
    tool_number: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    manufacturer: Optional[str] = Field(None, max_length=255)
    model_number: Optional[str] = Field(None, max_length=255)
    tool_type: Optional[str] = Field(None, max_length=100)

    supplier: Optional[str] = Field(None, max_length=255)
    supplier_part_number: Optional[str] = Field(None, max_length=255)
    supplier_url: Optional[str] = None
    product_url: Optional[str] = None

    image_url: Optional[str] = None
    emoji: Optional[str] = Field(None, max_length=50)

    additional_properties: Optional[Dict[str, Any]] = None

    condition: Optional[str] = None
    maintenance_notes: Optional[str] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None

    is_checkable: Optional[bool] = None
    is_calibrated_tool: Optional[bool] = None
    is_consumable: Optional[bool] = None

    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = Field(None, ge=0)
    current_value: Optional[float] = Field(None, ge=0)

    category_ids: Optional[List[str]] = None

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        if v is None:
            return v
        valid_conditions = ['excellent', 'good', 'fair', 'poor', 'needs_repair', 'out_of_service']
        if v not in valid_conditions:
            raise ValueError(f"Condition must be one of: {', '.join(valid_conditions)}")
        return v


class ToolCheckoutRequest(BaseModel):
    """Request schema for checking out a tool"""
    user_id: str = Field(..., description="User ID checking out the tool")
    expected_return_date: Optional[datetime] = Field(None, description="Expected return date")
    notes: Optional[str] = Field(None, description="Checkout notes")


class ToolReturnRequest(BaseModel):
    """Request schema for returning a tool"""
    condition: Optional[str] = Field(None, description="Tool condition after return")
    notes: Optional[str] = Field(None, description="Return notes (issues, damage, etc.)")

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        if v is None:
            return v
        valid_conditions = ['excellent', 'good', 'fair', 'poor', 'needs_repair', 'out_of_service']
        if v not in valid_conditions:
            raise ValueError(f"Condition must be one of: {', '.join(valid_conditions)}")
        return v


class ToolMaintenanceRequest(BaseModel):
    """Request schema for recording tool maintenance"""
    maintenance_date: datetime = Field(..., description="Date maintenance was performed")
    maintenance_type: str = Field(
        ...,
        description="Type of maintenance: calibration, repair, inspection, cleaning"
    )
    performed_by: Optional[str] = Field(None, description="User ID who performed maintenance (auto-set by backend if not provided)")
    notes: Optional[str] = Field(None, description="Maintenance notes and details")
    next_maintenance_date: Optional[datetime] = Field(None, description="Next scheduled maintenance")
    cost: Optional[float] = Field(None, ge=0, description="Maintenance cost")

    @field_validator('maintenance_type')
    @classmethod
    def validate_maintenance_type(cls, v):
        valid_types = ['calibration', 'repair', 'inspection', 'cleaning', 'other']
        if v not in valid_types:
            raise ValueError(f"Maintenance type must be one of: {', '.join(valid_types)}")
        return v


class ToolAllocationRequest(BaseModel):
    """Request schema for creating or updating tool allocation"""
    location_id: str = Field(..., description="Location ID")
    quantity: int = Field(..., ge=0, description="Quantity at location")
    is_primary: Optional[bool] = Field(False, description="Is this the primary storage location")
    notes: Optional[str] = Field(None, description="Allocation notes")


class ToolTransferRequest(BaseModel):
    """Request schema for transferring tool between locations"""
    from_location_id: str = Field(..., description="Source location ID")
    to_location_id: str = Field(..., description="Destination location ID")
    quantity: int = Field(..., gt=0, description="Quantity to transfer")
    notes: Optional[str] = Field(None, description="Transfer notes")


class ToolSearchRequest(BaseModel):
    """Request schema for advanced tool search"""
    search_term: Optional[str] = Field(None, description="General search term")
    manufacturer: Optional[str] = Field(None, description="Filter by manufacturer")
    tool_type: Optional[str] = Field(None, description="Filter by tool type")
    condition: Optional[str] = Field(None, description="Filter by condition")
    is_checked_out: Optional[bool] = Field(None, description="Filter by checkout status")
    is_available: Optional[bool] = Field(None, description="Filter by availability")
    needs_maintenance: Optional[bool] = Field(None, description="Filter tools needing maintenance")
    is_calibrated_tool: Optional[bool] = Field(None, description="Filter calibrated tools")
    is_consumable: Optional[bool] = Field(None, description="Filter consumable tools")
    category_ids: Optional[List[str]] = Field(None, description="Filter by category IDs")
    location_id: Optional[str] = Field(None, description="Filter by location")

    sort_by: str = Field("tool_name", description="Sort field: tool_name, manufacturer, tool_type, condition")
    sort_order: str = Field("asc", description="Sort order: asc or desc")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        valid_fields = ['tool_name', 'tool_number', 'manufacturer', 'model_number', 'tool_type', 'condition', 'created_at']
        if v not in valid_fields:
            raise ValueError(f"sort_by must be one of: {', '.join(valid_fields)}")
        return v

    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class ToolResponse(BaseModel):
    """Response schema for tool data"""
    id: str
    tool_name: str
    tool_number: Optional[str]
    description: Optional[str]
    manufacturer: Optional[str]
    model_number: Optional[str]
    tool_type: Optional[str]

    supplier: Optional[str]
    supplier_part_number: Optional[str]
    supplier_url: Optional[str]
    product_url: Optional[str]

    image_url: Optional[str]
    emoji: Optional[str]

    additional_properties: Dict[str, Any]

    condition: str
    last_maintenance_date: Optional[datetime]
    next_maintenance_date: Optional[datetime]
    maintenance_notes: Optional[str]

    is_checked_out: bool
    checked_out_by: Optional[str]
    checked_out_at: Optional[datetime]
    expected_return_date: Optional[datetime]

    purchase_date: Optional[datetime]
    purchase_price: Optional[float]
    current_value: Optional[float]

    is_checkable: bool
    is_calibrated_tool: bool
    is_consumable: bool
    exclude_from_analytics: bool

    quantity: int  # Total quantity across all allocations
    location: Optional[Dict[str, Any]]  # Primary location
    location_id: Optional[str]
    categories: List[Dict[str, Any]]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """Response schema for paginated tool list"""
    tools: List[ToolResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ToolAllocationResponse(BaseModel):
    """Response schema for tool allocation"""
    id: str
    tool_id: str
    location_id: str
    quantity_at_location: int
    is_primary_storage: bool
    notes: Optional[str]
    allocated_at: datetime
    last_updated: datetime
    location: Optional[Dict[str, Any]]
    location_path: Optional[str]

    class Config:
        from_attributes = True


class ToolStatisticsResponse(BaseModel):
    """Response schema for tool statistics"""
    total_tools: int
    total_by_type: Dict[str, int]
    total_by_condition: Dict[str, int]
    checked_out_count: int
    available_count: int
    needs_maintenance_count: int
    total_value: float
    by_location: Dict[str, int]
