"""
Mock printer driver for testing without actual hardware.
"""
import asyncio
import io
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
import time

from MakerMatrix.printers.base import (
    BasePrinter,
    PrinterStatus,
    PrinterCapability,
    LabelSize,
    PrintJobResult,
    PreviewResult,
    PrinterInfo,
    TestResult,
    InvalidLabelSizeError,
    PrintJobError
)


class MockPrinter(BasePrinter):
    """
    Mock printer implementation for testing.
    Simulates all printer operations without requiring actual hardware.
    """
    
    # Mock label sizes (Brother QL compatible) - support both "12" and "12mm" formats
    SUPPORTED_SIZES = [
        LabelSize("12", 12.0, 29.0, 106, 164),
        LabelSize("12mm", 12.0, 29.0, 106, 164),  # Alternative format
        LabelSize("17", 17.0, 54.0, 201, 614),
        LabelSize("17mm", 17.0, 54.0, 201, 614),
        LabelSize("23", 23.0, 23.0, 202, 202),
        LabelSize("23mm", 23.0, 23.0, 202, 202),
        LabelSize("29", 29.0, 90.0, 306, 991),
        LabelSize("29mm", 29.0, 90.0, 306, 991),
        LabelSize("38", 38.0, 90.0, 413, 991),
        LabelSize("38mm", 38.0, 90.0, 413, 991),
        LabelSize("50", 50.0, 30.0, 554, 331),
        LabelSize("50mm", 50.0, 30.0, 554, 331),
        LabelSize("54", 54.0, 30.0, 590, 331),
        LabelSize("54mm", 54.0, 30.0, 590, 331),
        LabelSize("62", 62.0, 29.0, 696, 271),
        LabelSize("62mm", 62.0, 29.0, 696, 271),
        LabelSize("102", 102.0, 51.0, 1164, 565),
        LabelSize("102mm", 102.0, 51.0, 1164, 565),
        LabelSize("17x54", 17.0, 54.0, 201, 614),
        LabelSize("17x87", 17.0, 87.0, 201, 956),
        LabelSize("23x23", 23.0, 23.0, 202, 202)
    ]
    
    def __init__(self, printer_id: str = "mock_printer", name: str = "Mock Printer",
                 model: str = "MockQL-800", backend: str = "mock", identifier: str = "mock://localhost",
                 simulate_errors: bool = False, print_delay: float = 0.1):
        super().__init__(printer_id, name, model, backend, identifier)
        self.simulate_errors = simulate_errors
        self.print_delay = print_delay
        self._status = PrinterStatus.READY
        self._current_job_id: Optional[str] = None
        self._print_history: List[dict] = []
        
    async def print_label(self, image: Image.Image, label_size: str, copies: int = 1) -> PrintJobResult:
        """Mock print operation with simulated delay."""
        job_id = self._generate_job_id()
        
        # Validate label size
        if not self._is_valid_label_size(label_size):
            supported = [size.name for size in self.SUPPORTED_SIZES]
            raise InvalidLabelSizeError(label_size, self.printer_id, supported)
        
        # Simulate error conditions
        if self.simulate_errors and len(self._print_history) % 5 == 4:  # Every 5th job fails
            error_msg = "Simulated printer error - out of paper"
            self._set_status(PrinterStatus.OUT_OF_PAPER, error_msg)
            return PrintJobResult(
                success=False,
                job_id=job_id,
                error=error_msg
            )
        
        # Simulate printing
        self._set_status(PrinterStatus.PRINTING)
        self._current_job_id = job_id
        
        # Simulate print time (longer for more copies)
        await asyncio.sleep(self.print_delay * copies)
        
        # Record print job
        self._print_history.append({
            "job_id": job_id,
            "label_size": label_size,
            "copies": copies,
            "image_size": image.size,
            "timestamp": time.time()
        })
        
        self._set_status(PrinterStatus.READY)
        self._current_job_id = None
        
        return PrintJobResult(
            success=True,
            job_id=job_id,
            message=f"Printed {copies} label(s) on {label_size}mm"
        )
    
    async def preview_label(self, image: Image.Image, label_size: str) -> PreviewResult:
        """Generate a preview image with label border and info."""
        print(f"[DEBUG] MockPrinter.preview_label called with label_size: {label_size}")
        if not self._is_valid_label_size(label_size):
            supported = [size.name for size in self.SUPPORTED_SIZES]
            print(f"[ERROR] MockPrinter: Invalid label size '{label_size}'. Supported sizes: {supported}")
            raise InvalidLabelSizeError(label_size, self.printer_id, supported)
        
        # Get label dimensions
        label_info = self._get_label_size_info(label_size)
        
        # Create preview with border and metadata
        border_width = 20
        preview_width = image.width + 2 * border_width
        preview_height = image.height + 2 * border_width + 60  # Extra space for text
        
        preview = Image.new('RGB', (preview_width, preview_height), 'white')
        
        # Draw border
        draw = ImageDraw.Draw(preview)
        draw.rectangle([0, 0, preview_width-1, preview_height-1], outline='black', width=2)
        draw.rectangle([border_width-1, border_width-1, preview_width-border_width, image.height+border_width+1], 
                      outline='gray', width=1)
        
        # Paste the label image
        preview.paste(image, (border_width, border_width))
        
        # Add label info text with improved font handling
        print(f"[DEBUG] MockPrinter loading font for preview...")
        font = self._get_safe_font()
        print(f"[DEBUG] Font loaded: {font}")

        info_text = f"Label: {label_size}mm ({label_info.width_mm}x{label_info.height_mm}mm)"
        size_text = f"Image: {image.width}x{image.height}px"

        print(f"[DEBUG] Drawing text: {info_text}")
        try:
            draw.text((border_width, image.height + border_width + 10), info_text, fill='black', font=font)
            draw.text((border_width, image.height + border_width + 30), size_text, fill='gray', font=font)
            print(f"[DEBUG] Text drawn successfully")
        except Exception as e:
            print(f"[ERROR] Failed to draw text: {e}")
            # Fall back to no text if drawing fails
            pass
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        preview.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return PreviewResult(
            image_data=img_byte_arr,
            format='png',
            width_px=preview_width,
            height_px=preview_height,
            label_size=label_info,
            message=f"Preview for {label_size}mm label"
        )
    
    async def get_status(self) -> PrinterStatus:
        """Return current printer status."""
        return self._status
    
    async def get_capabilities(self) -> List[PrinterCapability]:
        """Return mock printer capabilities."""
        return [
            PrinterCapability.QR_CODES,
            PrinterCapability.BARCODES,
            PrinterCapability.IMAGES,
            PrinterCapability.DIE_CUT_LABELS,
            PrinterCapability.CONTINUOUS_LABELS
        ]
    
    async def test_connection(self) -> TestResult:
        """Simulate connection test."""
        start_time = time.time()
        
        # Simulate network delay
        await asyncio.sleep(0.05)
        
        response_time = (time.time() - start_time) * 1000
        
        if self.simulate_errors and response_time > 100:  # Simulate timeout
            return TestResult(
                success=False,
                response_time_ms=response_time,
                error="Connection timeout (simulated)"
            )
        
        return TestResult(
            success=True,
            response_time_ms=response_time,
            message=f"Connected to mock printer at {self.identifier}"
        )
    
    def get_supported_label_sizes(self) -> List[LabelSize]:
        """Return supported label sizes."""
        return self.SUPPORTED_SIZES.copy()
    
    def get_printer_info(self) -> PrinterInfo:
        """Get printer information."""
        info = super().get_printer_info()
        info.capabilities = [
            PrinterCapability.QR_CODES,
            PrinterCapability.BARCODES, 
            PrinterCapability.IMAGES,
            PrinterCapability.DIE_CUT_LABELS,
            PrinterCapability.CONTINUOUS_LABELS
        ]
        return info
    
    async def cancel_current_job(self) -> bool:
        """Cancel current print job."""
        if self._current_job_id:
            self._set_status(PrinterStatus.READY)
            self._current_job_id = None
            return True
        return False
    
    def _is_valid_label_size(self, label_size: str) -> bool:
        """Check if label size is supported."""
        return any(size.name == label_size for size in self.SUPPORTED_SIZES)

    def _get_safe_font(self):
        """Get a safe font for text rendering with comprehensive fallbacks."""
        print(f"[DEBUG] _get_safe_font called")

        # List of font paths to try in order of preference
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "C:/Windows/Fonts/arial.ttf",  # Windows
        ]

        # Try TrueType fonts first
        for font_path in font_paths:
            try:
                print(f"[DEBUG] Trying font: {font_path}")
                font = ImageFont.truetype(font_path, 12)
                print(f"[DEBUG] Successfully loaded font: {font_path}")
                return font
            except Exception as e:
                print(f"[DEBUG] Font {font_path} failed: {e}")
                continue

        # Fall back to default font
        try:
            print(f"[DEBUG] Falling back to default font")
            font = ImageFont.load_default()
            print(f"[DEBUG] Default font loaded successfully")
            return font
        except Exception as e:
            print(f"[ERROR] Even default font failed: {e}")
            # Return None as absolute fallback
            return None

    def _get_label_size_info(self, label_size: str) -> LabelSize:
        """Get label size information."""
        for size in self.SUPPORTED_SIZES:
            if size.name == label_size:
                return size
        raise InvalidLabelSizeError(label_size, self.printer_id)
    
    # Additional mock-specific methods for testing
    def get_print_history(self) -> List[dict]:
        """Get print job history for testing."""
        return self._print_history.copy()
    
    def clear_print_history(self):
        """Clear print history for testing."""
        self._print_history.clear()
    
    def set_error_simulation(self, enabled: bool):
        """Enable/disable error simulation for testing."""
        self.simulate_errors = enabled
    
    def simulate_paper_out(self):
        """Simulate out of paper condition."""
        self._set_status(PrinterStatus.OUT_OF_PAPER, "Simulated: Out of paper")
    
    def simulate_offline(self):
        """Simulate offline condition."""
        self._set_status(PrinterStatus.OFFLINE, "Simulated: Printer offline")
    
    def reset_to_ready(self):
        """Reset printer to ready state."""
        self._set_status(PrinterStatus.READY)
        self._current_job_id = None