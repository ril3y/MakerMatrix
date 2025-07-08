"""
Integration tests for database clear operations.

Tests all the clear endpoints including parts, suppliers, and categories.
Ensures proper admin authentication, activity logging, and data cleanup.
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from typing import Dict, Any

from MakerMatrix.main import app
from MakerMatrix.models.models import *
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.supplier_config_models import SupplierConfigModel, SupplierCredentialsModel
from MakerMatrix.models.rate_limiting_models import SupplierUsageTrackingModel, SupplierRateLimitModel, SupplierUsageSummaryModel
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.services.activity_service import get_activity_service


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def admin_headers(test_client):
    """Login as admin and get authorization headers."""
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    response = test_client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def non_admin_headers(test_client):
    """Create a non-admin user and get authorization headers."""
    # First, create a non-admin user using admin credentials
    admin_login = {"username": "admin", "password": "Admin123!"}
    admin_response = test_client.post("/auth/login", data=admin_login)
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a regular user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "roles": ["user"]
    }
    test_client.post("/auth/register", json=user_data, headers=admin_headers)
    
    # Login as the regular user
    login_data = {"username": "testuser", "password": "TestPass123!"}
    response = test_client.post("/auth/login", data=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_test_data():
    """Set up test data for clearing operations."""
    with Session(engine) as session:
        # Create test parts
        test_part = PartModel(
            part_name="Test_Clear_Part_1",
            part_number="TCP001",
            description="Test part for clear operations",
            quantity=10,
            supplier="LCSC"
        )
        session.add(test_part)
        
        # Create test category
        test_category = CategoryModel(
            name="Test_Clear_Category",
            description="Test category for clear operations"
        )
        session.add(test_category)
        
        # Create test supplier config
        test_supplier_config = SupplierConfigModel(
            supplier_name="test_supplier",
            config_data={"api_key": "test_key", "base_url": "test.com"}
        )
        session.add(test_supplier_config)
        
        # Create test supplier credentials
        test_credentials = SupplierCredentialsModel(
            supplier_name="test_supplier",
            credentials_data_encrypted=b"encrypted_test_data"
        )
        session.add(test_credentials)
        
        session.commit()


def get_data_counts():
    """Get current counts of various data types."""
    with Session(engine) as session:
        parts_count = len(session.exec(select(PartModel)).all())
        categories_count = len(session.exec(select(CategoryModel)).all())
        supplier_configs_count = len(session.exec(select(SupplierConfigModel)).all())
        supplier_credentials_count = len(session.exec(select(SupplierCredentialsModel)).all())
        
        return {
            "parts": parts_count,
            "categories": categories_count,
            "supplier_configs": supplier_configs_count,
            "supplier_credentials": supplier_credentials_count
        }


class TestClearParts:
    """Test clearing all parts from the database."""
    
    def test_clear_parts_admin_success(self, test_client, admin_headers):
        """Test successful parts clearing by admin user."""
        # Setup test data
        setup_test_data()
        
        # Verify we have parts before clearing
        initial_counts = get_data_counts()
        assert initial_counts["parts"] > 0
        
        # Clear all parts
        response = test_client.delete("/api/parts/clear_all", headers=admin_headers)
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cleared successfully" in data["message"]
        
        # Verify parts are cleared
        final_counts = get_data_counts()
        assert final_counts["parts"] == 0
    
    def test_clear_parts_non_admin_forbidden(self, test_client, non_admin_headers):
        """Test that non-admin users cannot clear parts."""
        response = test_client.delete("/api/parts/clear_all", headers=non_admin_headers)
        assert response.status_code == 403
    
    def test_clear_parts_unauthenticated_unauthorized(self, test_client):
        """Test that unauthenticated requests are rejected."""
        response = test_client.delete("/api/parts/clear_all")
        assert response.status_code == 401


class TestClearSuppliers:
    """Test clearing all supplier data from the database."""
    
    def test_clear_suppliers_admin_success(self, test_client, admin_headers):
        """Test successful supplier data clearing by admin user."""
        # Setup test data
        setup_test_data()
        
        # Verify we have supplier data before clearing
        initial_counts = get_data_counts()
        assert initial_counts["supplier_configs"] > 0 or initial_counts["supplier_credentials"] > 0
        
        # Clear all supplier data
        response = test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cleared successfully" in data["message"]
        
        # Verify supplier data is cleared
        final_counts = get_data_counts()
        assert final_counts["supplier_configs"] == 0
        assert final_counts["supplier_credentials"] == 0
    
    def test_clear_suppliers_removes_part_supplier_references(self, test_client, admin_headers):
        """Test that clearing suppliers also removes supplier references from parts."""
        # Setup test data with parts that have supplier info
        setup_test_data()
        
        # Verify parts have supplier data
        with Session(engine) as session:
            parts_with_suppliers = session.exec(
                select(PartModel).where(PartModel.supplier.is_not(None))
            ).all()
            assert len(parts_with_suppliers) > 0
        
        # Clear supplier data
        response = test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)
        assert response.status_code == 200
        
        # Verify supplier references are removed from parts
        with Session(engine) as session:
            parts_with_suppliers = session.exec(
                select(PartModel).where(PartModel.supplier.is_not(None))
            ).all()
            assert len(parts_with_suppliers) == 0
    
    def test_clear_suppliers_non_admin_forbidden(self, test_client, non_admin_headers):
        """Test that non-admin users cannot clear suppliers."""
        response = test_client.delete("/api/utility/clear_suppliers", headers=non_admin_headers)
        assert response.status_code == 403


class TestClearCategories:
    """Test clearing all categories from the database."""
    
    def test_clear_categories_admin_success(self, test_client, admin_headers):
        """Test successful categories clearing by admin user."""
        # Setup test data
        setup_test_data()
        
        # Verify we have categories before clearing
        initial_counts = get_data_counts()
        assert initial_counts["categories"] > 0
        
        # Clear all categories
        response = test_client.delete("/api/categories/delete_all_categories", headers=admin_headers)
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted_count" in data["data"]
        
        # Verify categories are cleared
        final_counts = get_data_counts()
        assert final_counts["categories"] == 0
    
    def test_clear_categories_non_admin_forbidden(self, test_client, non_admin_headers):
        """Test that non-admin users cannot clear categories."""
        response = test_client.delete("/api/categories/delete_all_categories", headers=non_admin_headers)
        assert response.status_code == 403


class TestActivityLogging:
    """Test that clear operations are properly logged."""
    
    def test_clear_operations_are_logged(self, test_client, admin_headers):
        """Test that all clear operations create activity log entries."""
        # Setup test data
        setup_test_data()
        
        activity_service = get_activity_service()
        
        # Clear parts and check logging
        response = test_client.delete("/api/parts/clear_all", headers=admin_headers)
        assert response.status_code == 200
        
        # Check for activity log entry
        recent_activities = activity_service.get_recent_activities(limit=10, hours=1)
        parts_clear_activities = [
            activity for activity in recent_activities 
            if activity.action == "cleared" and activity.entity_type == "parts"
        ]
        assert len(parts_clear_activities) > 0
        
        # Clear suppliers and check logging
        setup_test_data()  # Re-setup supplier data
        response = test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)
        assert response.status_code == 200
        
        # Check for activity log entry
        recent_activities = activity_service.get_recent_activities(limit=10, hours=1)
        supplier_clear_activities = [
            activity for activity in recent_activities 
            if activity.action == "cleared" and activity.entity_type == "supplier_data"
        ]
        assert len(supplier_clear_activities) > 0


class TestClearOperationsIntegration:
    """Integration tests for multiple clear operations."""
    
    def test_clear_all_data_sequence(self, test_client, admin_headers):
        """Test clearing all data types in sequence."""
        # Setup comprehensive test data
        setup_test_data()
        
        # Record initial state
        initial_counts = get_data_counts()
        assert initial_counts["parts"] > 0
        assert initial_counts["categories"] > 0
        
        # Clear in sequence: suppliers, parts, categories
        
        # 1. Clear suppliers
        response = test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)
        assert response.status_code == 200
        
        # 2. Clear parts
        response = test_client.delete("/api/parts/clear_all", headers=admin_headers)
        assert response.status_code == 200
        
        # 3. Clear categories
        response = test_client.delete("/api/categories/delete_all_categories", headers=admin_headers)
        assert response.status_code == 200
        
        # Verify all data is cleared
        final_counts = get_data_counts()
        assert final_counts["parts"] == 0
        assert final_counts["categories"] == 0
        assert final_counts["supplier_configs"] == 0
        assert final_counts["supplier_credentials"] == 0
    
    def test_error_handling_on_empty_database(self, test_client, admin_headers):
        """Test that clear operations handle empty database gracefully."""
        # Ensure database is empty first
        test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)
        test_client.delete("/api/parts/clear_all", headers=admin_headers)
        test_client.delete("/api/categories/delete_all_categories", headers=admin_headers)
        
        # Try clearing again - should not fail
        response = test_client.delete("/api/parts/clear_all", headers=admin_headers)
        assert response.status_code == 200
        
        response = test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)
        assert response.status_code == 200
        
        response = test_client.delete("/api/categories/delete_all_categories", headers=admin_headers)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])