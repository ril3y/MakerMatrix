"""
Tag Models Module

Contains TagModel and related tag management models.
Tags provide a flexible hashtag-style labeling system for parts and tools.

Examples:
- Organization tags: #todo, #review, #urgent
- Project tags: #prototype, #testing, #production
- Status tags: #needs-reorder, #backordered, #obsolete
- Custom tags: #3d-printing, #robotics, #automotive
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, String, ForeignKey
from sqlalchemy import UniqueConstraint, func
from pydantic import ConfigDict, field_validator


class PartTagLink(SQLModel, table=True):
    """Link table for many-to-many relationship between parts and tags"""

    __tablename__ = "part_tag_links"

    part_id: str = Field(foreign_key="partmodel.id", primary_key=True)
    tag_id: str = Field(foreign_key="tagmodel.id", primary_key=True)

    # Optional metadata for the relationship
    added_at: datetime = Field(default_factory=datetime.utcnow)
    added_by: Optional[str] = Field(default=None, description="User who added the tag")


class ToolTagLink(SQLModel, table=True):
    """Link table for many-to-many relationship between tools and tags"""

    __tablename__ = "tool_tag_links"

    tool_id: str = Field(foreign_key="toolmodel.id", primary_key=True)
    tag_id: str = Field(foreign_key="tagmodel.id", primary_key=True)

    # Optional metadata for the relationship
    added_at: datetime = Field(default_factory=datetime.utcnow)
    added_by: Optional[str] = Field(default=None, description="User who added the tag")


class TagModel(SQLModel, table=True):
    """
    Main model for tags.

    This model represents hashtag-style labels that can be applied to parts and tools
    for flexible organization and filtering.

    Features:
    - Case-insensitive matching with case-preserved storage
    - Optional color coding for UI display
    - Many-to-many relationships with parts and tools
    - Usage tracking and statistics
    """

    __tablename__ = "tagmodel"

    # === CORE IDENTIFICATION ===
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True, description="Tag name without # prefix (e.g., 'todo', 'prototype')")
    name_lower: str = Field(index=True, description="Lowercase version of name for case-insensitive searches")

    # === TAG PROPERTIES ===
    color: Optional[str] = Field(
        default=None, max_length=7, description="Hex color code for UI display (e.g., '#FF5733')"
    )
    description: Optional[str] = Field(default=None, description="Optional description of tag purpose/usage")
    icon: Optional[str] = Field(default=None, max_length=50, description="Optional icon name or emoji for UI display")

    # === METADATA ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None, description="User who created the tag")

    # === USAGE STATISTICS ===
    # These are computed properties that can be cached
    usage_count: int = Field(default=0, description="Total number of parts and tools using this tag")
    parts_count: int = Field(default=0, description="Number of parts using this tag")
    tools_count: int = Field(default=0, description="Number of tools using this tag")
    last_used_at: Optional[datetime] = Field(default=None, description="Last time this tag was applied to an item")

    # === FLAGS ===
    is_system: bool = Field(default=False, description="True if this is a system-defined tag that shouldn't be deleted")
    is_active: bool = Field(default=True, description="True if tag is active and available for use")

    # === RELATIONSHIPS ===
    parts: List["PartModel"] = Relationship(
        back_populates="tags", link_model=PartTagLink, sa_relationship_kwargs={"lazy": "selectin"}
    )

    tools: List["ToolModel"] = Relationship(
        back_populates="tags", link_model=ToolTagLink, sa_relationship_kwargs={"lazy": "selectin"}
    )

    # === CONSTRAINTS ===
    __table_args__ = (UniqueConstraint("name_lower", name="uix_tag_name_lower"),)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_tag_name(cls, v: str) -> str:
        """Remove leading # if present and strip whitespace"""
        if v:
            v = v.strip()
            if v.startswith("#"):
                v = v[1:]
        return v

    @field_validator("color", mode="before")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Ensure color is a valid hex code"""
        if v and not v.startswith("#"):
            v = f"#{v}"
        if v and len(v) != 7:
            raise ValueError("Color must be a valid hex color code (e.g., '#FF5733')")
        return v

    def __init__(self, **data):
        """Custom init to handle name_lower"""
        if "name" in data:
            data["name_lower"] = data["name"].lower()
        super().__init__(**data)

    def update_usage_stats(self, session) -> None:
        """Update usage statistics for this tag"""
        # Count parts using this tag
        self.parts_count = len(self.parts) if hasattr(self, "parts") else 0

        # Count tools using this tag
        self.tools_count = len(self.tools) if hasattr(self, "tools") else 0

        # Update total usage count
        self.usage_count = self.parts_count + self.tools_count

        # Update last used timestamp
        self.last_used_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self, include_items: bool = False) -> Dict[str, Any]:
        """
        Custom serialization method for TagModel

        Args:
            include_items: If True, include lists of tagged parts and tools
        """
        base_dict = {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "description": self.description,
            "icon": self.icon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "usage_count": self.usage_count,
            "parts_count": self.parts_count,
            "tools_count": self.tools_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_system": self.is_system,
            "is_active": self.is_active,
        }

        # Optionally include tagged items
        if include_items:
            # Include basic info about tagged parts
            if hasattr(self, "parts") and self.parts:
                base_dict["parts"] = [
                    {
                        "id": part.id,
                        "part_name": part.part_name,
                        "part_number": part.part_number,
                        "manufacturer": part.manufacturer,
                        "description": part.description,
                    }
                    for part in self.parts
                ]
            else:
                base_dict["parts"] = []

            # Include basic info about tagged tools
            if hasattr(self, "tools") and self.tools:
                base_dict["tools"] = [
                    {
                        "id": tool.id,
                        "tool_name": tool.tool_name,
                        "tool_number": tool.tool_number,
                        "manufacturer": tool.manufacturer,
                        "description": tool.description,
                    }
                    for tool in self.tools
                ]
            else:
                base_dict["tools"] = []

        return base_dict

    def get_display_name(self) -> str:
        """Get the display name with # prefix for UI"""
        return f"#{self.name}"

    def matches(self, search_term: str) -> bool:
        """Check if tag matches a search term (case-insensitive)"""
        search_term = search_term.lower().strip()
        if search_term.startswith("#"):
            search_term = search_term[1:]

        # Check exact match
        if self.name_lower == search_term:
            return True

        # Check if tag contains search term
        if search_term in self.name_lower:
            return True

        # Check description
        if self.description and search_term in self.description.lower():
            return True

        return False


# Forward reference updates (resolved when all model files are imported)
if False:  # Type checking only - prevents circular imports at runtime
    from .part_models import PartModel
    from .tool_models import ToolModel
