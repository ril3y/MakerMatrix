"""
Part Metadata Models Module

Contains metadata models for parts including enrichment tracking, pricing history,
and system metadata extracted from models.py.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, String, ForeignKey, JSON, Numeric
from pydantic import field_serializer, ConfigDict


class PartEnrichmentMetadata(SQLModel, table=True):
    """
    Tracks enrichment attempts and data quality for parts.
    
    Stores metadata about automated part enrichment processes including
    success/failure tracking, data quality scoring, and enrichment history.
    """
    
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
    """
    Tracks pricing and stock information over time.
    
    Maintains historical pricing data from multiple suppliers with
    support for quantity breaks, currency tracking, and validity periods.
    """
    
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
    """
    System-level metadata and analytics for parts.
    
    Tracks usage analytics, import history, user organization features,
    and system-level flags for parts management.
    """
    
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


# Forward reference updates (resolved when all model files are imported)
if False:  # Type checking only - prevents circular imports at runtime
    from .part_models import PartModel