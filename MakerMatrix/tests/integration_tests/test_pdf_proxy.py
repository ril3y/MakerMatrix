"""
Integration tests for PDF proxy functionality.

Tests the PDF proxy endpoint that allows viewing external PDFs
without CORS issues.
"""

import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from io import BytesIO

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


class TestPDFProxy:
    """Test suite for PDF proxy endpoint."""

    def test_proxy_pdf_success(self):
        """Test successful PDF proxying from allowed domain."""
        # Mock PDF content
        mock_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        
        with patch('MakerMatrix.routers.static_routes.httpx.AsyncClient') as mock_client:
            # Mock the httpx response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.iter_bytes.return_value = [mock_pdf_content[i:i+8192] for i in range(0, len(mock_pdf_content), 8192)]
            
            # Mock the async context manager
            mock_client_instance = Mock()
            mock_client_instance.get = Mock(return_value=mock_response)
            
            # Create an async mock for the context manager
            async def mock_aenter():
                return mock_client_instance
                
            async def mock_aexit(exc_type, exc_val, exc_tb):
                return None
                
            mock_client.return_value.__aenter__ = mock_aenter
            mock_client.return_value.__aexit__ = mock_aexit
            
            # Test with LCSC URL
            test_url = "https://datasheet.lcsc.com/lcsc/2304140030_Texas-Instruments-TLV9061IDBVR_C693210.pdf"
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert mock_pdf_content in response.content

    def test_proxy_pdf_invalid_url(self):
        """Test PDF proxy with invalid URL."""
        response = client.get("/static/proxy-pdf?url=not-a-valid-url")
        
        assert response.status_code == 400
        assert "Invalid URL provided" in response.json()["detail"]

    def test_proxy_pdf_unauthorized_domain(self):
        """Test PDF proxy with unauthorized domain."""
        unauthorized_url = "https://evil-site.com/malicious.pdf"
        response = client.get(f"/static/proxy-pdf?url={unauthorized_url}")
        
        assert response.status_code == 403
        assert "Domain not allowed" in response.json()["detail"]

    def test_proxy_pdf_allowed_domains(self):
        """Test that all expected domains are allowed."""
        allowed_domains = [
            "https://lcsc.com/datasheet.pdf",
            "https://www.lcsc.com/datasheet.pdf", 
            "https://datasheet.lcsc.com/file.pdf",
            "https://digikey.com/datasheet.pdf",
            "https://www.digikey.com/datasheet.pdf",
            "https://mouser.com/datasheet.pdf",
            "https://www.mouser.com/datasheet.pdf",
            "https://easyeda.com/datasheet.pdf"
        ]
        
        mock_pdf_content = b"%PDF-1.4\ntest content"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.iter_bytes.return_value = [mock_pdf_content]
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            for domain_url in allowed_domains:
                response = client.get(f"/static/proxy-pdf?url={domain_url}")
                assert response.status_code == 200, f"Domain {domain_url} should be allowed"

    def test_proxy_pdf_http_error(self):
        """Test PDF proxy when external server returns error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            test_url = "https://lcsc.com/nonexistent.pdf"
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            assert response.status_code == 404
            assert "Failed to fetch PDF: HTTP 404" in response.json()["detail"]

    def test_proxy_pdf_timeout(self):
        """Test PDF proxy timeout handling."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = Mock()
            mock_client_instance.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            test_url = "https://lcsc.com/slow-response.pdf"
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            assert response.status_code == 408
            assert "Timeout while fetching PDF" in response.json()["detail"]

    def test_proxy_pdf_request_error(self):
        """Test PDF proxy network error handling."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = Mock()
            mock_client_instance.get.side_effect = httpx.RequestError("Network error")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            test_url = "https://lcsc.com/network-error.pdf"
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            assert response.status_code == 502
            assert "Failed to fetch PDF from source" in response.json()["detail"]

    def test_proxy_pdf_non_pdf_content_type(self):
        """Test PDF proxy with non-PDF content type (should still work)."""
        mock_html_content = b"<html><body>Not a PDF</body></html>"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'text/html'}
            mock_response.iter_bytes.return_value = [mock_html_content]
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            test_url = "https://lcsc.com/webpage-not-pdf.html"
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            # Should still return 200 but with warning logged
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"

    def test_proxy_pdf_headers(self):
        """Test that proxy sets correct headers."""
        mock_pdf_content = b"%PDF-1.4\ntest content"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.iter_bytes.return_value = [mock_pdf_content]
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            test_url = "https://lcsc.com/test.pdf"
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "inline" in response.headers.get("content-disposition", "")
            assert "max-age=3600" in response.headers.get("cache-control", "")

    def test_proxy_pdf_user_agent(self):
        """Test that proxy uses correct User-Agent header."""
        mock_pdf_content = b"%PDF-1.4\ntest content"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.iter_bytes.return_value = [mock_pdf_content]
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            test_url = "https://lcsc.com/test.pdf"
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            # Verify that the request was made with correct headers
            mock_client_instance.get.assert_called_once()
            call_args = mock_client_instance.get.call_args
            assert call_args[0][0] == test_url  # URL
            
            # Check that AsyncClient was created with correct headers
            assert mock_client.called
            client_call_args = mock_client.call_args[1]
            assert client_call_args['headers']['User-Agent'] == "MakerMatrix/1.0.0 (Component Management System)"
            assert client_call_args['follow_redirects'] == True
            assert client_call_args['timeout'] == 30.0

    def test_proxy_pdf_missing_url_parameter(self):
        """Test PDF proxy without URL parameter."""
        response = client.get("/static/proxy-pdf")
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])