"""
Tag Schemas Module

Contains Pydantic schemas for tag-related operations.
These schemas handle request/response validation and transformation
for the tag management system.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TagBase(BaseModel):
    """Base schema for tags with common fields"""

    name: str = Field(..., description="Tag name without # prefix", min_length=1, max_length=50)
    color: Optional[str] = Field(None, description="Hex color code for UI display (e.g., '#FF5733')", max_length=7)
    description: Optional[str] = Field(None, description="Optional description of tag purpose/usage", max_length=500)
    icon: Optional[str] = Field(None, description="Optional icon name or emoji for UI display", max_length=50)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_tag_name(cls, v: str) -> str:
        """Remove leading # if present and strip whitespace"""
        if v:
            v = v.strip()
            if v.startswith("#"):
                v = v[1:]
            # Ensure no spaces in tag name
            v = v.replace(" ", "-")
        return v

    @field_validator("color", mode="before")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Ensure color is a valid hex code"""
        if not v:
            return v
        v = v.strip()
        if not v.startswith("#"):
            v = f"#{v}"
        if len(v) != 7:
            raise ValueError("Color must be a valid hex color code (e.g., '#FF5733')")
        # Validate hex characters
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must contain valid hexadecimal characters")
        return v.upper()


class TagCreate(TagBase):
    """Schema for creating a new tag"""

    is_system: bool = Field(False, description="Mark as system tag (protected from deletion)")


class TagUpdate(BaseModel):
    """Schema for updating an existing tag"""

    name: Optional[str] = Field(None, description="Tag name without # prefix", min_length=1, max_length=50)
    color: Optional[str] = Field(None, description="Hex color code for UI display", max_length=7)
    description: Optional[str] = Field(None, description="Optional description", max_length=500)
    icon: Optional[str] = Field(None, description="Optional icon name or emoji", max_length=50)
    is_active: Optional[bool] = Field(None, description="Set tag active/inactive status")

    @field_validator("name", mode="before")
    @classmethod
    def normalize_tag_name(cls, v: Optional[str]) -> Optional[str]:
        """Remove leading # if present and strip whitespace"""
        if v:
            v = v.strip()
            if v.startswith("#"):
                v = v[1:]
            v = v.replace(" ", "-")
        return v

    @field_validator("color", mode="before")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Ensure color is a valid hex code"""
        if not v:
            return v
        v = v.strip()
        if not v.startswith("#"):
            v = f"#{v}"
        if len(v) != 7:
            raise ValueError("Color must be a valid hex color code")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must contain valid hexadecimal characters")
        return v.upper()


class TagResponse(BaseModel):
    """Schema for tag responses"""

    id: str = Field(..., description="Tag unique identifier")
    name: str = Field(..., description="Tag name without # prefix")
    color: Optional[str] = Field(None, description="Hex color code for UI display")
    description: Optional[str] = Field(None, description="Tag description")
    icon: Optional[str] = Field(None, description="Icon name or emoji")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="User who created the tag")
    usage_count: int = Field(0, description="Total number of items using this tag")
    parts_count: int = Field(0, description="Number of parts using this tag")
    tools_count: int = Field(0, description="Number of tools using this tag")
    last_used_at: Optional[datetime] = Field(None, description="Last time tag was applied")
    is_system: bool = Field(False, description="True if system-protected tag")
    is_active: bool = Field(True, description="True if tag is active")

    model_config = ConfigDict(from_attributes=True)

    def get_display_name(self) -> str:
        """Get the display name with # prefix for UI"""
        return f"#{self.name}"


class TagWithItemsResponse(TagResponse):
    """Schema for tag response including tagged items"""

    parts: List[Dict[str, Any]] = Field(default_factory=list, description="List of tagged parts")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="List of tagged tools")


class TagFilter(BaseModel):
    """Schema for filtering tags"""

    search: Optional[str] = Field(None, description="Search term for tag name or description")
    is_active: Optional[bool] = Field(None, description="Filter by active/inactive status")
    is_system: Optional[bool] = Field(None, description="Filter by system/user tags")
    min_usage: Optional[int] = Field(None, ge=0, description="Minimum usage count")
    max_usage: Optional[int] = Field(None, ge=0, description="Maximum usage count")
    has_color: Optional[bool] = Field(None, description="Filter tags with/without color")
    created_after: Optional[datetime] = Field(None, description="Filter tags created after date")
    created_before: Optional[datetime] = Field(None, description="Filter tags created before date")
    sort_by: str = Field("name", description="Sort field: name, usage_count, created_at, updated_at")
    sort_order: str = Field("asc", description="Sort order: asc or desc")
    page: int = Field(1, ge=1, description="Page number for pagination")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class TagAssignment(BaseModel):
    """Schema for assigning tags to items"""

    tag_ids: List[str] = Field(..., description="List of tag IDs to assign", min_length=1)
    user_id: Optional[str] = Field(None, description="User performing the assignment")


class TagBulkOperation(BaseModel):
    """Schema for bulk tag operations"""

    item_ids: List[str] = Field(..., description="List of part or tool IDs", min_length=1)
    tag_ids: List[str] = Field(..., description="List of tag IDs", min_length=1)
    operation: str = Field(..., description="Operation type: 'add' or 'remove'")
    item_type: str = Field(..., description="Item type: 'part' or 'tool'")


class TagSummaryResponse(BaseModel):
    """Schema for tag system summary statistics"""

    total_tags: int = Field(..., description="Total number of tags in system")
    active_tags: int = Field(..., description="Number of active tags")
    system_tags: int = Field(..., description="Number of system-protected tags")
    user_tags: int = Field(..., description="Number of user-created tags")
    most_used_tags: List[TagResponse] = Field(default_factory=list, description="Top 10 most used tags")
    recently_used_tags: List[TagResponse] = Field(default_factory=list, description="Recently applied tags")
    unused_tags: int = Field(0, description="Number of unused tags")


class TagSuggestion(BaseModel):
    """Schema for tag suggestions based on context"""

    suggested_tags: List[str] = Field(default_factory=list, description="List of suggested tag names")
    reason: Optional[str] = Field(None, description="Reason for suggestions")


class TagMergeRequest(BaseModel):
    """Schema for merging multiple tags into one"""

    source_tag_ids: List[str] = Field(..., description="Tags to merge from", min_length=1)
    target_tag_id: str = Field(..., description="Tag to merge into")
    delete_sources: bool = Field(True, description="Delete source tags after merge")


class TagCleanupRequest(BaseModel):
    """Schema for cleaning up unused or duplicate tags"""

    remove_unused: bool = Field(True, description="Remove tags with zero usage")
    merge_similar: bool = Field(False, description="Merge tags with similar names")
    similarity_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Similarity threshold for merging")
