"""
Unit tests for the modern Brother QL printer driver.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image
import socket

from MakerMatrix.printers.drivers.brother_ql import BrotherQLModern
from MakerMatrix.printers.base import (
    PrinterStatus,
    PrinterCapability,
    InvalidLabelSizeError,
    PrintJobError,
    PrinterOfflineError
)


@pytest.mark.asyncio
class TestBrotherQLModern:
    """Test the modern Brother QL printer driver."""
    
    @pytest.fixture
    def brother_ql_printer(self):
        """Create a Brother QL printer for testing."""
        return BrotherQLModern(
            printer_id="brother_ql_test",
            name="Test Brother QL",
            model="QL-800",
            backend="network",
            identifier="tcp://192.168.1.100:9100",
            dpi=300,
            scaling_factor=1.0
        )
    
    @pytest.fixture
    def usb_brother_ql_printer(self):
        """Create a USB Brother QL printer for testing."""
        return BrotherQLModern(
            printer_id="brother_ql_usb",
            name="USB Brother QL",
            model="QL-700",
            backend="usb",
            identifier="/dev/usb/lp0",
            dpi=300
        )
    
    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        return Image.new('RGB', (200, 100), 'white')
    
    def test_printer_initialization(self, brother_ql_printer):
        """Test Brother QL printer initialization."""
        assert brother_ql_printer.printer_id == "brother_ql_test"
        assert brother_ql_printer.name == "Test Brother QL"
        assert brother_ql_printer.model == "QL-800"
        assert brother_ql_printer.backend == "network"
        assert brother_ql_printer.identifier == "tcp://192.168.1.100:9100"
        assert brother_ql_printer.dpi == 300
        assert brother_ql_printer.scaling_factor == 1.0
    
    def test_supported_label_sizes(self, brother_ql_printer):
        """Test Brother QL supported label sizes."""
        sizes = brother_ql_printer.get_supported_label_sizes()
        assert len(sizes) > 0
        
        # Check for common Brother QL sizes
        size_names = [size.name for size in sizes]
        assert "62" in size_names
        assert "29" in size_names
        assert "12" in size_names
        assert "62mm" in size_names  # Continuous
        
        # Check die-cut vs continuous
        size_62_die_cut = next(s for s in sizes if s.name == "62")
        size_62_continuous = next(s for s in sizes if s.name == "62mm")
        
        assert not size_62_die_cut.is_continuous()
        assert size_62_continuous.is_continuous()
    
    async def test_get_capabilities(self, brother_ql_printer):
        """Test getting Brother QL capabilities."""
        capabilities = await brother_ql_printer.get_capabilities()
        
        expected_capabilities = [
            PrinterCapability.QR_CODES,
            PrinterCapability.BARCODES,
            PrinterCapability.IMAGES,
            PrinterCapability.DIE_CUT_LABELS,
            PrinterCapability.CONTINUOUS_LABELS
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities
    
    async def test_get_status_ready(self, brother_ql_printer):
        """Test getting printer status when ready."""
        # Mock network connection for status check
        with patch('socket.create_connection') as mock_socket:
            mock_socket.return_value.close.return_value = None
            
            status = await brother_ql_printer.get_status()
            assert status == PrinterStatus.READY
    
    async def test_get_status_offline(self, brother_ql_printer):
        """Test getting printer status when offline."""
        # Mock failed network connection
        with patch('socket.create_connection', side_effect=socket.error("Connection failed")):
            status = await brother_ql_printer.get_status()
            assert status == PrinterStatus.OFFLINE
    
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.send')
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.convert')
    async def test_print_label_success(self, mock_convert, mock_send, brother_ql_printer, test_image):
        """Test successful label printing."""
        # Mock the Brother QL components
        mock_convert.return_value = b"mock_instructions"
        mock_send.return_value = True
        
        # Mock network connectivity check
        with patch('socket.create_connection') as mock_socket:
            mock_socket.return_value.close.return_value = None
            
            result = await brother_ql_printer.print_label(test_image, "62", 1)
            
            assert result.success
            assert result.job_id.startswith("job_")
            assert "Brother QL" in result.message
            assert result.error is None
            
            # Verify the print was recorded
            history = brother_ql_printer.get_print_history()
            assert len(history) == 1
            assert history[0]["label_size"] == "62"
            assert history[0]["copies"] == 1
            assert history[0]["success"] is True
    
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.send')
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.convert')
    async def test_print_label_multiple_copies(self, mock_convert, mock_send, brother_ql_printer, test_image):
        """Test printing multiple copies."""
        mock_convert.return_value = b"mock_instructions"
        mock_send.return_value = True
        
        with patch('socket.create_connection') as mock_socket:
            mock_socket.return_value.close.return_value = None
            
            result = await brother_ql_printer.print_label(test_image, "29", 3)
            
            assert result.success
            assert mock_send.call_count == 3  # Should be called once per copy
            
            history = brother_ql_printer.get_print_history()
            assert len(history) == 1
            assert history[0]["copies"] == 3
    
    async def test_print_label_invalid_size(self, brother_ql_printer, test_image):
        """Test printing with invalid label size."""
        with pytest.raises(InvalidLabelSizeError) as exc_info:
            await brother_ql_printer.print_label(test_image, "999", 1)
        
        error = exc_info.value
        assert error.label_size == "999"
        assert error.printer_id == "brother_ql_test"
        assert len(error.supported_sizes) > 0
    
    async def test_print_label_printer_offline(self, brother_ql_printer, test_image):
        """Test printing when printer is offline."""
        # Mock failed network connection
        with patch('socket.create_connection', side_effect=socket.error("Connection failed")):
            with pytest.raises(PrinterOfflineError) as exc_info:
                await brother_ql_printer.print_label(test_image, "62", 1)
            
            error = exc_info.value
            assert error.printer_id == "brother_ql_test"
            assert "not ready" in error.message.lower()
    
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.send')
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.convert')
    async def test_print_label_send_failure(self, mock_convert, mock_send, brother_ql_printer, test_image):
        """Test handling print send failure."""
        mock_convert.return_value = b"mock_instructions"
        mock_send.return_value = False  # Simulate send failure
        
        with patch('socket.create_connection') as mock_socket:
            mock_socket.return_value.close.return_value = None
            
            result = await brother_ql_printer.print_label(test_image, "62", 1)
            
            assert not result.success
            assert result.error is not None
            assert "Print failed" in result.error
    
    async def test_preview_label(self, brother_ql_printer, test_image):
        """Test label preview generation."""
        result = await brother_ql_printer.preview_label(test_image, "62")
        
        assert result.format == "png"
        assert result.width_px > test_image.width  # Has border
        assert result.height_px > test_image.height  # Has border and header
        assert len(result.image_data) > 0
        assert "Brother QL" in result.message
        assert result.label_size.name == "62"
    
    async def test_preview_label_continuous(self, brother_ql_printer, test_image):
        """Test preview for continuous label."""
        result = await brother_ql_printer.preview_label(test_image, "62mm")
        
        assert result.label_size.is_continuous()
        assert "continuous" in result.message.lower() or "mm" in result.message
    
    async def test_preview_invalid_size(self, brother_ql_printer, test_image):
        """Test preview with invalid label size."""
        with pytest.raises(InvalidLabelSizeError):
            await brother_ql_printer.preview_label(test_image, "invalid")
    
    async def test_test_connection_network_success(self, brother_ql_printer):
        """Test successful network connection test."""
        with patch('socket.create_connection') as mock_socket:
            mock_socket.return_value.close.return_value = None
            
            result = await brother_ql_printer.test_connection()
            
            assert result.success
            assert result.response_time_ms > 0
            assert "192.168.1.100" in result.message
            assert result.error is None
    
    async def test_test_connection_network_timeout(self, brother_ql_printer):
        """Test network connection timeout."""
        with patch('socket.create_connection', side_effect=socket.timeout("Timeout")):
            result = await brother_ql_printer.test_connection()
            
            assert not result.success
            assert result.response_time_ms > 0
            assert "timeout" in result.error.lower()
    
    async def test_test_connection_usb(self, usb_brother_ql_printer):
        """Test USB connection test."""
        result = await usb_brother_ql_printer.test_connection()
        
        # USB test should succeed (basic implementation)
        assert result.success
        assert "USB" in result.message
    
    async def test_cancel_job(self, brother_ql_printer):
        """Test job cancellation."""
        # No current job
        result = await brother_ql_printer.cancel_current_job()
        assert not result
        
        # Simulate job in progress
        brother_ql_printer._current_job_id = "test_job"
        brother_ql_printer._set_status(PrinterStatus.PRINTING)
        
        # Mock network connection for status check after cancel
        with patch('socket.create_connection') as mock_socket:
            mock_socket.return_value.close.return_value = None
            
            result = await brother_ql_printer.cancel_current_job()
            assert result
            assert brother_ql_printer._current_job_id is None
            
            status = await brother_ql_printer.get_status()
            assert status == PrinterStatus.READY
    
    def test_printer_info(self, brother_ql_printer):
        """Test getting printer info."""
        info = brother_ql_printer.get_printer_info()
        
        assert info.id == "brother_ql_test"
        assert info.name == "Test Brother QL"
        assert info.driver == "BrotherQLModern"
        assert info.model == "QL-800"
        assert info.backend == "network"
        assert PrinterCapability.QR_CODES in info.capabilities
        assert PrinterCapability.DIE_CUT_LABELS in info.capabilities
    
    def test_brother_ql_specific_info(self, brother_ql_printer):
        """Test Brother QL specific information."""
        info = brother_ql_printer.get_brother_ql_info()
        
        assert info["model"] == "QL-800"
        assert info["backend"] == "network"
        assert info["dpi"] == 300
        assert info["scaling_factor"] == 1.0
        assert "qlr_initialized" in info
    
    def test_print_history_management(self, brother_ql_printer):
        """Test print history management."""
        # Initially empty
        assert len(brother_ql_printer.get_print_history()) == 0
        
        # Add some history manually for testing
        brother_ql_printer._print_history.append({
            "job_id": "test_123",
            "label_size": "62",
            "copies": 1,
            "success": True
        })
        
        history = brother_ql_printer.get_print_history()
        assert len(history) == 1
        assert history[0]["job_id"] == "test_123"
        
        # Clear history
        brother_ql_printer.clear_print_history()
        assert len(brother_ql_printer.get_print_history()) == 0
    
    def test_label_size_validation(self, brother_ql_printer):
        """Test label size validation methods."""
        # Valid sizes
        assert brother_ql_printer._is_valid_label_size("62")
        assert brother_ql_printer._is_valid_label_size("29mm")
        assert brother_ql_printer._is_valid_label_size("17x54")
        
        # Invalid sizes
        assert not brother_ql_printer._is_valid_label_size("999")
        assert not brother_ql_printer._is_valid_label_size("invalid")
        
        # Get label info
        info = brother_ql_printer._get_label_size_info("62")
        assert info.name == "62"
        assert info.width_mm == 62.0
        assert info.height_mm == 29.0
        
        # Test continuous label
        continuous_info = brother_ql_printer._get_label_size_info("62mm")
        assert continuous_info.is_continuous()


@pytest.mark.asyncio
class TestBrotherQLErrorHandling:
    """Test error handling in Brother QL driver."""
    
    @pytest.fixture
    def error_printer(self):
        """Create a Brother QL printer with initialization error."""
        with patch('brother_ql.raster.BrotherQLRaster', side_effect=Exception("QL Init failed")):
            printer = BrotherQLModern(
                printer_id="error_printer",
                name="Error Printer",
                model="QL-INVALID",
                backend="network",
                identifier="tcp://invalid:9100"
            )
        return printer
    
    def test_initialization_error(self, error_printer):
        """Test handling initialization errors."""
        assert error_printer._status == PrinterStatus.ERROR
        assert "Failed to initialize Brother QL" in error_printer._last_error
    
    async def test_print_with_uninitialized_qlr(self, error_printer):
        """Test printing with uninitialized QLR."""
        test_image = Image.new('RGB', (100, 50), 'white')
        
        # Since the printer is in ERROR state, it will fail the readiness check first
        with pytest.raises(PrinterOfflineError) as exc_info:
            await error_printer.print_label(test_image, "62", 1)
        
        error = exc_info.value
        assert error.printer_id == "error_printer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])