"""
Integration tests for Brother QL driver with the modern printer service.
"""
import pytest
from unittest.mock import patch, MagicMock

from MakerMatrix.printers.drivers.brother_ql import BrotherQLModern

from MakerMatrix.models.models import PartModel
from MakerMatrix.printers.base import PrinterStatus, PrinterCapability


@pytest.mark.integration
@pytest.mark.asyncio
class TestBrotherQLIntegration:
    """Integration tests for Brother QL with the modern printer system."""
    
    @pytest.fixture
    def brother_ql_printer(self):
        """Create a Brother QL printer for integration testing."""
        return BrotherQLModern(
            printer_id="integration_brother_ql",
            name="Integration Test Brother QL",
            model="QL-800",
            backend="network", 
            identifier="tcp://192.168.1.100:9100",
            dpi=300,
            scaling_factor=1.1
        )
    
    @pytest.fixture
    def printer_service_with_brother_ql(self, brother_ql_printer):
        """Create printer service with Brother QL."""
        return ModernPrinterService(default_printer=brother_ql_printer)
    
    @pytest.fixture
    def test_part(self):
        """Create a test part for printing."""
        return PartModel(
            part_number="BQL_TEST_001",
            part_name="Brother QL Test Component", 
            description="Integration test component for Brother QL",
            quantity=25
        )
    
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.send')
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.convert')
    @patch('socket.create_connection')
    async def test_brother_ql_with_service_qr_code(self, mock_socket, mock_convert, mock_send, 
                                                   printer_service_with_brother_ql, test_part):
        """Test Brother QL QR code printing through the modern service."""
        # Mock successful network connection and printing
        mock_socket.return_value.close.return_value = None
        mock_convert.return_value = b"brother_ql_instructions"
        mock_send.return_value = True
        
        # Print QR code through service
        result = await printer_service_with_brother_ql.print_part_qr_code(test_part)
        
        assert result.success
        assert result.job_id.startswith("job_")
        assert "Brother QL" in result.message
        
        # Verify Brother QL specific calls were made
        mock_convert.assert_called_once()
        mock_send.assert_called_once()
        
        # Check convert call parameters
        convert_args = mock_convert.call_args
        assert convert_args[1]["label"] == "62"  # Default label size
        assert convert_args[1]["dpi_600"] is False  # 300 DPI
        assert convert_args[1]["cut"] is True
        
        # Check print history
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        history = brother_ql.get_print_history()
        assert len(history) == 1
        assert history[0]["label_size"] == "62"
    
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.send')
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.convert')
    @patch('socket.create_connection')
    async def test_brother_ql_with_service_part_name(self, mock_socket, mock_convert, mock_send,
                                                     printer_service_with_brother_ql, test_part):
        """Test Brother QL part name printing through the modern service."""
        # Mock successful operations
        mock_socket.return_value.close.return_value = None
        mock_convert.return_value = b"brother_ql_text_instructions"
        mock_send.return_value = True
        
        # Print part name through service
        result = await printer_service_with_brother_ql.print_part_name(test_part)
        
        assert result.success
        assert result.job_id.startswith("job_")
        
        # Verify Brother QL was called
        mock_convert.assert_called_once()
        mock_send.assert_called_once()
    
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.send')
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.convert')
    @patch('socket.create_connection')
    async def test_brother_ql_with_service_text_label(self, mock_socket, mock_convert, mock_send,
                                                      printer_service_with_brother_ql):
        """Test Brother QL text label printing through the modern service."""
        # Mock successful operations
        mock_socket.return_value.close.return_value = None
        mock_convert.return_value = b"brother_ql_custom_text"
        mock_send.return_value = True
        
        # Print custom text
        result = await printer_service_with_brother_ql.print_text_label(
            "Integration Test Label", 
            label_size="29",
            copies=2
        )
        
        assert result.success
        
        # Should be called twice for 2 copies
        assert mock_send.call_count == 2
        
        # Check Brother QL history
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        history = brother_ql.get_print_history()
        assert len(history) == 1
        assert history[0]["copies"] == 2
        assert history[0]["label_size"] == "29"
    
    async def test_brother_ql_capabilities_through_service(self, printer_service_with_brother_ql):
        """Test Brother QL capabilities are accessible through service."""
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        
        # Test capabilities
        capabilities = await brother_ql.get_capabilities()
        expected_capabilities = [
            PrinterCapability.QR_CODES,
            PrinterCapability.BARCODES,
            PrinterCapability.IMAGES,
            PrinterCapability.DIE_CUT_LABELS,
            PrinterCapability.CONTINUOUS_LABELS
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities
        
        # Test label sizes
        sizes = brother_ql.get_supported_label_sizes()
        size_names = [s.name for s in sizes]
        
        # Check both die-cut and continuous sizes
        assert "62" in size_names     # Die-cut
        assert "62mm" in size_names   # Continuous
        assert "17x54" in size_names  # Special size
    
    @patch('socket.create_connection')
    async def test_brother_ql_status_monitoring(self, mock_socket, printer_service_with_brother_ql):
        """Test Brother QL status monitoring through service."""
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        
        # Test online status
        mock_socket.return_value.close.return_value = None
        status = await brother_ql.get_status()
        assert status == PrinterStatus.READY
        
        # Test offline status
        mock_socket.side_effect = ConnectionError("Network unreachable")
        status = await brother_ql.get_status()
        assert status == PrinterStatus.OFFLINE
    
    @patch('socket.create_connection')
    async def test_brother_ql_connection_test(self, mock_socket, printer_service_with_brother_ql):
        """Test Brother QL connection testing through service."""
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        
        # Test successful connection
        mock_socket.return_value.close.return_value = None
        result = await brother_ql.test_connection()
        
        assert result.success
        assert result.response_time_ms > 0
        assert "192.168.1.100" in result.message
        assert result.error is None
        
        # Verify correct port was used
        mock_socket.assert_called_with(("192.168.1.100", 9100), timeout=5)
    
    async def test_brother_ql_preview_generation(self, printer_service_with_brother_ql):
        """Test Brother QL preview generation."""
        from PIL import Image
        
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        test_image = Image.new('RGB', (200, 100), 'white')
        
        # Test preview generation
        preview = await brother_ql.preview_label(test_image, "62")
        
        assert preview.format == "png"
        assert preview.width_px > test_image.width   # Has border
        assert preview.height_px > test_image.height # Has header
        assert len(preview.image_data) > 0
        assert "Brother QL preview for 62mm label" in preview.message
        assert preview.label_size.name == "62"
    
    def test_brother_ql_printer_info(self, printer_service_with_brother_ql):
        """Test Brother QL printer info through service."""
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        
        info = brother_ql.get_printer_info()
        
        assert info.id == "integration_brother_ql"
        assert info.name == "Integration Test Brother QL"
        assert info.driver == "BrotherQLModern"
        assert info.model == "QL-800"
        assert info.backend == "network"
        assert info.identifier == "tcp://192.168.1.100:9100"
        
        # Check Brother QL specific capabilities
        assert PrinterCapability.QR_CODES in info.capabilities
        assert PrinterCapability.DIE_CUT_LABELS in info.capabilities
        assert PrinterCapability.CONTINUOUS_LABELS in info.capabilities
    
    def test_brother_ql_specific_info(self, printer_service_with_brother_ql):
        """Test Brother QL specific information methods."""
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        
        # Test Brother QL specific info
        ql_info = brother_ql.get_brother_ql_info()
        
        assert ql_info["model"] == "QL-800"
        assert ql_info["backend"] == "network"
        assert ql_info["identifier"] == "tcp://192.168.1.100:9100"
        assert ql_info["dpi"] == 300
        assert ql_info["scaling_factor"] == 1.1
        assert ql_info["qlr_initialized"] is True
    
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.send', side_effect=Exception("Print hardware error"))
    @patch('MakerMatrix.printers.drivers.brother_ql.driver.convert')
    @patch('socket.create_connection')
    async def test_brother_ql_error_handling(self, mock_socket, mock_convert, mock_send,
                                             printer_service_with_brother_ql, test_part):
        """Test Brother QL error handling in integration."""
        # Mock network OK but print fails
        mock_socket.return_value.close.return_value = None
        mock_convert.return_value = b"instructions"
        
        # This should handle the print error gracefully
        result = await printer_service_with_brother_ql.print_part_qr_code(test_part)
        
        assert not result.success
        assert result.error is not None
        assert "Print error on copy 1: Print hardware error" in result.error
        
        # Printer should recover to ready state
        brother_ql = printer_service_with_brother_ql.get_default_printer()
        status = await brother_ql.get_status()
        assert status == PrinterStatus.READY  # Should recover


if __name__ == "__main__":
    pytest.main([__file__, "-v"])