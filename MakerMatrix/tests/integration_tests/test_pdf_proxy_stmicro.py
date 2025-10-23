"""
Integration test for PDF proxy with manufacturer datasheets.
Tests the fix for 403 Forbidden error when viewing DigiKey/Mouser datasheets hosted on manufacturer domains.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from urllib.parse import quote

from MakerMatrix.main import app
from MakerMatrix.auth.dependencies import get_current_user
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


class TestManufacturerPDFProxy:
    """Test suite for manufacturer PDF proxy functionality."""

    def test_st_com_domain_allowed(self):
        """Test that st.com domain is allowed for PDF proxying"""
        test_url = "https://www.st.com/resource/en/datasheet/stm32f103cb.pdf"

        # Mock successful response
        mock_pdf_content = b"%PDF-1.4\ntest content"
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/pdf"}
            mock_response.iter_bytes.return_value = [mock_pdf_content]

            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            response = client.get(f"/api/utility/static/proxy-pdf?url={test_url}")

            # Should not return 403 (domain is now allowed)
            assert response.status_code != 403, "st.com domain should be allowed for PDF proxying"
            assert response.status_code == 200

    def test_ti_com_domain_allowed(self):
        """Test that ti.com domain is allowed for PDF proxying"""
        test_url = "https://www.ti.com/lit/ds/symlink/lm358.pdf"

        mock_pdf_content = b"%PDF-1.4\ntest content"
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/pdf"}
            mock_response.iter_bytes.return_value = [mock_pdf_content]

            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            response = client.get(f"/api/utility/static/proxy-pdf?url={test_url}")

            assert response.status_code != 403, "ti.com domain should be allowed for PDF proxying"
            assert response.status_code == 200

    def test_unauthorized_domain_blocked(self):
        """Test that unauthorized domains are still blocked"""
        test_url = "https://example.com/datasheet.pdf"

        response = client.get(f"/static/proxy-pdf?url={test_url}")

        # Should return 403 for unauthorized domain
        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"].lower()

    def test_common_manufacturers_allowed(self):
        """Test that all major manufacturer domains are in the allowlist"""
        manufacturer_domains = [
            "st.com",
            "ti.com",
            "infineon.com",
            "nxp.com",
            "analog.com",
            "microchip.com",
            "onsemi.com",
            "renesas.com",
            "vishay.com",
            "murata.com",
            "te.com",
        ]

        mock_pdf_content = b"%PDF-1.4\ntest content"

        for domain in manufacturer_domains:
            test_url = f"https://www.{domain}/datasheet.pdf"

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "application/pdf"}
                mock_response.iter_bytes.return_value = [mock_pdf_content]

                mock_client_instance = Mock()
                mock_client_instance.get.return_value = mock_response
                mock_client.return_value.__aenter__.return_value = mock_client_instance

                response = client.get(f"/api/utility/static/proxy-pdf?url={test_url}")

                # Should not return 403 for domain restriction
                assert response.status_code != 403, f"{domain} should be allowed for PDF proxying"
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
