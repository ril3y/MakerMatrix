"""
Integration test for PDF proxy with manufacturer datasheets.
Tests the fix for 403 Forbidden error when viewing DigiKey/Mouser datasheets hosted on manufacturer domains.

This test verifies that the allowed_domains list in utility_routes.py includes common manufacturer domains.
"""

import pytest


class TestManufacturerDomainAllowlist:
    """Test suite to verify manufacturer domains are in PDF proxy allowlist."""

    def test_allowed_domains_includes_manufacturers(self):
        """Test that allowed_domains list includes major manufacturer domains"""
        # Import the actual utility_routes module and check the source code
        from MakerMatrix.routers import utility_routes
        import inspect

        # Get the source code of the proxy_pdf function
        source = inspect.getsource(utility_routes.proxy_pdf)

        # Verify that important manufacturer domains are in the source
        critical_manufacturer_domains = [
            "st.com",  # STMicroelectronics - the original bug report
            "ti.com",  # Texas Instruments
            "infineon.com",  # Infineon
            "nxp.com",  # NXP
            "analog.com",  # Analog Devices
            "microchip.com",  # Microchip
            "onsemi.com",  # ON Semiconductor
            "renesas.com",  # Renesas
            "vishay.com",  # Vishay
            "murata.com",  # Murata
            "te.com",  # TE Connectivity
            "molex.com",  # Molex
            "silabs.com",  # Silicon Labs
            "espressif.com",  # Espressif (ESP32)
        ]

        missing_domains = []
        for domain in critical_manufacturer_domains:
            if domain not in source:
                missing_domains.append(domain)

        assert not missing_domains, f"Critical manufacturer domains missing from allowlist: {missing_domains}"

    def test_original_suppliers_still_allowed(self):
        """Test that original supplier domains are still in the allowlist"""
        from MakerMatrix.routers import utility_routes
        import inspect

        source = inspect.getsource(utility_routes.proxy_pdf)

        original_suppliers = [
            "lcsc.com",
            "digikey.com",
            "mouser.com",
            "easyeda.com",
        ]

        missing_domains = []
        for domain in original_suppliers:
            if domain not in source:
                missing_domains.append(domain)

        assert not missing_domains, f"Original supplier domains missing from allowlist: {missing_domains}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
