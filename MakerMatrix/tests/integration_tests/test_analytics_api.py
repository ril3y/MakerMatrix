"""
Integration tests for analytics API endpoints.

Tests all analytics endpoints with various query parameters
and verifies correct data aggregation and response formats.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from MakerMatrix.models.models import (
    PartModel, CategoryModel, LocationModel, PartCategoryLink
)
from MakerMatrix.models.order_models import (
    OrderModel, OrderItemModel, OrderSummary
)
from MakerMatrix.repositories.part_repository import PartRepository
from MakerMatrix.repositories.location_repository import LocationRepository
from MakerMatrix.repositories.category_repositories import CategoryRepository


@pytest.fixture
def sample_analytics_data(test_session):
    """Create sample data for analytics testing."""
    # Create locations
    location_repo = LocationRepository()
    location1 = location_repo.add_location(test_session, {
        "name": "Storage A",
        "location_type": "storage"
    })
    
    # Create categories
    category_repo = CategoryRepository()
    electronics = category_repo.add_category(test_session, {"name": "Electronics"})
    resistors = category_repo.add_category(test_session, {"name": "Resistors"})
    capacitors = category_repo.add_category(test_session, {"name": "Capacitors"})
    
    # Create parts
    part_repo = PartRepository()
    
    # Part 1: Frequently ordered resistor
    part1 = part_repo.add_part(test_session, {
        "name": "10K Resistor",
        "part_number": "RES-10K",
        "quantity": 50,
        "minimum_quantity": 100,
        "location_id": location1.id
    })
    link1 = PartCategoryLink(part_id=part1.id, category_id=electronics.id)
    link2 = PartCategoryLink(part_id=part1.id, category_id=resistors.id)
    test_session.add_all([link1, link2])
    
    # Part 2: Low stock capacitor
    part2 = part_repo.add_part(test_session, {
        "name": "100uF Capacitor",
        "part_number": "CAP-100UF",
        "quantity": 5,
        "minimum_quantity": 20,
        "location_id": location1.id
    })
    link3 = PartCategoryLink(part_id=part2.id, category_id=electronics.id)
    link4 = PartCategoryLink(part_id=part2.id, category_id=capacitors.id)
    test_session.add_all([link3, link4])
    
    # Part 3: Well-stocked part
    part3 = part_repo.add_part(test_session, {
        "name": "LED Red",
        "part_number": "LED-RED",
        "quantity": 500,
        "location_id": location1.id
    })
    link5 = PartCategoryLink(part_id=part3.id, category_id=electronics.id)
    test_session.add(link5)
    
    # Create orders with different dates
    now = datetime.now()
    
    # Order 1: LCSC order from 30 days ago
    order1 = OrderModel(
        order_number="LCSC-001",
        order_date=now - timedelta(days=30),
        supplier="LCSC",
        status="completed",
        total=125.50,
        subtotal=120.00,
        tax=5.50,
        shipping=0.00,
        currency="USD"
    )
    test_session.add(order1)
    test_session.flush()
    
    # Order items for order 1
    order1_item1 = OrderItemModel(
        order_id=order1.id,
        part_id=part1.id,
        supplier_part_number="C12345",
        quantity=100,
        unit_price=0.02,
        extended_price=2.00
    )
    order1_item2 = OrderItemModel(
        order_id=order1.id,
        part_id=part2.id,
        supplier_part_number="C67890",
        quantity=50,
        unit_price=2.36,
        extended_price=118.00
    )
    test_session.add_all([order1_item1, order1_item2])
    
    # Order 2: Mouser order from 15 days ago
    order2 = OrderModel(
        order_number="MOUSER-001",
        order_date=now - timedelta(days=15),
        supplier="Mouser",
        status="completed",
        total=89.75,
        subtotal=80.00,
        tax=4.75,
        shipping=5.00,
        currency="USD"
    )
    test_session.add(order2)
    test_session.flush()
    
    # Order items for order 2
    order2_item1 = OrderItemModel(
        order_id=order2.id,
        part_id=part1.id,
        supplier_part_number="123-456",
        quantity=200,
        unit_price=0.025,  # Price increased
        extended_price=5.00
    )
    order2_item2 = OrderItemModel(
        order_id=order2.id,
        part_id=part3.id,
        supplier_part_number="789-012",
        quantity=100,
        unit_price=0.75,
        extended_price=75.00
    )
    test_session.add_all([order2_item1, order2_item2])
    
    # Order 3: DigiKey order from 7 days ago
    order3 = OrderModel(
        order_number="DIGIKEY-001",
        order_date=now - timedelta(days=7),
        supplier="DigiKey",
        status="completed",
        total=156.25,
        subtotal=145.00,
        tax=11.25,
        shipping=0.00,
        currency="USD"
    )
    test_session.add(order3)
    test_session.flush()
    
    # Order items for order 3
    order3_item1 = OrderItemModel(
        order_id=order3.id,
        part_id=part1.id,
        supplier_part_number="DK-10K",
        quantity=500,
        unit_price=0.018,  # Price decreased
        extended_price=9.00
    )
    order3_item2 = OrderItemModel(
        order_id=order3.id,
        part_id=part2.id,
        supplier_part_number="DK-100UF",
        quantity=30,
        unit_price=2.20,  # Price decreased
        extended_price=66.00
    )
    order3_item3 = OrderItemModel(
        order_id=order3.id,
        part_id=part3.id,
        supplier_part_number="DK-LED",
        quantity=100,
        unit_price=0.70,
        extended_price=70.00
    )
    test_session.add_all([order3_item1, order3_item2, order3_item3])
    
    # Create OrderSummary records
    summary1 = OrderSummary(
        part_id=part1.id,
        last_order_date=now - timedelta(days=7),
        last_order_price=0.018,
        last_order_number="DIGIKEY-001",
        lowest_price=0.018,
        highest_price=0.025,
        average_price=0.021,
        total_orders=3
    )
    summary2 = OrderSummary(
        part_id=part2.id,
        last_order_date=now - timedelta(days=7),
        last_order_price=2.20,
        last_order_number="DIGIKEY-001",
        lowest_price=2.20,
        highest_price=2.36,
        average_price=2.28,
        total_orders=2
    )
    summary3 = OrderSummary(
        part_id=part3.id,
        last_order_date=now - timedelta(days=7),
        last_order_price=0.70,
        last_order_number="DIGIKEY-001",
        lowest_price=0.70,
        highest_price=0.75,
        average_price=0.725,
        total_orders=2
    )
    test_session.add_all([summary1, summary2, summary3])
    
    test_session.commit()
    
    return {
        "parts": [part1, part2, part3],
        "orders": [order1, order2, order3],
        "categories": [electronics, resistors, capacitors],
        "location": location1
    }


class TestAnalyticsAPI:
    """Test analytics API endpoints."""
    
    def test_spending_by_supplier(self, auth_client, sample_analytics_data):
        """Test spending by supplier endpoint."""
        response = auth_client.get("/api/analytics/spending/by-supplier")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        
        suppliers = data["data"]
        assert len(suppliers) == 3
        
        # Check supplier data
        supplier_map = {s["supplier"]: s for s in suppliers}
        
        assert "DigiKey" in supplier_map
        assert supplier_map["DigiKey"]["total_spent"] == pytest.approx(156.25)
        assert supplier_map["DigiKey"]["order_count"] == 1
        
        assert "LCSC" in supplier_map
        assert supplier_map["LCSC"]["total_spent"] == pytest.approx(125.50)
        assert supplier_map["LCSC"]["order_count"] == 1
        
        assert "Mouser" in supplier_map
        assert supplier_map["Mouser"]["total_spent"] == pytest.approx(89.75)
        assert supplier_map["Mouser"]["order_count"] == 1
    
    def test_spending_by_supplier_date_filter(self, auth_client, sample_analytics_data):
        """Test spending by supplier with date filters."""
        # Last 14 days - should exclude LCSC order
        start_date = (datetime.now() - timedelta(days=14)).isoformat()
        response = auth_client.get(
            f"/api/analytics/spending/by-supplier?start_date={start_date}"
        )
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert len(data) == 2
        supplier_names = [s["supplier"] for s in data]
        assert "LCSC" not in supplier_names
        assert "DigiKey" in supplier_names
        assert "Mouser" in supplier_names
    
    def test_spending_trend(self, auth_client, sample_analytics_data):
        """Test spending trend endpoint."""
        response = auth_client.get("/api/analytics/spending/trend?period=week&lookback_periods=6")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        trends = data["data"]
        assert len(trends) > 0
        
        # Verify trend data structure
        for trend in trends:
            assert "period" in trend
            assert "total_spent" in trend
            assert "order_count" in trend
            assert isinstance(trend["total_spent"], (int, float))
            assert isinstance(trend["order_count"], int)
    
    def test_part_order_frequency(self, auth_client, sample_analytics_data):
        """Test part order frequency endpoint."""
        response = auth_client.get("/api/analytics/parts/order-frequency?min_orders=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        parts = data["data"]
        assert len(parts) == 3  # All parts have at least 2 orders
        
        # Most frequently ordered should be first
        assert parts[0]["name"] == "10K Resistor"
        assert parts[0]["total_orders"] == 3
        assert parts[0]["average_price"] == pytest.approx(0.021)
        
        # Check all required fields
        for part in parts:
            assert "part_id" in part
            assert "name" in part
            assert "part_number" in part
            assert "current_quantity" in part
            assert "total_orders" in part
            assert "average_price" in part
            assert "last_order_date" in part
    
    def test_price_trends(self, auth_client, sample_analytics_data):
        """Test price trends endpoint."""
        # Get price trends for resistor
        part_id = sample_analytics_data["parts"][0].id
        response = auth_client.get(f"/api/analytics/prices/trends?part_id={part_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        trends = data["data"]
        assert len(trends) == 3  # 3 orders for this part
        
        # Should be ordered by date descending
        dates = [datetime.fromisoformat(t["order_date"]) for t in trends]
        assert dates == sorted(dates, reverse=True)
        
        # Verify price progression
        assert trends[0]["unit_price"] == 0.018  # Most recent
        assert trends[1]["unit_price"] == 0.025
        assert trends[2]["unit_price"] == 0.02   # Oldest
    
    def test_price_trends_by_supplier(self, auth_client, sample_analytics_data):
        """Test price trends filtered by supplier."""
        response = auth_client.get("/api/analytics/prices/trends?supplier=LCSC")
        assert response.status_code == 200
        
        data = response.json()
        trends = data["data"]
        
        # Should only show LCSC orders
        for trend in trends:
            assert trend["supplier"] == "LCSC"
    
    def test_low_stock_parts(self, auth_client, sample_analytics_data):
        """Test low stock parts detection."""
        response = auth_client.get("/api/analytics/inventory/low-stock")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        low_stock = data["data"]
        assert len(low_stock) >= 1
        
        # Capacitor should be in low stock
        capacitor = next((p for p in low_stock if p["name"] == "100uF Capacitor"), None)
        assert capacitor is not None
        assert capacitor["current_quantity"] == 5
        assert capacitor["minimum_quantity"] == 20
        assert capacitor["average_order_quantity"] == 40  # (50 + 30) / 2
        assert capacitor["suggested_reorder_quantity"] == 80  # avg * 2
    
    def test_category_spending(self, auth_client, sample_analytics_data):
        """Test spending by category."""
        response = auth_client.get("/api/analytics/spending/by-category")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        categories = data["data"]
        assert len(categories) > 0
        
        # Electronics should have the most spending
        electronics = next((c for c in categories if c["category"] == "Electronics"), None)
        assert electronics is not None
        assert electronics["total_spent"] > 0
        assert electronics["unique_parts"] == 3
    
    def test_inventory_value(self, auth_client, sample_analytics_data):
        """Test inventory value calculation."""
        response = auth_client.get("/api/analytics/inventory/value")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        value = data["data"]
        assert "total_value" in value
        assert "priced_parts" in value
        assert "unpriced_parts" in value
        assert "total_units" in value
        
        # Calculate expected value
        # Part1: 50 units * $0.021 avg = $1.05
        # Part2: 5 units * $2.28 avg = $11.40
        # Part3: 500 units * $0.725 avg = $362.50
        expected_value = 1.05 + 11.40 + 362.50
        assert value["total_value"] == pytest.approx(expected_value, rel=0.01)
        assert value["priced_parts"] == 3
        assert value["unpriced_parts"] == 0
        assert value["total_units"] == 555
    
    def test_dashboard_summary(self, auth_client, sample_analytics_data):
        """Test dashboard summary endpoint."""
        response = auth_client.get("/api/analytics/dashboard/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        summary = data["data"]
        assert "period" in summary
        assert "spending_by_supplier" in summary
        assert "spending_trend" in summary
        assert "frequent_parts" in summary
        assert "low_stock_count" in summary
        assert "low_stock_parts" in summary
        assert "inventory_value" in summary
        assert "category_spending" in summary
        
        # Verify period dates
        assert "start_date" in summary["period"]
        assert "end_date" in summary["period"]
        
        # Verify data is populated
        assert len(summary["spending_by_supplier"]) > 0
        assert len(summary["spending_trend"]) > 0
        assert len(summary["frequent_parts"]) > 0
        assert summary["low_stock_count"] >= 1
        assert len(summary["category_spending"]) > 0
    
    def test_analytics_without_auth(self, client):
        """Test that analytics endpoints require authentication."""
        endpoints = [
            "/api/analytics/spending/by-supplier",
            "/api/analytics/spending/trend",
            "/api/analytics/parts/order-frequency",
            "/api/analytics/prices/trends",
            "/api/analytics/inventory/low-stock",
            "/api/analytics/spending/by-category",
            "/api/analytics/inventory/value",
            "/api/analytics/dashboard/summary"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
    
    def test_analytics_with_empty_data(self, auth_client):
        """Test analytics endpoints with no data."""
        # All endpoints should return empty but valid responses
        response = auth_client.get("/api/analytics/spending/by-supplier")
        assert response.status_code == 200
        assert response.json()["data"] == []
        
        response = auth_client.get("/api/analytics/inventory/value")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_value"] == 0
        assert data["priced_parts"] == 0