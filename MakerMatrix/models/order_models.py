from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy import ForeignKey, String, Numeric
from datetime import datetime
import uuid
from pydantic import ConfigDict, field_serializer
from decimal import Decimal


class OrderModel(SQLModel, table=True):
    """Model for tracking orders from suppliers"""
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    order_number: Optional[str] = Field(index=True)  # Supplier's order number
    supplier: str = Field(index=True)  # DigiKey, LCSC, Mouser, etc.
    order_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Order status
    status: str = Field(default="pending")  # pending, ordered, shipped, delivered, cancelled
    tracking_number: Optional[str] = None
    
    # Financial information
    subtotal: Optional[float] = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    tax: Optional[float] = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    shipping: Optional[float] = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    total: Optional[float] = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    currency: str = Field(default="USD")
    
    # Import information
    import_source: Optional[str] = None  # "CSV Import", "Manual Entry", etc.
    import_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    notes: Optional[str] = None
    order_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    
    # Relationships
    order_items: List["OrderItemModel"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_serializer('subtotal', 'tax', 'shipping', 'total')
    def serialize_decimal_fields(self, value: Optional[float]) -> Optional[float]:
        """Convert Decimal values to float during serialization"""
        if isinstance(value, Decimal):
            return float(value)
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump()
        
        # Manually convert Decimal fields to float to prevent warnings
        for field in ['subtotal', 'tax', 'shipping', 'total']:
            if field in base_dict and isinstance(base_dict[field], Decimal):
                base_dict[field] = float(base_dict[field])
        
        # Include order items
        base_dict["order_items"] = [item.to_dict() for item in self.order_items] if self.order_items else []
        return base_dict


class OrderItemModel(SQLModel, table=True):
    """Model for individual items within an order"""
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    order_id: str = Field(foreign_key="ordermodel.id")
    part_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String, ForeignKey("partmodel.id", ondelete="SET NULL"))
    )
    
    # Part information (stored even if part doesn't exist in inventory yet)
    supplier_part_number: str = Field(index=True)
    manufacturer_part_number: Optional[str] = Field(index=True)
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    
    # Order details
    quantity_ordered: int
    quantity_received: int = Field(default=0)
    unit_price: Optional[float] = Field(default=0.0, sa_column=Column(Numeric(10, 4)))
    extended_price: Optional[float] = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    
    # Additional part properties from CSV
    package: Optional[str] = None
    customer_reference: Optional[str] = None
    
    # Status tracking
    status: str = Field(default="ordered")  # ordered, backordered, shipped, received, cancelled
    expected_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    
    # Additional metadata
    properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    
    # Relationships
    order: Optional[OrderModel] = Relationship(back_populates="order_items")
    part: Optional["PartModel"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_serializer('unit_price', 'extended_price')
    def serialize_decimal_fields(self, value: Optional[float]) -> Optional[float]:
        """Convert Decimal values to float during serialization"""
        if isinstance(value, Decimal):
            return float(value)
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump(exclude={"order", "part"})
        
        # Manually convert Decimal fields to float to prevent warnings
        for field in ['unit_price', 'extended_price']:
            if field in base_dict and isinstance(base_dict[field], Decimal):
                base_dict[field] = float(base_dict[field])
        
        # Include basic part info if linked
        if self.part:
            base_dict["part"] = {
                "id": self.part.id,
                "part_name": self.part.part_name,
                "current_quantity": self.part.quantity
            }
        return base_dict


# Link table for many-to-many relationship between parts and orders
class PartOrderLink(SQLModel, table=True):
    """Link table for parts that have been ordered multiple times"""
    
    part_id: str = Field(foreign_key="partmodel.id", primary_key=True)
    order_item_id: str = Field(foreign_key="orderitemmodel.id", primary_key=True)
    
    # Track the specific relationship
    quantity_from_order: int  # How much of current inventory came from this order
    date_added: datetime = Field(default_factory=datetime.utcnow)


# Request/Response models for API
class CreateOrderRequest(SQLModel):
    order_number: Optional[str] = None
    supplier: str
    order_date: Optional[datetime] = None
    status: str = "pending"
    tracking_number: Optional[str] = None
    subtotal: Optional[float] = 0.0
    tax: Optional[float] = 0.0
    shipping: Optional[float] = 0.0
    total: Optional[float] = 0.0
    currency: str = "USD"
    notes: Optional[str] = None
    import_source: Optional[str] = None
    order_metadata: Optional[Dict[str, Any]] = None


class CreateOrderItemRequest(SQLModel):
    supplier_part_number: str
    manufacturer_part_number: Optional[str] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity_ordered: int
    unit_price: Optional[float] = 0.0
    extended_price: Optional[float] = 0.0
    package: Optional[str] = None
    customer_reference: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class UpdateOrderRequest(SQLModel):
    order_number: Optional[str] = None
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class OrderSummary(SQLModel):
    """Summary model for order statistics"""
    
    total_orders: int
    total_value: float
    pending_orders: int
    delivered_orders: int
    orders_by_supplier: Dict[str, int]
    recent_orders: List[Dict[str, Any]]