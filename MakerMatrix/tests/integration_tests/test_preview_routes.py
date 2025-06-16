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
from MakerMatrix.models.models import engine


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
            quantity=15
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
        response = client.post(
            f"/api/preview/part/qr_code/{test_part_id}?label_size=29&printer_id=mock_preview"
        )
        
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
        request_data = {
            "text": "Custom Test Label",
            "label_size": "29",
            "printer_id": "mock_preview"
        }
        
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
        request_data = {
            "text": "Simple Text"
        }
        
        response = client.post("/api/preview/text", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_preview_combined_label(self, client, test_part_id):
        """Test combined QR + text preview generation."""
        response = client.post(
            f"/api/preview/part/combined/{test_part_id}?custom_text=Custom Text&label_size=62"
        )
        
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
        response = client.post("/api/preview/text", json={
            "text": "Test",
            "printer_id": "invalid_printer"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Should still work by falling back to default printer
        assert data["success"] is True


@pytest.mark.integration
class TestPreviewRoutesError:
    """Test error handling in preview routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('MakerMatrix.routers.preview_routes.get_preview_manager')
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