from typing import Optional, Dict, Any, List, Union
from pydantic import model_validator, field_validator, BaseModel, ConfigDict, field_serializer
from decimal import Decimal
from sqlalchemy import create_engine, ForeignKey, String, or_, cast, UniqueConstraint, Numeric
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import SQLModel, Field, Relationship, Session, select
import uuid
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
from MakerMatrix.models.user_models import UserModel, RoleModel, UserRoleLink
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.models.supplier_config_models import SupplierConfigModel, SupplierCredentialsModel, EnrichmentProfileModel
from MakerMatrix.models.supplier_credentials import SimpleSupplierCredentials
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
    image_url: Optional[str] = None
    emoji: Optional[str] = None

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
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: Optional[str] = None
    image_url: Optional[str] = None
    emoji: Optional[str] = None


# PartModel - Clean core part data only
class PartModel(SQLModel, table=True):
    # === CORE IDENTIFICATION ===
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_name: str = Field(index=True, unique=True)
    part_number: Optional[str] = Field(index=True)
    
    # === PART DESCRIPTION ===
    description: Optional[str] = None
    manufacturer: Optional[str] = Field(default=None, index=True, description="Component manufacturer")
    manufacturer_part_number: Optional[str] = Field(default=None, index=True, description="Manufacturer's part number")
    component_type: Optional[str] = Field(default=None, index=True, description="Part type: resistor, capacitor, screwdriver, etc.")
    
    # === CURRENT INVENTORY ===
    quantity: Optional[int] = None
    location_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String, ForeignKey("locationmodel.id", ondelete="SET NULL"))
    )
    supplier: Optional[str] = None  # Primary/preferred supplier

    location: Optional["LocationModel"] = Relationship(
        back_populates="parts",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # === MEDIA & COMPLIANCE ===
    image_url: Optional[str] = None
    rohs_status: Optional[str] = Field(default=None, description="RoHS compliance status")
    lifecycle_status: Optional[str] = Field(default=None, description="Part lifecycle status (active, obsolete, etc.)")
    
    # === PART-SPECIFIC PROPERTIES ===
    # Examples:
    # Resistor: {"resistance": "10k", "tolerance": "5%", "power": "0.25W", "package": "0603"}
    # Screwdriver: {"type": "phillips", "size": "#2", "shaft_length": "4in", "handle_type": "plastic"}
    # Capacitor: {"capacitance": "100uF", "voltage": "35V", "tolerance": "20%", "package": "SMD,D6.3xL7.7mm"}
    # IC: {"package": "SOIC-8", "pins": 8, "operating_voltage": "3.3V", "interface": "SPI"}
    additional_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Part-specific properties (resistance, capacitance, package, type, size, etc.)"
    )
    
    # === TIMESTAMPS ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # === CORE RELATIONSHIPS ===
    categories: List["CategoryModel"] = Relationship(
        back_populates="parts",
        link_model=PartCategoryLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    # Datasheet files (one-to-many relationship)
    datasheets: List["DatasheetModel"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )
    
    # === METADATA RELATIONSHIPS (optional, lazy-loaded) ===
    # These are only loaded when specifically requested via include parameters
    
    # Enrichment metadata (one-to-one)
    enrichment_metadata: Optional["PartEnrichmentMetadata"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "noload", "uselist": False, "cascade": "all, delete-orphan"}
    )
    
    # Pricing history (one-to-many) - historical pricing data from different suppliers
    pricing_history: List["PartPricingHistory"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan"}
    )
    
    # System metadata (one-to-one) - analytics, import tracking, user flags
    system_metadata: Optional["PartSystemMetadata"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "noload", "uselist": False, "cascade": "all, delete-orphan"}
    )
    
    # === ORDER RELATIONSHIPS (optional, lazy-loaded) ===
    # Order tracking - parts can be linked to multiple order items
    order_items: List["OrderItemModel"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "noload"}
    )
    
    # Order summary information (one-to-one relationship)
    order_summary: Optional["PartOrderSummary"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"lazy": "noload", "uselist": False}
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
            include: List of metadata to include. Options:
                - 'pricing': Include pricing history
                - 'enrichment': Include enrichment metadata  
                - 'system': Include system metadata
                - 'orders': Include order relationships
                - 'all': Include all metadata
        """
        include = include or []
        
        # Always exclude metadata relationships unless specifically requested
        exclude_fields = {
            "location", "enrichment_metadata", "pricing_history", "system_metadata",
            "order_items", "order_summary"
        }
        
        # Datasheets are part of core part data (always included)
        # Categories and location are part of core part data (always included)
        
        # Determine what metadata to include
        include_pricing = 'pricing' in include or 'all' in include
        include_enrichment = 'enrichment' in include or 'all' in include
        include_system = 'system' in include or 'all' in include
        include_orders = 'orders' in include or 'all' in include
        
        # Get base part data (core fields only)
        base_dict = self.model_dump(exclude=exclude_fields)
        
        # Always include categories (core part data)
        base_dict["categories"] = [
            {"id": category.id, "name": category.name, "description": category.description}
            for category in self.categories
        ] if self.categories else []
        
        # Always include location (core part data)
        if hasattr(self, 'location') and self.location is not None:
            base_dict["location"] = {
                "id": self.location.id,
                "name": self.location.name,
                "description": self.location.description,
                "location_type": self.location.location_type
            }
        else:
            base_dict["location"] = None
        
        # Always include datasheets (core part data)
        if hasattr(self, 'datasheets') and self.datasheets:
            base_dict["datasheets"] = [datasheet.to_dict() for datasheet in self.datasheets]
        else:
            base_dict["datasheets"] = []
        
        # === OPTIONAL METADATA ===
        
        # Include pricing metadata if requested
        if include_pricing:
            if hasattr(self, 'pricing_history') and self.pricing_history:
                base_dict["pricing_history"] = [pricing.to_dict() for pricing in self.pricing_history]
                
                # Add current pricing summary for convenience
                current_pricing = [p for p in self.pricing_history if p.is_current]
                if current_pricing:
                    base_dict["current_pricing"] = {
                        supplier_pricing.supplier: {
                            "unit_price": supplier_pricing.unit_price,
                            "currency": supplier_pricing.currency,
                            "stock_quantity": supplier_pricing.stock_quantity,
                            "last_updated": supplier_pricing.created_at.isoformat() if supplier_pricing.created_at else None
                        }
                        for supplier_pricing in current_pricing
                    }
            else:
                base_dict["pricing_history"] = []
        
        # Include enrichment metadata if requested
        if include_enrichment:
            if hasattr(self, 'enrichment_metadata') and self.enrichment_metadata:
                base_dict["enrichment_metadata"] = self.enrichment_metadata.to_dict()
            else:
                base_dict["enrichment_metadata"] = None
        
        # Include system metadata if requested
        if include_system:
            if hasattr(self, 'system_metadata') and self.system_metadata:
                base_dict["system_metadata"] = self.system_metadata.to_dict()
            else:
                base_dict["system_metadata"] = None
        
        # Include order information if requested
        if include_orders:
            # Include order summary information
            if hasattr(self, 'order_summary') and self.order_summary:
                base_dict["order_summary"] = self.order_summary.to_dict()
            else:
                base_dict["order_summary"] = None
            
            # Include order history summary
            if hasattr(self, 'order_items') and self.order_items:
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
        
        # Convert datetime fields to ISO strings for JSON serialization
        if 'created_at' in base_dict and base_dict['created_at']:
            base_dict['created_at'] = base_dict['created_at'].isoformat()
        if 'updated_at' in base_dict and base_dict['updated_at']:
            base_dict['updated_at'] = base_dict['updated_at'].isoformat()
            
        return base_dict
    
    # === UI CONVENIENCE METHODS FOR STANDARDIZED DATA ===
    
    def get_display_name(self) -> str:
        """Get the best display name for UI (manufacturer + part number preferred)"""
        if self.manufacturer and self.manufacturer_part_number:
            return f"{self.manufacturer} {self.manufacturer_part_number}"
        elif self.manufacturer_part_number:
            return self.manufacturer_part_number
        elif self.part_number:
            return self.part_number
        else:
            return self.part_name
    
    def get_standardized_additional_properties(self) -> Dict[str, Any]:
        """Get additional properties structured according to part_data_standards"""
        from MakerMatrix.schemas.part_data_standards import StandardizedAdditionalProperties
        
        if not self.additional_properties:
            return StandardizedAdditionalProperties().to_dict()
        
        try:
            return StandardizedAdditionalProperties.from_dict(self.additional_properties).to_dict()
        except Exception:
            # If data doesn't conform to standard, return as-is
            return self.additional_properties
    
    def get_specifications_dict(self) -> Dict[str, Any]:
        """Get technical specifications as flat dictionary for UI display"""
        std_props = self.get_standardized_additional_properties()
        return std_props.get('specifications', {})
    
    def get_supplier_data(self, supplier_name: str = None) -> Dict[str, Any]:
        """Get supplier-specific data (defaults to primary supplier)"""
        supplier = supplier_name or self.supplier
        if not supplier:
            return {}
        
        std_props = self.get_standardized_additional_properties()
        supplier_data = std_props.get('supplier_data', {})
        return supplier_data.get(supplier.lower(), {})
    
    def has_datasheet(self) -> bool:
        """Check if part has a datasheet available"""
        # Check if we have datasheets in relationships
        if hasattr(self, 'datasheets') and self.datasheets:
            return True
        
        # Check standardized metadata flag
        std_props = self.get_standardized_additional_properties()
        metadata = std_props.get('metadata', {})
        return metadata.get('has_datasheet', False)
    
    def get_datasheet_url(self) -> Optional[str]:
        """Get datasheet URL from standardized supplier data"""
        std_props = self.get_standardized_additional_properties()
        supplier_data = std_props.get('supplier_data', {})
        
        # Check all suppliers for datasheet URL
        for supplier_name, supplier_info in supplier_data.items():
            if isinstance(supplier_info, dict):
                datasheet_url = supplier_info.get('datasheet_url')
                if datasheet_url:
                    return datasheet_url
        
        return None
    
    def has_complete_identification(self) -> bool:
        """Check if part has complete manufacturer identification"""
        return bool(self.manufacturer and self.manufacturer_part_number)
    
    def needs_enrichment(self) -> bool:
        """Determine if part needs enrichment based on data completeness"""
        # Check if enrichment metadata explicitly says we need enrichment
        if hasattr(self, 'enrichment_metadata') and self.enrichment_metadata:
            if self.enrichment_metadata.needs_enrichment:
                return True
        
        # Missing manufacturer identification (needed for enrichment)
        if not self.has_complete_identification():
            return True
        
        # Missing image
        if not self.image_url:
            return True
        
        # Missing datasheets
        if not self.has_datasheet():
            return True
        
        # Sparse additional_properties (enrichment adds specifications)
        if not self.additional_properties or len(self.additional_properties) < 3:
            return True
        
        return False
    
    def update_data_quality_score(self):
        """Calculate and update data quality score in enrichment metadata"""
        # Core fields scoring (60% weight) - removed package since it's in additional_properties now
        core_fields = [
            self.manufacturer,
            self.manufacturer_part_number,
            self.component_type,
            self.description,
            self.image_url
        ]
        core_score = sum(1 for field in core_fields if field is not None) / len(core_fields)
        
        # Pricing data (20% weight) - check if we have current pricing in metadata
        pricing_score = 0.0
        if hasattr(self, 'pricing_history') and self.pricing_history:
            current_pricing = [p for p in self.pricing_history if p.is_current]
            pricing_score = 1.0 if current_pricing else 0.0
        
        # Additional properties/specifications (20% weight)
        additional_props = self.additional_properties or {}
        spec_score = min(len(additional_props) / 5, 1.0) if additional_props else 0.0  # Up to 5 properties for full score
        
        # Overall weighted score
        calculated_score = (core_score * 0.6 + pricing_score * 0.2 + spec_score * 0.2)
        
        # Store score in enrichment metadata (create if it doesn't exist)
        if hasattr(self, 'enrichment_metadata') and self.enrichment_metadata:
            self.enrichment_metadata.data_quality_score = calculated_score
        
        return calculated_score
    
    def get_enrichment_status(self) -> Dict[str, Any]:
        """Get comprehensive enrichment status for UI display"""
        # Pull enrichment data from metadata
        enrichment_meta = getattr(self, 'enrichment_metadata', None)
        
        # Check for current pricing from pricing history
        has_pricing = False
        if hasattr(self, 'pricing_history') and self.pricing_history:
            current_pricing = [p for p in self.pricing_history if p.is_current]
            has_pricing = bool(current_pricing)
        
        return {
            'last_enrichment': enrichment_meta.last_enrichment_date.isoformat() if enrichment_meta and enrichment_meta.last_enrichment_date else None,
            'enrichment_source': enrichment_meta.enrichment_source if enrichment_meta else None,
            'data_quality_score': enrichment_meta.data_quality_score if enrichment_meta else None,
            'enrichment_attempts': enrichment_meta.enrichment_attempts if enrichment_meta else 0,
            'last_error': enrichment_meta.last_error if enrichment_meta else None,
            'needs_enrichment': self.needs_enrichment(),
            'has_datasheet': self.has_datasheet(),
            'has_image': bool(self.image_url),
            'has_pricing': has_pricing,
            'has_additional_props': bool(self.additional_properties and len(self.additional_properties) > 0),
            'has_complete_id': self.has_complete_identification()
        }

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


# ========== PART METADATA TABLES ==========
# These tables store system metadata about parts, separate from core part data

class PartEnrichmentMetadata(SQLModel, table=True):
    """Tracks enrichment attempts and data quality for parts"""
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(
        sa_column=Column(String, ForeignKey("partmodel.id", ondelete="CASCADE"), unique=True)
    )
    
    # Enrichment tracking
    last_enrichment_date: Optional[datetime] = None
    enrichment_source: Optional[str] = None  # Which supplier/service enriched
    data_quality_score: Optional[float] = None  # 0.0-1.0 completeness score
    enrichment_attempts: int = Field(default=0)
    last_error: Optional[str] = None
    
    # Capabilities used during enrichment
    capabilities_used: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    
    # Flags
    needs_enrichment: bool = Field(default=False)
    enrichment_enabled: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    part: Optional["PartModel"] = Relationship(back_populates="enrichment_metadata")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump(exclude={"part"})
        
        # Convert datetime fields to ISO strings
        datetime_fields = ['last_enrichment_date', 'created_at', 'updated_at']
        for field in datetime_fields:
            if field in base_dict and base_dict[field]:
                base_dict[field] = base_dict[field].isoformat()
        
        return base_dict


class PartPricingHistory(SQLModel, table=True):
    """Tracks pricing and stock information over time"""
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(foreign_key="partmodel.id", index=True)
    
    # Pricing information
    supplier: str = Field(index=True)
    unit_price: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 4)))
    currency: str = Field(default="USD", max_length=3)
    stock_quantity: Optional[int] = None
    
    # Pricing tiers (quantity breaks)
    pricing_tiers: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Quantity-based pricing: {qty: price, ...}"
    )
    
    # Source tracking
    source: str = Field(index=True)  # "import", "api", "manual", "enrichment"
    source_reference: Optional[str] = None  # Order number, API call ID, batch ID, etc.
    
    # Validity period
    valid_from: datetime = Field(default_factory=datetime.utcnow, index=True)
    valid_until: Optional[datetime] = None
    is_current: bool = Field(default=True, index=True)  # Latest price for this supplier
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationship
    part: Optional["PartModel"] = Relationship(back_populates="pricing_history")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_serializer('unit_price')
    def serialize_decimal_fields(self, value: Optional[float]) -> Optional[float]:
        """Convert Decimal values to float during serialization"""
        if isinstance(value, Decimal):
            return float(value)
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump(exclude={"part"})
        
        # Convert Decimal fields to float
        if isinstance(base_dict.get('unit_price'), Decimal):
            base_dict['unit_price'] = float(base_dict['unit_price'])
        
        # Convert datetime fields to ISO strings
        datetime_fields = ['valid_from', 'valid_until', 'created_at']
        for field in datetime_fields:
            if field in base_dict and base_dict[field]:
                base_dict[field] = base_dict[field].isoformat()
        
        return base_dict


class PartSystemMetadata(SQLModel, table=True):
    """System-level metadata and analytics for parts"""
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(
        sa_column=Column(String, ForeignKey("partmodel.id", ondelete="CASCADE"), unique=True)
    )
    
    # Analytics and usage tracking
    view_count: int = Field(default=0)
    search_count: int = Field(default=0)
    last_accessed: Optional[datetime] = None
    
    # Import tracking
    import_source: Optional[str] = None  # "csv", "api", "manual", "migration"
    import_reference: Optional[str] = None  # filename, batch ID, migration ID, etc.
    import_date: Optional[datetime] = None
    
    # Quality and organization flags
    needs_review: bool = Field(default=False)
    is_favorite: bool = Field(default=False)
    is_obsolete: bool = Field(default=False)
    
    # User-defined organization
    tags: Optional[List[str]] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )
    notes: Optional[str] = None  # User notes about this part
    
    # System flags
    auto_reorder_enabled: bool = Field(default=False)
    reorder_threshold: Optional[int] = None
    preferred_supplier: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    part: Optional["PartModel"] = Relationship(back_populates="system_metadata")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump(exclude={"part"})
        
        # Convert datetime fields to ISO strings
        datetime_fields = ['last_accessed', 'import_date', 'created_at', 'updated_at']
        for field in datetime_fields:
            if field in base_dict and base_dict[field]:
                base_dict[field] = base_dict[field].isoformat()
        
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
