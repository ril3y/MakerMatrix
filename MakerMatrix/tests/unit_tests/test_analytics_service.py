"""
Unit tests for analytics service.

Tests all analytics calculations and aggregations
with mocked database queries.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import func

from MakerMatrix.services.analytics_service import AnalyticsService


class TestAnalyticsService:
    """Test analytics service methods."""
    
    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance."""
        return AnalyticsService()
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        # Make the session work as a context manager
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=None)
        return session
    
    def test_get_spending_by_supplier(self, analytics_service, mock_session):
        """Test spending by supplier calculation."""
        # Mock query results
        mock_results = [
            Mock(supplier="LCSC", total_spent=250.50, order_count=3),
            Mock(supplier="DigiKey", total_spent=189.75, order_count=2),
            Mock(supplier="Mouser", total_spent=125.00, order_count=1)
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        mock_session.query.return_value = mock_query
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_spending_by_supplier(limit=10)
        
        assert len(result) == 3
        assert result[0]["supplier"] == "LCSC"
        assert result[0]["total_spent"] == 250.50
        assert result[0]["order_count"] == 3
        
        # Verify query construction
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.group_by.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(10)
    
    def test_get_spending_by_supplier_with_dates(self, analytics_service, mock_session):
        """Test spending by supplier with date filters."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_session.query.return_value = mock_query
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            analytics_service.get_spending_by_supplier(
                start_date=start_date,
                end_date=end_date
            )
        
        # Verify date filter was applied
        mock_query.filter.assert_called_once()
    
    def test_get_spending_trend_monthly(self, analytics_service, mock_session):
        """Test monthly spending trend calculation."""
        mock_results = [
            Mock(period="2024-01", total_spent=1000.0, order_count=5),
            Mock(period="2024-02", total_spent=1500.0, order_count=7),
            Mock(period="2024-03", total_spent=800.0, order_count=4)
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        mock_session.query.return_value = mock_query
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_spending_trend(period='month', lookback_periods=6)
        
        assert len(result) == 3
        assert result[0]["period"] == "2024-01-01"
        assert result[0]["total_spent"] == 1000.0
        assert result[0]["order_count"] == 5
    
    def test_get_spending_trend_different_periods(self, analytics_service):
        """Test spending trend with different period types."""
        periods = ['day', 'week', 'month', 'year']
        
        for period in periods:
            mock_session = MagicMock()
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = []
            
            mock_session.query.return_value = mock_query
            
            with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
                mock_session_class.return_value = mock_session
                analytics_service.get_spending_trend(period=period)
            
            # Should not raise an error
            mock_session.query.assert_called_once()
    
    def test_get_part_order_frequency(self, analytics_service, mock_session):
        """Test part order frequency calculation."""
        mock_results = [
            Mock(
                id=1,
                name="10K Resistor",
                part_number="RES-10K",
                quantity=100,
                total_orders=15,
                average_price=0.05,
                last_order_date=datetime.now()
            ),
            Mock(
                id=2,
                name="100uF Capacitor",
                part_number="CAP-100UF",
                quantity=50,
                total_orders=10,
                average_price=0.25,
                last_order_date=None
            )
        ]
        
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        mock_session.query.return_value = mock_query
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_part_order_frequency(limit=20, min_orders=5)
        
        assert len(result) == 2
        assert result[0]["part_id"] == 1
        assert result[0]["name"] == "10K Resistor"
        assert result[0]["total_orders"] == 15
        assert result[0]["average_price"] == 0.05
        assert result[0]["last_order_date"] is not None
        assert result[1]["last_order_date"] is None
    
    def test_get_price_trends_for_part(self, analytics_service, mock_session):
        """Test price trends for specific part."""
        mock_results = [
            Mock(
                part_id=1,
                unit_price=0.05,
                order_date=datetime.now(),
                supplier="LCSC",
                name="10K Resistor",
                part_number="RES-10K"
            ),
            Mock(
                part_id=1,
                unit_price=0.055,
                order_date=datetime.now() - timedelta(days=30),
                supplier="DigiKey",
                name="10K Resistor",
                part_number="RES-10K"
            )
        ]
        
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        mock_session.query.return_value = mock_query
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_price_trends(part_id=1, limit=50)
        
        assert len(result) == 2
        assert result[0]["part_id"] == 1
        assert result[0]["unit_price"] == 0.05
        assert result[0]["supplier"] == "LCSC"
        
        # Verify part_id filter was applied
        mock_query.filter.assert_called()
    
    def test_get_low_stock_parts(self, analytics_service, mock_session):
        """Test low stock parts detection."""
        # Mock subquery for average quantities
        mock_avg_subquery = Mock()
        mock_avg_subquery.c.part_id = "part_id"
        mock_avg_subquery.c.avg_order_qty = "avg_order_qty"
        
        mock_results = [
            Mock(
                id=1,
                name="100uF Capacitor",
                part_number="CAP-100UF",
                quantity=5,
                minimum_quantity=20,
                avg_order_qty=50.0,
                last_order_date=datetime.now(),
                total_orders=10
            ),
            Mock(
                id=2,
                name="LED Red",
                part_number="LED-RED",
                quantity=10,
                minimum_quantity=None,
                avg_order_qty=20.0,
                last_order_date=None,
                total_orders=None
            )
        ]
        
        mock_query = Mock()
        mock_query.group_by.return_value = mock_query
        mock_query.subquery.return_value = mock_avg_subquery
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        mock_session.query.return_value = mock_query
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_low_stock_parts(threshold_multiplier=1.5)
        
        assert len(result) == 2
        assert result[0]["part_id"] == 1
        assert result[0]["current_quantity"] == 5
        assert result[0]["minimum_quantity"] == 20
        assert result[0]["average_order_quantity"] == 50.0
        assert result[0]["suggested_reorder_quantity"] == 100  # avg * 2
    
    def test_get_category_spending(self, analytics_service, mock_session):
        """Test spending by category calculation."""
        mock_results = [
            Mock(name="Electronics", total_spent=1500.0, unique_parts=25),
            Mock(name="Resistors", total_spent=500.0, unique_parts=10),
            Mock(name="Capacitors", total_spent=750.0, unique_parts=15)
        ]
        
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        mock_session.query.return_value = mock_query
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_category_spending()
        
        assert len(result) == 3
        assert result[0]["category"] == "Electronics"
        assert result[0]["total_spent"] == 1500.0
        assert result[0]["unique_parts"] == 25
    
    def test_get_inventory_value(self, analytics_service, mock_session):
        """Test inventory value calculation."""
        # Mock priced parts query
        mock_priced_result = Mock(
            total_value=5000.0,
            total_parts=100,
            total_units=2500
        )
        
        # Mock queries
        mock_query1 = Mock()
        mock_query1.join.return_value = mock_query1
        mock_query1.filter.return_value = mock_query1
        mock_query1.first.return_value = mock_priced_result
        
        mock_query2 = Mock()
        mock_query2.outerjoin.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = 25  # Unpriced parts
        
        # Configure session to return different queries
        mock_session.query.side_effect = [mock_query1, mock_query2]
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_inventory_value()
        
        assert result["total_value"] == 5000.0
        assert result["priced_parts"] == 100
        assert result["unpriced_parts"] == 25
        assert result["total_units"] == 2500
    
    def test_get_inventory_value_no_priced_parts(self, analytics_service, mock_session):
        """Test inventory value with no priced parts."""
        # Mock empty results
        mock_query1 = Mock()
        mock_query1.join.return_value = mock_query1
        mock_query1.filter.return_value = mock_query1
        mock_query1.first.return_value = None
        
        mock_query2 = Mock()
        mock_query2.outerjoin.return_value = mock_query2
        mock_query2.filter.return_value = mock_query2
        mock_query2.scalar.return_value = 50
        
        mock_session.query.side_effect = [mock_query1, mock_query2]
        
        with patch('MakerMatrix.services.analytics_service.Session') as mock_session_class:
            mock_session_class.return_value = mock_session
            result = analytics_service.get_inventory_value()
        
        assert result["total_value"] == 0
        assert result["priced_parts"] == 0
        assert result["unpriced_parts"] == 50
        assert result["total_units"] == 0