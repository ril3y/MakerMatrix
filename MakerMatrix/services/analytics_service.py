"""
Analytics service for order and inventory analytics.

Provides spending trends, order frequency analysis, price trends,
and inventory insights.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, select
from sqlalchemy.orm import Session

from MakerMatrix.models.models import (
    PartModel, CategoryModel, LocationModel, PartCategoryLink
)
from MakerMatrix.models.order_models import (
    OrderModel, OrderItemModel, OrderSummary
)
from MakerMatrix.database.db import engine

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating analytics and insights from order and inventory data."""
    
    def __init__(self):
        """Initialize the analytics service."""
        self.engine = engine
    
    def get_spending_by_supplier(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get spending breakdown by supplier.
        
        Args:
            start_date: Start date for analysis (default: 30 days ago)
            end_date: End date for analysis (default: today)
            limit: Maximum number of suppliers to return
            
        Returns:
            List of supplier spending data
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        logger.info(f"Calculating spending by supplier from {start_date} to {end_date}")
        
        with Session(self.engine) as session:
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
    
    def get_spending_trend(
        self,
        period: str = 'month',
        lookback_periods: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get spending trend over time.
        
        Args:
            period: 'day', 'week', 'month', or 'year'
            lookback_periods: Number of periods to look back
            
        Returns:
            List of spending data by period
        """
        logger.info(f"Calculating spending trend by {period} for {lookback_periods} periods")
        
        # Calculate date range
        end_date = datetime.now()
        if period == 'day':
            start_date = end_date - timedelta(days=lookback_periods)
            # SQLite compatible: use date function
            date_trunc = func.date(OrderModel.order_date)
        elif period == 'week':
            start_date = end_date - timedelta(weeks=lookback_periods)
            # SQLite compatible: use strftime to get week start
            date_trunc = func.strftime('%Y-%W', OrderModel.order_date)
        elif period == 'month':
            start_date = end_date - timedelta(days=lookback_periods * 30)
            # SQLite compatible: use strftime to get year-month
            date_trunc = func.strftime('%Y-%m', OrderModel.order_date)
        else:  # year
            start_date = end_date - timedelta(days=lookback_periods * 365)
            # SQLite compatible: use strftime to get year
            date_trunc = func.strftime('%Y', OrderModel.order_date)
        
        with Session(self.engine) as session:
            results = session.query(
                date_trunc.label('period'),
                func.sum(OrderModel.total).label('total_spent'),
                func.count(OrderModel.id).label('order_count')
            ).filter(
                OrderModel.order_date >= start_date
            ).group_by(
                date_trunc
            ).order_by(
                date_trunc
            ).all()
            
            # Format the period string appropriately
            formatted_results = []
            for result in results:
                period_str = str(result.period)
                
                # Convert period string to ISO format based on period type
                if period == 'day':
                    # Already in date format
                    period_iso = period_str
                elif period == 'week':
                    # Convert YYYY-WW to date of week start
                    try:
                        year, week = period_str.split('-')
                        # Get the Monday of that week
                        jan1 = datetime(int(year), 1, 1)
                        week_start = jan1 + timedelta(days=(int(week) - 1) * 7 - jan1.weekday())
                        period_iso = week_start.date().isoformat()
                    except:
                        period_iso = period_str
                elif period == 'month':
                    # Convert YYYY-MM to first day of month
                    try:
                        period_iso = f"{period_str}-01"
                    except:
                        period_iso = period_str
                else:  # year
                    # Convert YYYY to first day of year
                    try:
                        period_iso = f"{period_str}-01-01"
                    except:
                        period_iso = period_str
                
                formatted_results.append({
                    'period': period_iso,
                    'total_spent': float(result.total_spent or 0),
                    'order_count': result.order_count
                })
            
            return formatted_results
    
    def get_part_order_frequency(
        self,
        limit: int = 20,
        min_orders: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently ordered parts.
        
        Args:
            limit: Maximum number of parts to return
            min_orders: Minimum number of orders to include
            
        Returns:
            List of frequently ordered parts
        """
        logger.info(f"Getting top {limit} frequently ordered parts")
        
        with Session(self.engine) as session:
            results = session.query(
                PartModel.id,
                PartModel.part_name,
                PartModel.part_number,
                PartModel.quantity,
                OrderSummary.total_orders,
                OrderSummary.average_price,
                OrderSummary.last_order_date
            ).join(
                OrderSummary, PartModel.id == OrderSummary.part_id
            ).filter(
                OrderSummary.total_orders >= min_orders
            ).order_by(
                OrderSummary.total_orders.desc()
            ).limit(limit).all()
            
            return [
                {
                    'part_id': result.id,
                    'name': result.part_name,
                    'part_number': result.part_number,
                    'current_quantity': result.quantity,
                    'total_orders': result.total_orders,
                    'average_price': float(result.average_price or 0),
                    'last_order_date': result.last_order_date.isoformat() if result.last_order_date else None
                }
                for result in results
            ]
    
    def get_price_trends(
        self,
        part_id: Optional[str] = None,
        supplier: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get price trends for parts.
        
        Args:
            part_id: Specific part to analyze
            supplier: Filter by supplier
            limit: Maximum number of data points
            
        Returns:
            List of price trend data
        """
        logger.info(f"Getting price trends for part_id={part_id}, supplier={supplier}")
        
        with Session(self.engine) as session:
            query = session.query(
                OrderItemModel.part_id,
                OrderItemModel.unit_price,
                OrderModel.order_date,
                OrderModel.supplier,
                PartModel.part_name,
                PartModel.part_number
            ).join(
                OrderModel, OrderItemModel.order_id == OrderModel.id
            ).join(
                PartModel, OrderItemModel.part_id == PartModel.id
            )
            
            if part_id:
                query = query.filter(OrderItemModel.part_id == part_id)
            if supplier:
                query = query.filter(OrderModel.supplier == supplier)
                
            results = query.order_by(
                OrderModel.order_date.desc()
            ).limit(limit).all()
            
            return [
                {
                    'part_id': result.part_id,
                    'part_name': result.part_name,
                    'part_number': result.part_number,
                    'unit_price': float(result.unit_price or 0),
                    'order_date': result.order_date.isoformat() if result.order_date else None,
                    'supplier': result.supplier
                }
                for result in results
            ]
    
    def get_low_stock_parts(
        self,
        threshold_multiplier: float = 1.5
    ) -> List[Dict[str, Any]]:
        """
        Get parts that are low in stock based on order history.
        
        Args:
            threshold_multiplier: Multiplier for average order quantity
            
        Returns:
            List of low stock parts
        """
        logger.info(f"Getting low stock parts with threshold multiplier {threshold_multiplier}")
        
        with Session(self.engine) as session:
            # Calculate average order quantity for each part
            avg_quantities = session.query(
                OrderItemModel.part_id,
                func.avg(OrderItemModel.quantity).label('avg_order_qty')
            ).group_by(
                OrderItemModel.part_id
            ).subquery()
            
            # Find parts where current quantity is below threshold
            results = session.query(
                PartModel.id,
                PartModel.part_name,
                PartModel.part_number,
                PartModel.quantity,
                PartModel.minimum_quantity,
                avg_quantities.c.avg_order_qty,
                OrderSummary.last_order_date,
                OrderSummary.total_orders
            ).join(
                avg_quantities, PartModel.id == avg_quantities.c.part_id
            ).outerjoin(
                OrderSummary, PartModel.id == OrderSummary.part_id
            ).filter(
                or_(
                    # Below minimum quantity
                    and_(
                        PartModel.minimum_quantity.isnot(None),
                        PartModel.quantity <= PartModel.minimum_quantity
                    ),
                    # Below average order quantity threshold
                    PartModel.quantity <= (avg_quantities.c.avg_order_qty * threshold_multiplier)
                )
            ).all()
            
            return [
                {
                    'part_id': result.id,
                    'name': result.part_name,
                    'part_number': result.part_number,
                    'current_quantity': result.quantity,
                    'minimum_quantity': result.minimum_quantity,
                    'average_order_quantity': float(result.avg_order_qty or 0),
                    'suggested_reorder_quantity': int((result.avg_order_qty or 0) * 2),
                    'last_order_date': result.last_order_date.isoformat() if result.last_order_date else None,
                    'total_orders': result.total_orders or 0
                }
                for result in results
            ]
    
    def get_category_spending(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get spending breakdown by category.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            List of category spending data
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        logger.info(f"Calculating spending by category from {start_date} to {end_date}")
        
        with Session(self.engine) as session:
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
    
    def get_inventory_value(self) -> Dict[str, Any]:
        """
        Calculate total inventory value based on average prices.
        
        Returns:
            Dictionary with inventory value statistics
        """
        logger.info("Calculating inventory value")
        
        with Session(self.engine) as session:
            # Get parts with pricing information
            results = session.query(
                func.sum(PartModel.quantity * OrderSummary.average_price).label('total_value'),
                func.count(PartModel.id).label('total_parts'),
                func.sum(PartModel.quantity).label('total_units')
            ).join(
                OrderSummary, PartModel.id == OrderSummary.part_id
            ).filter(
                OrderSummary.average_price.isnot(None)
            ).first()
            
            # Get parts without pricing
            unpriced_count = session.query(
                func.count(PartModel.id)
            ).outerjoin(
                OrderSummary, PartModel.id == OrderSummary.part_id
            ).filter(
                or_(
                    OrderSummary.average_price.is_(None),
                    OrderSummary.part_id.is_(None)
                )
            ).scalar()
            
            return {
                'total_value': float(results.total_value or 0) if results else 0,
                'priced_parts': results.total_parts if results else 0,
                'unpriced_parts': unpriced_count or 0,
                'total_units': results.total_units if results else 0
            }


# Global service instance
analytics_service = AnalyticsService()