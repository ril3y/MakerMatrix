"""
Simple integration tests for PDF proxy functionality.

Tests the PDF proxy endpoint with basic functionality.
"""

import pytest
from fastapi.testclient import TestClient

from MakerMatrix.main import app
from MakerMatrix.dependencies.auth import get_current_user
from MakerMatrix.models.models import UserModel


# Mock user for authentication
def mock_get_current_user():
    user = UserModel()
    user.id = "test-user-id"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    return user


# Override the dependency
app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)


class TestPDFProxySimple:
    """Simple test suite for PDF proxy endpoint."""

    def test_proxy_pdf_invalid_url(self):
        """Test PDF proxy with invalid URL."""
        response = client.get("/static/proxy-pdf?url=not-a-valid-url")
        
        # Should fail with 400 or 500, but not auth error
        assert response.status_code in [400, 500]
        # Should not be an auth error (401/403)
        assert response.status_code not in [401, 403]

    def test_proxy_pdf_unauthorized_domain(self):
        """Test PDF proxy with unauthorized domain."""
        unauthorized_url = "https://evil-site.com/malicious.pdf"
        response = client.get(f"/static/proxy-pdf?url={unauthorized_url}")
        
        assert response.status_code == 403
        response_data = response.json()
        # Check if response has detail field (might be in different format)
        if "detail" in response_data:
            assert "Domain not allowed" in response_data["detail"]
        else:
            # Check the full response for the error message
            assert "Domain not allowed" in str(response_data)

    def test_proxy_pdf_missing_url_parameter(self):
        """Test PDF proxy without URL parameter."""
        response = client.get("/static/proxy-pdf")
        
        assert response.status_code == 422  # Validation error

    def test_proxy_pdf_allowed_domains_validation(self):
        """Test that allowed domains pass validation."""
        allowed_urls = [
            "https://lcsc.com/test.pdf",
            "https://www.lcsc.com/test.pdf", 
            "https://datasheet.lcsc.com/test.pdf",
            "https://digikey.com/test.pdf",
            "https://www.digikey.com/test.pdf",
            "https://mouser.com/test.pdf",
            "https://www.mouser.com/test.pdf",
            "https://easyeda.com/test.pdf"
        ]
        
        for url in allowed_urls:
            response = client.get(f"/static/proxy-pdf?url={url}")
            
            # Should not be rejected for domain reasons (403)
            # May fail for other reasons (network, etc.) but domain should be allowed
            assert response.status_code != 403, f"Domain should be allowed: {url}"

    def test_proxy_pdf_endpoint_exists(self):
        """Test that the proxy endpoint exists and is accessible."""
        # Test with a valid domain but non-existent file
        test_url = "https://datasheet.lcsc.com/nonexistent-file-12345.pdf"
        response = client.get(f"/static/proxy-pdf?url={test_url}")
        
        # Should not be a 404 from our endpoint (would be 502, 408, etc.)
        assert response.status_code != 404
        # Should not be auth error
        assert response.status_code not in [401, 403]

    def test_proxy_pdf_url_encoding(self):
        """Test that URL encoding works correctly."""
        # Test with special characters that need encoding
        special_url = "https://datasheet.lcsc.com/lcsc/test file with spaces.pdf"
        response = client.get(f"/static/proxy-pdf?url={special_url}")
        
        # Should not fail due to URL parsing
        assert response.status_code != 400, "URL encoding should work"

    def test_proxy_pdf_headers_acceptance(self):
        """Test that the endpoint accepts requests."""
        test_url = "https://datasheet.lcsc.com/test.pdf"
        response = client.get(f"/static/proxy-pdf?url={test_url}")
        
        # Should accept the request (not 405 Method Not Allowed)
        assert response.status_code != 405
        # Should not be auth error
        assert response.status_code not in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])