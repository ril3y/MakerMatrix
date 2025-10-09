"""
Part Models Module

Contains PartModel and related part-specific models extracted from models.py.
This module focuses specifically on electronic part inventory management.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Session, Column, String, ForeignKey, JSON, select
from MakerMatrix.models.project_models import PartProjectLink
from sqlalchemy import or_, UniqueConstraint, Numeric
from pydantic import field_serializer, model_validator, ConfigDict


class PartCategoryLink(SQLModel, table=True):
    """Link table for many-to-many relationship between parts and categories"""
    part_id: str = Field(foreign_key="partmodel.id", primary_key=True)
    category_id: str = Field(foreign_key="categorymodel.id", primary_key=True)


class DatasheetModel(SQLModel, table=True):
    """Model for storing datasheet file information"""
    __tablename__ = "datasheets"
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(foreign_key="partmodel.id", index=True)
    
    # File information
    filename: str = Field(description="Original filename of the datasheet")
    file_path: str = Field(description="Path to the stored datasheet file")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    file_type: str = Field(default="pdf", description="File type (pdf, doc, etc.)")
    
    # Metadata
    title: Optional[str] = Field(default=None, description="Datasheet title")
    supplier: Optional[str] = Field(default=None, description="Supplier that provided the datasheet")
    url: Optional[str] = Field(default=None, description="Original URL of the datasheet")
    download_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    is_primary: bool = Field(default=False, description="Whether this is the primary datasheet")
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    part: Optional["PartModel"] = Relationship(back_populates="datasheets")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        base_dict = self.model_dump(exclude={"part"})
        # Convert datetime fields to ISO strings
        if self.download_date:
            base_dict["download_date"] = self.download_date.isoformat()
        if self.created_at:
            base_dict["created_at"] = self.created_at.isoformat()
        return base_dict


class PartModel(SQLModel, table=True):
    """
    Main model for electronic parts/components.
    
    This model represents individual electronic parts in inventory with support for:
    - Core identification and description
    - Inventory tracking (quantity, location)
    - Supplier information and sourcing
    - Media and compliance data
    - Part-specific properties (resistance, capacitance, etc.)
    - Rich metadata relationships for enrichment, pricing, and orders
    """
    
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
    # NOTE: Quantity and location are managed through allocations (PartLocationAllocation)
    # Use part.total_quantity and part.primary_location computed properties instead
    supplier: Optional[str] = None  # Primary/preferred supplier
    supplier_part_number: Optional[str] = Field(default=None, index=True, description="Supplier's part number for API calls (e.g., LCSC: C25804, DigiKey: 296-1234-ND)")
    supplier_url: Optional[str] = None  # URL to supplier homepage (e.g., https://boltdepot.com)
    product_url: Optional[str] = None  # URL to specific product page (e.g., https://boltdepot.com/Product-Details?product=15294)

    # === MEDIA ===
    image_url: Optional[str] = None
    emoji: Optional[str] = Field(default=None, max_length=50, description="Unicode emoji character or shortcode to use as visual icon (e.g., '🔩' or ':screw:')")
    
    # === PART-SPECIFIC PROPERTIES ===
    # Examples:
    # Resistor: {"resistance": "10k", "tolerance": "5%", "power": "0.25W", "package": "0603"}
    # Screwdriver: {"type": "phillips", "size": "#2", "shaft_length": "4in", "handle_type": "plastic"}
    # Capacitor: {"capacitance": "100uF", "voltage": "35V", "tolerance": "20%", "package": "SMD,D6.3xL7.7mm"}
    # IC: {"package": "SOIC-8", "pins": 8, "operating_voltage": "3.3V", "interface": "SPI"}
    additional_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Part-specific properties as FLAT key-value pairs only (resistance, capacitance, package, type, size, etc.)"
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

    # Projects (many-to-many relationship through link table)
    projects: List["ProjectModel"] = Relationship(
        back_populates="parts",
        link_model=PartProjectLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # === MULTI-LOCATION ALLOCATIONS (NEW) ===
    allocations: List["PartLocationAllocation"] = Relationship(
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

    # === COMPUTED PROPERTIES FOR MULTI-LOCATION SUPPORT ===

    @property
    def total_quantity(self) -> int:
        """
        Calculate total quantity across all location allocations.

        Returns 0 if no allocations exist.
        """
        if not hasattr(self, 'allocations') or not self.allocations:
            return 0

        return sum(alloc.quantity_at_location for alloc in self.allocations)

    @property
    def primary_location(self) -> Optional["LocationModel"]:
        """
        Get the primary storage location.

        Returns the location marked as primary storage, or the first allocation if none marked.
        Returns None if no allocations exist.
        """
        if not hasattr(self, 'allocations') or not self.allocations:
            return None

        # Find primary storage allocation
        primary_alloc = next(
            (alloc for alloc in self.allocations if alloc.is_primary_storage),
            None
        )

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
                "total_quantity": 4000,
                "location_count": 2,
                "primary_location": {...},
                "allocations": [...]
            }
        """
        if not hasattr(self, 'allocations') or not self.allocations:
            return {
                "total_quantity": 0,
                "location_count": 0,
                "primary_location": None,
                "allocations": []
            }

        return {
            "total_quantity": self.total_quantity,
            "location_count": len(self.allocations),
            "primary_location": self.primary_location.to_dict() if self.primary_location else None,
            "allocations": [alloc.to_dict() for alloc in self.allocations]
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "PartModel":
        """
        Create a PartModel from a JSON dictionary.
        If the JSON includes a list of categories (as dicts), they will be converted
        to CategoryModel instances.
        """
        data_copy = data.copy()
        if "categories" in data_copy and isinstance(data_copy["categories"], list):
            # Import here to avoid circular imports
            from .category_models import CategoryModel
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
            "enrichment_metadata", "pricing_history", "system_metadata",
            "order_items", "order_summary", "allocations"  # Allocations included separately if needed
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

        # Always include projects (core part data)
        base_dict["projects"] = [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "image_url": project.image_url,
                "parts_count": project.parts_count,
                "estimated_cost": project.estimated_cost,
                "links": project.links
            }
            for project in self.projects
        ] if self.projects else []

        # Always include primary location from allocations (core part data)
        primary_loc = self.primary_location
        if primary_loc:
            # Use LocationModel's to_dict() to include all fields (container slots, parent, etc.)
            base_dict["location"] = primary_loc.to_dict()
            # Include location_id for frontend compatibility
            base_dict["location_id"] = primary_loc.id
        else:
            base_dict["location"] = None
            base_dict["location_id"] = None

        # Include total quantity from allocations
        base_dict["quantity"] = self.total_quantity
        
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
    """Request model for updating part quantities"""
    part_id: Optional[str] = None
    part_name: Optional[str] = None
    part_number: Optional[str] = None
    quantity: int
    operation: str = "set"  # "add", "subtract", "set"
    location_id: Optional[str] = None
    notes: Optional[str] = None


class GenericPartQuery(SQLModel):
    """Generic query model for finding parts by various criteria"""
    part_id: Optional[str] = None
    part_name: Optional[str] = None
    part_number: Optional[str] = None
    supplier_part_number: Optional[str] = None
    manufacturer_part_number: Optional[str] = None


class AdvancedPartSearch(SQLModel):
    """Advanced search model for parts with multiple criteria"""
    search_term: Optional[str] = None
    manufacturer: Optional[str] = None
    component_type: Optional[str] = None
    supplier: Optional[str] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    category_names: Optional[List[str]] = None
    location_id: Optional[str] = None
    has_datasheet: Optional[bool] = None
    has_image: Optional[bool] = None
    needs_enrichment: Optional[bool] = None
    sort_by: str = "part_name"  # part_name, part_number, quantity, manufacturer, created_at
    sort_order: str = "asc"  # asc, desc
    page: int = 1
    page_size: int = 20


# Forward reference updates (these will be resolved when all model files are imported)
# These imports will be added to the main models __init__.py
if False:  # Type checking only - prevents circular imports at runtime
    from .location_models import LocationModel
    from .category_models import CategoryModel
    from .order_models import OrderItemModel
    from .part_metadata_models import PartSystemMetadata
    from .part_allocation_models import PartLocationAllocation