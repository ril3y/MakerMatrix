"""
Integration tests for analytics fixes.

Tests the analytics system to ensure:
1. Supplier names are correctly set instead of "Unknown"
2. Extended prices are calculated properly
3. Date filtering works correctly for recent orders
4. Category spending is calculated
"""

import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, select
from MakerMatrix.models.models import engine
from MakerMatrix.models.order_models import OrderModel, OrderItemModel
from MakerMatrix.services.data.analytics_service import analytics_service


class TestAnalyticsFixes:
    """Test analytics data quality and calculations."""
    
    def test_no_unknown_suppliers(self):
        """Test that no orders have 'Unknown' as supplier."""
        with Session(engine) as session:
            unknown_orders = session.exec(
                select(OrderModel).where(OrderModel.supplier == "Unknown")
            ).all()
            
            assert len(unknown_orders) == 0, f"Found {len(unknown_orders)} orders with 'Unknown' supplier"
    
    def test_extended_prices_calculated(self):
        """Test that all order items with unit_price > 0 have extended_price > 0."""
        with Session(engine) as session:
            # Get items with unit price but no extended price
            items_missing_extended = session.exec(
                select(OrderItemModel).where(
                    OrderItemModel.unit_price > 0.0,
                    OrderItemModel.extended_price == 0.0
                )
            ).all()
            
            assert len(items_missing_extended) == 0, \
                f"Found {len(items_missing_extended)} items with unit_price > 0 but extended_price = 0"
            
            # Verify extended_price = unit_price * quantity for a sample
            sample_items = session.exec(
                select(OrderItemModel).where(OrderItemModel.unit_price > 0.0)
            ).all()
            
            if sample_items:
                item = sample_items[0]
                expected_extended = float(item.unit_price) * item.quantity_ordered
                actual_extended = float(item.extended_price)
                assert abs(actual_extended - expected_extended) < 0.01, \
                    f"Extended price calculation incorrect: {actual_extended} != {expected_extended}"
    
    def test_recent_orders_in_spending_analysis(self):
        """Test that recent orders appear in 30-day spending analysis."""
        # Get orders from today
        today = datetime.now().date()
        
        with Session(engine) as session:
            recent_orders = session.exec(
                select(OrderModel).where(OrderModel.order_date >= today)
            ).all()
            
            if recent_orders:
                # Test analytics service with default date range (30 days)
                spending_30_days = analytics_service.get_spending_by_supplier()
                
                # Should include suppliers from recent orders
                recent_suppliers = {order.supplier for order in recent_orders}
                analytics_suppliers = {item['supplier'] for item in spending_30_days}
                
                missing_suppliers = recent_suppliers - analytics_suppliers
                assert len(missing_suppliers) == 0, \
                    f"Recent suppliers missing from 30-day analysis: {missing_suppliers}"
    
    def test_spending_by_supplier_all_time(self):
        """Test that all-time spending includes all suppliers with orders."""
        with Session(engine) as session:
            # Get all unique suppliers from orders
            all_suppliers = session.exec(
                select(OrderModel.supplier).distinct()
            ).all()
            
            # Get spending analysis for all time
            all_time_start = datetime(2020, 1, 1)
            all_time_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            spending_all_time = analytics_service.get_spending_by_supplier(
                start_date=all_time_start,
                end_date=all_time_end
            )
            
            analytics_suppliers = {item['supplier'] for item in spending_all_time}
            db_suppliers = set(all_suppliers)
            
            missing_suppliers = db_suppliers - analytics_suppliers
            assert len(missing_suppliers) == 0, \
                f"Suppliers missing from all-time analysis: {missing_suppliers}"
    
    def test_order_totals_match_items(self):
        """Test that order totals match sum of order item extended prices."""
        with Session(engine) as session:
            orders = session.exec(select(OrderModel)).all()
            
            for order in orders:
                # Get order items
                items = session.exec(
                    select(OrderItemModel).where(OrderItemModel.order_id == order.id)
                ).all()
                
                # Calculate expected subtotal
                expected_subtotal = sum(float(item.extended_price or 0) for item in items)
                
                # Allow small floating point differences
                actual_subtotal = float(order.subtotal)
                if abs(actual_subtotal - expected_subtotal) > 0.01:
                    pytest.fail(
                        f"Order {order.order_number} subtotal mismatch: "
                        f"expected {expected_subtotal}, got {order.subtotal}"
                    )
    
    def test_category_spending_calculation(self):
        """Test category spending calculation."""
        # This test checks if category spending can be calculated
        # Even if no categories are assigned, the query should not fail
        
        category_spending = analytics_service.get_category_spending()
        
        # Should return empty list or populated list, but not fail
        assert isinstance(category_spending, list), "Category spending should return a list"
        
        # If there are results, verify structure
        for item in category_spending:
            assert 'category' in item, "Category spending item should have 'category' field"
            assert 'total_spent' in item, "Category spending item should have 'total_spent' field"
            assert 'unique_parts' in item, "Category spending item should have 'unique_parts' field"
    
    def test_spending_trend_has_multiple_datapoints(self):
        """Test that spending trend returns reasonable data."""
        spending_trend = analytics_service.get_spending_trend(period="month", lookback_periods=6)
        
        assert isinstance(spending_trend, list), "Spending trend should return a list"
        
        # Should have at least some data if there are orders
        with Session(engine) as session:
            order_count = session.exec(select(OrderModel)).all()
            
            if len(order_count) > 0:
                # Should have at least one datapoint
                assert len(spending_trend) > 0, "Should have spending trend data when orders exist"
                
                # Verify datapoint structure
                for point in spending_trend:
                    assert 'period' in point, "Trend point should have 'period' field"
                    assert 'total_spent' in point, "Trend point should have 'total_spent' field"
                    assert 'order_count' in point, "Trend point should have 'order_count' field"
    
    def test_low_stock_algorithm_reasonable(self):
        """Test that low stock algorithm produces reasonable suggestions."""
        low_stock = analytics_service.get_low_stock_parts()
        
        assert isinstance(low_stock, list), "Low stock should return a list"
        
        # Test that suggestions are reasonable (not negative, not absurdly high)
        for part in low_stock:
            assert part['suggested_reorder_quantity'] > 0, \
                f"Suggested reorder should be positive for {part['name']}"
            
            # Suggestion should be reasonable relative to current stock and average order
            current = part['current_quantity']
            avg_order = part['average_order_quantity']
            suggested = part['suggested_reorder_quantity']
            
            # Suggestion should be at least as much as average order
            assert suggested >= avg_order, \
                f"Suggested ({suggested}) should be >= avg order ({avg_order}) for {part['name']}"
            
            # But not absurdly high (more than 10x current stock unless current is very low)
            if current > 10:
                assert suggested <= current * 10, \
                    f"Suggested ({suggested}) too high vs current ({current}) for {part['name']}"