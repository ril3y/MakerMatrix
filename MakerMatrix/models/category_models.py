"""
Category Models Module

Contains CategoryModel and related categorization models extracted from models.py.
This module focuses on part categorization and organization.
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from pydantic import ConfigDict

# Import link tables to avoid circular dependency
from .part_models import PartCategoryLink


class CategoryUpdate(SQLModel):
    """Update model for category modifications"""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    children: Optional[List[str]] = None  # List of child category IDs


class CategoryModel(SQLModel, table=True):
    """
    Model for organizing parts and tools into categories.

    Provides hierarchical categorization system for parts and tools
    (e.g., Electronics > Resistors > Surface Mount Resistors, or Tools > Hand Tools > Screwdrivers).
    """

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

    # Many-to-many relationship with parts through PartCategoryLink
    parts: List["PartModel"] = Relationship(
        back_populates="categories",
        link_model=PartCategoryLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Many-to-many relationship with tools through ToolCategoryLink
    tools: List["ToolModel"] = Relationship(
        back_populates="categories",
        link_model="ToolCategoryLink",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method for CategoryModel"""
        return self.model_dump(exclude={"parts", "tools"})


# Forward reference updates (resolved when all model files are imported)
if False:  # Type checking only - prevents circular imports at runtime
    from .part_models import PartModel, PartCategoryLink
    from .tool_models import ToolModel, ToolCategoryLink