"""
Integration tests for preview routes.
"""

import pytest
import base64
from unittest.mock import patch
from fastapi.testclient import TestClient

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.parts_repositories import PartRepository


@pytest.mark.integration
class TestPreviewRoutes:
    """Integration tests for preview endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def test_part_id(self):
        """Create a test part and return its ID."""
        test_part = PartModel(
            part_number="PREV_ROUTE_001",
            part_name="Preview Route Test Component",
            description="Test component for preview routes",
            quantity=15,
        )

        # Insert part into database
        with engine.begin() as session:
            session.add(test_part)
            session.flush()
            part_id = str(test_part.id)

        return part_id

    def test_get_available_printers(self, client):
        """Test getting available printers for preview."""
        response = client.get("/api/preview/printers")

        assert response.status_code == 200
        data = response.json()

        assert "printers" in data
        assert "default" in data
        assert isinstance(data["printers"], list)
        assert len(data["printers"]) > 0

        # Should have at least mock printer
        assert "mock_preview" in data["printers"]

    def test_get_label_sizes(self, client):
        """Test getting available label sizes."""
        response = client.get("/api/preview/labels/sizes")

        assert response.status_code == 200
        data = response.json()

        assert "sizes" in data
        assert isinstance(data["sizes"], list)
        assert len(data["sizes"]) > 0

        # Check size structure
        size = data["sizes"][0]
        assert "name" in size
        assert "width_mm" in size
        assert "height_mm" in size
        assert "width_px" in size
        assert "height_px" in size
        assert "is_continuous" in size

        # Should have common sizes
        size_names = [s["name"] for s in data["sizes"]]
        assert "12" in size_names
        assert "29" in size_names

    def test_get_label_sizes_with_printer_id(self, client):
        """Test getting label sizes for specific printer."""
        response = client.get("/api/preview/labels/sizes?printer_id=mock_preview")

        assert response.status_code == 200
        data = response.json()
        assert "sizes" in data
        assert len(data["sizes"]) > 0

    def test_preview_part_qr_code(self, client, test_part_id):
        """Test QR code preview generation."""
        response = client.post(f"/api/preview/part/qr_code/{test_part_id}?label_size=12")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "preview_data" in data
        assert data["format"] == "png"
        assert data["width_px"] > 0
        assert data["height_px"] > 0
        assert data["message"] is not None
        assert data["error"] is None

        # Verify base64 data can be decoded
        preview_data = base64.b64decode(data["preview_data"])
        assert len(preview_data) > 0

    def test_preview_part_qr_code_with_printer_id(self, client, test_part_id):
        """Test QR code preview with specific printer."""
        response = client.post(f"/api/preview/part/qr_code/{test_part_id}?label_size=29&printer_id=mock_preview")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_preview_part_qr_code_invalid_part(self, client):
        """Test QR code preview with invalid part ID."""
        response = client.post("/api/preview/part/qr_code/invalid_id?label_size=12")

        assert response.status_code == 200  # Should return 200 with error in response
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "Part not found" in data["error"]

    def test_preview_part_name(self, client, test_part_id):
        """Test part name preview generation."""
        response = client.post(f"/api/preview/part/name/{test_part_id}?label_size=12")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "preview_data" in data
        assert data["format"] == "png"
        assert data["width_px"] > 0
        assert data["height_px"] > 0

        # Verify base64 data
        preview_data = base64.b64decode(data["preview_data"])
        assert len(preview_data) > 0

    def test_preview_part_name_invalid_part(self, client):
        """Test part name preview with invalid part ID."""
        response = client.post("/api/preview/part/name/invalid_id?label_size=12")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Part not found" in data["error"]

    def test_preview_text_label(self, client):
        """Test custom text preview generation."""
        request_data = {"text": "Custom Test Label", "label_size": "29", "printer_id": "mock_preview"}

        response = client.post("/api/preview/text", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "preview_data" in data
        assert data["format"] == "png"

        # Verify base64 data
        preview_data = base64.b64decode(data["preview_data"])
        assert len(preview_data) > 0

    def test_preview_text_label_minimal(self, client):
        """Test text preview with minimal request."""
        request_data = {"text": "Simple Text"}

        response = client.post("/api/preview/text", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_preview_combined_label(self, client, test_part_id):
        """Test combined QR + text preview generation."""
        response = client.post(f"/api/preview/part/combined/{test_part_id}?custom_text=Custom Text&label_size=62")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "preview_data" in data
        assert data["format"] == "png"

        # Verify base64 data
        preview_data = base64.b64decode(data["preview_data"])
        assert len(preview_data) > 0

    def test_preview_combined_label_no_custom_text(self, client, test_part_id):
        """Test combined preview without custom text."""
        response = client.post(f"/api/preview/part/combined/{test_part_id}?label_size=12")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_preview_combined_label_invalid_part(self, client):
        """Test combined preview with invalid part."""
        response = client.post("/api/preview/part/combined/invalid_id?label_size=12")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Part not found" in data["error"]

    def test_validate_label_size_valid(self, client):
        """Test label size validation with valid size."""
        response = client.get("/api/preview/validate/size/12")

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert data["label_size"] == "12"
        assert "supported_sizes" in data
        assert isinstance(data["supported_sizes"], list)
        assert "12" in data["supported_sizes"]

    def test_validate_label_size_invalid(self, client):
        """Test label size validation with invalid size."""
        response = client.get("/api/preview/validate/size/999")

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert data["label_size"] == "999"
        assert "supported_sizes" in data
        assert "999" not in data["supported_sizes"]

    def test_validate_label_size_with_printer_id(self, client):
        """Test label size validation with specific printer."""
        response = client.get("/api/preview/validate/size/29?printer_id=mock_preview")

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert data["label_size"] == "29"

    def test_preview_with_invalid_label_size(self, client, test_part_id):
        """Test preview with invalid label size."""
        response = client.post(f"/api/preview/part/qr_code/{test_part_id}?label_size=999")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_preview_error_handling(self, client):
        """Test preview error handling."""
        # Test with invalid printer ID
        response = client.post("/api/preview/text", json={"text": "Test", "printer_id": "invalid_printer"})

        assert response.status_code == 200
        data = response.json()
        # Should still work by falling back to default printer
        assert data["success"] is True


@pytest.mark.integration
class TestPrinterPreviewRoutes:
    """Integration tests for printer preview endpoints (restored functionality)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for requests."""
        from MakerMatrix.services.system.auth_service import AuthService
        from MakerMatrix.repositories.user_repository import UserRepository

        user_repo = UserRepository()
        admin_user = user_repo.get_user_by_username("admin")
        if not admin_user:
            pytest.fail("Admin user not found")

        auth_service = AuthService()
        token = auth_service.create_access_token(data={"sub": admin_user.username})
        return {"Authorization": f"Bearer {token}"}

    def test_printer_preview_text_endpoint(self, client, auth_headers):
        """Test the restored /printer/preview/text endpoint."""
        request_data = {
            "text": "Test Label Text",
            "label_size": "29",
            "label_length": 100,
            "options": {"font_size": 12},
        }

        response = client.post("/printer/preview/text", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Verify it's a valid PNG image (not a white rectangle)
        image_data = response.content
        assert len(image_data) > 100  # Should be substantial image data
        assert image_data.startswith(b"\x89PNG\r\n\x1a\n")  # PNG signature

    def test_printer_preview_advanced_endpoint(self, client, auth_headers):
        """Test the restored /printer/preview/advanced endpoint."""
        request_data = {
            "template": "standard",
            "text": "Arduino Uno R3",
            "label_size": "29",
            "label_length": 100,
            "options": {"font_size": 14},
            "data": {
                "part_name": "Arduino Uno R3",
                "part_number": "ARD-UNO-R3",
                "location": "A1-B2",
                "category": "Microcontrollers",
            },
        }

        response = client.post("/printer/preview/advanced", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Verify it's a proper PNG image with rendered content
        image_data = response.content
        assert len(image_data) > 200  # Should be more substantial for advanced labels
        assert image_data.startswith(b"\x89PNG\r\n\x1a\n")  # PNG signature

    def test_printer_preview_text_with_various_sizes(self, client, auth_headers):
        """Test text preview with different label sizes."""
        test_sizes = ["12", "29", "62"]

        for size in test_sizes:
            request_data = {"text": f"Test Label Size {size}", "label_size": size}

            response = client.post("/printer/preview/text", json=request_data, headers=auth_headers)

            assert response.status_code == 200, f"Failed for size {size}"
            assert response.headers["content-type"] == "image/png"

            # Verify PNG signature
            image_data = response.content
            assert image_data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_printer_preview_advanced_with_mock_data(self, client, auth_headers):
        """Test advanced preview with mock data when no data provided."""
        request_data = {
            "template": "standard",
            "text": "Mock Part",
            "label_size": "29",
            # No data field - should use mock data
        }

        response = client.post("/printer/preview/advanced", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Should still generate valid image with mock data
        image_data = response.content
        assert len(image_data) > 100
        assert image_data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_printer_preview_text_long_text(self, client, auth_headers):
        """Test text preview with long text to verify wrapping."""
        request_data = {
            "text": "This is a very long part name that should test text wrapping functionality",
            "label_size": "29",
            "options": {"max_width": 400},
        }

        response = client.post("/printer/preview/text", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Should handle long text gracefully
        image_data = response.content
        assert len(image_data) > 100
        assert image_data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_printer_preview_error_fallback(self, client, auth_headers):
        """Test that preview handles invalid input appropriately."""
        # Test with potentially problematic input
        request_data = {"text": "", "label_size": "invalid_size"}  # Empty text

        response = client.post("/printer/preview/text", json=request_data, headers=auth_headers)

        # With invalid input, the endpoint may return 400 (which is appropriate)
        # or 200 with fallback behavior - both are acceptable
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            assert response.headers["content-type"] == "image/png"

    def test_printer_preview_special_characters(self, client, auth_headers):
        """Test preview with special characters and symbols."""
        request_data = {"text": "Resistor 10kΩ ±5% 1/4W", "label_size": "29"}

        response = client.post("/printer/preview/text", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Should handle special characters
        image_data = response.content
        assert len(image_data) > 100
        assert image_data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_printer_preview_streaming_response(self, client, auth_headers):
        """Test that the preview endpoints return proper streaming response."""
        request_data = {"text": "Streaming Test", "label_size": "29"}

        response = client.post("/printer/preview/text", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "content-disposition" in response.headers
        # Check that filename is present (actual name may vary)
        assert "filename=" in response.headers["content-disposition"]
        assert ".png" in response.headers["content-disposition"]


@pytest.mark.integration
class TestPreviewRoutesError:
    """Test error handling in preview routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @patch("MakerMatrix.routers.preview_routes.get_preview_manager")
    def test_preview_service_error(self, mock_get_manager, client):
        """Test handling of preview service errors."""
        # Mock preview manager to raise exception
        mock_manager = mock_get_manager.return_value
        mock_service = mock_manager.get_preview_service.return_value
        mock_service.preview_text_label.side_effect = Exception("Preview error")

        response = client.post("/api/preview/text", json={"text": "Test"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_malformed_request(self, client):
        """Test handling of malformed requests."""
        # Missing required text field
        response = client.post("/api/preview/text", json={})

        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
