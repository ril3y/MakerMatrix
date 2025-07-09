from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from MakerMatrix.database.db import get_session
from MakerMatrix.models.order_models import (
    OrderModel, OrderItemModel, PartOrderLink,
    CreateOrderRequest, CreateOrderItemRequest, UpdateOrderRequest
)
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.repositories.order_repository import OrderRepository, OrderItemRepository
from MakerMatrix.services.base_service import BaseService, ServiceResponse
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


class OrderService(BaseService):
    """
    Service for managing orders and order items with consolidated session management.
    
    This migration eliminates 8+ instances of duplicated session management code.
    """

    def __init__(self):
        super().__init__()
        self.entity_name = "Order"
        self.order_repo = OrderRepository()
        self.order_item_repo = OrderItemRepository()

    async def create_order(self, order_data: CreateOrderRequest) -> ServiceResponse[OrderModel]:
        """
        Create a new order.
        
        CONSOLIDATED SESSION MANAGEMENT: This method previously had 15+ lines
        of manual session/transaction management. Now uses BaseService patterns.
        """
        try:
            self.log_operation("create", self.entity_name, order_data.order_number)
            
            with self.get_session() as session:
                # Create order
                order = OrderModel(
                    order_number=order_data.order_number,
                    supplier=order_data.supplier,
                    order_date=order_data.order_date,
                    status=order_data.status,
                    tracking_number=order_data.tracking_number,
                    subtotal=order_data.subtotal,
                    tax=order_data.tax,
                    shipping=order_data.shipping,
                    total=order_data.total,
                    currency=order_data.currency,
                    notes=order_data.notes,
                    import_source=order_data.import_source,
                    order_metadata=order_data.order_metadata or {}
                )
                
                created_order = self.order_repo.create_order(session, order)
                
                return self.success_response(
                    f"{self.entity_name} {created_order.order_number} created successfully for supplier {created_order.supplier}",
                    created_order
                )
                
        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    async def get_order(self, order_id: str) -> ServiceResponse[OrderModel]:
        """
        Get order by ID.
        
        CONSOLIDATED SESSION MANAGEMENT: Eliminates manual session management.
        """
        try:
            self.log_operation("get", self.entity_name, order_id)
            
            with self.get_session() as session:
                order = self.order_repo.get_by_id(session, order_id)
                
                if not order:
                    return self.error_response(f"{self.entity_name} with ID {order_id} not found")
                
                return self.success_response(
                    f"{self.entity_name} retrieved successfully",
                    order
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name}")

    async def get_orders(self, 
                        supplier: Optional[str] = None,
                        status: Optional[str] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[OrderModel]:
        """Get orders with optional filtering"""
        with self.get_session() as session:
            return self.order_repo.get_orders_with_filters(session, supplier, status, limit, offset)

    async def update_order(self, order_id: str, update_data: UpdateOrderRequest) -> OrderModel:
        """Update an existing order"""
        with self.get_session() as session:
            order = self.order_repo.get_by_id(session, order_id)
            
            if not order:
                raise ResourceNotFoundError(f"Order with id {order_id} not found")
            
            # Update fields that are provided
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(order, field, value)
            
            return self.order_repo.update_order(session, order)

    async def add_order_item(self, order_id: str, item_data: CreateOrderItemRequest) -> OrderItemModel:
        """Add an item to an order"""
        with self.get_session() as session:
            # Verify order exists
            order = self.order_repo.get_by_id(session, order_id)
            
            if not order:
                raise ResourceNotFoundError(f"Order with id {order_id} not found")
            
            # Create order item
            order_item = OrderItemModel(
                order_id=order_id,
                supplier_part_number=item_data.supplier_part_number,
                manufacturer_part_number=item_data.manufacturer_part_number,
                description=item_data.description,
                manufacturer=item_data.manufacturer,
                quantity_ordered=item_data.quantity_ordered,
                quantity_received=item_data.quantity_ordered,  # Default to ordered quantity
                unit_price=item_data.unit_price,
                extended_price=item_data.extended_price,
                package=item_data.package,
                customer_reference=item_data.customer_reference,
                properties=item_data.properties or {}
            )
            
            return self.order_item_repo.create_order_item(session, order_item)

    async def link_order_item_to_part(self, order_item_id: str, part_id: str) -> None:
        """Link an order item to a part in inventory"""
        with self.get_session() as session:
            self.order_item_repo.link_order_item_to_part(session, order_item_id, part_id)

    async def calculate_order_totals(self, order_id: str) -> OrderModel:
        """Recalculate and update order totals based on order items"""
        with self.get_session() as session:
            # Get order
            order = self.order_repo.get_by_id(session, order_id)
            
            if not order:
                raise ResourceNotFoundError(f"Order with id {order_id} not found")
            
            # Calculate subtotal from order items
            subtotal = self.order_item_repo.calculate_order_totals(session, order_id)
            
            # Update order totals (keep existing tax/shipping if set, convert to float)
            order.subtotal = subtotal
            if order.tax is None:
                order.tax = 0.0
            if order.shipping is None:
                order.shipping = 0.0
            
            # Convert Decimal to float to avoid type mixing
            tax_float = float(order.tax) if order.tax is not None else 0.0
            shipping_float = float(order.shipping) if order.shipping is not None else 0.0
            order.total = subtotal + tax_float + shipping_float
            
            updated_order = self.order_repo.update_order(session, order)
            
            logger.info(f"Updated totals for order {order_id}: subtotal=${subtotal:.2f}, total=${updated_order.total:.2f}")
            return updated_order

    async def get_order_items(self, order_id: str) -> List[OrderItemModel]:
        """Get all items for an order"""
        with self.get_session() as session:
            return self.order_item_repo.get_order_items_by_order(session, order_id)

    async def get_orders_by_supplier(self, supplier: str) -> List[OrderModel]:
        """Get all orders from a specific supplier"""
        return await self.get_orders(supplier=supplier)

    async def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        with self.get_session() as session:
            return self.order_repo.get_order_statistics(session)


# Singleton instance
order_service = OrderService()