"""
Real URL tests for PDF proxy functionality.

Tests the PDF proxy with actual external URLs to ensure
it works with real supplier datasheets.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch

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


class TestPDFProxyRealURLs:
    """Test PDF proxy with real supplier URLs."""

    def test_lcsc_domain_allowed(self):
        """Test that LCSC domains are properly allowed."""
        lcsc_urls = [
            "https://lcsc.com/product-detail/C123456.html",
            "https://www.lcsc.com/product-detail/C123456.html",
            "https://datasheet.lcsc.com/lcsc/test.pdf",
            "https://easyeda.com/api/products/C123456/components"
        ]
        
        for url in lcsc_urls:
            # We don't expect these to work fully, but they should pass domain validation
            response = client.get(f"/static/proxy-pdf?url={url}")
            
            # Should not be rejected for domain reasons (403)
            # Might fail for other reasons (502, 404, etc.)
            assert response.status_code != 403, f"LCSC domain should be allowed: {url}"

    @pytest.mark.integration  
    def test_digikey_domain_allowed(self):
        """Test that DigiKey domains are properly allowed."""
        digikey_urls = [
            "https://digikey.com/en/datasheets/test.pdf",
            "https://www.digikey.com/en/datasheets/test.pdf"
        ]
        
        for url in digikey_urls:
            response = client.get(f"/static/proxy-pdf?url={url}")
            assert response.status_code != 403, f"DigiKey domain should be allowed: {url}"

    @pytest.mark.integration
    def test_mouser_domain_allowed(self):
        """Test that Mouser domains are properly allowed."""
        mouser_urls = [
            "https://mouser.com/pdfdocs/test.pdf",
            "https://www.mouser.com/pdfdocs/test.pdf"
        ]
        
        for url in mouser_urls:
            response = client.get(f"/static/proxy-pdf?url={url}")
            assert response.status_code != 403, f"Mouser domain should be allowed: {url}"

    @pytest.mark.integration
    def test_unauthorized_domains_blocked(self):
        """Test that unauthorized domains are properly blocked."""
        unauthorized_urls = [
            "https://evil-site.com/malicious.pdf",
            "https://random-domain.net/test.pdf",
            "https://github.com/user/repo/file.pdf",
            "https://google.com/search?q=test"
        ]
        
        for url in unauthorized_urls:
            response = client.get(f"/static/proxy-pdf?url={url}")
            assert response.status_code == 403, f"Unauthorized domain should be blocked: {url}"
            assert "Domain not allowed" in response.json()["detail"]

    @pytest.mark.integration
    def test_url_encoding_with_real_patterns(self):
        """Test URL encoding with real LCSC URL patterns."""
        # Real LCSC datasheet URL pattern
        real_lcsc_url = "https://datasheet.lcsc.com/lcsc/2304140030_Texas-Instruments-TLV9061IDBVR_C693210.pdf"
        
        # Test the URL gets properly encoded and decoded
        response = client.get(f"/static/proxy-pdf?url={real_lcsc_url}")
        
        # Should not fail due to URL encoding issues
        # Might fail for network reasons but not parsing
        assert response.status_code != 400, "Real LCSC URL should be properly parsed"

    @pytest.mark.integration
    def test_complex_query_parameters(self):
        """Test handling of complex query parameters in URLs."""
        complex_url = "https://datasheet.lcsc.com/lcsc/test.pdf?version=2&download=true&token=abc123"
        
        response = client.get(f"/static/proxy-pdf?url={complex_url}")
        
        # Should not fail due to query parameter handling
        assert response.status_code != 400, "Complex URLs should be properly handled"

    @pytest.mark.integration
    def test_international_characters_in_urls(self):
        """Test handling of international characters in URLs."""
        international_url = "https://datasheet.lcsc.com/lcsc/产品数据表.pdf"
        
        response = client.get(f"/static/proxy-pdf?url={international_url}")
        
        # Should not fail due to encoding issues
        assert response.status_code != 400, "International characters should be handled"

    @pytest.mark.integration
    def test_very_long_urls(self):
        """Test handling of very long URLs."""
        long_filename = "A" * 200 + ".pdf"
        long_url = f"https://datasheet.lcsc.com/lcsc/{long_filename}"
        
        response = client.get(f"/static/proxy-pdf?url={long_url}")
        
        # Should not fail due to URL length
        assert response.status_code != 400, "Long URLs should be handled"

    @pytest.mark.integration
    def test_response_headers_set_correctly(self):
        """Test that response headers are set correctly for proxied content."""
        test_url = "https://datasheet.lcsc.com/test.pdf"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful PDF response
            from unittest.mock import Mock
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf', 'content-length': '12345'}
            mock_response.iter_bytes.return_value = [b'%PDF-1.4\ntest content']
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "inline" in response.headers.get("content-disposition", "")
            assert "max-age=3600" in response.headers.get("cache-control", "")

    @pytest.mark.integration
    def test_timeout_handling_with_real_patterns(self):
        """Test timeout handling with realistic timeout scenarios."""
        test_url = "https://datasheet.lcsc.com/slow-response.pdf"
        
        with patch('httpx.AsyncClient') as mock_client:
            import httpx
            mock_client_instance = Mock()
            mock_client_instance.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            assert response.status_code == 408
            assert "Timeout while fetching PDF" in response.json()["detail"]

    @pytest.mark.integration
    def test_redirect_handling(self):
        """Test that redirects are properly followed."""
        redirect_url = "https://lcsc.com/redirect-to-datasheet"
        
        with patch('httpx.AsyncClient') as mock_client:
            from unittest.mock import Mock
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.iter_bytes.return_value = [b'%PDF-1.4\nredirected content']
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            response = client.get(f"/static/proxy-pdf?url={redirect_url}")
            
            # Verify that the client was configured to follow redirects
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args[1]
            assert call_kwargs['follow_redirects'] == True
            assert call_kwargs['timeout'] == 30.0

    @pytest.mark.integration
    def test_user_agent_with_real_request(self):
        """Test that proper User-Agent is sent with requests."""
        test_url = "https://datasheet.lcsc.com/test.pdf"
        
        with patch('httpx.AsyncClient') as mock_client:
            from unittest.mock import Mock
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.iter_bytes.return_value = [b'%PDF-1.4\ntest']
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            response = client.get(f"/static/proxy-pdf?url={test_url}")
            
            # Verify User-Agent header
            call_kwargs = mock_client.call_args[1]
            assert call_kwargs['headers']['User-Agent'] == "MakerMatrix/1.0.0 (Component Management System)"
            assert call_kwargs['headers']['Accept'] == "application/pdf,*/*"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])