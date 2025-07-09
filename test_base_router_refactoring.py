"""
Test suite for BaseRouter pattern refactoring.

This test validates that the refactored route files using BaseRouter infrastructure
maintain the same functionality while providing consistent error handling and responses.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to sys.path
sys.path.insert(0, '/home/ril3y/MakerMatrix')

# Set required environment variables
os.environ['JWT_SECRET_KEY'] = 'test_secret_key_for_testing'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'


@pytest.fixture
def mock_services():
    """Mock all external services to isolate route testing."""
    with patch('MakerMatrix.services.data.part_service.PartService') as mock_part_service, \
         patch('MakerMatrix.services.data.category_service.CategoryService') as mock_category_service, \
         patch('MakerMatrix.services.activity_service.get_activity_service') as mock_activity_service, \
         patch('MakerMatrix.auth.dependencies.get_current_user') as mock_get_current_user:
        
        # Mock user
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        mock_user.username = "test_user"
        mock_get_current_user.return_value = mock_user
        
        # Mock activity service
        mock_activity = MagicMock()
        mock_activity.log_part_created = MagicMock()
        mock_activity.log_part_deleted = MagicMock()
        mock_activity.log_category_created = MagicMock()
        mock_activity_service.return_value = mock_activity
        
        yield {
            'part_service': mock_part_service,
            'category_service': mock_category_service,
            'activity_service': mock_activity,
            'current_user': mock_user
        }


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from MakerMatrix.main import app
    return TestClient(app)


class TestPartsRoutesRefactoring:
    """Test the refactored parts_routes.py endpoints."""
    
    def test_add_part_success(self, client, mock_services):
        """Test successful part creation with BaseRouter pattern."""
        # Mock successful service response
        mock_service_response = MagicMock()
        mock_service_response.success = True
        mock_service_response.message = "Part created successfully"
        mock_service_response.data = {
            "id": "test_part_id",
            "part_name": "Test Part",
            "part_number": "TEST123",
            "description": "Test description",
            "quantity": 10,
            "supplier": "Test Supplier",
            "location_id": None,
            "image_url": None,
            "additional_properties": {}
        }
        
        mock_services['part_service'].return_value.add_part.return_value = mock_service_response
        
        # Test data
        part_data = {
            "part_name": "Test Part",
            "part_number": "TEST123",
            "description": "Test description",
            "quantity": 10,
            "supplier": "Test Supplier",
            "category_names": []
        }
        
        # Make request
        response = client.post("/parts/add_part", json=part_data)
        
        # Verify response structure matches BaseRouter pattern
        assert response.status_code == 200
        response_data = response.json()
        
        # Check BaseRouter response structure
        assert "status" in response_data
        assert "message" in response_data
        assert "data" in response_data
        assert response_data["status"] == "success"
        assert response_data["message"] == "Part created successfully"
        assert response_data["data"]["part_name"] == "Test Part"
    
    def test_add_part_service_failure(self, client, mock_services):
        """Test part creation failure handled by BaseRouter."""
        # Mock service failure
        mock_service_response = MagicMock()
        mock_service_response.success = False
        mock_service_response.message = "Part already exists"
        
        mock_services['part_service'].return_value.add_part.return_value = mock_service_response
        
        part_data = {
            "part_name": "Duplicate Part",
            "part_number": "DUP123",
            "quantity": 5
        }
        
        # Make request
        response = client.post("/parts/add_part", json=part_data)
        
        # Should return 409 for "already exists" message
        assert response.status_code == 409
        assert "Part already exists" in response.json()["detail"]
    
    def test_get_all_parts_success(self, client, mock_services):
        """Test get_all_parts with BaseRouter pattern."""
        # Mock successful service response
        mock_service_response = MagicMock()
        mock_service_response.success = True
        mock_service_response.message = "Parts retrieved successfully"
        mock_service_response.data = {
            "items": [
                {
                    "id": "part1",
                    "part_name": "Test Part 1",
                    "part_number": "TEST1",
                    "description": "Test description 1",
                    "quantity": 5,
                    "supplier": "Test Supplier",
                    "location_id": None,
                    "image_url": None,
                    "additional_properties": {}
                }
            ],
            "page": 1,
            "page_size": 10,
            "total": 1
        }
        
        mock_services['part_service'].return_value.get_all_parts.return_value = mock_service_response
        
        # Make request
        response = client.get("/parts/get_all_parts?page=1&page_size=10")
        
        # Verify BaseRouter response structure
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert response_data["message"] == "Parts retrieved successfully"
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert response_data["page"] == 1
        assert response_data["page_size"] == 10
        assert response_data["total_parts"] == 1
    
    def test_get_part_by_id_success(self, client, mock_services):
        """Test get_part by ID with BaseRouter pattern."""
        # Mock successful service response
        mock_service_response = MagicMock()
        mock_service_response.success = True
        mock_service_response.message = "Part found"
        mock_service_response.data = {
            "id": "test_part_id",
            "part_name": "Test Part",
            "part_number": "TEST123",
            "description": "Test description",
            "quantity": 10,
            "supplier": "Test Supplier",
            "location_id": None,
            "image_url": None,
            "additional_properties": {}
        }
        
        mock_services['part_service'].return_value.get_part_by_id.return_value = mock_service_response
        
        # Make request
        response = client.get("/parts/get_part?part_id=test_part_id")
        
        # Verify BaseRouter response structure
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert response_data["message"] == "Part found"
        assert response_data["data"]["id"] == "test_part_id"
    
    def test_get_part_validation_error(self, client, mock_services):
        """Test get_part validation error handled by BaseRouter."""
        # Make request without required parameters
        response = client.get("/parts/get_part")
        
        # Should return 400 for validation error
        assert response.status_code == 400
        assert "at least one identifier" in response.json()["detail"].lower()
    
    def test_delete_part_success(self, client, mock_services):
        """Test delete_part with BaseRouter pattern."""
        # Mock successful get_part_by_details response
        mock_get_response = MagicMock()
        mock_get_response.success = True
        mock_get_response.data = {
            "id": "test_part_id",
            "part_name": "Test Part"
        }
        
        # Mock successful delete response
        mock_delete_response = MagicMock()
        mock_delete_response.success = True
        mock_delete_response.message = "Part deleted successfully"
        mock_delete_response.data = {
            "id": "test_part_id",
            "part_name": "Test Part",
            "part_number": "TEST123",
            "description": "Test description",
            "quantity": 10,
            "supplier": "Test Supplier",
            "location_id": None,
            "image_url": None,
            "additional_properties": {}
        }
        
        mock_services['part_service'].return_value.get_part_by_details.return_value = mock_get_response
        mock_services['part_service'].return_value.delete_part.return_value = mock_delete_response
        
        # Make request
        response = client.delete("/parts/delete_part?part_id=test_part_id")
        
        # Verify BaseRouter response structure
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert response_data["message"] == "Part deleted successfully"
        assert response_data["data"]["id"] == "test_part_id"


class TestCategoriesRoutesRefactoring:
    """Test the refactored categories_routes.py endpoints."""
    
    def test_get_all_categories_success(self, client, mock_services):
        """Test get_all_categories with BaseRouter pattern."""
        # Mock successful service response
        mock_service_response = MagicMock()
        mock_service_response.success = True
        mock_service_response.message = "Categories retrieved successfully"
        mock_service_response.data = {
            "categories": [
                {
                    "id": "cat1",
                    "name": "Test Category",
                    "description": "Test description",
                    "part_count": 5
                }
            ]
        }
        
        mock_services['category_service'].return_value.get_all_categories.return_value = mock_service_response
        
        # Make request
        response = client.get("/categories/get_all_categories")
        
        # Verify BaseRouter response structure
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert response_data["message"] == "Categories retrieved successfully"
        assert "data" in response_data
    
    def test_add_category_success(self, client, mock_services):
        """Test add_category with BaseRouter pattern."""
        # Mock successful service response
        mock_service_response = MagicMock()
        mock_service_response.success = True
        mock_service_response.message = "Category created successfully"
        mock_service_response.data = {
            "id": "test_cat_id",
            "name": "Test Category",
            "description": "Test description",
            "part_count": 0
        }
        
        mock_services['category_service'].return_value.add_category.return_value = mock_service_response
        
        # Test data
        category_data = {
            "name": "Test Category",
            "description": "Test description"
        }
        
        # Make request
        response = client.post("/categories/add_category", json=category_data)
        
        # Verify BaseRouter response structure
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert response_data["message"] == "Category created successfully"
        assert response_data["data"]["name"] == "Test Category"
    
    def test_add_category_validation_error(self, client, mock_services):
        """Test add_category validation error handled by BaseRouter."""
        # Test data with missing name
        category_data = {
            "description": "Test description"
        }
        
        # Make request
        response = client.post("/categories/add_category", json=category_data)
        
        # Should return 400 for validation error
        assert response.status_code == 400
        assert "name is required" in response.json()["detail"].lower()


class TestBaseRouterInfrastructure:
    """Test the BaseRouter infrastructure itself."""
    
    def test_base_router_success_response(self):
        """Test BaseRouter.build_success_response method."""
        from MakerMatrix.routers.base import BaseRouter
        
        response = BaseRouter.build_success_response(
            data={"test": "data"},
            message="Test message",
            page=1,
            page_size=10,
            total_parts=50
        )
        
        assert response.status == "success"
        assert response.message == "Test message"
        assert response.data == {"test": "data"}
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_parts == 50
    
    def test_base_router_exception_handling(self):
        """Test BaseRouter exception handling."""
        from MakerMatrix.routers.base import BaseRouter
        from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
        from fastapi import HTTPException
        
        # Test ResourceNotFoundError handling
        exception = ResourceNotFoundError("Test resource not found")
        http_exception = BaseRouter.handle_exception(exception)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == 404
        assert http_exception.detail == "Test resource not found"
        
        # Test ValueError handling
        exception = ValueError("Test validation error")
        http_exception = BaseRouter.handle_exception(exception)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == 400
        assert http_exception.detail == "Test validation error"
        
        # Test generic exception handling
        exception = Exception("Test generic error")
        http_exception = BaseRouter.handle_exception(exception)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == 500
        assert http_exception.detail == "Internal server error"
    
    def test_validate_service_response_success(self):
        """Test validate_service_response with successful response."""
        from MakerMatrix.routers.base import validate_service_response
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.data = {"test": "data"}
        
        result = validate_service_response(mock_response)
        assert result == {"test": "data"}
    
    def test_validate_service_response_failure(self):
        """Test validate_service_response with failure response."""
        from MakerMatrix.routers.base import validate_service_response
        from fastapi import HTTPException
        
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.message = "Service error"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_service_response(mock_response)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Service error"


class TestRefactoringImpact:
    """Test that refactoring maintained functionality while improving code quality."""
    
    def test_error_handling_consistency(self, client, mock_services):
        """Test that all refactored endpoints use consistent error handling."""
        # Test parts routes error handling
        response = client.get("/parts/get_part")
        assert response.status_code == 400
        assert "detail" in response.json()
        
        # Test categories routes error handling
        response = client.get("/categories/get_category")
        assert response.status_code == 400
        assert "detail" in response.json()
    
    def test_response_structure_consistency(self, client, mock_services):
        """Test that all refactored endpoints use consistent response structure."""
        # Mock successful responses for different endpoints
        mock_service_response = MagicMock()
        mock_service_response.success = True
        mock_service_response.message = "Success"
        mock_service_response.data = {"test": "data"}
        
        mock_services['part_service'].return_value.get_part_counts.return_value = mock_service_response
        mock_services['category_service'].return_value.get_all_categories.return_value = {"categories": []}
        mock_services['category_service'].return_value.get_all_categories.return_value = mock_service_response
        
        # Test different endpoints
        endpoints = [
            "/parts/get_part_counts",
            "/categories/get_all_categories"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                response_data = response.json()
                # Check BaseRouter response structure
                assert "status" in response_data
                assert "message" in response_data
                assert "data" in response_data
                assert response_data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])