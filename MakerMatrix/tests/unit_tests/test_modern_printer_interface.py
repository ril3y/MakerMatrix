"""
Unit tests for the modern printer interface and base classes.
"""
import pytest
import asyncio
from PIL import Image
from datetime import datetime

from MakerMatrix.printers.base import (
    PrinterInterface,
    BasePrinter,
    PrinterStatus,
    PrinterCapability,
    LabelSize,
    PrintJobResult,
    PreviewResult,
    PrinterInfo,
    TestResult
)
from MakerMatrix.printers.base.exceptions import (
    PrinterError,
    PrinterNotFoundError,
    InvalidLabelSizeError,
    PrintJobError
)


class TestPrinterDataClasses:
    """Test the data classes used in the printer interface."""
    
    def test_label_size_creation(self):
        """Test LabelSize creation and methods."""
        # Die-cut label
        label = LabelSize("62", 62.0, 29.0, 696, 271)
        assert label.name == "62"
        assert label.width_mm == 62.0
        assert label.height_mm == 29.0
        assert not label.is_continuous()
        
        # Continuous label
        continuous = LabelSize("62_continuous", 62.0, None)
        assert continuous.is_continuous()
    
    def test_print_job_result(self):
        """Test PrintJobResult creation."""
        result = PrintJobResult(True, "job_123", "Success")
        assert result.success
        assert result.job_id == "job_123"
        assert result.message == "Success"
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
        
        error_result = PrintJobResult(False, "job_456", error="Print failed")
        assert not error_result.success
        assert error_result.error == "Print failed"
    
    def test_preview_result(self):
        """Test PreviewResult creation."""
        label_size = LabelSize("62", 62.0, 29.0)
        result = PreviewResult(
            image_data=b"fake_image_data",
            format="png",
            width_px=200,
            height_px=100,
            label_size=label_size
        )
        assert result.format == "png"
        assert result.width_px == 200
        assert len(result.image_data) > 0
    
    def test_printer_info(self):
        """Test PrinterInfo creation."""
        info = PrinterInfo(
            id="printer_1",
            name="Test Printer",
            driver="MockDriver",
            model="Mock-800",
            status=PrinterStatus.READY,
            capabilities=[PrinterCapability.QR_CODES],
            backend="mock",
            identifier="mock://test"
        )
        assert info.id == "printer_1"
        assert info.status == PrinterStatus.READY
        assert PrinterCapability.QR_CODES in info.capabilities
    
    def test_test_result(self):
        """Test TestResult creation."""
        result = TestResult(True, 50.0, "Connected")
        assert result.success
        assert result.response_time_ms == 50.0
        assert isinstance(result.timestamp, datetime)


class TestPrinterExceptions:
    """Test custom printer exceptions."""
    
    def test_printer_error_base(self):
        """Test base PrinterError."""
        error = PrinterError("Test error", "printer_1", "TEST_CODE")
        assert str(error) == "Test error"
        assert error.printer_id == "printer_1"
        assert error.error_code == "TEST_CODE"
    
    def test_printer_not_found_error(self):
        """Test PrinterNotFoundError."""
        error = PrinterNotFoundError("missing_printer")
        assert error.printer_id == "missing_printer"
        assert error.error_code == "PRINTER_NOT_FOUND"
        assert "not found" in str(error)
    
    def test_invalid_label_size_error(self):
        """Test InvalidLabelSizeError."""
        error = InvalidLabelSizeError("99", "printer_1", ["12", "29", "62"])
        assert error.label_size == "99"
        assert error.supported_sizes == ["12", "29", "62"]
        assert "Invalid label size: 99" in str(error)
        assert "12, 29, 62" in str(error)
    
    def test_print_job_error(self):
        """Test PrintJobError."""
        error = PrintJobError("Job failed", "printer_1", "job_123")
        assert error.job_id == "job_123"
        assert error.printer_id == "printer_1"


class TestBasePrinter:
    """Test the BasePrinter abstract base class."""
    
    def test_base_printer_initialization(self):
        """Test BasePrinter initialization."""
        # Can't instantiate abstract class directly, so we'll test via mock
        pass  # Will test via MockPrinter
    
    def test_generate_job_id(self):
        """Test job ID generation is unique."""
        from MakerMatrix.printers.drivers.mock import MockPrinter
        
        printer = MockPrinter()
        job_id1 = printer._generate_job_id()
        job_id2 = printer._generate_job_id()
        
        assert job_id1 != job_id2
        assert job_id1.startswith("job_")
        assert len(job_id1) == 12  # "job_" + 8 hex chars
    
    def test_status_management(self):
        """Test status setting and retrieval."""
        from MakerMatrix.printers.drivers.mock import MockPrinter
        
        printer = MockPrinter()
        
        # Test initial status
        assert printer._status == PrinterStatus.READY
        
        # Test status change
        printer._set_status(PrinterStatus.PRINTING)
        assert printer._status == PrinterStatus.PRINTING
        
        # Test status with error
        printer._set_status(PrinterStatus.ERROR, "Test error")
        assert printer._status == PrinterStatus.ERROR
        assert printer._last_error == "Test error"


@pytest.mark.asyncio
class TestMockPrinter:
    """Test the MockPrinter implementation."""
    
    @pytest.fixture
    def mock_printer(self):
        """Create a mock printer for testing."""
        from MakerMatrix.printers.drivers.mock import MockPrinter
        return MockPrinter(simulate_errors=False)
    
    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        return Image.new('RGB', (200, 100), 'white')
    
    async def test_mock_printer_creation(self, mock_printer):
        """Test mock printer creation."""
        assert mock_printer.name == "Mock Printer"
        assert mock_printer.model == "MockQL-800"
        assert mock_printer.backend == "mock"
        
        status = await mock_printer.get_status()
        assert status == PrinterStatus.READY
    
    async def test_get_capabilities(self, mock_printer):
        """Test getting printer capabilities."""
        capabilities = await mock_printer.get_capabilities()
        assert PrinterCapability.QR_CODES in capabilities
        assert PrinterCapability.IMAGES in capabilities
        assert len(capabilities) > 0
    
    async def test_get_supported_label_sizes(self, mock_printer):
        """Test getting supported label sizes."""
        sizes = mock_printer.get_supported_label_sizes()
        assert len(sizes) > 0
        
        # Check for common Brother QL sizes
        size_names = [size.name for size in sizes]
        assert "62" in size_names
        assert "29" in size_names
        assert "12" in size_names
    
    async def test_connection_test(self, mock_printer):
        """Test connection testing."""
        result = await mock_printer.test_connection()
        assert result.success
        assert result.response_time_ms > 0
        assert result.error is None
    
    async def test_print_label_success(self, mock_printer, test_image):
        """Test successful label printing."""
        result = await mock_printer.print_label(test_image, "62", 1)
        
        assert result.success
        assert result.job_id.startswith("job_")
        assert result.error is None
        assert "Printed 1 label" in result.message
        
        # Check print history
        history = mock_printer.get_print_history()
        assert len(history) == 1
        assert history[0]["label_size"] == "62"
        assert history[0]["copies"] == 1
    
    async def test_print_label_multiple_copies(self, mock_printer, test_image):
        """Test printing multiple copies."""
        result = await mock_printer.print_label(test_image, "29", 3)
        
        assert result.success
        assert "Printed 3 label" in result.message
        
        history = mock_printer.get_print_history()
        assert history[-1]["copies"] == 3
    
    async def test_print_label_invalid_size(self, mock_printer, test_image):
        """Test printing with invalid label size."""
        with pytest.raises(InvalidLabelSizeError) as exc_info:
            await mock_printer.print_label(test_image, "999", 1)
        
        error = exc_info.value
        assert error.label_size == "999"
        assert error.error_code == "INVALID_LABEL_SIZE"
        assert len(error.supported_sizes) > 0
    
    async def test_preview_label(self, mock_printer, test_image):
        """Test label preview generation."""
        result = await mock_printer.preview_label(test_image, "62")
        
        assert result.format == "png"
        assert result.width_px > test_image.width  # Has border
        assert result.height_px > test_image.height  # Has border and text
        assert len(result.image_data) > 0
        assert "62mm" in result.message
    
    async def test_preview_invalid_size(self, mock_printer, test_image):
        """Test preview with invalid label size."""
        with pytest.raises(InvalidLabelSizeError):
            await mock_printer.preview_label(test_image, "invalid")
    
    async def test_cancel_job(self, mock_printer):
        """Test job cancellation."""
        # No current job
        result = await mock_printer.cancel_current_job()
        assert not result
        
        # Simulate job in progress
        mock_printer._current_job_id = "test_job"
        mock_printer._set_status(PrinterStatus.PRINTING)
        
        result = await mock_printer.cancel_current_job()
        assert result
        assert mock_printer._current_job_id is None
        
        status = await mock_printer.get_status()
        assert status == PrinterStatus.READY
    
    async def test_error_simulation(self, test_image):
        """Test error simulation functionality."""
        from MakerMatrix.printers.drivers.mock import MockPrinter
        
        # Create printer with error simulation
        error_printer = MockPrinter(simulate_errors=True)
        
        # Print several jobs to trigger error (every 5th fails)
        for i in range(4):
            result = await error_printer.print_label(test_image, "62", 1)
            assert result.success
        
        # 5th job should fail
        result = await error_printer.print_label(test_image, "62", 1)
        assert not result.success
        assert "out of paper" in result.error.lower()
        
        status = await error_printer.get_status()
        assert status == PrinterStatus.OUT_OF_PAPER
    
    def test_printer_info(self, mock_printer):
        """Test getting printer info."""
        info = mock_printer.get_printer_info()
        
        assert info.name == "Mock Printer"
        assert info.driver == "MockPrinter"
        assert info.model == "MockQL-800"
        assert info.backend == "mock"
        assert PrinterCapability.QR_CODES in info.capabilities
    
    def test_mock_specific_methods(self, mock_printer):
        """Test mock-specific testing methods."""
        # Test print history management
        assert len(mock_printer.get_print_history()) == 0
        
        # Test error simulation control
        mock_printer.set_error_simulation(True)
        assert mock_printer.simulate_errors
        
        # Test status simulation
        mock_printer.simulate_paper_out()
        assert mock_printer._status == PrinterStatus.OUT_OF_PAPER
        
        mock_printer.simulate_offline()
        assert mock_printer._status == PrinterStatus.OFFLINE
        
        mock_printer.reset_to_ready()
        assert mock_printer._status == PrinterStatus.READY
        
        # Test history clearing
        mock_printer._print_history.append({"test": "data"})
        mock_printer.clear_print_history()
        assert len(mock_printer.get_print_history()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])