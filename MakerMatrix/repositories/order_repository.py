"""
Order Repository

Repository for order database operations.
Follows the established repository pattern where ONLY repositories
handle database sessions and SQL operations.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_, func
from datetime import datetime

from MakerMatrix.models.order_models import OrderModel, OrderItemModel, PartOrderLink
from MakerMatrix.repositories.base_repository import BaseRepository
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository[OrderModel]):
    """
    Repository for order database operations.

    Handles all database operations for orders, order items, and part-order links.
    """

    def __init__(self):
        super().__init__(OrderModel)

    def create_order(self, session: Session, order: OrderModel) -> OrderModel:
        """
        Create a new order.

        Args:
            session: Database session
            order: Order to create

        Returns:
            Created order
        """
        session.add(order)
        session.commit()
        session.refresh(order)

        logger.info(f"Created order: {order.order_number} for supplier {order.supplier}")
        return order

    def get_orders_with_filters(
        self,
        session: Session,
        supplier: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[OrderModel]:
        """
        Get orders with optional filtering.

        Args:
            session: Database session
            supplier: Filter by supplier
            status: Filter by status
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of orders
        """
        statement = select(OrderModel)

        if supplier:
            statement = statement.where(OrderModel.supplier == supplier)
        if status:
            statement = statement.where(OrderModel.status == status)

        statement = statement.offset(offset).limit(limit).order_by(OrderModel.order_date.desc())

        orders = session.exec(statement).all()
        return list(orders)

    def update_order(self, session: Session, order: OrderModel) -> OrderModel:
        """
        Update an existing order.

        Args:
            session: Database session
            order: Updated order

        Returns:
            Updated order
        """
        session.add(order)
        session.commit()
        session.refresh(order)

        logger.info(f"Updated order {order.id}")
        return order

    def get_order_statistics(self, session: Session) -> Dict[str, Any]:
        """
        Get order statistics.

        Args:
            session: Database session

        Returns:
            Dictionary containing order statistics
        """
        # Total orders
        total_orders = session.exec(select(func.count(OrderModel.id))).first()

        # Total value
        total_value = session.exec(select(func.sum(OrderModel.total))).first() or 0

        # Orders by status
        pending_orders = session.exec(select(func.count(OrderModel.id)).where(OrderModel.status == "pending")).first()

        delivered_orders = session.exec(
            select(func.count(OrderModel.id)).where(OrderModel.status == "delivered")
        ).first()

        # Orders by supplier
        supplier_counts = session.exec(
            select(OrderModel.supplier, func.count(OrderModel.id)).group_by(OrderModel.supplier)
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
                    "order_date": order.order_date.isoformat() if order.order_date else None,
                }
                for order in recent_orders
            ],
        }


class OrderItemRepository(BaseRepository[OrderItemModel]):
    """
    Repository for order item database operations.
    """

    def __init__(self):
        super().__init__(OrderItemModel)

    def create_order_item(self, session: Session, order_item: OrderItemModel) -> OrderItemModel:
        """
        Create a new order item.

        Args:
            session: Database session
            order_item: Order item to create

        Returns:
            Created order item
        """
        session.add(order_item)
        session.commit()
        session.refresh(order_item)

        logger.info(f"Created order item {order_item.id} for order {order_item.order_id}")
        return order_item

    def get_order_items_by_order(self, session: Session, order_id: str) -> List[OrderItemModel]:
        """
        Get all items for a specific order.

        Args:
            session: Database session
            order_id: Order ID

        Returns:
            List of order items
        """
        statement = select(OrderItemModel).where(OrderItemModel.order_id == order_id)
        items = session.exec(statement).all()
        return list(items)

    def update_order_item(self, session: Session, order_item: OrderItemModel) -> OrderItemModel:
        """
        Update an existing order item.

        Args:
            session: Database session
            order_item: Updated order item

        Returns:
            Updated order item
        """
        session.add(order_item)
        session.commit()
        session.refresh(order_item)

        logger.info(f"Updated order item {order_item.id}")
        return order_item

    def link_order_item_to_part(self, session: Session, order_item_id: str, part_id: str) -> None:
        """
        Link an order item to a part in inventory.

        Args:
            session: Database session
            order_item_id: Order item ID
            part_id: Part ID

        Raises:
            ResourceNotFoundError: If order item not found
        """
        # Get the order item to check quantity
        order_item = self.get_by_id(session, order_item_id)
        if not order_item:
            raise ResourceNotFoundError(f"Order item with id {order_item_id} not found")

        # Update the order item to reference the part
        order_item.part_id = part_id
        session.add(order_item)

        # Create link record for tracking quantity relationships
        link = PartOrderLink(
            part_id=part_id, order_item_id=order_item_id, quantity_from_order=order_item.quantity_received
        )

        session.add(link)
        session.commit()

        logger.info(f"Linked order item {order_item_id} to part {part_id}")

    def calculate_order_totals(self, session: Session, order_id: str) -> float:
        """
        Calculate subtotal for an order based on its items.

        Args:
            session: Database session
            order_id: Order ID

        Returns:
            Calculated subtotal
        """
        items = self.get_order_items_by_order(session, order_id)
        subtotal = sum(float(item.extended_price or 0) for item in items)
        return subtotal
