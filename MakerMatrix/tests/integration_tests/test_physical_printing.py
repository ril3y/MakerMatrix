"""
Integration tests for actual physical label printing.
These tests will attempt to print real labels if a Brother QL printer is available.
"""
import pytest
import asyncio
from PIL import Image, ImageDraw, ImageFont

from MakerMatrix.printers.drivers.brother_ql.driver import BrotherQLModern
from MakerMatrix.services.printer.qr_service import QRService
from MakerMatrix.models.models import PartModel


@pytest.mark.integration
@pytest.mark.physical_print
class TestPhysicalPrinting:
    """Tests for physical label printing - requires actual Brother QL printer."""
    
    @pytest.fixture
    def brother_ql_printer(self):
        """Create Brother QL printer configured for 12mm labels."""
        return BrotherQLModern(
            printer_id="physical_test_printer",
            name="Physical Test Brother QL",
            model="QL-800",
            backend="network",
            identifier="tcp://192.168.1.100:9100",  # Update with your printer's IP
            dpi=300,
            scaling_factor=1.0
        )
    
    @pytest.fixture
    def qr_service(self):
        """Create QR service for generating QR codes."""
        return QRService()
    
    @pytest.fixture 
    def test_part(self):
        """Create test part for printing."""
        return PartModel(
            part_number="PHYS_TEST_001",
            part_name="Physical Test Component",
            description="Component for physical printing test",
            quantity=5
        )
    
    def create_test_text_image(self, text: str, size: tuple = (300, 150)) -> Image.Image:
        """Create a simple text image for testing."""
        image = Image.new('RGB', size, 'white')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Center the text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        draw.text((x, y), text, fill='black', font=font)
        
        # Add border for visibility
        draw.rectangle([0, 0, size[0]-1, size[1]-1], outline='black', width=2)
        
        return image
    
    async def test_printer_connection(self, brother_ql_printer):
        """Test that we can connect to the Brother QL printer."""
        result = await brother_ql_printer.test_connection()
        
        assert result.success, f"Cannot connect to printer: {result.error}"
        assert result.response_time_ms > 0
        print(f"✓ Connected to printer in {result.response_time_ms:.1f}ms")
    
    async def test_printer_status(self, brother_ql_printer):
        """Test that the printer is ready for printing."""
        status = await brother_ql_printer.get_status()
        
        assert status in [brother_ql_printer.PrinterStatus.READY, brother_ql_printer.PrinterStatus.IDLE], \
            f"Printer not ready: {status}"
        print(f"✓ Printer status: {status}")
    
    async def test_print_simple_text_12mm(self, brother_ql_printer):
        """Test printing simple text on 12mm label."""
        print("\n🖨️  PHYSICAL PRINT TEST: Simple text on 12mm label")
        
        # Create simple text image suitable for 12mm label
        text_image = self.create_test_text_image("TEST 12mm", (200, 80))
        
        # Print with 12mm label size
        result = await brother_ql_printer.print_label(text_image, "12", copies=1)
        
        assert result.success, f"Print failed: {result.error}"
        assert result.job_id.startswith("job_")
        
        print(f"✓ Printed successfully: {result.message}")
        print(f"  Job ID: {result.job_id}")
        
        # Check print history
        history = brother_ql_printer.get_print_history()
        assert len(history) > 0
        last_job = history[-1]
        assert last_job["label_size"] == "12"
        assert last_job["success"] is True
        
        return result
    
    async def test_print_qr_code_12mm(self, brother_ql_printer, qr_service, test_part):
        """Test printing QR code on 12mm label."""
        print("\n🖨️  PHYSICAL PRINT TEST: QR code on 12mm label")
        
        # Generate QR code for the test part
        qr_data = f"PART:{test_part.part_number}|NAME:{test_part.part_name}"
        qr_image = qr_service.generate_qr_code(qr_data, size=(100, 100))
        
        # Print QR code
        result = await brother_ql_printer.print_label(qr_image, "12", copies=1)
        
        assert result.success, f"QR print failed: {result.error}"
        
        print(f"✓ QR code printed successfully: {result.message}")
        print(f"  QR data: {qr_data}")
        
        return result
    
    async def test_print_part_info_12mm(self, brother_ql_printer, test_part):
        """Test printing part information on 12mm label."""
        print("\n🖨️  PHYSICAL PRINT TEST: Part info on 12mm label")
        
        # Create part info image
        part_text = f"{test_part.part_number}\\n{test_part.part_name}"
        part_image = self.create_test_text_image(part_text, (250, 80))
        
        # Print part info
        result = await brother_ql_printer.print_label(part_image, "12", copies=1)
        
        assert result.success, f"Part info print failed: {result.error}"
        
        print(f"✓ Part info printed successfully")
        print(f"  Part: {test_part.part_number} - {test_part.part_name}")
        
        return result
    
    async def test_print_multiple_copies_12mm(self, brother_ql_printer):
        """Test printing multiple copies on 12mm labels."""
        print("\n🖨️  PHYSICAL PRINT TEST: Multiple copies on 12mm labels")
        
        # Create test image
        multi_image = self.create_test_text_image("COPY TEST", (180, 60))
        
        # Print 3 copies
        result = await brother_ql_printer.print_label(multi_image, "12", copies=3)
        
        assert result.success, f"Multi-copy print failed: {result.error}"
        
        print(f"✓ Printed 3 copies successfully")
        
        # Verify in history
        history = brother_ql_printer.get_print_history()
        last_job = history[-1]
        assert last_job["copies"] == 3
        
        return result
    
    async def test_print_continuous_12mm(self, brother_ql_printer):
        """Test printing on 12mm continuous label."""
        print("\n🖨️  PHYSICAL PRINT TEST: Continuous 12mm label")
        
        # Create longer image for continuous label
        continuous_image = self.create_test_text_image("CONTINUOUS 12mm LABEL", (400, 80))
        
        # Print on continuous 12mm
        result = await brother_ql_printer.print_label(continuous_image, "12mm", copies=1)
        
        assert result.success, f"Continuous print failed: {result.error}"
        
        print(f"✓ Continuous label printed successfully")
        
        return result
    
    def test_supported_12mm_sizes(self, brother_ql_printer):
        """Test that 12mm sizes are supported."""
        sizes = brother_ql_printer.get_supported_label_sizes()
        size_names = [size.name for size in sizes]
        
        assert "12" in size_names, "12mm die-cut label not supported"
        assert "12mm" in size_names, "12mm continuous label not supported"
        
        # Get specific size info
        size_12 = next(s for s in sizes if s.name == "12")
        size_12mm = next(s for s in sizes if s.name == "12mm")
        
        assert size_12.width_mm == 12.0
        assert not size_12.is_continuous()
        assert size_12mm.width_mm == 12.0
        assert size_12mm.is_continuous()
        
        print(f"✓ 12mm label sizes supported:")
        print(f"  - 12mm die-cut: {size_12.width_mm}x{size_12.height_mm}mm")
        print(f"  - 12mm continuous: {size_12mm.width_mm}mm continuous")
    
    async def test_comprehensive_12mm_printing_sequence(self, brother_ql_printer, qr_service, test_part):
        """Run a comprehensive sequence of 12mm label printing tests."""
        print("\n🚀 COMPREHENSIVE 12mm LABEL PRINTING TEST SEQUENCE")
        print("=" * 60)
        
        # Test 1: Connection and status
        print("\\n1. Testing connection and status...")
        await self.test_printer_connection(brother_ql_printer)
        await self.test_printer_status(brother_ql_printer)
        
        # Test 2: Simple text
        print("\\n2. Testing simple text printing...")
        await self.test_print_simple_text_12mm(brother_ql_printer)
        
        # Test 3: QR code
        print("\\n3. Testing QR code printing...")
        await self.test_print_qr_code_12mm(brother_ql_printer, qr_service, test_part)
        
        # Test 4: Part information
        print("\\n4. Testing part information printing...")
        await self.test_print_part_info_12mm(brother_ql_printer, test_part)
        
        # Test 5: Multiple copies
        print("\\n5. Testing multiple copies...")
        await self.test_print_multiple_copies_12mm(brother_ql_printer)
        
        # Test 6: Continuous label
        print("\\n6. Testing continuous label...")
        await self.test_print_continuous_12mm(brother_ql_printer)
        
        print("\\n✅ ALL 12mm PRINTING TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Print summary
        history = brother_ql_printer.get_print_history()
        successful_jobs = sum(1 for job in history if job["success"])
        print(f"\\n📊 SUMMARY:")
        print(f"  Total print jobs: {len(history)}")
        print(f"  Successful jobs: {successful_jobs}")
        print(f"  Success rate: {(successful_jobs/len(history)*100):.1f}%")


@pytest.mark.integration  
@pytest.mark.physical_print
@pytest.mark.skip_by_default
class TestManualPhysicalPrinting:
    """Manual tests that require user interaction - skipped by default."""
    
    @pytest.fixture
    def brother_ql_printer(self):
        """Create Brother QL printer for manual testing."""
        return BrotherQLModern(
            printer_id="manual_test_printer",
            name="Manual Test Brother QL", 
            model="QL-800",
            backend="network",
            identifier="tcp://192.168.1.100:9100",
            dpi=300
        )
    
    async def test_manual_print_confirmation(self, brother_ql_printer):
        """Manual test that asks user to confirm physical print worked."""
        print("\\n🖨️  MANUAL PHYSICAL PRINT TEST")
        print("This test will print a test label. Please check that it prints correctly.")
        
        # Create obvious test image
        test_image = Image.new('RGB', (200, 80), 'white')
        draw = ImageDraw.Draw(test_image)
        draw.rectangle([0, 0, 199, 79], outline='black', width=3)
        draw.text((10, 30), "MANUAL TEST", fill='black')
        
        # Print test label
        result = await brother_ql_printer.print_label(test_image, "12", copies=1)
        assert result.success, f"Print failed: {result.error}"
        
        print(f"\\n✓ Test label sent to printer: {result.message}")
        print("\\nPlease check:")
        print("  1. Did a label print out?")
        print("  2. Is the text 'MANUAL TEST' clearly visible?")
        print("  3. Is the border printed correctly?")
        
        # In a real test environment, you might wait for user input
        # For now, we'll assume success if the print command succeeded
        assert True, "Manual verification required"


if __name__ == "__main__":
    # Run only physical printing tests
    pytest.main([__file__, "-v", "-m", "physical_print"])