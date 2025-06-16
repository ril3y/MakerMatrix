"""
Integration tests for the modern printer routes.
Tests actual API endpoints with the mock printer system.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, engine, create_db_and_tables
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.services.modern_printer_service import get_printer_service, set_printer_service, ModernPrinterService
from MakerMatrix.printers.drivers.mock import MockPrinter


client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    
    # Set up the database (tables creation)
    create_db_and_tables()
    
    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield  # Let the tests run
    
    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    return response.json()["access_token"]


@pytest.fixture
def mock_printer_service():
    """Set up a mock printer service for testing."""
    # Create a mock printer with known settings
    mock_printer = MockPrinter(
        printer_id="test_mock_printer",
        name="Test Mock Printer",
        simulate_errors=False,
        print_delay=0.01  # Fast for testing
    )
    
    # Create service with this printer
    service = ModernPrinterService(default_printer=mock_printer)
    
    # Set it as the global service
    set_printer_service(service)
    
    yield service
    
    # Reset to default after test
    set_printer_service(None)


@pytest.fixture
def test_part(admin_token):
    """Create a test part for printing."""
    part_data = {
        "part_number": "MODERN_TEST_123",
        "part_name": "Modern Test Component",
        "quantity": 42,
        "description": "A test component for modern printer testing",
        "location_id": None,
        "category_names": ["test", "modern"],
        "additional_properties": {
            "color": "blue",
            "material": "plastic"
        }
    }
    
    response = client.post(
        "/api/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.integration
class TestModernPrinterRoutes:
    """Test the modern printer API endpoints."""
    
    def test_print_part_qr_code(self, mock_printer_service, test_part, admin_token):
        """Test printing QR code for a part."""
        # The part response is nested under 'data'
        part_id = test_part["data"]["id"]
        
        response = client.post(
            f"/printer/print_qr_code/{part_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Debug: print response if there's an error
        if response.status_code != 200:
            print(f"Error response: {response.status_code}")
            print(f"Error detail: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "QR code printed successfully" in data["message"]
        assert "job_id" in data
        assert data["job_id"].startswith("job_")
        assert data.get("error") is None
        
        # Verify the mock printer received the job
        mock_printer = mock_printer_service.get_default_printer()
        history = mock_printer.get_print_history()
        assert len(history) == 1
        
        last_job = history[0]
        assert last_job["label_size"] == "62"  # Default size
        assert last_job["copies"] == 1
        assert last_job["image_size"][0] > 0  # Has width
        assert last_job["image_size"][1] > 0  # Has height
    
    def test_print_part_qr_code_nonexistent_part(self, mock_printer_service, admin_token):
        """Test printing QR code for non-existent part."""
        response = client.post(
            "/printer/print_qr_code/nonexistent-part-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404
        assert "Part not found" in response.json()["detail"]
    
    def test_print_part_name(self, mock_printer_service, test_part, admin_token):
        """Test printing part name as text label."""
        part_id = test_part["data"]["id"]
        
        response = client.post(
            f"/printer/print_part_name/{part_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Part name printed successfully" in data["message"]
        assert "job_id" in data
        assert data["job_id"].startswith("job_")
        
        # Verify print job details
        mock_printer = mock_printer_service.get_default_printer()
        history = mock_printer.get_print_history()
        assert len(history) == 1
        
        last_job = history[0]
        assert last_job["label_size"] == "62"
        assert last_job["copies"] == 1
    
    def test_print_text_label_basic(self, mock_printer_service, admin_token):
        """Test printing a basic text label."""
        request_data = {
            "text": "Custom Test Label"
        }
        
        response = client.post(
            "/printer/print_text",
            json=request_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Text label printed successfully" in data["message"]
        assert "job_id" in data
        
        # Verify default settings
        mock_printer = mock_printer_service.get_default_printer()
        history = mock_printer.get_print_history()
        assert len(history) == 1
        
        last_job = history[0]
        assert last_job["label_size"] == "62"  # Default
        assert last_job["copies"] == 1  # Default
    
    def test_print_text_label_with_options(self, mock_printer_service, admin_token):
        """Test printing text label with custom options."""
        request_data = {
            "text": "Custom Label with Options",
            "label_size": "29",
            "copies": 3
        }
        
        response = client.post(
            "/printer/print_text",
            json=request_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify custom settings were used
        mock_printer = mock_printer_service.get_default_printer()
        history = mock_printer.get_print_history()
        assert len(history) == 1
        
        last_job = history[0]
        assert last_job["label_size"] == "29"  # Custom size
        assert last_job["copies"] == 3  # Custom copies
    
    def test_print_qr_and_text_combined(self, mock_printer_service, admin_token):
        """Test printing combined QR and text label."""
        printer_config = {
            "backend": "mock",
            "driver": "mock",
            "printer_identifier": "mock://test",
            "model": "MockQL-800",
            "dpi": 300,
            "scaling_factor": 1.1
        }
        
        label_data = {
            "qr_data": "https://example.com/part/TEST123",
            "text": "Example Test Label",
            "font_size": 24,
            "qr_size": 200,
            "label_width": 62,
            "label_margin": 5
        }
        
        request_data = {
            "printer_config": printer_config,
            "label_data": label_data
        }
        
        response = client.post(
            "/printer/print_qr_and_text",
            json=request_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "QR code and text label printed successfully" in data["message"]
        
        # Verify the print job
        mock_printer = mock_printer_service.get_default_printer()
        history = mock_printer.get_print_history()
        assert len(history) == 1
        
        last_job = history[0]
        assert last_job["label_size"] == "62"
        assert last_job["copies"] == 1
    
    def test_list_printers(self, mock_printer_service, admin_token):
        """Test listing available printers."""
        response = client.get(
            "/printer/printers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "printers" in data
        assert len(data["printers"]) >= 1
        
        printer = data["printers"][0]
        assert printer["id"] == "test_mock_printer"
        assert printer["name"] == "Test Mock Printer"
        assert printer["driver"] == "MockPrinter"
        assert printer["model"] == "MockQL-800"
        assert printer["status"] == "ready"
        assert printer["backend"] == "mock"
        assert "qr_codes" in printer["capabilities"]
    
    def test_get_printer_status(self, mock_printer_service, admin_token):
        """Test getting printer status."""
        response = client.get(
            "/printer/printers/test_mock_printer/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["printer_id"] == "test_mock_printer"
        assert data["status"] == "ready"
    
    def test_get_printer_status_not_found(self, mock_printer_service, admin_token):
        """Test getting status of non-existent printer."""
        response = client.get(
            "/printer/printers/nonexistent/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404
        assert "Printer not found" in response.json()["detail"]
    
    def test_test_printer_connection(self, mock_printer_service, admin_token):
        """Test printer connectivity test."""
        response = client.post(
            "/printer/printers/test_mock_printer/test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["printer_id"] == "test_mock_printer"
        assert data["success"] is True
        assert data["response_time_ms"] > 0
        assert data["message"] is not None
        assert data.get("error") is None
    
    def test_unauthorized_access(self, mock_printer_service):
        """Test that endpoints require authentication."""
        # Test without auth header
        response = client.post("/printer/print_text", json={"text": "test"})
        assert response.status_code == 401
        
        # Test with invalid token
        response = client.post(
            "/printer/print_text",
            json={"text": "test"},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestPrinterErrorHandling:
    """Test error handling in printer routes."""
    
    @pytest.fixture
    def error_printer_service(self):
        """Set up a printer service that simulates errors."""
        error_printer = MockPrinter(
            printer_id="error_printer",
            name="Error Printer",
            simulate_errors=True,  # Enable error simulation
            print_delay=0.01
        )
        
        service = ModernPrinterService(default_printer=error_printer)
        set_printer_service(service)
        
        yield service
        
        set_printer_service(None)
    
    def test_print_with_error_simulation(self, error_printer_service, test_part, admin_token):
        """Test printing with simulated printer errors."""
        part_id = test_part["data"]["id"]
        
        # Print several jobs - some should succeed, some fail
        results = []
        for i in range(6):  # Mock printer fails every 5th job
            response = client.post(
                f"/printer/print_qr_code/{part_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            results.append(response)
        
        # Should have mix of success and failure
        success_count = sum(1 for r in results if r.status_code == 200 and r.json().get("status") == "success")
        error_count = sum(1 for r in results if r.json().get("status") == "error")
        
        assert success_count > 0, "Should have some successful prints"
        assert error_count > 0, "Should have some failed prints due to simulation"
        
        # Check that error responses have proper format
        for response in results:
            if response.json().get("status") == "error":
                data = response.json()
                assert "error" in data
                assert data["message"] == "Print job failed"
    
    def test_invalid_label_size_error(self, mock_printer_service, admin_token):
        """Test error handling for invalid label sizes."""
        request_data = {
            "text": "Test Label",
            "label_size": "999"  # Invalid size
        }
        
        response = client.post(
            "/printer/print_text",
            json=request_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should return 500 with error details
        assert response.status_code == 500
        assert "Invalid label size" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])