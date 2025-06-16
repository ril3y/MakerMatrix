"""
Tests for text label printing functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image

from MakerMatrix.services.printer_manager_service import PrinterManagerService
from MakerMatrix.printers.base import PrintJobResult, LabelSize, PrinterStatus
from MakerMatrix.printers.drivers.brother_ql.driver import BrotherQLModern


class TestTextLabelPrinting:
    """Test text label printing with correct dimensions and orientation."""
    
    @pytest.fixture
    def printer_manager(self):
        """Create printer manager instance."""
        return PrinterManagerService()
    
    @pytest.fixture
    def mock_brother_printer(self):
        """Create mock Brother QL printer."""
        printer = MagicMock()
        printer.get_printer_info.return_value = MagicMock(
            id="test_brother",
            name="Test Brother QL",
            model="QL-800"
        )
        printer.get_supported_label_sizes.return_value = [
            LabelSize("12", 12.0, 29.0, 106, 164),
            LabelSize("29", 29.0, 90.0, 306, 991),
        ]
        printer.print_label = AsyncMock(return_value=PrintJobResult(
            success=True,
            job_id="test_job_123",
            message="Test print successful"
        ))
        return printer
    
    @pytest.mark.asyncio
    async def test_12mm_text_label_dimensions(self, printer_manager, mock_brother_printer):
        """Test that 12mm text labels are created with correct dimensions (43.1mm x 12mm)."""
        # Register mock printer
        await printer_manager.register_printer(mock_brother_printer)
        
        # Print text label
        result = await printer_manager.print_text_label(
            printer_id="test_brother",
            text="Test Label 12mm",
            label_size="12",
            copies=1
        )
        
        # Verify success
        assert result.success
        assert result.job_id == "test_job_123"
        
        # Verify printer.print_label was called
        mock_brother_printer.print_label.assert_called_once()
        
        # Get the image that was passed to print_label
        call_args = mock_brother_printer.print_label.call_args
        image, label_size, copies = call_args[0]
        
        # Verify label size parameter
        assert label_size == "12"
        assert copies == 1
        
        # Verify image dimensions (should be rotated, so height > width for 12mm labels)
        # Original: 43.1mm x 12mm -> ~509 x 141 pixels
        # After 90° rotation: 141 x ~509 pixels
        assert isinstance(image, Image.Image)
        assert image.width == 141  # 12mm in pixels
        assert image.height in [508, 509]  # 43.1mm in pixels (for 39mm final output)
    
    @pytest.mark.asyncio 
    async def test_29mm_text_label_no_rotation(self, printer_manager, mock_brother_printer):
        """Test that non-12mm labels don't get the special rotation treatment."""
        # Register mock printer
        await printer_manager.register_printer(mock_brother_printer)
        
        # Print text label on 29mm
        result = await printer_manager.print_text_label(
            printer_id="test_brother", 
            text="Test Label 29mm",
            label_size="29",
            copies=1
        )
        
        # Verify success
        assert result.success
        
        # Get the image that was passed to print_label
        call_args = mock_brother_printer.print_label.call_args
        image, label_size, copies = call_args[0]
        
        # Verify label size
        assert label_size == "29"
        
        # Verify image dimensions (should use normal label size, not rotated)
        assert image.width == 306  # 29mm width
        assert image.height == 991  # 90mm height
    
    @pytest.mark.asyncio
    async def test_text_label_font_scaling(self, printer_manager, mock_brother_printer):
        """Test that font size scales appropriately for long text."""
        # Register mock printer
        await printer_manager.register_printer(mock_brother_printer)
        
        # Print very long text
        long_text = "This is a very long text that should trigger font scaling to fit within the label width"
        
        result = await printer_manager.print_text_label(
            printer_id="test_brother",
            text=long_text, 
            label_size="12",
            copies=1
        )
        
        # Should still succeed even with long text
        assert result.success
        
        # Verify print_label was called
        mock_brother_printer.print_label.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_printer_not_found(self, printer_manager):
        """Test error handling when printer not found."""
        result = await printer_manager.print_text_label(
            printer_id="nonexistent_printer",
            text="Test",
            label_size="12", 
            copies=1
        )
        
        assert not result.success
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_unsupported_label_size(self, printer_manager, mock_brother_printer):
        """Test error handling for unsupported label sizes."""
        # Register mock printer
        await printer_manager.register_printer(mock_brother_printer)
        
        result = await printer_manager.print_text_label(
            printer_id="test_brother",
            text="Test",
            label_size="999",  # Unsupported size
            copies=1
        )
        
        assert not result.success
        assert "not supported" in result.error


class TestBrotherQLDriver:
    """Test Brother QL driver scaling behavior."""
    
    def test_brother_ql_12mm_label_size_definition(self):
        """Test that Brother QL driver has correct 12mm label size definition."""
        printer = BrotherQLModern(
            printer_id="test",
            name="Test",
            model="QL-800", 
            backend="network",
            identifier="tcp://192.168.1.1:9100"
        )
        
        sizes = printer.get_supported_label_sizes()
        label_12mm = next((size for size in sizes if size.name == "12"), None)
        
        assert label_12mm is not None
        assert label_12mm.width_mm == 12.0
        assert label_12mm.height_mm == 29.0
        assert label_12mm.width_px == 106
        assert label_12mm.height_px == 164


if __name__ == "__main__":
    pytest.main([__file__, "-v"])