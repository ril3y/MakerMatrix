from typing import Optional, Dict, Any, List, Union
from pydantic import model_validator, field_validator, BaseModel, ConfigDict, field_serializer
from decimal import Decimal
from sqlalchemy import create_engine, ForeignKey, String, or_, cast, UniqueConstraint, Numeric
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import SQLModel, Field, Relationship, Session, select
import uuid
from pydantic import Field as PydanticField
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
from MakerMatrix.models.user_models import UserModel, RoleModel, UserRoleLink
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.models.supplier_config_models import SupplierConfigModel, SupplierCredentialsModel, EnrichmentProfileModel
from MakerMatrix.models.rate_limiting_models import (
    SupplierRateLimitModel, 
    SupplierUsageTrackingModel, 
    SupplierUsageSummaryModel
)

# Association table to link PartModel and CategoryModel
# Association table to link PartModel and CategoryModel
class PartCategoryLink(SQLModel, table=True):
    part_id: str = Field(foreign_key="partmodel.id", primary_key=True)
    category_id: str = Field(foreign_key="categorymodel.id", primary_key=True)


# Datasheet model for managing PDF files
class DatasheetModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(foreign_key="partmodel.id")
    
    # File information
    file_uuid: str = Field(unique=True)  # UUID used for filename
    original_filename: Optional[str] = None
    file_extension: str = Field(default=".pdf")
    file_size: Optional[int] = None
    
    # Source information
    source_url: Optional[str] = None
    supplier: Optional[str] = None
    manufacturer: Optional[str] = None
    
    # Metadata
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Download status
    is_downloaded: bool = Field(default=False)
    download_error: Optional[str] = None
    
    # Relationship back to part
    part: Optional["PartModel"] = Relationship(back_populates="datasheets")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @property
    def filename(self) -> str:
        """Generate the actual filename used on disk"""
        return f"{self.file_uuid}{self.file_extension}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump(exclude={"part"})
        base_dict["filename"] = self.filename
        if self.created_at:
            base_dict["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            base_dict["updated_at"] = self.updated_at.isoformat()
        return base_dict


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    children: Optional[List[str]] = None  # List of child category IDs


# CategoryModel
class CategoryModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    parts: List["PartModel"] = Relationship(back_populates="categories", link_model=PartCategoryLink, sa_relationship_kwargs={"lazy": "selectin"})

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for CategoryModel """
        return self.model_dump(exclude={"parts"})


class LocationQueryModel(SQLModel):
    id: Optional[str] = None
    name: Optional[str] = None


class LocationModel(SQLModel, table=True):

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = Field(index=True)
    description: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, foreign_key="locationmodel.id")
    location_type: str = Field(default="standard")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Add SQLAlchemy table constraints
    __table_args__ = (
        UniqueConstraint('name', 'parent_id', name='uix_location_name_parent'),
    )

    parent: Optional["LocationModel"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "LocationModel.id"}
    )
    children: List["LocationModel"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    parts: List["PartModel"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={"passive_deletes": True}
    )


    @classmethod
    def get_with_children(cls, session: Session, location_id: str) -> Optional["LocationModel"]:
        """ Custom method to get a location with its children """
        statement = select(cls).options(selectinload(cls.children)).where(cls.id == location_id)
        return session.exec(statement).first()

    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for LocationModel """
        # Start with basic fields only
        base_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "location_type": self.location_type
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
                        "location_type": child.location_type
                    }
                    base_dict["children"].append(child_dict)
        except Exception:
            # If children can't be accessed, skip them
            pass
        
        return base_dict


class LocationUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: Optional[str] = None


# PartModel
class PartModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_number: Optional[str] = Field(index=True)
    part_name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    quantity: Optional[int]
    supplier: Optional[str] = None

    location_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String, ForeignKey("locationmodel.id", ondelete="SET NULL")
        )
    )

    location: Optional["LocationModel"] = Relationship(
        back_populates="parts",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    image_url: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )

    categories: List["CategoryModel"] = Relationship(
        back_populates="parts",
        link_model=PartCategoryLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    # Order tracking - parts can be linked to multiple order items
    order_items: List["OrderItemModel"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    # Order summary information (one-to-one relationship)
    order_summary: Optional["PartOrderSummary"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "selectin", "uselist": False}
    )
    
    # Datasheet files (one-to-many relationship)
    datasheets: List["DatasheetModel"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "PartModel":
        """
        Create a PartModel from a JSON dictionary.
        If the JSON includes a list of categories (as dicts), they will be converted
        to CategoryModel instances.
        """
        data_copy = data.copy()
        if "categories" in data_copy and isinstance(data_copy["categories"], list):
            data_copy["categories"] = [
                CategoryModel(**item) if isinstance(item, dict) else item
                for item in data_copy["categories"]
            ]
        return cls(**data_copy)

    @classmethod
    def search_properties(cls, session: Session, search_term: str):
        """Search through additional_properties and description"""
        return session.query(cls).filter(
            or_(
                cls.description.ilike(f'%{search_term}%'),
                cls.additional_properties.cast(String).ilike(f'%{search_term}%')
            )
        ).all()

    def to_dict(self, include: List[str] = None) -> Dict[str, Any]:
        """ 
        Custom serialization method for PartModel 
        
        Args:
            include: List of additional data to include. Options: 'orders', 'datasheets', 'all'
        """
        include = include or []
        exclude_fields = {"location", "order_items", "order_summary", "datasheets"}
        
        # Determine what to include based on parameters
        include_orders = 'orders' in include or 'all' in include
        include_datasheets = 'datasheets' in include or 'all' in include
        
        # Adjust exclusions based on what we want to include
        if include_orders:
            exclude_fields.discard("order_items")
            exclude_fields.discard("order_summary")
        if include_datasheets:
            exclude_fields.discard("datasheets")
            
        base_dict = self.model_dump(exclude=exclude_fields)
        # Always include categories, even if empty
        base_dict["categories"] = [
            {"id": category.id, "name": category.name, "description": category.description}
            for category in self.categories
        ] if self.categories else []
        
        # Include location information if available
        if hasattr(self, 'location') and self.location is not None:
            base_dict["location"] = {
                "id": self.location.id,
                "name": self.location.name,
                "description": self.location.description,
                "location_type": self.location.location_type
            }
        else:
            base_dict["location"] = None
        
        # Conditionally include order information
        if include_orders:
            # Include order summary information
            if self.order_summary:
                base_dict["order_summary"] = self.order_summary.to_dict()
            else:
                base_dict["order_summary"] = None
            
            # Include order history summary
            if self.order_items:
                base_dict["order_history"] = [
                    {
                        "order_id": item.order_id,
                        "supplier": item.order.supplier if item.order else None,
                        "order_date": item.order.order_date.isoformat() if item.order and item.order.order_date else None,
                        "quantity_ordered": item.quantity_ordered,
                        "quantity_received": item.quantity_received,
                        "unit_price": float(item.unit_price) if item.unit_price else 0.0,
                        "status": item.status
                    }
                    for item in self.order_items
                ]
            else:
                base_dict["order_history"] = []
        
        # Conditionally include datasheet information  
        if include_datasheets:
            if hasattr(self, 'datasheets') and self.datasheets:
                base_dict["datasheets"] = [datasheet.to_dict() for datasheet in self.datasheets]
            else:
                base_dict["datasheets"] = []
        
        return base_dict

    @model_validator(mode='before')
    @classmethod
    def check_unique_part_name(cls, values):
        # Remove the circular import and validation since it's handled in the service layer
        return values


class PartOrderSummary(SQLModel, table=True):
    """Summary table for part order information"""
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(
        sa_column=Column(String, ForeignKey("partmodel.id", ondelete="CASCADE"), unique=True)
    )  # One-to-one relationship with cascade delete
    
    # Order summary information
    last_ordered_date: Optional[datetime] = None
    last_ordered_price: Optional[float] = Field(default=0.0, sa_column=Column(Numeric(10, 4)))
    last_order_number: Optional[str] = None
    supplier_url: Optional[str] = None
    total_orders: int = Field(default=0)
    
    # Pricing history
    lowest_price: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 4)))
    highest_price: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 4)))
    average_price: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 4)))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    part: Optional[PartModel] = Relationship(back_populates="order_summary")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_serializer('last_ordered_price', 'lowest_price', 'highest_price', 'average_price')
    def serialize_decimal_fields(self, value: Optional[float]) -> Optional[float]:
        """Convert Decimal values to float during serialization"""
        if isinstance(value, Decimal):
            return float(value)
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump(exclude={"part"})
        
        # Manually convert Decimal fields to float to prevent warnings
        for field in ['last_ordered_price', 'lowest_price', 'highest_price', 'average_price']:
            if field in base_dict and isinstance(base_dict[field], Decimal):
                base_dict[field] = float(base_dict[field])
        
        # Convert datetime fields to ISO strings
        if self.last_ordered_date:
            base_dict["last_ordered_date"] = self.last_ordered_date.isoformat()
        if self.created_at:
            base_dict["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            base_dict["updated_at"] = self.updated_at.isoformat()
        return base_dict


# Additional models for operations
class UpdateQuantityRequest(SQLModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None
    new_quantity: int

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode='before')
    @classmethod
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")
        return values


class GenericPartQuery(SQLModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode='before')
    @classmethod
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")
        return values


class AdvancedPartSearch(SQLModel):
    search_term: Optional[str] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    category_names: Optional[List[str]] = None
    location_id: Optional[str] = None
    supplier: Optional[str] = None
    sort_by: Optional[str] = None  # "part_name", "part_number", "quantity", "location"
    sort_order: Optional[str] = "asc"  # "asc" or "desc"
    page: int = 1
    page_size: int = 10

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        if v and v not in ["part_name", "part_number", "quantity", "location"]:
            raise ValueError("sort_by must be one of: part_name, part_number, quantity, location")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v not in ["asc", "desc"]:
            raise ValueError("sort_order must be one of: asc, desc")
        return v

# Activity log model for tracking user actions
class ActivityLogModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # What happened
    action: str = Field(index=True)  # "created", "updated", "deleted", "printed", etc.
    entity_type: str = Field(index=True)  # "part", "printer", "label", "location", etc.
    entity_id: Optional[str] = Field(index=True)  # ID of the entity acted upon
    entity_name: Optional[str] = None  # Human-readable name (part name, printer name, etc.)
    
    # Who did it
    user_id: Optional[str] = Field(foreign_key="usermodel.id", index=True)
    username: Optional[str] = None  # Cached for performance
    
    # When and details
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump()
        if self.timestamp:
            base_dict["timestamp"] = self.timestamp.isoformat()
        return base_dict


# Printer model for persistence
class PrinterModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    printer_id: str = Field(unique=True, index=True)  # The internal printer ID
    name: str = Field(index=True)
    driver_type: str  # e.g., "brother_ql", "mock"
    model: str  # e.g., "QL-800", "QL-820NWB"
    backend: str  # e.g., "network", "usb", "serial"
    identifier: str  # e.g., "tcp://192.168.1.71", "/dev/usb/lp0"
    dpi: int = Field(default=300)
    scaling_factor: float = Field(default=1.0)
    
    # Status and metadata
    is_active: bool = Field(default=True)
    last_seen: Optional[datetime] = None
    
    # Configuration JSON for driver-specific settings
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump()
        if self.created_at:
            base_dict["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            base_dict["updated_at"] = self.updated_at.isoformat()
        if self.last_seen:
            base_dict["last_seen"] = self.last_seen.isoformat()
        return base_dict


# Create an engine for SQLite
sqlite_file_name = "makers_matrix.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(
    sqlite_url, 
    echo=False,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600,
    connect_args={"check_same_thread": False}
)


# Create tables if they don't exist
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
