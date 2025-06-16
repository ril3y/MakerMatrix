"""
Integration tests for analytics edge cases and null handling.

Tests scenarios where analytics data might be null or missing,
ensuring the system handles these gracefully.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, CategoryModel, LocationModel, engine
from MakerMatrix.models.order_models import OrderModel, OrderItemModel
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_empty_database():
    """Set up a completely empty database to test null scenarios."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Create default roles and admin user
    user_repo = UserRepository()
    user_repo.engine = engine
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # Cleanup
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token(setup_empty_database):
    """Get admin authentication token."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": "admin", "password_change_required": False})
    return token


@pytest.fixture
def auth_headers(admin_token):
    """Authentication headers for API calls."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestAnalyticsEdgeCases:
    """Test analytics edge cases with empty/null data."""
    
    def test_dashboard_summary_empty_database(self, auth_headers):
        """Test dashboard summary with completely empty database."""
        response = client.get("/api/analytics/dashboard/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        summary = data["data"]
        
        # Test all expected fields exist and handle nulls properly
        assert "period" in summary
        assert "spending_by_supplier" in summary
        assert "spending_trend" in summary
        assert "frequent_parts" in summary
        assert "low_stock_count" in summary
        assert "low_stock_parts" in summary
        assert "inventory_value" in summary
        assert "category_spending" in summary
        
        # Test that empty lists are returned (not null)
        assert isinstance(summary["spending_by_supplier"], list)
        assert isinstance(summary["spending_trend"], list)
        assert isinstance(summary["frequent_parts"], list)
        assert isinstance(summary["low_stock_parts"], list)
        assert isinstance(summary["category_spending"], list)
        
        # Test that counts are integers (not null)
        assert isinstance(summary["low_stock_count"], int)
        assert summary["low_stock_count"] == 0
        
        # Test inventory value structure and null handling
        inventory_value = summary["inventory_value"]
        assert isinstance(inventory_value, dict)
        assert "total_value" in inventory_value
        assert "priced_parts" in inventory_value
        assert "unpriced_parts" in inventory_value
        assert "total_units" in inventory_value
        
        # These should be numbers, not None
        assert isinstance(inventory_value["total_value"], (int, float))
        assert isinstance(inventory_value["priced_parts"], int)
        assert isinstance(inventory_value["unpriced_parts"], int)
        assert isinstance(inventory_value["total_units"], (int, type(None)))  # Allow 0 or None
        
        # Values should be 0 for empty database
        assert inventory_value["total_value"] == 0
        assert inventory_value["priced_parts"] == 0
        # unpriced_parts might be > 0 if there are parts without orders
        assert inventory_value["total_units"] is not None  # Should not be None after our fix
    
    def test_inventory_value_no_orders(self, auth_headers, setup_empty_database):
        """Test inventory value calculation with parts but no orders."""
        # Add some parts without any orders
        with Session(engine) as session:
            # Create a location first
            location = LocationModel(name="Test Location", description="Test")
            session.add(location)
            session.commit()
            session.refresh(location)
            
            # Create parts without any order history
            parts = [
                PartModel(
                    part_name=f"Test Part {i}",
                    part_number=f"TP{i:03d}",
                    quantity=10,
                    location_id=location.id
                )
                for i in range(3)
            ]
            
            for part in parts:
                session.add(part)
            session.commit()
        
        # Test inventory value endpoint
        response = client.get("/api/analytics/inventory/value", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        inventory_value = data["data"]
        # Should handle no pricing data gracefully
        assert inventory_value["total_value"] == 0  # No pricing data
        assert inventory_value["priced_parts"] == 0  # No parts with pricing
        assert inventory_value["unpriced_parts"] == 3  # All 3 parts are unpriced
        assert inventory_value["total_units"] == 0  # No units with pricing data
    
    def test_part_order_frequency_no_orders(self, auth_headers, setup_empty_database):
        """Test part order frequency with parts but no orders."""
        # Add some parts without any orders
        with Session(engine) as session:
            location = LocationModel(name="Test Location", description="Test")
            session.add(location)
            session.commit()
            session.refresh(location)
            
            parts = [
                PartModel(
                    part_name=f"Test Part {i}",
                    part_number=f"TP{i:03d}",
                    quantity=10,
                    location_id=location.id
                )
                for i in range(3)
            ]
            
            for part in parts:
                session.add(part)
            session.commit()
        
        # Test part order frequency endpoint
        response = client.get("/api/analytics/parts/order-frequency", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0  # No parts with orders
    
    def test_spending_by_supplier_no_orders(self, auth_headers, setup_empty_database):
        """Test spending by supplier with no orders."""
        response = client.get("/api/analytics/spending/by-supplier", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0  # No suppliers with orders
    
    def test_spending_trend_no_orders(self, auth_headers, setup_empty_database):
        """Test spending trend with no orders."""
        response = client.get(
            "/api/analytics/spending/trend",
            params={"period": "month", "lookback_periods": 6},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0  # No spending data
    
    def test_low_stock_parts_no_order_history(self, auth_headers, setup_empty_database):
        """Test low stock calculation with parts but no order history."""
        # Add parts with low quantities but no order history
        with Session(engine) as session:
            location = LocationModel(name="Test Location", description="Test")
            session.add(location)
            session.commit()
            session.refresh(location)
            
            # Create parts with low quantities
            parts = [
                PartModel(
                    part_name=f"Low Stock Part {i}",
                    part_number=f"LSP{i:03d}",
                    quantity=1,  # Low quantity
                    location_id=location.id
                )
                for i in range(2)
            ]
            
            for part in parts:
                session.add(part)
            session.commit()
        
        # Test low stock endpoint
        response = client.get("/api/analytics/inventory/low-stock", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        # Should return empty list since we need order history to calculate averages
        assert len(data["data"]) == 0
    
    def test_category_spending_no_orders(self, auth_headers, setup_empty_database):
        """Test category spending with categories but no orders."""
        # Add categories and parts but no orders
        with Session(engine) as session:
            location = LocationModel(name="Test Location", description="Test")
            session.add(location)
            session.commit()
            session.refresh(location)
            
            # Create category
            category = CategoryModel(name="Test Category", description="Test")
            session.add(category)
            session.commit()
            session.refresh(category)
            
            # Create part with category
            part = PartModel(
                part_name="Test Part",
                part_number="TP001",
                quantity=10,
                location_id=location.id
            )
            part.categories = [category]
            session.add(part)
            session.commit()
        
        # Test category spending endpoint
        response = client.get("/api/analytics/spending/by-category", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0  # No category spending without orders
    
    def test_price_trends_no_orders(self, auth_headers, setup_empty_database):
        """Test price trends with no orders."""
        response = client.get("/api/analytics/prices/trends", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0  # No price trends without orders
    
    def test_analytics_api_parameter_validation(self, auth_headers):
        """Test that analytics endpoints handle invalid parameters gracefully."""
        
        # Test invalid period for spending trend
        response = client.get(
            "/api/analytics/spending/trend",
            params={"period": "invalid", "lookback_periods": 6},
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error
        
        # Test negative lookback periods
        response = client.get(
            "/api/analytics/spending/trend",
            params={"period": "month", "lookback_periods": -1},
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error
        
        # Test invalid part_id for price trends
        response = client.get(
            "/api/analytics/prices/trends",
            params={"part_id": "invalid-uuid"},
            headers=auth_headers
        )
        assert response.status_code == 200  # Should work but return empty results
        
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 0
    
    def test_dashboard_summary_null_safety_comprehensive(self, auth_headers, setup_empty_database):
        """Comprehensive test for null safety in dashboard summary."""
        response = client.get("/api/analytics/dashboard/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        summary = data["data"]
        
        # Recursively check that no values are None where they shouldn't be
        def check_no_unexpected_nulls(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if key in ["total_units"] and value is None:
                        # This was the problematic field - should now be fixed
                        pytest.fail(f"Found None at {new_path} - this should be fixed")
                    elif isinstance(value, (dict, list)):
                        check_no_unexpected_nulls(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_no_unexpected_nulls(item, f"{path}[{i}]")
        
        check_no_unexpected_nulls(summary)
        
        # Specifically check the inventory_value.total_units field
        assert summary["inventory_value"]["total_units"] is not None
        assert isinstance(summary["inventory_value"]["total_units"], (int, float))