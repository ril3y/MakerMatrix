from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from MakerMatrix.database.db import get_session
from MakerMatrix.models.order_models import (
    OrderModel, OrderItemModel, PartOrderLink,
    CreateOrderRequest, CreateOrderItemRequest, UpdateOrderRequest
)
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


class OrderService:
    """Service for managing orders and order items"""

    def __init__(self):
        pass

    async def create_order(self, order_data: CreateOrderRequest) -> OrderModel:
        """Create a new order"""
        session = next(get_session())
        try:
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
            
            session.add(order)
            session.commit()
            session.refresh(order)
            
            logger.info(f"Created order {order.id} for supplier {order.supplier}")
            return order
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create order: {e}")
            raise
        finally:
            session.close()

    async def get_order(self, order_id: str) -> OrderModel:
        """Get order by ID"""
        session = next(get_session())
        try:
            statement = select(OrderModel).where(OrderModel.id == order_id)
            order = session.exec(statement).first()
            
            if not order:
                raise ResourceNotFoundError(f"Order with id {order_id} not found")
            
            return order
            
        finally:
            session.close()

    async def get_orders(self, 
                        supplier: Optional[str] = None,
                        status: Optional[str] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[OrderModel]:
        """Get orders with optional filtering"""
        session = next(get_session())
        try:
            statement = select(OrderModel)
            
            if supplier:
                statement = statement.where(OrderModel.supplier == supplier)
            if status:
                statement = statement.where(OrderModel.status == status)
                
            statement = statement.offset(offset).limit(limit).order_by(OrderModel.order_date.desc())
            
            orders = session.exec(statement).all()
            return orders
            
        finally:
            session.close()

    async def update_order(self, order_id: str, update_data: UpdateOrderRequest) -> OrderModel:
        """Update an existing order"""
        session = next(get_session())
        try:
            statement = select(OrderModel).where(OrderModel.id == order_id)
            order = session.exec(statement).first()
            
            if not order:
                raise ResourceNotFoundError(f"Order with id {order_id} not found")
            
            # Update fields that are provided
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(order, field, value)
            
            session.add(order)
            session.commit()
            session.refresh(order)
            
            logger.info(f"Updated order {order_id}")
            return order
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update order {order_id}: {e}")
            raise
        finally:
            session.close()

    async def add_order_item(self, order_id: str, item_data: CreateOrderItemRequest) -> OrderItemModel:
        """Add an item to an order"""
        session = next(get_session())
        try:
            # Verify order exists
            order_statement = select(OrderModel).where(OrderModel.id == order_id)
            order = session.exec(order_statement).first()
            
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
            
            session.add(order_item)
            session.commit()
            session.refresh(order_item)
            
            logger.info(f"Added item {order_item.id} to order {order_id}")
            return order_item
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add item to order {order_id}: {e}")
            raise
        finally:
            session.close()

    async def link_order_item_to_part(self, order_item_id: str, part_id: str) -> None:
        """Link an order item to a part in inventory"""
        session = next(get_session())
        try:
            # Get the order item to check quantity
            item_statement = select(OrderItemModel).where(OrderItemModel.id == order_item_id)
            order_item = session.exec(item_statement).first()
            
            if not order_item:
                raise ResourceNotFoundError(f"Order item with id {order_item_id} not found")
            
            # Update the order item to reference the part
            order_item.part_id = part_id
            session.add(order_item)
            
            # Create link record for tracking quantity relationships
            link = PartOrderLink(
                part_id=part_id,
                order_item_id=order_item_id,
                quantity_from_order=order_item.quantity_received
            )
            
            session.add(link)
            session.commit()
            
            logger.info(f"Linked order item {order_item_id} to part {part_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to link order item {order_item_id} to part {part_id}: {e}")
            raise
        finally:
            session.close()

    async def calculate_order_totals(self, order_id: str) -> OrderModel:
        """Recalculate and update order totals based on order items"""
        session = next(get_session())
        try:
            # Get order with items
            order_statement = select(OrderModel).where(OrderModel.id == order_id)
            order = session.exec(order_statement).first()
            
            if not order:
                raise ResourceNotFoundError(f"Order with id {order_id} not found")
            
            # Calculate totals from order items
            items_statement = select(OrderItemModel).where(OrderItemModel.order_id == order_id)
            items = session.exec(items_statement).all()
            
            subtotal = sum(float(item.extended_price or 0) for item in items)
            
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
            
            session.add(order)
            session.commit()
            session.refresh(order)
            
            logger.info(f"Updated totals for order {order_id}: subtotal=${subtotal:.2f}, total=${order.total:.2f}")
            return order
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to calculate totals for order {order_id}: {e}")
            raise
        finally:
            session.close()

    async def get_order_items(self, order_id: str) -> List[OrderItemModel]:
        """Get all items for an order"""
        session = next(get_session())
        try:
            statement = select(OrderItemModel).where(OrderItemModel.order_id == order_id)
            items = session.exec(statement).all()
            return items
            
        finally:
            session.close()

    async def get_orders_by_supplier(self, supplier: str) -> List[OrderModel]:
        """Get all orders from a specific supplier"""
        return await self.get_orders(supplier=supplier)

    async def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        session = next(get_session())
        try:
            # Total orders
            total_orders = session.exec(select(func.count(OrderModel.id))).first()
            
            # Total value
            total_value = session.exec(select(func.sum(OrderModel.total))).first() or 0
            
            # Orders by status
            pending_orders = session.exec(
                select(func.count(OrderModel.id)).where(OrderModel.status == "pending")
            ).first()
            
            delivered_orders = session.exec(
                select(func.count(OrderModel.id)).where(OrderModel.status == "delivered")
            ).first()
            
            # Orders by supplier
            supplier_counts = session.exec(
                select(OrderModel.supplier, func.count(OrderModel.id))
                .group_by(OrderModel.supplier)
            ).all()
            
            orders_by_supplier = {supplier: count for supplier, count in supplier_counts}
            
            # Recent orders
            recent_orders_stmt = select(OrderModel).order_by(OrderModel.order_date.desc()).limit(5)
            recent_orders = session.exec(recent_orders_stmt).all()
            
            return {
                "total_orders": total_orders,
                "total_value": float(total_value),
                "pending_orders": pending_orders,
                "delivered_orders": delivered_orders,
                "orders_by_supplier": orders_by_supplier,
                "recent_orders": [
                    {
                        "id": order.id,
                        "order_number": order.order_number,
                        "supplier": order.supplier,
                        "total": float(order.total),
                        "status": order.status,
                        "order_date": order.order_date.isoformat() if order.order_date else None
                    }
                    for order in recent_orders
                ]
            }
            
        finally:
            session.close()


# Singleton instance
order_service = OrderService()