"""
Tool Models Module

Contains ToolModel and related tool management models.
Tools are physical items tracked individually or in small quantities,
distinct from electronic parts which are typically tracked in bulk.

Examples:
- Hand tools (screwdrivers, pliers, wrenches)
- Power tools (drills, soldering stations, oscilloscopes)
- Consumable tools (drill bits, saw blades)
- Measuring instruments (multimeters, calipers, scales)
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, String, ForeignKey, JSON
from sqlalchemy import UniqueConstraint
from pydantic import ConfigDict


class ToolCategoryLink(SQLModel, table=True):
    """Link table for many-to-many relationship between tools and categories"""

    __tablename__ = "tool_category_links"

    tool_id: str = Field(foreign_key="toolmodel.id", primary_key=True)
    category_id: str = Field(foreign_key="categorymodel.id", primary_key=True)


class ToolModel(SQLModel, table=True):
    """
    Main model for tools and equipment.

    This model represents individual tools in inventory with support for:
    - Core identification and description
    - Inventory tracking (typically single units or small quantities)
    - Location tracking (where tool is stored)
    - Tool-specific properties (size, type, specifications)
    - Maintenance and usage tracking
    - Supplier information
    """

    __tablename__ = "toolmodel"

    # === CORE IDENTIFICATION ===
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tool_name: str = Field(index=True, unique=True, description="Unique tool identifier/name")
    tool_number: Optional[str] = Field(default=None, index=True, description="Internal tool tracking number")

    # === TOOL DESCRIPTION ===
    description: Optional[str] = Field(default=None, description="Tool description and notes")
    manufacturer: Optional[str] = Field(default=None, index=True, description="Tool manufacturer")
    model_number: Optional[str] = Field(default=None, index=True, description="Manufacturer's model number")
    tool_type: Optional[str] = Field(
        default=None,
        index=True,
        description="Tool category: hand_tool, power_tool, measuring_instrument, consumable, etc.",
    )

    # === CURRENT INVENTORY ===
    # NOTE: Quantity and location are managed through allocations (ToolLocationAllocation)
    # Use tool.total_quantity and tool.primary_location computed properties instead

    # === SUPPLIER INFORMATION ===
    supplier: Optional[str] = Field(default=None, description="Primary/preferred supplier")
    supplier_part_number: Optional[str] = Field(default=None, index=True, description="Supplier's part number")
    supplier_url: Optional[str] = Field(default=None, description="URL to supplier homepage")
    product_url: Optional[str] = Field(default=None, description="URL to specific product page")

    # === MEDIA ===
    image_url: Optional[str] = Field(default=None, description="URL to tool image")
    emoji: Optional[str] = Field(
        default=None, max_length=50, description="Unicode emoji character or shortcode (e.g., '🔧' or ':wrench:')"
    )

    # === TOOL-SPECIFIC PROPERTIES ===
    # Examples:
    # Screwdriver: {"type": "phillips", "size": "#2", "shaft_length": "4in", "handle_type": "magnetic"}
    # Drill: {"voltage": "20V", "battery_type": "lithium", "chuck_size": "1/2in", "max_torque": "650in-lbs"}
    # Multimeter: {"max_voltage": "1000V", "max_current": "10A", "features": ["auto-ranging", "true-rms"]}
    # Caliper: {"type": "digital", "range": "0-6in", "resolution": "0.0005in", "accuracy": "±0.001in"}
    additional_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Tool-specific properties as FLAT key-value pairs (size, voltage, capacity, etc.)",
    )

    # === MAINTENANCE & STATUS ===
    condition: Optional[str] = Field(
        default="good", description="Tool condition: excellent, good, fair, poor, needs_repair, out_of_service"
    )
    last_maintenance_date: Optional[datetime] = Field(default=None, description="Last maintenance/calibration date")
    next_maintenance_date: Optional[datetime] = Field(default=None, description="Scheduled next maintenance date")
    maintenance_notes: Optional[str] = Field(default=None, description="Maintenance history and notes")

    # === USAGE TRACKING ===
    is_checked_out: bool = Field(default=False, description="True if tool is currently checked out/in use")
    checked_out_by: Optional[str] = Field(default=None, description="User ID who has checked out the tool")
    checked_out_at: Optional[datetime] = Field(default=None, description="When tool was checked out")
    expected_return_date: Optional[datetime] = Field(
        default=None, description="Expected return date for checked out tool"
    )

    # === PURCHASE & VALUE ===
    purchase_date: Optional[datetime] = Field(default=None, description="Date tool was purchased")
    purchase_price: Optional[float] = Field(default=None, description="Original purchase price")
    current_value: Optional[float] = Field(default=None, description="Current estimated value")

    # === FLAGS ===
    is_checkable: bool = Field(
        default=True, description="True if tool can be checked out (False for large/stationary equipment)"
    )
    is_calibrated_tool: bool = Field(
        default=False, description="True if tool requires regular calibration (e.g., measuring instruments)"
    )
    is_consumable: bool = Field(default=False, description="True if tool is consumable (drill bits, blades, etc.)")
    exclude_from_analytics: bool = Field(
        default=True, description="Exclude from low stock and other part-specific analytics"
    )

    # === TIMESTAMPS ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # === CORE RELATIONSHIPS ===
    categories: List["CategoryModel"] = Relationship(
        back_populates="tools", link_model=ToolCategoryLink, sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Tags (many-to-many relationship through link table)
    # Note: link_model is imported later to avoid circular imports
    tags: List["TagModel"] = Relationship(
        back_populates="tools", sa_relationship_kwargs={"lazy": "selectin", "secondary": "tool_tag_links"}
    )

    # === MULTI-LOCATION ALLOCATIONS ===
    allocations: List["ToolLocationAllocation"] = Relationship(
        back_populates="tool", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    # === MAINTENANCE RECORDS ===
    maintenance_records: List["ToolMaintenanceRecord"] = Relationship(
        back_populates="tool", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # === COMPUTED PROPERTIES FOR MULTI-LOCATION SUPPORT ===

    @property
    def total_quantity(self) -> int:
        """
        Calculate total quantity across all location allocations.

        Returns 0 if no allocations exist.
        For most tools, this will be 1 (single item).
        For consumables, this may be higher.
        """
        if not hasattr(self, "allocations") or not self.allocations:
            return 0

        return sum(alloc.quantity_at_location for alloc in self.allocations)

    @property
    def primary_location(self) -> Optional["LocationModel"]:
        """
        Get the primary storage location.

        Returns the location marked as primary storage, or the first allocation if none marked.
        Returns None if no allocations exist.
        """
        if not hasattr(self, "allocations") or not self.allocations:
            return None

        # Find primary storage allocation
        primary_alloc = next((alloc for alloc in self.allocations if alloc.is_primary_storage), None)

        if primary_alloc:
            return primary_alloc.location

        # If no primary marked, return first allocation's location
        if self.allocations:
            return self.allocations[0].location

        return None

    def get_allocations_summary(self) -> Dict[str, Any]:
        """
        Get summary of all location allocations for UI display.

        Returns:
            {
                "total_quantity": 1,
                "location_count": 1,
                "primary_location": {...},
                "allocations": [...]
            }
        """
        if not hasattr(self, "allocations") or not self.allocations:
            return {"total_quantity": 0, "location_count": 0, "primary_location": None, "allocations": []}

        return {
            "total_quantity": self.total_quantity,
            "location_count": len(self.allocations),
            "primary_location": self.primary_location.to_dict() if self.primary_location else None,
            "allocations": [alloc.to_dict() for alloc in self.allocations],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method for ToolModel"""
        # Exclude allocations from base dict (included separately)
        base_dict = self.model_dump(exclude={"allocations"})

        # Always include categories
        base_dict["categories"] = (
            [
                {"id": category.id, "name": category.name, "description": category.description}
                for category in self.categories
            ]
            if self.categories
            else []
        )

        # Always include tags (core tool data)
        base_dict["tags"] = (
            [{"id": tag.id, "name": tag.name, "color": tag.color, "icon": tag.icon} for tag in self.tags]
            if hasattr(self, "tags") and self.tags
            else []
        )

        # Always include primary location from allocations
        primary_loc = self.primary_location
        if primary_loc:
            base_dict["location"] = primary_loc.to_dict()
            base_dict["location_id"] = primary_loc.id
        else:
            base_dict["location"] = None
            base_dict["location_id"] = None

        # Include total quantity from allocations
        base_dict["quantity"] = self.total_quantity

        # Convert datetime fields to ISO strings for JSON serialization
        datetime_fields = [
            "last_maintenance_date",
            "next_maintenance_date",
            "checked_out_at",
            "expected_return_date",
            "purchase_date",
            "created_at",
            "updated_at",
        ]
        for field in datetime_fields:
            if field in base_dict and base_dict[field]:
                base_dict[field] = base_dict[field].isoformat()

        return base_dict

    def is_available(self) -> bool:
        """Check if tool is available (not checked out and in good condition)"""
        return not self.is_checked_out and self.condition not in ["needs_repair", "out_of_service"]

    def needs_maintenance(self) -> bool:
        """Check if tool needs maintenance"""
        if not self.next_maintenance_date:
            return False
        return datetime.utcnow() >= self.next_maintenance_date

    def get_display_name(self) -> str:
        """Get the best display name for UI"""
        if self.manufacturer and self.model_number:
            return f"{self.manufacturer} {self.model_number}"
        elif self.model_number:
            return self.model_number
        elif self.tool_number:
            return self.tool_number
        else:
            return self.tool_name


class ToolLocationAllocation(SQLModel, table=True):
    """
    Track quantities of tools across multiple locations.

    Similar to PartLocationAllocation but for tools.
    Most tools will have quantity=1 at a single location.
    Consumable tools may have higher quantities or multiple locations.
    """

    __tablename__ = "tool_location_allocations"

    # === IDENTITY ===
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tool_id: str = Field(
        sa_column=Column(String, ForeignKey("toolmodel.id", ondelete="CASCADE"), index=True),
        description="Tool that is allocated",
    )
    location_id: str = Field(
        sa_column=Column(String, ForeignKey("locationmodel.id", ondelete="CASCADE"), index=True),
        description="Location where tool is allocated",
    )

    # === QUANTITY TRACKING ===
    quantity_at_location: int = Field(default=1, ge=0, description="Quantity at this location (typically 1 for tools)")
    is_primary_storage: bool = Field(default=True, description="True for primary storage location")

    # === METADATA ===
    allocated_at: datetime = Field(default_factory=datetime.utcnow, description="When this allocation was created")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last quantity change timestamp")
    notes: Optional[str] = Field(default=None, description="Allocation notes")

    # === RELATIONSHIPS ===
    tool: Optional["ToolModel"] = Relationship(
        back_populates="allocations", sa_relationship_kwargs={"lazy": "selectin"}
    )
    location: Optional["LocationModel"] = Relationship(
        back_populates="tool_allocations", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # === CONSTRAINTS ===
    __table_args__ = (UniqueConstraint("tool_id", "location_id", name="uix_tool_location"),)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method for API responses"""
        base_dict = {
            "id": self.id,
            "tool_id": self.tool_id,
            "location_id": self.location_id,
            "quantity_at_location": self.quantity_at_location,
            "is_primary_storage": self.is_primary_storage,
            "notes": self.notes,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

        # Include location details if loaded
        if hasattr(self, "location") and self.location is not None:
            base_dict["location"] = self.location.to_dict()

            # Add location path if available
            try:
                if hasattr(self.location, "get_full_path"):
                    base_dict["location_path"] = self.location.get_full_path()
            except Exception:
                pass

        # Include tool details if loaded
        if hasattr(self, "tool") and self.tool is not None:
            base_dict["tool"] = {
                "id": self.tool.id,
                "tool_name": self.tool.tool_name,
                "tool_number": self.tool.tool_number,
            }

        return base_dict


# === REQUEST/RESPONSE MODELS ===


class ToolCreate(SQLModel):
    """Request model for creating a new tool"""

    tool_name: str
    tool_number: Optional[str] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    tool_type: Optional[str] = None

    supplier: Optional[str] = None
    supplier_part_number: Optional[str] = None
    supplier_url: Optional[str] = None
    product_url: Optional[str] = None

    image_url: Optional[str] = None
    emoji: Optional[str] = None

    additional_properties: Optional[Dict[str, Any]] = None

    condition: Optional[str] = "good"
    is_checkable: Optional[bool] = True
    is_calibrated_tool: Optional[bool] = False
    is_consumable: Optional[bool] = False

    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None

    # Initial location and quantity
    location_id: Optional[str] = None
    quantity: int = 1

    category_ids: Optional[List[str]] = []


class ToolUpdate(SQLModel):
    """Request model for updating a tool"""

    tool_name: Optional[str] = None
    tool_number: Optional[str] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    tool_type: Optional[str] = None

    supplier: Optional[str] = None
    supplier_part_number: Optional[str] = None
    supplier_url: Optional[str] = None
    product_url: Optional[str] = None

    image_url: Optional[str] = None
    emoji: Optional[str] = None

    additional_properties: Optional[Dict[str, Any]] = None

    condition: Optional[str] = None
    maintenance_notes: Optional[str] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None

    is_checkable: Optional[bool] = None
    is_calibrated_tool: Optional[bool] = None
    is_consumable: Optional[bool] = None

    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None

    category_ids: Optional[List[str]] = None


class ToolCheckout(SQLModel):
    """Request model for checking out a tool"""

    user_id: str
    expected_return_date: Optional[datetime] = None
    notes: Optional[str] = None


class ToolReturn(SQLModel):
    """Request model for returning a tool"""

    condition: Optional[str] = None
    notes: Optional[str] = None


class ToolMaintenanceRecord(SQLModel, table=True):
    """
    Tool maintenance and service record tracking.

    Tracks all maintenance, repairs, calibrations, and inspections performed on tools.
    Each record includes who performed the work, when, what was done, and any associated costs.
    """

    __tablename__ = "tool_maintenance_records"

    # === IDENTITY ===
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tool_id: str = Field(
        sa_column=Column(String, ForeignKey("toolmodel.id", ondelete="CASCADE"), index=True),
        description="Tool that was maintained",
    )

    # === MAINTENANCE DETAILS ===
    maintenance_date: datetime = Field(..., description="Date maintenance was performed")
    maintenance_type: str = Field(
        ..., description="Type of maintenance: calibration, repair, inspection, cleaning, other"
    )
    performed_by: str = Field(..., description="Username of user who performed maintenance")
    notes: Optional[str] = Field(default=None, description="Maintenance notes and details")
    next_maintenance_date: Optional[datetime] = Field(default=None, description="Next scheduled maintenance date")
    cost: Optional[float] = Field(default=None, ge=0, description="Maintenance cost")

    # === TIMESTAMPS ===
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # === RELATIONSHIPS ===
    tool: Optional["ToolModel"] = Relationship(
        back_populates="maintenance_records", sa_relationship_kwargs={"lazy": "selectin"}
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method for API responses"""
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "maintenance_date": self.maintenance_date.isoformat() if self.maintenance_date else None,
            "maintenance_type": self.maintenance_type,
            "performed_by": self.performed_by,
            "notes": self.notes,
            "next_maintenance_date": self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            "cost": self.cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Forward reference updates (resolved when all model files are imported)
if False:  # Type checking only - prevents circular imports at runtime
    from .location_models import LocationModel
    from .category_models import CategoryModel
    from .tag_models import TagModel, ToolTagLink
