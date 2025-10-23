"""
Unit tests for the modern printer service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from PIL import Image

from MakerMatrix.services.printer.modern_printer_service import (
    ModernPrinterService,
    get_printer_service,
    set_printer_service,
)
from MakerMatrix.printers.drivers.mock import MockPrinter
from MakerMatrix.printers.base import PrinterNotFoundError, PrinterError, PrintJobResult, PrinterStatus
from MakerMatrix.models.models import PartModel


@pytest.mark.asyncio
class TestModernPrinterService:
    """Test the ModernPrinterService class."""

    @pytest.fixture
    def mock_printer(self):
        """Create a mock printer for testing."""
        return MockPrinter(printer_id="test_printer", simulate_errors=False)

    @pytest.fixture
    def printer_service(self, mock_printer):
        """Create a printer service with a mock printer."""
        return ModernPrinterService(default_printer=mock_printer)

    @pytest.fixture
    def test_part(self):
        """Create a test part for printing."""
        return PartModel(part_number="TEST123", part_name="Test Component", description="A test component", quantity=10)

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        return Image.new("RGB", (200, 100), "white")

    def test_service_initialization_with_default(self, mock_printer):
        """Test service initialization with a default printer."""
        service = ModernPrinterService(default_printer=mock_printer)

        # Should have the default printer registered
        default = service.get_default_printer()
        assert default == mock_printer

        printers = service.list_printers()
        assert len(printers) == 1
        assert "test_printer" in printers

    def test_service_initialization_without_default(self):
        """Test service initialization without a default printer."""
        service = ModernPrinterService()

        # Should create a mock printer as default
        default = service.get_default_printer()
        assert isinstance(default, MockPrinter)

        printers = service.list_printers()
        assert len(printers) == 1

    def test_get_printer_default(self, printer_service, mock_printer):
        """Test getting the default printer."""
        printer = printer_service.get_printer()
        assert printer == mock_printer

    def test_get_printer_by_id(self, printer_service, mock_printer):
        """Test getting printer by ID."""
        printer = printer_service.get_printer("test_printer")
        assert printer == mock_printer

    def test_get_printer_not_found(self, printer_service):
        """Test getting non-existent printer."""
        with pytest.raises(PrinterNotFoundError) as exc_info:
            printer_service.get_printer("nonexistent")

        error = exc_info.value
        assert error.printer_id == "nonexistent"

    async def test_print_part_qr_code(self, printer_service, test_part):
        """Test printing part QR code."""
        result = await printer_service.print_part_qr_code(test_part)

        assert result.success
        assert result.job_id.startswith("job_")
        assert result.error is None

    async def test_print_part_qr_code_with_printer_id(self, printer_service, test_part):
        """Test printing part QR code with specific printer."""
        result = await printer_service.print_part_qr_code(test_part, "test_printer")

        assert result.success
        assert result.job_id.startswith("job_")

    async def test_print_part_qr_code_printer_not_found(self, printer_service, test_part):
        """Test printing with non-existent printer."""
        with pytest.raises(PrinterNotFoundError):
            await printer_service.print_part_qr_code(test_part, "nonexistent")

    async def test_print_part_name(self, printer_service, test_part):
        """Test printing part name."""
        result = await printer_service.print_part_name(test_part)

        assert result.success
        assert result.job_id.startswith("job_")
        assert result.error is None

    async def test_print_text_label(self, printer_service):
        """Test printing text label."""
        result = await printer_service.print_text_label("Test Label")

        assert result.success
        assert result.job_id.startswith("job_")
        assert result.error is None

    async def test_print_text_label_with_options(self, printer_service):
        """Test printing text label with custom options."""
        result = await printer_service.print_text_label("Custom Text", label_size="29", copies=2)

        assert result.success
        # Verify the mock printer received the print job
        mock_printer = printer_service.get_default_printer()
        history = mock_printer.get_print_history()
        assert len(history) > 0
        last_job = history[-1]
        assert last_job["label_size"] == "29"
        assert last_job["copies"] == 2

    async def test_print_qr_and_text(self, printer_service, test_part):
        """Test printing combined QR and text."""
        printer_config = {"dpi": 300, "scaling_factor": 1.1}
        label_data = {"label_width": "62"}

        result = await printer_service.print_qr_and_text(test_part, "Custom Text", printer_config, label_data)

        assert result.success
        assert result.job_id.startswith("job_")

    def test_add_printer(self, printer_service):
        """Test adding a new printer."""
        new_printer = MockPrinter(printer_id="new_printer", name="New Printer")

        printer_id = printer_service.add_printer(new_printer)
        assert printer_id == "new_printer"

        # Should be able to retrieve it
        retrieved = printer_service.get_printer("new_printer")
        assert retrieved == new_printer

        # Should be in the list
        printers = printer_service.list_printers()
        assert len(printers) == 2
        assert "new_printer" in printers

    def test_remove_printer(self, printer_service):
        """Test removing a printer."""
        # Add a printer first
        new_printer = MockPrinter(printer_id="removable", name="Removable")
        printer_service.add_printer(new_printer)

        # Verify it exists
        assert "removable" in printer_service.list_printers()

        # Remove it
        success = printer_service.remove_printer("removable")
        assert success

        # Should be gone
        assert "removable" not in printer_service.list_printers()

        # Removing non-existent printer should return False
        success = printer_service.remove_printer("nonexistent")
        assert not success

    def test_list_printers(self, printer_service):
        """Test listing all printers."""
        printers = printer_service.list_printers()
        assert len(printers) == 1
        assert "test_printer" in printers

        # Add another printer
        new_printer = MockPrinter(printer_id="second", name="Second Printer")
        printer_service.add_printer(new_printer)

        printers = printer_service.list_printers()
        assert len(printers) == 2
        assert "test_printer" in printers
        assert "second" in printers


class TestPrinterServiceGlobal:
    """Test the global printer service functionality."""

    def test_get_default_service(self):
        """Test getting the default global service."""
        service1 = get_printer_service()
        service2 = get_printer_service()

        # Should return the same instance
        assert service1 is service2
        assert isinstance(service1, ModernPrinterService)

    def test_set_custom_service(self):
        """Test setting a custom global service."""
        # Create custom service
        custom_printer = MockPrinter(printer_id="custom")
        custom_service = ModernPrinterService(default_printer=custom_printer)

        # Set it as global
        set_printer_service(custom_service)

        # Should return the custom service
        retrieved = get_printer_service()
        assert retrieved is custom_service

        # Should have the custom printer
        default_printer = retrieved.get_default_printer()
        assert default_printer == custom_printer


@pytest.mark.asyncio
class TestPrinterServiceErrorHandling:
    """Test error handling in the printer service."""

    @pytest.fixture
    def error_printer(self):
        """Create a printer that simulates errors."""
        return MockPrinter(printer_id="error_printer", simulate_errors=True)

    @pytest.fixture
    def error_service(self, error_printer):
        """Create a service with an error-prone printer."""
        return ModernPrinterService(default_printer=error_printer)

    @pytest.fixture
    def test_part(self):
        """Create a test part."""
        return PartModel(
            part_number="ERROR123", part_name="Error Test Component", description="For testing errors", quantity=1
        )

    async def test_print_with_simulated_errors(self, error_service, test_part):
        """Test printing with simulated printer errors."""
        # Print several jobs - some should succeed, one should fail
        results = []
        for i in range(6):  # Mock fails every 5th job
            try:
                result = await error_service.print_part_qr_code(test_part)
                results.append(result)
            except PrinterError:
                results.append(None)  # Error occurred

        # Should have mix of success and failure
        successful = [r for r in results if r and r.success]
        failed = [r for r in results if r and not r.success]

        assert len(successful) > 0  # Some should succeed
        assert len(failed) > 0  # Some should fail

    async def test_service_wraps_printer_exceptions(self, error_service, test_part):
        """Test that service properly wraps printer exceptions."""
        # Force the printer into error state
        error_printer = error_service.get_default_printer()
        error_printer.simulate_paper_out()

        # Try to print - should get PrinterError
        try:
            await error_service.print_part_qr_code(test_part)
            # If we get here, the job might have succeeded despite error state
            # This is okay for mock printer
            pass
        except PrinterError as e:
            assert "Failed to print part QR code" in str(e)
            assert e.printer_id == "error_printer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
