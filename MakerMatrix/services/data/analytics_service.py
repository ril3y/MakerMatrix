"""
Analytics service for order and inventory analytics.

Provides spending trends, order frequency analysis, price trends,
and inventory insights.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from MakerMatrix.repositories.analytics_repository import AnalyticsRepository
from MakerMatrix.services.base_service import BaseService

logger = logging.getLogger(__name__)


class AnalyticsService(BaseService):
    """Service for generating analytics and insights from order and inventory data."""
    
    def __init__(self):
        """Initialize the analytics service."""
        super().__init__()
        self.analytics_repo = AnalyticsRepository()
    
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
            end_date: End date for analysis (default: end of today)
            limit: Maximum number of suppliers to return
            
        Returns:
            List of supplier spending data
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            # Use end of current day to include orders from later today
            end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
        logger.info(f"Calculating spending by supplier from {start_date} to {end_date}")
        
        with self.get_session() as session:
            return self.analytics_repo.get_spending_by_supplier(session, start_date, end_date, limit)
    
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
        elif period == 'week':
            start_date = end_date - timedelta(weeks=lookback_periods)
        elif period == 'month':
            start_date = end_date - timedelta(days=lookback_periods * 30)
        else:  # year
            start_date = end_date - timedelta(days=lookback_periods * 365)
        
        with self.get_session() as session:
            results = self.analytics_repo.get_spending_trend_by_period(session, period, start_date, end_date)
            
            # Format the period string appropriately
            formatted_results = []
            for result in results:
                period_str = str(result['period'])
                
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
                    'total_spent': result['total_spent'],
                    'order_count': result['order_count']
                })
            
            return formatted_results
    
    def get_part_order_frequency(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently ordered parts.
        
        Args:
            start_date: Start date for analysis (default: 30 days ago)
            end_date: End date for analysis (default: now)
            limit: Maximum number of parts to return
            
        Returns:
            List of frequently ordered parts
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        logger.info(f"Getting top {limit} frequently ordered parts from {start_date} to {end_date}")
        
        with self.get_session() as session:
            return self.analytics_repo.get_part_order_frequency(session, start_date, end_date, limit)
    
    def get_price_trends(
        self,
        part_number: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get price trends for parts.
        
        Args:
            part_number: Specific part number to analyze
            start_date: Start date for analysis (default: 90 days ago)
            end_date: End date for analysis (default: now)
            
        Returns:
            List of price trend data
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=90)
        if not end_date:
            end_date = datetime.now()
            
        logger.info(f"Getting price trends for part_number={part_number} from {start_date} to {end_date}")
        
        if not part_number:
            return []
        
        with self.get_session() as session:
            return self.analytics_repo.get_price_trends(session, part_number, start_date, end_date)
    
    def get_low_stock_parts(
        self,
        threshold: int = 5,
        include_zero: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get parts that are low in stock.
        
        Args:
            threshold: Stock threshold below which parts are considered low
            include_zero: Whether to include parts with zero stock
            
        Returns:
            List of low stock parts
        """
        logger.info(f"Getting low stock parts with threshold {threshold}, include_zero={include_zero}")
        
        with self.get_session() as session:
            return self.analytics_repo.get_low_stock_parts(session, threshold, include_zero)
    
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
            # Use end of current day to include orders from later today
            end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
        logger.info(f"Calculating spending by category from {start_date} to {end_date}")
        
        with self.get_session() as session:
            return self.analytics_repo.get_category_spending(session, start_date, end_date)
    
    def get_inventory_value(self) -> Dict[str, Any]:
        """
        Calculate total inventory value based on average prices.

        Returns:
            Dictionary with inventory value statistics
        """
        logger.info("Calculating inventory value")

        with self.get_session() as session:
            return self.analytics_repo.get_inventory_value(session)

    def get_parts_by_category(self) -> List[Dict[str, Any]]:
        """
        Get parts distribution by category.

        Returns:
            List of category distribution data
        """
        logger.info("Getting parts distribution by category")

        with self.get_session() as session:
            return self.analytics_repo.get_parts_by_category(session)

    def get_parts_by_location(self) -> List[Dict[str, Any]]:
        """
        Get parts distribution by location.

        Returns:
            List of location distribution data
        """
        logger.info("Getting parts distribution by location")

        with self.get_session() as session:
            return self.analytics_repo.get_parts_by_location(session)

    def get_most_stocked_parts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get parts with highest stock quantities.

        Args:
            limit: Maximum number of parts to return

        Returns:
            List of most stocked parts
        """
        logger.info(f"Getting top {limit} most stocked parts")

        with self.get_session() as session:
            return self.analytics_repo.get_most_stocked_parts(session, limit)

    def get_least_stocked_parts(self, limit: int = 10, exclude_zero: bool = True) -> List[Dict[str, Any]]:
        """
        Get parts with lowest stock quantities.

        Args:
            limit: Maximum number of parts to return
            exclude_zero: Whether to exclude parts with zero stock

        Returns:
            List of least stocked parts
        """
        logger.info(f"Getting top {limit} least stocked parts (exclude_zero={exclude_zero})")

        with self.get_session() as session:
            return self.analytics_repo.get_least_stocked_parts(session, limit, exclude_zero)

    def get_inventory_summary(self) -> Dict[str, Any]:
        """
        Get overall inventory summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        logger.info("Getting inventory summary")

        with self.get_session() as session:
            return self.analytics_repo.get_inventory_summary(session)


# Global service instance
analytics_service = AnalyticsService()