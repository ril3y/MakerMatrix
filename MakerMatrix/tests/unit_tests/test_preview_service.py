"""
Unit tests for the preview service.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from PIL import Image

from MakerMatrix.services.preview_service import PreviewService, PreviewManager
from MakerMatrix.models.models import PartModel
from MakerMatrix.printers.base import PreviewResult, LabelSize, PrinterInterface
from MakerMatrix.printers.drivers.mock.driver import MockPrinter


@pytest.mark.asyncio
class TestPreviewService:
    """Test the preview service functionality."""
    
    @pytest.fixture
    def mock_printer(self):
        """Create a mock printer for testing."""
        return MockPrinter(
            printer_id="test_preview_printer",
            name="Test Preview Printer",
            model="TestQL-800",
            backend="mock",
            identifier="mock://test"
        )
    
    @pytest.fixture
    def preview_service(self, mock_printer):
        """Create a preview service with mock printer."""
        return PreviewService(mock_printer)
    
    @pytest.fixture
    def test_part(self):
        """Create a test part."""
        return PartModel(
            part_number="PREV_001",
            part_name="Preview Test Component",
            description="Test component for preview",
            quantity=10
        )
    
    def test_preview_service_initialization(self, mock_printer):
        """Test preview service initialization."""
        service = PreviewService(mock_printer)
        assert service.default_printer == mock_printer
        assert service.qr_service is not None
    
    def test_set_default_printer(self, preview_service):
        """Test setting default printer."""
        new_printer = MockPrinter("new_printer", "New Printer", "NewQL", "mock", "mock://new")
        preview_service.set_default_printer(new_printer)
        assert preview_service.default_printer == new_printer
    
    async def test_preview_part_qr_code(self, preview_service, test_part):
        """Test QR code preview generation."""
        result = await preview_service.preview_part_qr_code(test_part, "12")
        
        assert isinstance(result, PreviewResult)
        assert result.format == "png"
        assert result.width_px > 0
        assert result.height_px > 0
        assert len(result.image_data) > 0
        assert "Preview" in result.message
        assert result.label_size.name == "12"
    
    async def test_preview_part_qr_code_with_custom_printer(self, test_part):
        """Test QR code preview with custom printer."""
        custom_printer = MockPrinter("custom", "Custom", "CustomQL", "mock", "mock://custom")
        service = PreviewService()
        
        result = await service.preview_part_qr_code(test_part, "29", custom_printer)
        
        assert isinstance(result, PreviewResult)
        assert result.label_size.name == "29"
    
    async def test_preview_part_qr_code_no_printer(self, test_part):
        """Test QR code preview without printer raises error."""
        service = PreviewService()
        
        with pytest.raises(ValueError, match="No printer available"):
            await service.preview_part_qr_code(test_part)
    
    async def test_preview_part_name(self, preview_service, test_part):
        """Test part name preview generation."""
        result = await preview_service.preview_part_name(test_part, "12")
        
        assert isinstance(result, PreviewResult)
        assert result.format == "png"
        assert result.width_px > 0
        assert result.height_px > 0
        assert len(result.image_data) > 0
        assert result.label_size.name == "12"
    
    async def test_preview_text_label(self, preview_service):
        """Test custom text preview generation."""
        test_text = "Custom Label Text"
        result = await preview_service.preview_text_label(test_text, "29")
        
        assert isinstance(result, PreviewResult)
        assert result.format == "png"
        assert result.label_size.name == "29"
    
    async def test_preview_combined_label(self, preview_service, test_part):
        """Test combined QR + text preview generation."""
        custom_text = "Custom Text"
        result = await preview_service.preview_combined_label(test_part, custom_text, "62")
        
        assert isinstance(result, PreviewResult)
        assert result.format == "png"
        assert result.label_size.name == "62"
    
    async def test_preview_combined_label_no_custom_text(self, preview_service, test_part):
        """Test combined preview without custom text."""
        result = await preview_service.preview_combined_label(test_part, label_size="12")
        
        assert isinstance(result, PreviewResult)
        assert result.label_size.name == "12"
    
    def test_get_available_label_sizes(self, preview_service):
        """Test getting available label sizes."""
        sizes = preview_service.get_available_label_sizes()
        
        assert isinstance(sizes, list)
        assert len(sizes) > 0
        assert all(isinstance(size, LabelSize) for size in sizes)
        
        # Check for common sizes
        size_names = [size.name for size in sizes]
        assert "12" in size_names
        assert "29" in size_names
    
    def test_validate_label_size(self, preview_service):
        """Test label size validation."""
        # Valid sizes
        assert preview_service.validate_label_size("12")
        assert preview_service.validate_label_size("29")
        assert preview_service.validate_label_size("62")
        
        # Invalid size
        assert not preview_service.validate_label_size("999")
        assert not preview_service.validate_label_size("invalid")
    
    def test_validate_label_size_no_printer(self):
        """Test label size validation without printer."""
        service = PreviewService()
        sizes = service.get_available_label_sizes()
        assert sizes == []
    
    def test_generate_text_image(self, preview_service):
        """Test text image generation."""
        text = "Test Text"
        size = (300, 100)
        
        image = preview_service._generate_text_image(text, size)
        
        assert isinstance(image, Image.Image)
        assert image.size == size
        assert image.mode == 'RGB'
    
    def test_create_combined_image(self, preview_service):
        """Test combined image creation."""
        qr_image = Image.new('RGB', (100, 100), 'black')
        text = "Test Label Text"
        size = (300, 150)
        
        combined = preview_service._create_combined_image(qr_image, text, size)
        
        assert isinstance(combined, Image.Image)
        assert combined.size == size
        assert combined.mode == 'RGB'
    
    def test_wrap_text(self, preview_service):
        """Test text wrapping functionality."""
        from PIL import ImageDraw, ImageFont
        
        image = Image.new('RGB', (100, 100), 'white')
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        
        # Test with text that should wrap
        long_text = "This is a very long text that should be wrapped across multiple lines"
        lines = preview_service._wrap_text(long_text, 100, font, draw)
        
        assert isinstance(lines, list)
        assert len(lines) > 1  # Should be wrapped into multiple lines
        
        # Test with short text
        short_text = "Short"
        lines = preview_service._wrap_text(short_text, 200, font, draw)
        assert len(lines) == 1
        assert lines[0] == "Short"


@pytest.mark.asyncio 
class TestPreviewManager:
    """Test the preview manager functionality."""
    
    @pytest.fixture
    def preview_manager(self):
        """Create a fresh preview manager."""
        return PreviewManager()
    
    @pytest.fixture
    def test_printers(self):
        """Create test printers."""
        printer1 = MockPrinter("printer1", "Printer 1", "Mock1", "mock", "mock://1")
        printer2 = MockPrinter("printer2", "Printer 2", "Mock2", "mock", "mock://2")
        return printer1, printer2
    
    def test_preview_manager_initialization(self, preview_manager):
        """Test preview manager initialization."""
        assert len(preview_manager.preview_services) == 0
        assert preview_manager.default_service is None
    
    def test_register_printer(self, preview_manager, test_printers):
        """Test registering printers."""
        printer1, printer2 = test_printers
        
        # Register first printer (should become default)
        preview_manager.register_printer("printer1", printer1)
        assert "printer1" in preview_manager.preview_services
        assert preview_manager.default_service is not None
        
        # Register second printer
        preview_manager.register_printer("printer2", printer2)
        assert "printer2" in preview_manager.preview_services
        assert len(preview_manager.preview_services) == 2
    
    def test_get_preview_service_by_id(self, preview_manager, test_printers):
        """Test getting preview service by printer ID."""
        printer1, printer2 = test_printers
        
        preview_manager.register_printer("printer1", printer1)
        preview_manager.register_printer("printer2", printer2)
        
        # Get specific printer service
        service1 = preview_manager.get_preview_service("printer1")
        assert service1.default_printer == printer1
        
        service2 = preview_manager.get_preview_service("printer2")
        assert service2.default_printer == printer2
    
    def test_get_preview_service_default(self, preview_manager, test_printers):
        """Test getting default preview service."""
        printer1, _ = test_printers
        
        preview_manager.register_printer("printer1", printer1)
        
        # Get default service
        service = preview_manager.get_preview_service()
        assert service.default_printer == printer1
    
    def test_get_preview_service_invalid_id(self, preview_manager, test_printers):
        """Test getting preview service with invalid ID falls back to default."""
        printer1, _ = test_printers
        
        preview_manager.register_printer("printer1", printer1)
        
        # Invalid ID should return default
        service = preview_manager.get_preview_service("invalid_id")
        assert service.default_printer == printer1
    
    def test_get_preview_service_no_printers(self, preview_manager):
        """Test getting preview service when no printers registered."""
        with pytest.raises(ValueError, match="No preview service available"):
            preview_manager.get_preview_service()
    
    def test_get_registered_printers(self, preview_manager, test_printers):
        """Test getting list of registered printers."""
        printer1, printer2 = test_printers
        
        # Initially empty
        assert preview_manager.get_registered_printers() == []
        
        # Register printers
        preview_manager.register_printer("printer1", printer1)
        preview_manager.register_printer("printer2", printer2)
        
        registered = preview_manager.get_registered_printers()
        assert "printer1" in registered
        assert "printer2" in registered
        assert len(registered) == 2
    
    async def test_preview_with_printer(self, preview_manager, test_printers):
        """Test preview generation with specific printer."""
        printer1, _ = test_printers
        
        preview_manager.register_printer("printer1", printer1)
        
        # Create test image
        test_image = Image.new('RGB', (100, 50), 'white')
        
        # Generate preview
        result = await preview_manager.preview_with_printer("printer1", test_image, "12")
        
        assert isinstance(result, PreviewResult)
        assert result.label_size.name == "12"
    
    async def test_preview_with_invalid_printer(self, preview_manager):
        """Test preview with invalid printer ID."""
        test_image = Image.new('RGB', (100, 50), 'white')
        
        with pytest.raises(ValueError, match="No preview service available"):
            await preview_manager.preview_with_printer("invalid", test_image, "12")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])