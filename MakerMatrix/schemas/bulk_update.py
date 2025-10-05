"""
Bulk Update Schema

Schema for bulk updating multiple parts at once
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class BulkUpdateRequest(BaseModel):
    """Request model for bulk updating parts"""
    part_ids: List[str] = Field(..., description="List of part IDs to update")

    # Optional field updates (only update if provided)
    supplier: Optional[str] = Field(None, description="Update supplier")
    location_id: Optional[str] = Field(None, description="Update primary location")
    minimum_quantity: Optional[int] = Field(None, description="Set minimum quantity")

    # Category operations
    add_categories: Optional[List[str]] = Field(None, description="Categories to add")
    remove_categories: Optional[List[str]] = Field(None, description="Categories to remove")


class BulkUpdateResponse(BaseModel):
    """Response model for bulk update operation"""
    updated_count: int = Field(..., description="Number of parts successfully updated")
    failed_count: int = Field(default=0, description="Number of parts that failed to update")
    errors: List[dict] = Field(default_factory=list, description="List of errors encountered")
