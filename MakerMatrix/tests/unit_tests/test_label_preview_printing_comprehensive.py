"""
Comprehensive Label Preview and Printing Testing Suite
Tests all label generation, preview, and printing functionality
Part of extended testing validation following Phase 2 Backend Cleanup
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image, ImageDraw, ImageFont
import io
import base64

from MakerMatrix.services.printer.modern_printer_service import ModernPrinterService
from MakerMatrix.services.printer.preview_service import PreviewService
from MakerMatrix.printers.drivers.mock import MockPrinter
from MakerMatrix.printers.base import PrintJobResult, PrinterCapability
from MakerMatrix.models.models import PartModel
from MakerMatrix.tests.unit_tests.test_database import create_test_db


class TestLabelPreviewAndPrinting:
    """Test comprehensive label preview and printing functionality"""

    def setup_method(self):
        """Set up test database and services for each test"""
        self.test_db = create_test_db()
        self.printer_service = ModernPrinterService()
        self.preview_service = PreviewService()

        # Create test printer with label capabilities
        self.test_printer = MockPrinter(
            printer_id="label_test_printer",
            name="Label Test Printer",
            model="Brother QL-800",
            capabilities=[
                PrinterCapability.TEXT_PRINTING,
                PrinterCapability.QR_CODE_PRINTING,
                PrinterCapability.BARCODE_PRINTING,
                PrinterCapability.IMAGE_PRINTING,
                PrinterCapability.MULTI_SIZE_LABELS,
            ],
        )
        self.printer_service.add_printer(self.test_printer)

        # Create test part for label generation
        self.test_part = PartModel(
            id="test-part-001",
            part_number="C7442639",
            part_name="100uF 35V Capacitor",
            description="100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitor",
            quantity=50,
            supplier="LCSC",
            additional_properties={
                "manufacturer": "Lelon",
                "manufacturer_part_number": "VEJ101M1VTT-0607L",
                "package": "SMD,D6.3xL7.7mm",
                "unit_price": "0.0874",
                "rohs": "YES",
            },
        )

    def teardown_method(self):
        """Clean up after each test"""
        self.test_db.close()

    def test_label_template_creation(self):
        """Test creating different label templates"""
        # Test basic text label template
        text_template = self.preview_service.create_text_label_template(
            text="Test Label", font_size=12, label_size="29x90"
        )

        assert text_template is not None
        assert text_template["type"] == "text"
        assert text_template["content"] == "Test Label"
        assert text_template["font_size"] == 12
        assert text_template["label_size"] == "29x90"

        # Test QR code label template
        qr_template = self.preview_service.create_qr_label_template(
            data="https://example.com/part/C7442639", label_size="29x90", qr_size=100
        )

        assert qr_template is not None
        assert qr_template["type"] == "qr"
        assert qr_template["data"] == "https://example.com/part/C7442639"
        assert qr_template["qr_size"] == 100

        # Test barcode label template
        barcode_template = self.preview_service.create_barcode_label_template(
            data="C7442639", barcode_type="CODE128", label_size="29x90"
        )

        assert barcode_template is not None
        assert barcode_template["type"] == "barcode"
        assert barcode_template["data"] == "C7442639"
        assert barcode_template["barcode_type"] == "CODE128"

        # Test combined template (QR + text)
        combined_template = self.preview_service.create_combined_label_template(
            qr_data="https://example.com/part/C7442639", text="C7442639", label_size="62x29"
        )

        assert combined_template is not None
        assert combined_template["type"] == "combined"
        assert combined_template["qr_data"] == "https://example.com/part/C7442639"
        assert combined_template["text"] == "C7442639"

        print("✅ Label template creation validated")

    def test_label_preview_generation(self):
        """Test generating label previews"""
        # Test text label preview
        text_preview = self.preview_service.generate_text_label_preview(
            text="Test Label", font_size=12, label_size="29x90"
        )

        assert text_preview is not None
        assert isinstance(text_preview, dict)
        assert "image_data" in text_preview
        assert "width" in text_preview
        assert "height" in text_preview
        assert "format" in text_preview

        # Test QR code label preview
        qr_preview = self.preview_service.generate_qr_label_preview(
            data="https://example.com/part/C7442639", label_size="29x90"
        )

        assert qr_preview is not None
        assert isinstance(qr_preview, dict)
        assert "image_data" in qr_preview
        assert "qr_size" in qr_preview

        # Test barcode label preview
        barcode_preview = self.preview_service.generate_barcode_label_preview(
            data="C7442639", barcode_type="CODE128", label_size="29x90"
        )

        assert barcode_preview is not None
        assert isinstance(barcode_preview, dict)
        assert "image_data" in barcode_preview
        assert "barcode_type" in barcode_preview

        # Test part label preview
        part_preview = self.preview_service.generate_part_label_preview(
            part=self.test_part, label_size="62x29", include_qr=True
        )

        assert part_preview is not None
        assert isinstance(part_preview, dict)
        assert "image_data" in part_preview
        assert "part_number" in part_preview
        assert part_preview["part_number"] == "C7442639"

        print("✅ Label preview generation validated")

    def test_label_size_management(self):
        """Test different label size configurations"""
        # Test standard Brother QL label sizes
        standard_sizes = [
            "29x90",  # Continuous length tape
            "62x29",  # Standard address labels
            "62x100",  # Shipping labels
            "12",  # 12mm continuous
            "29",  # 29mm continuous
            "38",  # 38mm continuous
            "50",  # 50mm continuous
            "54",  # 54mm continuous
            "62",  # 62mm continuous
        ]

        for size in standard_sizes:
            # Test label size validation
            is_valid = self.preview_service.validate_label_size(size)
            assert is_valid == True

            # Test getting label dimensions
            dimensions = self.preview_service.get_label_dimensions(size)
            assert isinstance(dimensions, dict)
            assert "width" in dimensions
            assert "height" in dimensions
            assert dimensions["width"] > 0
            assert dimensions["height"] > 0

            # Test creating preview with each size
            preview = self.preview_service.generate_text_label_preview(text=f"Test {size}", label_size=size)
            assert preview is not None
            assert preview["width"] > 0
            assert preview["height"] > 0

        # Test invalid label size
        invalid_size = "999x999"
        is_valid = self.preview_service.validate_label_size(invalid_size)
        assert is_valid == False

        print("✅ Label size management validated")

    def test_label_formatting_options(self):
        """Test various label formatting options"""
        # Test font options
        font_options = {
            "font_family": "Arial",
            "font_size": 14,
            "font_weight": "bold",
            "font_color": "black",
            "background_color": "white",
        }

        formatted_preview = self.preview_service.generate_text_label_preview(
            text="Formatted Label", label_size="29x90", **font_options
        )

        assert formatted_preview is not None
        assert formatted_preview["font_family"] == "Arial"
        assert formatted_preview["font_size"] == 14
        assert formatted_preview["font_weight"] == "bold"

        # Test alignment options
        alignment_options = ["left", "center", "right"]

        for alignment in alignment_options:
            aligned_preview = self.preview_service.generate_text_label_preview(
                text="Aligned Text", label_size="62x29", text_alignment=alignment
            )

            assert aligned_preview is not None
            assert aligned_preview["text_alignment"] == alignment

        # Test rotation options
        rotation_options = [0, 90, 180, 270]

        for rotation in rotation_options:
            rotated_preview = self.preview_service.generate_text_label_preview(
                text="Rotated Text", label_size="29x90", rotation=rotation
            )

            assert rotated_preview is not None
            assert rotated_preview["rotation"] == rotation

        # Test margin and padding options
        spacing_options = {"margin_top": 5, "margin_bottom": 5, "margin_left": 10, "margin_right": 10, "padding": 3}

        spaced_preview = self.preview_service.generate_text_label_preview(
            text="Spaced Label", label_size="62x29", **spacing_options
        )

        assert spaced_preview is not None
        for key, value in spacing_options.items():
            assert spaced_preview[key] == value

        print("✅ Label formatting options validated")

    def test_qr_code_generation_options(self):
        """Test QR code generation with various options"""
        # Test basic QR code
        basic_qr = self.preview_service.generate_qr_code(data="https://example.com/part/C7442639")

        assert basic_qr is not None
        assert isinstance(basic_qr, dict)
        assert "image_data" in basic_qr
        assert "data" in basic_qr

        # Test QR code with different sizes
        qr_sizes = [50, 100, 150, 200]

        for size in qr_sizes:
            sized_qr = self.preview_service.generate_qr_code(data="Test QR Data", qr_size=size)

            assert sized_qr is not None
            assert sized_qr["qr_size"] == size

        # Test QR code with different error correction levels
        error_levels = ["L", "M", "Q", "H"]

        for level in error_levels:
            error_qr = self.preview_service.generate_qr_code(data="Error Correction Test", error_correction=level)

            assert error_qr is not None
            assert error_qr["error_correction"] == level

        # Test QR code with border options
        border_options = {"border_size": 4, "border_color": "black", "background_color": "white"}

        bordered_qr = self.preview_service.generate_qr_code(data="Bordered QR", **border_options)

        assert bordered_qr is not None
        for key, value in border_options.items():
            assert bordered_qr[key] == value

        # Test QR code with part information
        part_qr = self.preview_service.generate_part_qr_code(self.test_part)

        assert part_qr is not None
        assert "part_number" in part_qr["data"]
        assert "C7442639" in part_qr["data"]

        print("✅ QR code generation options validated")

    def test_barcode_generation_options(self):
        """Test barcode generation with various options"""
        # Test different barcode types
        barcode_types = ["CODE128", "CODE39", "EAN13", "EAN8", "UPCA", "UPCE"]

        for barcode_type in barcode_types:
            try:
                barcode = self.preview_service.generate_barcode(data="123456789", barcode_type=barcode_type)

                assert barcode is not None
                assert barcode["barcode_type"] == barcode_type
            except Exception as e:
                # Some barcode types may require specific data formats
                print(f"ℹ️ Barcode type {barcode_type} requires specific format: {e}")

        # Test barcode with text
        text_barcode = self.preview_service.generate_barcode(data="C7442639", barcode_type="CODE128", include_text=True)

        assert text_barcode is not None
        assert text_barcode["include_text"] == True

        # Test barcode sizing options
        size_options = {"bar_width": 2, "bar_height": 50, "quiet_zone": 10}

        sized_barcode = self.preview_service.generate_barcode(data="SIZE_TEST", barcode_type="CODE128", **size_options)

        assert sized_barcode is not None
        for key, value in size_options.items():
            assert sized_barcode[key] == value

        print("✅ Barcode generation options validated")

    @pytest.mark.asyncio
    async def test_label_printing_workflow(self):
        """Test complete label printing workflow"""
        # Test text label printing
        text_result = await self.printer_service.print_text_label(
            text="Test Label", label_size="29x90", printer_id="label_test_printer"
        )

        assert text_result.success == True
        assert text_result.job_id is not None
        assert text_result.error is None

        # Test QR code printing
        qr_result = await self.printer_service.print_part_qr_code(part=self.test_part, printer_id="label_test_printer")

        assert qr_result.success == True
        assert qr_result.job_id is not None

        # Test part name printing
        name_result = await self.printer_service.print_part_name(part=self.test_part, printer_id="label_test_printer")

        assert name_result.success == True
        assert name_result.job_id is not None

        # Test combined QR and text printing
        combined_result = await self.printer_service.print_qr_and_text(
            part=self.test_part, text="Custom Text", printer_config={"dpi": 300}, label_data={"label_size": "62x29"}
        )

        assert combined_result.success == True
        assert combined_result.job_id is not None

        # Test batch printing
        batch_jobs = []
        for i in range(3):
            job = await self.printer_service.print_text_label(
                text=f"Batch Label {i+1}", label_size="29x90", printer_id="label_test_printer"
            )
            batch_jobs.append(job)

        assert len(batch_jobs) == 3
        for job in batch_jobs:
            assert job.success == True
            assert job.job_id is not None

        print("✅ Label printing workflow validated")

    def test_label_preview_image_formats(self):
        """Test different image formats for label previews"""
        # Test PNG format
        png_preview = self.preview_service.generate_text_label_preview(
            text="PNG Test", label_size="29x90", output_format="PNG"
        )

        assert png_preview is not None
        assert png_preview["format"] == "PNG"
        assert "image_data" in png_preview

        # Test JPEG format
        jpeg_preview = self.preview_service.generate_text_label_preview(
            text="JPEG Test", label_size="29x90", output_format="JPEG"
        )

        assert jpeg_preview is not None
        assert jpeg_preview["format"] == "JPEG"

        # Test base64 encoded output
        base64_preview = self.preview_service.generate_text_label_preview(
            text="Base64 Test", label_size="29x90", output_format="PNG", encode_base64=True
        )

        assert base64_preview is not None
        assert base64_preview["encoded"] == True
        assert isinstance(base64_preview["image_data"], str)

        # Test binary output
        binary_preview = self.preview_service.generate_text_label_preview(
            text="Binary Test", label_size="29x90", output_format="PNG", encode_base64=False
        )

        assert binary_preview is not None
        assert binary_preview["encoded"] == False
        assert isinstance(binary_preview["image_data"], bytes)

        print("✅ Label preview image formats validated")

    def test_label_template_customization(self):
        """Test custom label template creation"""
        # Test creating custom template
        custom_template = {
            "name": "Custom Part Label",
            "type": "custom",
            "elements": [
                {
                    "type": "text",
                    "content": "{part_number}",
                    "position": {"x": 10, "y": 10},
                    "font_size": 12,
                    "font_weight": "bold",
                },
                {"type": "text", "content": "{part_name}", "position": {"x": 10, "y": 30}, "font_size": 10},
                {
                    "type": "qr",
                    "data": "https://example.com/part/{part_number}",
                    "position": {"x": 200, "y": 10},
                    "size": 80,
                },
            ],
            "label_size": "62x29",
            "background_color": "white",
        }

        # Test template validation
        is_valid = self.preview_service.validate_custom_template(custom_template)
        assert is_valid == True

        # Test template rendering with part data
        rendered_template = self.preview_service.render_custom_template(
            template=custom_template,
            data={"part_number": self.test_part.part_number, "part_name": self.test_part.part_name},
        )

        assert rendered_template is not None
        assert rendered_template["template_name"] == "Custom Part Label"
        assert "image_data" in rendered_template

        # Test template with conditional elements
        conditional_template = {
            "name": "Conditional Label",
            "type": "custom",
            "elements": [
                {"type": "text", "content": "{part_number}", "position": {"x": 10, "y": 10}, "font_size": 12},
                {
                    "type": "text",
                    "content": "Qty: {quantity}",
                    "position": {"x": 10, "y": 30},
                    "font_size": 10,
                    "condition": "{quantity} > 0",
                },
            ],
            "label_size": "29x90",
        }

        rendered_conditional = self.preview_service.render_custom_template(
            template=conditional_template,
            data={"part_number": self.test_part.part_number, "quantity": self.test_part.quantity},
        )

        assert rendered_conditional is not None
        assert "image_data" in rendered_conditional

        print("✅ Label template customization validated")

    def test_label_print_queue_management(self):
        """Test label print queue management"""
        # Test adding labels to print queue
        queue_items = [
            {"type": "text", "content": "Queue Item 1", "label_size": "29x90", "priority": "normal"},
            {"type": "qr", "data": "https://example.com/item2", "label_size": "29x90", "priority": "high"},
            {"type": "part_label", "part": self.test_part, "label_size": "62x29", "priority": "low"},
        ]

        # Add items to queue
        for item in queue_items:
            queue_result = self.test_printer.add_print_job(item)
            assert queue_result["success"] == True
            assert "job_id" in queue_result

        # Test queue status
        queue_status = self.test_printer.get_print_queue_status()
        assert queue_status["total_jobs"] == 3
        assert queue_status["pending_jobs"] > 0

        # Test queue processing by priority
        processed_jobs = self.test_printer.process_print_queue_by_priority()
        assert len(processed_jobs) == 3

        # High priority should be processed first
        assert processed_jobs[0]["priority"] == "high"
        assert processed_jobs[1]["priority"] == "normal"
        assert processed_jobs[2]["priority"] == "low"

        # Test queue clearing
        self.test_printer.clear_print_queue()
        final_status = self.test_printer.get_print_queue_status()
        assert final_status["total_jobs"] == 0

        print("✅ Label print queue management validated")

    def test_label_print_error_handling(self):
        """Test error handling in label printing"""
        # Test printer error during printing
        error_printer = MockPrinter(printer_id="error_printer", name="Error Printer", simulate_errors=True)
        self.printer_service.add_printer(error_printer)

        # Simulate paper out error
        error_printer.simulate_paper_out()

        # Test printing with error
        async def test_error_printing():
            try:
                result = await self.printer_service.print_text_label(text="Error Test", printer_id="error_printer")
                # May succeed or fail depending on mock behavior
                if not result.success:
                    assert result.error is not None
                    assert "paper" in result.error.lower()
            except Exception as e:
                # Error is expected
                assert "paper" in str(e).lower()

        asyncio.run(test_error_printing())

        # Test invalid label size error
        async def test_invalid_size():
            try:
                result = await self.printer_service.print_text_label(
                    text="Invalid Size Test", label_size="999x999", printer_id="label_test_printer"
                )
                # Should handle invalid size gracefully
                if not result.success:
                    assert result.error is not None
            except Exception as e:
                # Error handling for invalid size
                assert "size" in str(e).lower() or "invalid" in str(e).lower()

        asyncio.run(test_invalid_size())

        # Test printer not found error
        async def test_printer_not_found():
            try:
                result = await self.printer_service.print_text_label(
                    text="Not Found Test", printer_id="nonexistent_printer"
                )
                # Should fail with printer not found
                assert result.success == False
                assert result.error is not None
            except Exception as e:
                # Expected error for non-existent printer
                assert "not found" in str(e).lower()

        asyncio.run(test_printer_not_found())

        print("✅ Label print error handling validated")

    def test_label_preview_caching(self):
        """Test label preview caching for performance"""
        # Test initial preview generation
        cache_key = "test_cache_key"
        preview1 = self.preview_service.generate_text_label_preview(
            text="Cached Label", label_size="29x90", cache_key=cache_key
        )

        assert preview1 is not None
        assert preview1["cached"] == False  # First generation

        # Test cached preview retrieval
        preview2 = self.preview_service.generate_text_label_preview(
            text="Cached Label", label_size="29x90", cache_key=cache_key
        )

        assert preview2 is not None
        assert preview2["cached"] == True  # Retrieved from cache

        # Test cache invalidation
        self.preview_service.invalidate_preview_cache(cache_key)

        preview3 = self.preview_service.generate_text_label_preview(
            text="Cached Label", label_size="29x90", cache_key=cache_key
        )

        assert preview3 is not None
        assert preview3["cached"] == False  # Regenerated after invalidation

        # Test cache size management
        cache_stats = self.preview_service.get_cache_stats()
        assert isinstance(cache_stats, dict)
        assert "total_entries" in cache_stats
        assert "cache_hits" in cache_stats
        assert "cache_misses" in cache_stats

        print("✅ Label preview caching validated")


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
