"""
Analytics Repository

Repository for analytics database operations.
Handles complex SQL queries for analytics and insights.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, select, case
from sqlalchemy.orm import Session

from MakerMatrix.models.models import (
    PartModel, CategoryModel, LocationModel, PartCategoryLink
)
from MakerMatrix.models.order_models import (
    OrderModel, OrderItemModel, OrderSummary
)
from MakerMatrix.models.part_allocation_models import PartLocationAllocation
from MakerMatrix.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """
    Repository for analytics database operations.
    
    Handles complex SQL queries for spending trends, order frequency analysis,
    price trends, and inventory insights.
    """
    
    def __init__(self):
        """Initialize the analytics repository."""
        pass
    
    def get_spending_by_supplier(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get spending breakdown by supplier.
        
        Args:
            session: Database session
            start_date: Start date for analysis
            end_date: End date for analysis
            limit: Maximum number of suppliers to return
            
        Returns:
            List of supplier spending data
        """
        # Query spending by supplier
        results = session.query(
            OrderModel.supplier,
            func.sum(OrderModel.total).label('total_spent'),
            func.count(OrderModel.id).label('order_count')
        ).filter(
            and_(
                OrderModel.order_date >= start_date,
                OrderModel.order_date <= end_date
            )
        ).group_by(
            OrderModel.supplier
        ).order_by(
            func.sum(OrderModel.total).desc()
        ).limit(limit).all()
        
        return [
            {
                'supplier': result.supplier,
                'total_spent': float(result.total_spent or 0),
                'order_count': result.order_count
            }
            for result in results
        ]
    
    def get_spending_trend_by_period(
        self,
        session: Session,
        period: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get spending trend over time by period.
        
        Args:
            session: Database session
            period: 'day', 'week', 'month', or 'year'
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            List of spending data by period
        """
        # Build date format based on period
        if period == 'day':
            date_format = '%Y-%m-%d'
        elif period == 'week':
            date_format = '%Y-%W'
        elif period == 'month':
            date_format = '%Y-%m'
        elif period == 'year':
            date_format = '%Y'
        else:
            date_format = '%Y-%m'
        
        # Query spending by period
        results = session.query(
            func.strftime(date_format, OrderModel.order_date).label('period'),
            func.sum(OrderModel.total).label('total_spent'),
            func.count(OrderModel.id).label('order_count')
        ).filter(
            and_(
                OrderModel.order_date >= start_date,
                OrderModel.order_date <= end_date
            )
        ).group_by(
            func.strftime(date_format, OrderModel.order_date)
        ).order_by(
            func.strftime(date_format, OrderModel.order_date)
        ).all()
        
        return [
            {
                'period': result.period,
                'total_spent': float(result.total_spent or 0),
                'order_count': result.order_count
            }
            for result in results
        ]
    
    def get_part_order_frequency(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get parts ordered most frequently.
        
        Args:
            session: Database session
            start_date: Start date for analysis
            end_date: End date for analysis
            limit: Maximum number of parts to return
            
        Returns:
            List of part order frequency data
        """
        # Query part order frequency
        results = session.query(
            OrderItemModel.supplier_part_number,
            OrderItemModel.manufacturer_part_number,
            OrderItemModel.description,
            func.count(OrderItemModel.id).label('order_count'),
            func.sum(OrderItemModel.quantity_ordered).label('total_quantity'),
            func.sum(OrderItemModel.extended_price).label('total_spent')
        ).join(
            OrderModel, OrderItemModel.order_id == OrderModel.id
        ).filter(
            and_(
                OrderModel.order_date >= start_date,
                OrderModel.order_date <= end_date
            )
        ).group_by(
            OrderItemModel.supplier_part_number,
            OrderItemModel.manufacturer_part_number,
            OrderItemModel.description
        ).order_by(
            func.count(OrderItemModel.id).desc()
        ).limit(limit).all()
        
        return [
            {
                'supplier_part_number': result.supplier_part_number,
                'manufacturer_part_number': result.manufacturer_part_number,
                'description': result.description,
                'order_count': result.order_count,
                'total_quantity': result.total_quantity,
                'total_spent': float(result.total_spent or 0)
            }
            for result in results
        ]
    
    def get_price_trends(
        self,
        session: Session,
        part_number: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get price trends for a specific part.
        
        Args:
            session: Database session
            part_number: Part number to analyze
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            List of price trend data
        """
        # Query price trends
        results = session.query(
            OrderModel.order_date,
            OrderItemModel.unit_price,
            OrderItemModel.quantity_ordered,
            OrderModel.supplier
        ).join(
            OrderItemModel, OrderModel.id == OrderItemModel.order_id
        ).filter(
            and_(
                or_(
                    OrderItemModel.supplier_part_number == part_number,
                    OrderItemModel.manufacturer_part_number == part_number
                ),
                OrderModel.order_date >= start_date,
                OrderModel.order_date <= end_date
            )
        ).order_by(
            OrderModel.order_date.desc()
        ).all()
        
        return [
            {
                'order_date': result.order_date.isoformat() if result.order_date else None,
                'unit_price': float(result.unit_price or 0),
                'quantity_ordered': result.quantity_ordered,
                'supplier': result.supplier
            }
            for result in results
        ]
    
    def get_low_stock_parts(
        self,
        session: Session,
        threshold: int = 5,
        include_zero: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get parts with low stock levels.

        Args:
            session: Database session
            threshold: Stock threshold below which parts are considered low
            include_zero: Whether to include parts with zero stock

        Returns:
            List of low stock parts
        """
        # Subquery to get total quantity and primary location per part
        part_totals = session.query(
            PartLocationAllocation.part_id,
            func.sum(PartLocationAllocation.quantity_at_location).label('total_quantity'),
            func.max(
                case(
                    (PartLocationAllocation.is_primary_storage == True, LocationModel.name),
                    else_=None
                )
            ).label('primary_location')
        ).outerjoin(
            LocationModel,
            PartLocationAllocation.location_id == LocationModel.id
        ).group_by(
            PartLocationAllocation.part_id
        ).subquery()

        # Build query
        query = session.query(
            PartModel.id,
            PartModel.part_name,
            PartModel.part_number,
            part_totals.c.total_quantity.label('quantity'),
            PartModel.supplier,
            part_totals.c.primary_location.label('location_name')
        ).join(
            part_totals,
            PartModel.id == part_totals.c.part_id
        )

        # Apply threshold filter
        if include_zero:
            query = query.filter(part_totals.c.total_quantity <= threshold)
        else:
            query = query.filter(
                and_(
                    part_totals.c.total_quantity <= threshold,
                    part_totals.c.total_quantity > 0
                )
            )

        results = query.order_by(
            part_totals.c.total_quantity.asc()
        ).all()

        return [
            {
                'id': result.id,
                'part_name': result.part_name,
                'part_number': result.part_number or '',
                'quantity': int(result.quantity or 0),
                'supplier': result.supplier or '',
                'location_name': result.location_name or 'Multiple Locations'
            }
            for result in results
        ]
    
    def get_inventory_value_by_category(
        self,
        session: Session,
        include_zero_quantity: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get inventory value breakdown by category.
        
        Args:
            session: Database session
            include_zero_quantity: Whether to include parts with zero quantity
            
        Returns:
            List of inventory value data by category
        """
        # Base query
        query = session.query(
            CategoryModel.name.label('category_name'),
            func.count(PartModel.id).label('part_count'),
            func.sum(PartModel.quantity).label('total_quantity')
        ).join(
            PartCategoryLink, CategoryModel.id == PartCategoryLink.category_id
        ).join(
            PartModel, PartCategoryLink.part_id == PartModel.id
        )
        
        # Apply quantity filter if needed
        if not include_zero_quantity:
            query = query.filter(PartModel.quantity > 0)
        
        # Group and order
        results = query.group_by(
            CategoryModel.name
        ).order_by(
            func.sum(PartModel.quantity).desc()
        ).all()
        
        return [
            {
                'category_name': result.category_name,
                'part_count': result.part_count,
                'total_quantity': result.total_quantity or 0
            }
            for result in results
        ]
    
    def get_supplier_performance(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get supplier performance metrics.
        
        Args:
            session: Database session
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            List of supplier performance data
        """
        # Query supplier performance
        results = session.query(
            OrderModel.supplier,
            func.count(OrderModel.id).label('total_orders'),
            func.avg(OrderModel.total).label('avg_order_value'),
            func.sum(OrderModel.total).label('total_spent'),
            func.count(func.distinct(OrderItemModel.supplier_part_number)).label('unique_parts')
        ).join(
            OrderItemModel, OrderModel.id == OrderItemModel.order_id
        ).filter(
            and_(
                OrderModel.order_date >= start_date,
                OrderModel.order_date <= end_date
            )
        ).group_by(
            OrderModel.supplier
        ).order_by(
            func.sum(OrderModel.total).desc()
        ).all()
        
        return [
            {
                'supplier': result.supplier,
                'total_orders': result.total_orders,
                'avg_order_value': float(result.avg_order_value or 0),
                'total_spent': float(result.total_spent or 0),
                'unique_parts': result.unique_parts
            }
            for result in results
        ]
    
    def get_category_spending(
        self,
        session: Session,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get spending breakdown by category.
        
        Args:
            session: Database session
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            List of category spending data
        """
        # Query spending by category
        results = session.query(
            CategoryModel.name,
            func.sum(OrderItemModel.extended_price).label('total_spent'),
            func.count(func.distinct(OrderItemModel.part_id)).label('unique_parts')
        ).join(
            PartCategoryLink,
            CategoryModel.id == PartCategoryLink.category_id
        ).join(
            OrderItemModel,
            PartCategoryLink.part_id == OrderItemModel.part_id
        ).join(
            OrderModel,
            OrderItemModel.order_id == OrderModel.id
        ).filter(
            and_(
                OrderModel.order_date >= start_date,
                OrderModel.order_date <= end_date
            )
        ).group_by(
            CategoryModel.name
        ).order_by(
            func.sum(OrderItemModel.extended_price).desc()
        ).all()
        
        return [
            {
                'category': result.name,
                'total_spent': float(result.total_spent or 0),
                'unique_parts': result.unique_parts
            }
            for result in results
        ]
    
    def get_inventory_value(
        self,
        session: Session
    ) -> Dict[str, Any]:
        """
        Calculate total inventory value based on average prices.

        Args:
            session: Database session

        Returns:
            Dictionary with inventory value statistics
        """
        # Calculate average price for each part
        avg_prices = session.query(
            OrderItemModel.part_id,
            func.avg(OrderItemModel.unit_price).label('average_price')
        ).filter(
            OrderItemModel.unit_price.isnot(None)
        ).group_by(
            OrderItemModel.part_id
        ).subquery()

        # Get parts with pricing information
        results = session.query(
            func.sum(PartModel.quantity * avg_prices.c.average_price).label('total_value'),
            func.count(PartModel.id).label('total_parts'),
            func.sum(PartModel.quantity).label('total_units')
        ).join(
            avg_prices, PartModel.id == avg_prices.c.part_id
        ).filter(
            avg_prices.c.average_price.isnot(None)
        ).first()

        # Get parts without pricing
        unpriced_count = session.query(
            func.count(PartModel.id)
        ).outerjoin(
            avg_prices, PartModel.id == avg_prices.c.part_id
        ).filter(
            or_(
                avg_prices.c.average_price.is_(None),
                avg_prices.c.part_id.is_(None)
            )
        ).scalar()

        return {
            'total_value': float(results.total_value or 0) if results else 0,
            'priced_parts': results.total_parts if results else 0,
            'unpriced_parts': unpriced_count or 0,
            'total_units': results.total_units if (results and results.total_units is not None) else 0
        }

    def get_parts_by_category(
        self,
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        Get parts distribution by category.

        Args:
            session: Database session

        Returns:
            List of category distribution data
        """
        # Subquery to get total quantity per part from allocations
        part_quantities = session.query(
            PartLocationAllocation.part_id,
            func.sum(PartLocationAllocation.quantity_at_location).label('total_quantity')
        ).group_by(
            PartLocationAllocation.part_id
        ).subquery()

        results = session.query(
            CategoryModel.name,
            func.count(PartModel.id).label('part_count'),
            func.coalesce(func.sum(part_quantities.c.total_quantity), 0).label('total_quantity')
        ).join(
            PartCategoryLink,
            CategoryModel.id == PartCategoryLink.category_id
        ).join(
            PartModel,
            PartCategoryLink.part_id == PartModel.id
        ).outerjoin(
            part_quantities,
            PartModel.id == part_quantities.c.part_id
        ).group_by(
            CategoryModel.name
        ).order_by(
            func.count(PartModel.id).desc()
        ).all()

        return [
            {
                'category': result.name,
                'part_count': result.part_count,
                'total_quantity': int(result.total_quantity or 0)
            }
            for result in results
        ]

    def get_parts_by_location(
        self,
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        Get parts distribution by location.

        Args:
            session: Database session

        Returns:
            List of location distribution data
        """
        # Get allocations grouped by location
        results = session.query(
            LocationModel.name,
            func.count(func.distinct(PartLocationAllocation.part_id)).label('part_count'),
            func.sum(PartLocationAllocation.quantity_at_location).label('total_quantity')
        ).join(
            PartLocationAllocation,
            LocationModel.id == PartLocationAllocation.location_id
        ).group_by(
            LocationModel.name
        ).order_by(
            func.count(func.distinct(PartLocationAllocation.part_id)).desc()
        ).all()

        result_list = [
            {
                'location': result.name,
                'part_count': result.part_count,
                'total_quantity': int(result.total_quantity or 0)
            }
            for result in results
        ]

        return result_list

    def get_most_stocked_parts(
        self,
        session: Session,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get parts with highest stock quantities.

        Args:
            session: Database session
            limit: Maximum number of parts to return

        Returns:
            List of most stocked parts
        """
        # Subquery to get total quantity and primary location per part
        part_totals = session.query(
            PartLocationAllocation.part_id,
            func.sum(PartLocationAllocation.quantity_at_location).label('total_quantity'),
            func.max(
                case(
                    (PartLocationAllocation.is_primary_storage == True, LocationModel.name),
                    else_=None
                )
            ).label('primary_location')
        ).outerjoin(
            LocationModel,
            PartLocationAllocation.location_id == LocationModel.id
        ).group_by(
            PartLocationAllocation.part_id
        ).subquery()

        results = session.query(
            PartModel.id,
            PartModel.part_name,
            PartModel.part_number,
            part_totals.c.total_quantity.label('quantity'),
            PartModel.supplier,
            part_totals.c.primary_location.label('location_name')
        ).join(
            part_totals,
            PartModel.id == part_totals.c.part_id
        ).order_by(
            part_totals.c.total_quantity.desc()
        ).limit(limit).all()

        return [
            {
                'id': result.id,
                'part_name': result.part_name,
                'part_number': result.part_number or '',
                'quantity': int(result.quantity or 0),
                'supplier': result.supplier or '',
                'location': result.location_name or 'Multiple Locations'
            }
            for result in results
        ]

    def get_least_stocked_parts(
        self,
        session: Session,
        limit: int = 10,
        exclude_zero: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get parts with lowest stock quantities.

        Args:
            session: Database session
            limit: Maximum number of parts to return
            exclude_zero: Whether to exclude parts with zero stock

        Returns:
            List of least stocked parts
        """
        # Subquery to get total quantity and primary location per part
        part_totals = session.query(
            PartLocationAllocation.part_id,
            func.sum(PartLocationAllocation.quantity_at_location).label('total_quantity'),
            func.max(
                case(
                    (PartLocationAllocation.is_primary_storage == True, LocationModel.name),
                    else_=None
                )
            ).label('primary_location')
        ).outerjoin(
            LocationModel,
            PartLocationAllocation.location_id == LocationModel.id
        ).group_by(
            PartLocationAllocation.part_id
        ).subquery()

        query = session.query(
            PartModel.id,
            PartModel.part_name,
            PartModel.part_number,
            part_totals.c.total_quantity.label('quantity'),
            PartModel.supplier,
            part_totals.c.primary_location.label('location_name')
        ).join(
            part_totals,
            PartModel.id == part_totals.c.part_id
        )

        if exclude_zero:
            query = query.filter(part_totals.c.total_quantity > 0)

        results = query.order_by(
            part_totals.c.total_quantity.asc()
        ).limit(limit).all()

        return [
            {
                'id': result.id,
                'part_name': result.part_name,
                'part_number': result.part_number or '',
                'quantity': int(result.quantity or 0),
                'supplier': result.supplier or '',
                'location': result.location_name or 'Multiple Locations'
            }
            for result in results
        ]

    def get_parts_by_supplier(
        self,
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        Get parts distribution by supplier.

        Args:
            session: Database session

        Returns:
            List of supplier distribution data
        """
        # Subquery to get total quantity per part from allocations
        part_quantities = session.query(
            PartLocationAllocation.part_id,
            func.sum(PartLocationAllocation.quantity_at_location).label('total_quantity')
        ).group_by(
            PartLocationAllocation.part_id
        ).subquery()

        # Use UPPER() to normalize supplier names for case-insensitive grouping
        results = session.query(
            func.upper(PartModel.supplier).label('supplier'),
            func.count(PartModel.id).label('part_count'),
            func.coalesce(func.sum(part_quantities.c.total_quantity), 0).label('total_quantity')
        ).outerjoin(
            part_quantities,
            PartModel.id == part_quantities.c.part_id
        ).filter(
            PartModel.supplier.isnot(None),
            PartModel.supplier != ''
        ).group_by(
            func.upper(PartModel.supplier)
        ).order_by(
            func.count(PartModel.id).desc()
        ).all()

        return [
            {
                'supplier': result.supplier,
                'part_count': result.part_count,
                'total_quantity': int(result.total_quantity or 0)
            }
            for result in results
        ]

    def get_inventory_summary(
        self,
        session: Session
    ) -> Dict[str, Any]:
        """
        Get overall inventory summary statistics.

        Args:
            session: Database session

        Returns:
            Dictionary with summary statistics
        """
        total_parts = session.query(func.count(PartModel.id)).scalar() or 0

        # Get total units from allocations
        total_units = session.query(
            func.sum(PartLocationAllocation.quantity_at_location)
        ).scalar() or 0

        total_categories = session.query(func.count(CategoryModel.id)).scalar() or 0
        total_locations = session.query(func.count(LocationModel.id)).scalar() or 0

        # Count parts with allocations (have locations)
        parts_with_location = session.query(
            func.count(func.distinct(PartLocationAllocation.part_id))
        ).scalar() or 0

        parts_without_location = total_parts - parts_with_location

        # Subquery for part totals
        part_totals = session.query(
            PartLocationAllocation.part_id,
            func.sum(PartLocationAllocation.quantity_at_location).label('total_quantity')
        ).group_by(
            PartLocationAllocation.part_id
        ).subquery()

        # Count low stock parts (< 10 units total)
        low_stock_count = session.query(
            func.count(part_totals.c.part_id)
        ).filter(
            part_totals.c.total_quantity < 10
        ).scalar() or 0

        # Count zero stock parts
        zero_stock_count = session.query(
            func.count(part_totals.c.part_id)
        ).filter(
            part_totals.c.total_quantity == 0
        ).scalar() or 0

        return {
            'total_parts': total_parts,
            'total_units': int(total_units),
            'total_categories': total_categories,
            'total_locations': total_locations,
            'parts_with_location': parts_with_location,
            'parts_without_location': parts_without_location,
            'low_stock_count': low_stock_count,
            'zero_stock_count': zero_stock_count
        }