"""
Integration tests for analytics endpoints.
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
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run
    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def auth_headers():
    """Get authentication headers for test requests."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_parts(db_session):
    """Create sample parts for testing."""
    parts = []
    for i in range(3):
        part = PartModel(
            part_name=f"Test Part {i}",
            part_number=f"TP{i:03d}",
            quantity=10 + i * 5,
            minimum_quantity=5
        )
        db_session.add(part)
        parts.append(part)
    
    db_session.commit()
    return parts


@pytest.fixture
def sample_orders(db_session, sample_parts):
    """Create sample orders for testing."""
    orders = []
    suppliers = ["DigiKey", "Mouser", "LCSC"]
    
    # Create orders over the past 60 days
    for i in range(10):
        order_date = datetime.now() - timedelta(days=i * 6)
        order = OrderModel(
            order_date=order_date,
            supplier=suppliers[i % 3],
            order_number=f"ORD{i:04d}",
            status="completed",
            total=100.0 + i * 10
        )
        db_session.add(order)
        db_session.flush()
        
        # Add order items
        for j, part in enumerate(sample_parts[:2]):
            item = OrderItemModel(
                order_id=order.id,
                part_id=part.id,
                supplier_part_number=f"{suppliers[i % 3]}-{part.part_number}",
                quantity_ordered=5 + j,
                quantity_received=5 + j,
                unit_price=10.0 + i * 0.5,
                extended_price=(5 + j) * (10.0 + i * 0.5),
                status="received"
            )
            db_session.add(item)
        
        orders.append(order)
    
    db_session.commit()
    return orders


def test_get_spending_by_supplier(setup_database, auth_headers, sample_orders):
    """Test spending by supplier endpoint."""
    response = client.get("/api/analytics/spending/by-supplier", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    
    suppliers = data["data"]
    assert len(suppliers) > 0
    
    # Check supplier data structure
    for supplier in suppliers:
        assert "supplier" in supplier
        assert "total_spent" in supplier
        assert "order_count" in supplier
        assert supplier["total_spent"] > 0
        assert supplier["order_count"] > 0


def test_get_spending_trend(setup_database, auth_headers, sample_orders):
    """Test spending trend endpoint."""
    response = client.get(
        "/api/analytics/spending/trend",
        params={"period": "week", "lookback_periods": 4},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    
    trends = data["data"]
    assert len(trends) > 0
    
    # Check trend data structure
    for trend in trends:
        assert "period" in trend
        assert "total_spent" in trend
        assert "order_count" in trend


def test_get_price_trends(setup_database, auth_headers, sample_orders, sample_parts):
    """Test price trends endpoint."""
    part_id = str(sample_parts[0].id)
    
    response = client.get(
        "/api/analytics/prices/trends",
        params={"part_id": part_id, "limit": 20},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    
    trends = data["data"]
    assert len(trends) > 0
    
    # Check price trend data structure
    for trend in trends:
        assert "part_id" in trend
        assert "part_name" in trend
        assert "part_number" in trend
        assert "unit_price" in trend
        assert "order_date" in trend
        assert "supplier" in trend


def test_get_dashboard_summary(setup_database, auth_headers, sample_orders):
    """Test dashboard summary endpoint."""
    response = client.get("/api/analytics/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    
    summary = data["data"]
    assert "period" in summary
    assert "spending_by_supplier" in summary
    assert "spending_trend" in summary
    assert "frequent_parts" in summary
    assert "low_stock_count" in summary
    assert "low_stock_parts" in summary
    assert "inventory_value" in summary
    assert "category_spending" in summary


def test_get_inventory_value(setup_database, auth_headers, sample_orders):
    """Test inventory value endpoint."""
    response = client.get("/api/analytics/inventory/value", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    
    value = data["data"]
    assert "total_value" in value
    assert "priced_parts" in value
    assert "unpriced_parts" in value
    assert "total_units" in value


def test_get_low_stock_parts(setup_database, auth_headers, sample_parts, sample_orders):
    """Test low stock parts endpoint."""
    # Update one part to have low stock
    with Session(engine) as session:
        part = session.get(PartModel, sample_parts[0].id)
        part.quantity = 1
        session.commit()
    
    response = client.get(
        "/api/analytics/inventory/low-stock",
        params={"threshold_multiplier": 1.5},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    
    low_stock = data["data"]
    # Should have at least one low stock part
    assert len(low_stock) > 0
    
    for part in low_stock:
        assert "part_id" in part
        assert "name" in part
        assert "current_quantity" in part
        assert "average_order_quantity" in part
        assert "suggested_reorder_quantity" in part


def test_spending_trend_sqlite_compatibility(setup_database, auth_headers, sample_orders):
    """Test that spending trend works with SQLite date functions."""
    # Test different period types to ensure SQLite compatibility
    periods = ["day", "week", "month", "year"]
    
    for period in periods:
        response = client.get(
            "/api/analytics/spending/trend",
            params={"period": period, "lookback_periods": 3},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed for period: {period}"
        
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        
        trends = data["data"]
        # Check that we got valid date strings
        for trend in trends:
            assert "period" in trend
            # Try to parse the date to ensure it's valid
            try:
                datetime.fromisoformat(trend["period"])
            except ValueError:
                pytest.fail(f"Invalid date format for period {period}: {trend['period']}")