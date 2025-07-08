"""
Location Models Module

Contains LocationModel and related location management models extracted from models.py.
This module focuses on hierarchical location/storage organization for parts inventory.
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import selectinload
from pydantic import ConfigDict


class LocationQueryModel(SQLModel):
    """Query model for location lookups"""
    id: Optional[str] = None
    name: Optional[str] = None


class LocationModel(SQLModel, table=True):
    """
    Model for hierarchical location/storage organization.
    
    Supports nested location structure (e.g., Building > Room > Cabinet > Drawer)
    with flexible categorization and visual identification features.
    """
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = Field(index=True)
    description: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, foreign_key="locationmodel.id")
    location_type: str = Field(default="standard")
    image_url: Optional[str] = None
    emoji: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Add SQLAlchemy table constraints
    __table_args__ = (
        UniqueConstraint('name', 'parent_id', name='uix_location_name_parent'),
    )

    # Self-referential relationships for hierarchy
    parent: Optional["LocationModel"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "LocationModel.id"}
    )
    children: List["LocationModel"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Parts stored at this location
    parts: List["PartModel"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={"passive_deletes": True}
    )

    @classmethod
    def get_with_children(cls, session: Session, location_id: str) -> Optional["LocationModel"]:
        """Custom method to get a location with its children"""
        statement = select(cls).options(selectinload(cls.children)).where(cls.id == location_id)
        return session.exec(statement).first()

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method for LocationModel"""
        # Start with basic fields only
        base_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "location_type": self.location_type,
            "image_url": self.image_url,
            "emoji": self.emoji
        }
        
        # Safely include parent if loaded and available
        try:
            if hasattr(self, 'parent') and self.parent is not None:
                base_dict["parent"] = {
                    "id": self.parent.id,
                    "name": self.parent.name,
                    "description": self.parent.description,
                    "location_type": self.parent.location_type
                }
        except Exception:
            # If parent can't be accessed, skip it
            pass
        
        # Safely include children if loaded and available
        try:
            if hasattr(self, 'children') and self.children is not None:
                base_dict["children"] = []
                for child in self.children:
                    child_dict = {
                        "id": child.id,
                        "name": child.name,
                        "description": child.description,
                        "parent_id": child.parent_id,
                        "location_type": child.location_type,
                        "image_url": child.image_url,
                        "emoji": child.emoji
                    }
                    base_dict["children"].append(child_dict)
        except Exception:
            # If children can't be accessed, skip them
            pass
        
        return base_dict


class LocationUpdate(SQLModel):
    """Update model for location modifications"""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: Optional[str] = None
    image_url: Optional[str] = None
    emoji: Optional[str] = None


# Forward reference updates (resolved when all model files are imported)
if False:  # Type checking only - prevents circular imports at runtime
    from .part_models import PartModel