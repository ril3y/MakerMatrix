"""
Location Models Module

Contains LocationModel and related location management models extracted from models.py.
This module focuses on hierarchical location/storage organization for parts inventory.
Supports mobile containers (cassettes) and future smart location integration.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Session, select, Column, JSON
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

    Supports:
    - Nested location structure (e.g., Building > Room > Cabinet > Drawer)
    - Mobile containers (cassettes, trays)
    - Smart locations with IoT integration (Phase 2)
    - Flexible categorization and visual identification
    """

    # === CORE FIELDS ===
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = Field(index=True)
    description: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, foreign_key="locationmodel.id")
    location_type: str = Field(default="standard")
    image_url: Optional[str] = None
    emoji: Optional[str] = None

    # === CONTAINER PROPERTIES ===
    is_mobile: bool = Field(
        default=False,
        description="True for mobile containers (cassettes, trays) that can move between parent locations"
    )
    container_capacity: Optional[int] = Field(
        default=None,
        description="Maximum quantity this container can hold (for capacity tracking)"
    )

    # === SMART LOCATION SUPPORT (Phase 2 - Not Implemented Yet) ===
    is_smart_location: bool = Field(
        default=False,
        description="True for IoT-enabled locations with sensors and connectivity"
    )
    smart_device_id: Optional[str] = Field(
        default=None,
        index=True,
        description="ESP32 or other IoT device ID (e.g., 'esp32-cabinet-01')"
    )
    smart_slot_number: Optional[int] = Field(
        default=None,
        description="Slot number in smart cabinet (for multi-slot devices)"
    )
    smart_capabilities: Optional[Dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Smart capabilities: {nfc: true, weight_sensor: true, led: true, etc.}"
    )

    # Auto-creation (for smart locations that register themselves)
    auto_created: bool = Field(
        default=False,
        description="True if location was auto-created by smart device registration"
    )
    hidden_by_default: bool = Field(
        default=False,
        description="True to hide from main location list (for auto-created smart slots)"
    )

    # Connection tracking (for smart locations)
    is_connected: bool = Field(
        default=False,
        description="True if smart device is currently connected via WebSocket/MQTT"
    )
    last_seen: Optional[datetime] = Field(
        default=None,
        description="Last connection timestamp for smart device"
    )
    firmware_version: Optional[str] = Field(
        default=None,
        description="Smart device firmware version"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Add SQLAlchemy table constraints
    __table_args__ = (
        UniqueConstraint('name', 'parent_id', name='uix_location_name_parent'),
    )

    # === RELATIONSHIPS ===

    # Self-referential relationships for hierarchy
    parent: Optional["LocationModel"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "LocationModel.id"}
    )
    children: List["LocationModel"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Parts stored at this location (DEPRECATED - use allocations instead)
    parts: List["PartModel"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={"passive_deletes": True}
    )

    # Part allocations at this location (NEW - multi-location system)
    allocations: List["PartLocationAllocation"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @classmethod
    def get_with_children(cls, session: Session, location_id: str) -> Optional["LocationModel"]:
        """Custom method to get a location with its children"""
        statement = select(cls).options(selectinload(cls.children)).where(cls.id == location_id)
        return session.exec(statement).first()

    def get_full_path(self, separator: str = " > ") -> str:
        """
        Get full hierarchical path to this location.

        Example: "Office > Storage > Reel Storage Shelf"
        """
        path_parts = [self.name]
        current = self.parent if hasattr(self, 'parent') else None

        while current is not None:
            path_parts.insert(0, current.name)
            current = current.parent if hasattr(current, 'parent') else None

        return separator.join(path_parts)

    def get_capacity_info(self) -> Optional[Dict[str, Any]]:
        """Get container capacity information if this is a container"""
        if not self.is_mobile or self.container_capacity is None:
            return None

        # Calculate total allocated quantity from allocations
        total_allocated = 0
        if hasattr(self, 'allocations') and self.allocations:
            total_allocated = sum(alloc.quantity_at_location for alloc in self.allocations)

        return {
            "capacity": self.container_capacity,
            "used": total_allocated,
            "available": self.container_capacity - total_allocated,
            "usage_percentage": (total_allocated / self.container_capacity * 100) if self.container_capacity > 0 else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method for LocationModel"""
        # Start with basic fields
        base_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "location_type": self.location_type,
            "image_url": self.image_url,
            "emoji": self.emoji,

            # Container properties
            "is_mobile": self.is_mobile,
            "container_capacity": self.container_capacity,

            # Smart location properties (Phase 2)
            "is_smart_location": self.is_smart_location,
            "smart_device_id": self.smart_device_id,
            "smart_slot_number": self.smart_slot_number,
            "smart_capabilities": self.smart_capabilities,
            "auto_created": self.auto_created,
            "hidden_by_default": self.hidden_by_default,
            "is_connected": self.is_connected,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "firmware_version": self.firmware_version
        }

        # Add capacity info if this is a container
        capacity_info = self.get_capacity_info()
        if capacity_info:
            base_dict["capacity_info"] = capacity_info
        
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
    from .part_allocation_models import PartLocationAllocation