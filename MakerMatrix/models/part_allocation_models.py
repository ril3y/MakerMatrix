"""
Part Allocation Models Module

Contains PartLocationAllocation and related models for tracking parts across multiple locations.
This module enables multi-location inventory with quantity distribution tracking.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, String, ForeignKey
from sqlalchemy import UniqueConstraint
from pydantic import ConfigDict


class PartLocationAllocation(SQLModel, table=True):
    """
    Track partial quantities of parts across multiple locations.

    Enables a single part to exist in multiple physical locations simultaneously,
    with quantity tracking for each allocation. For example:
    - Part C1591: 4000 total
      - Reel Storage Shelf: 3900 pcs (primary)
      - SMD Cassette #42: 100 pcs (working stock)
    """

    __tablename__ = "part_location_allocations"

    # === IDENTITY ===
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(
        sa_column=Column(String, ForeignKey("partmodel.id", ondelete="CASCADE"), index=True),
        description="Part that is allocated",
    )
    location_id: str = Field(
        sa_column=Column(String, ForeignKey("locationmodel.id", ondelete="CASCADE"), index=True),
        description="Location where quantity is allocated",
    )

    # === QUANTITY TRACKING ===
    quantity_at_location: int = Field(default=0, ge=0, description="Quantity allocated at this specific location")
    is_primary_storage: bool = Field(
        default=False, description="True for main storage (reel/bulk), False for working stock (cassettes)"
    )

    # === METADATA ===
    allocated_at: datetime = Field(default_factory=datetime.utcnow, description="When this allocation was created")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last quantity change timestamp")
    notes: Optional[str] = Field(
        default=None, description="Allocation notes (e.g., 'Working stock for GC_CONTROLLER project')"
    )

    # === FUTURE: SMART LOCATION SUPPORT (Phase 2 - Not Implemented Yet) ===
    auto_synced: bool = Field(default=False, description="True if quantity is auto-updated by smart location sensor")
    last_nfc_scan: Optional[datetime] = Field(default=None, description="Last NFC scan timestamp (for smart locations)")

    # === RELATIONSHIPS ===
    part: Optional["PartModel"] = Relationship(
        back_populates="allocations", sa_relationship_kwargs={"lazy": "selectin"}
    )
    location: Optional["LocationModel"] = Relationship(
        back_populates="allocations", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # === CONSTRAINTS ===
    __table_args__ = (UniqueConstraint("part_id", "location_id", name="uix_part_location"),)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method for API responses"""
        base_dict = {
            "id": self.id,
            "part_id": self.part_id,
            "location_id": self.location_id,
            "quantity_at_location": self.quantity_at_location,
            "is_primary_storage": self.is_primary_storage,
            "notes": self.notes,
            "auto_synced": self.auto_synced,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "last_nfc_scan": self.last_nfc_scan.isoformat() if self.last_nfc_scan else None,
        }

        # Include location details if loaded
        if hasattr(self, "location") and self.location is not None:
            # Use LocationModel's to_dict() to include all fields (container slots, parent, etc.)
            base_dict["location"] = self.location.to_dict()

            # Add location path if available
            try:
                if hasattr(self.location, "get_full_path"):
                    base_dict["location_path"] = self.location.get_full_path()
            except Exception:
                pass

        # Include part details if loaded (minimal to avoid circular refs)
        if hasattr(self, "part") and self.part is not None:
            base_dict["part"] = {
                "id": self.part.id,
                "part_name": self.part.part_name,
                "part_number": self.part.part_number,
            }

        return base_dict


# === REQUEST/RESPONSE MODELS ===


class AllocationCreate(SQLModel):
    """Request model for creating a new allocation"""

    location_id: str
    quantity: int = Field(gt=0, description="Quantity to allocate (must be > 0)")
    is_primary: bool = False
    notes: Optional[str] = None


class AllocationUpdate(SQLModel):
    """Request model for updating an allocation"""

    quantity: Optional[int] = Field(default=None, ge=0)
    is_primary: Optional[bool] = None
    notes: Optional[str] = None


class TransferRequest(SQLModel):
    """Request model for transferring quantity between locations"""

    from_location_id: str
    to_location_id: str
    quantity: int = Field(gt=0, description="Quantity to transfer (must be > 0)")
    notes: Optional[str] = None


class SplitToCassetteRequest(SQLModel):
    """Request model for quick split to cassette operation"""

    from_location_id: str
    quantity: int = Field(gt=0, description="Quantity to split (must be > 0)")

    # Cassette creation options
    create_new_cassette: bool = True
    cassette_id: Optional[str] = None  # If using existing cassette
    cassette_name: Optional[str] = None  # Required if creating new
    parent_location_id: Optional[str] = None  # Where cassette physically is
    cassette_capacity: Optional[int] = None
    cassette_emoji: Optional[str] = "📦"

    notes: Optional[str] = None


# Forward reference updates (resolved when all model files are imported)
if False:  # Type checking only - prevents circular imports at runtime
    from .part_models import PartModel
    from .location_models import LocationModel
