"""
Label preview service for generating print previews without actual printing.
"""
import io
import uuid
from typing import Optional, List
from PIL import Image

from MakerMatrix.models.models import PartModel
from MakerMatrix.printers.base import (
    PreviewResult,
    LabelSize,
    PrinterInterface,
    InvalidLabelSizeError
)
from MakerMatrix.services.printer.qr_service import QRService
from MakerMatrix.services.printer.label_service import LabelService


class PreviewService:
    """Service for generating label previews without printing."""
    
    def __init__(self, default_printer: Optional[PrinterInterface] = None):
        self.default_printer = default_printer
        self.qr_service = QRService()
    
    def set_default_printer(self, printer: PrinterInterface):
        """Set the default printer for preview generation."""
        self.default_printer = printer
    
    async def preview_part_qr_code(self, part: PartModel, label_size: str = "12", 
                                   printer: Optional[PrinterInterface] = None) -> PreviewResult:
        """Generate a preview of a part QR code label."""
        printer_to_use = printer or self.default_printer
        if not printer_to_use:
            raise ValueError("No printer available for preview generation")
        
        # Generate optimized QR code image for the part using label service
        from MakerMatrix.lib.print_settings import PrintSettings
        from MakerMatrix.services.printer.label_service import LabelService

        # Create print settings based on label size
        label_height_mm = float(label_size.replace('mm', '')) if 'mm' in label_size else 12.0
        print_settings = PrintSettings(
            label_size=label_height_mm,
            dpi=300,
            qr_scale=0.95,
            qr_min_size_mm=8.0,
            qr_max_margin_mm=1.0
        )

        part_dict = {'id': part.id}
        qr_image = LabelService.generate_optimized_qr(part_dict, print_settings)
        print(f"[DEBUG] Preview QR code: Generated optimized QR code for part {part.id}, size: {qr_image.width}x{qr_image.height}")
        
        # Generate preview using the printer's preview method
        return await printer_to_use.preview_label(qr_image, label_size)
    
    async def preview_part_name(self, part: PartModel, label_size: str = "12",
                                printer: Optional[PrinterInterface] = None) -> PreviewResult:
        """Generate a preview of a part name label."""
        printer_to_use = printer or self.default_printer
        if not printer_to_use:
            raise ValueError("No printer available for preview generation")
        
        # Generate text image for the part name
        text_image = self._generate_text_image(part.part_name, (400, 100))
        
        return await printer_to_use.preview_label(text_image, label_size)
    
    async def preview_text_label(self, text: str, label_size: str = "12",
                                 printer: Optional[PrinterInterface] = None) -> PreviewResult:
        """Generate a preview of a custom text label."""
        printer_to_use = printer or self.default_printer
        if not printer_to_use:
            raise ValueError("No printer available for preview generation")
        
        # Generate text image
        text_image = self._generate_text_image(text, (400, 100))
        
        return await printer_to_use.preview_label(text_image, label_size)
    
    async def preview_combined_label(self, part: PartModel, custom_text: Optional[str] = None,
                                     label_size: str = "12", printer: Optional[PrinterInterface] = None) -> PreviewResult:
        """Generate a preview of a combined QR code + text label."""
        printer_to_use = printer or self.default_printer
        if not printer_to_use:
            raise ValueError("No printer available for preview generation")
        
        # Generate optimized QR code image for combined preview
        from MakerMatrix.lib.print_settings import PrintSettings
        from MakerMatrix.services.printer.label_service import LabelService

        # Create print settings based on label size for combined layout
        label_height_mm = float(label_size.replace('mm', '')) if 'mm' in label_size else 12.0
        print_settings = PrintSettings(
            label_size=label_height_mm,
            dpi=300,
            qr_scale=0.90,  # Slightly smaller for combined layout to leave room for text
            qr_min_size_mm=6.0,  # Smaller minimum for combined layout
            qr_max_margin_mm=1.0
        )

        part_dict = {'id': part.id}
        qr_image = LabelService.generate_optimized_qr(part_dict, print_settings)
        print(f"[DEBUG] Preview: Generated optimized QR code for combined layout, size: {qr_image.width}x{qr_image.height}")
        
        # Create combined image
        text = custom_text or f"{part.part_name}\n{part.part_number}"
        combined_image = self._create_combined_image(qr_image, text, (400, 200))
        
        return await printer_to_use.preview_label(combined_image, label_size)
    
    def get_available_label_sizes(self, printer: Optional[PrinterInterface] = None) -> List[LabelSize]:
        """Get available label sizes from the printer."""
        printer_to_use = printer or self.default_printer
        if not printer_to_use:
            return []
        
        return printer_to_use.get_supported_label_sizes()
    
    def validate_label_size(self, label_size: str, printer: Optional[PrinterInterface] = None) -> bool:
        """Validate if a label size is supported by the printer."""
        sizes = self.get_available_label_sizes(printer)
        return any(size.name == label_size for size in sizes)
    
    def _generate_text_image(self, text: str, size: tuple[int, int]) -> Image.Image:
        """Generate a PIL image with the given text, scaled to fit the label height."""
        from PIL import ImageDraw, ImageFont

        image = Image.new('RGB', size, 'white')
        draw = ImageDraw.Draw(image)

        # Define target height as percentage of label height (with some margin)
        target_height = int(size[1] * 0.8)  # Use 80% of label height
        max_width = int(size[0] * 0.9)      # Use 90% of label width

        # Start with a large font size and scale down to fit
        font_size = max(target_height, 12)  # Start with target height or minimum 12
        font = None

        # Try to find the best font size that fits
        while font_size > 8:
            try:
                # Try to use a proper font
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                # Fall back to default font - note: default font size cannot be changed
                font = ImageFont.load_default()
                break

            # Check if text fits within bounds
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # If text fits both width and height constraints, we're done
            if text_width <= max_width and text_height <= target_height:
                break

            # Otherwise, reduce font size and try again
            font_size = int(font_size * 0.9)

        # If we couldn't load a TrueType font, use default
        if font is None:
            font = ImageFont.load_default()

        # Calculate final text position to center it
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2

        draw.text((x, y), text, fill='black', font=font)
        return image
    
    def _create_combined_image(self, qr_image: Image.Image, text: str, size: tuple[int, int]) -> Image.Image:
        """Create a combined image with QR code and text."""
        from PIL import ImageDraw, ImageFont
        
        # Create base image
        combined = Image.new('RGB', size, 'white')
        
        # Paste QR code on the left
        qr_y = (size[1] - qr_image.height) // 2
        combined.paste(qr_image, (10, qr_y))
        
        # Add text on the right with dynamic sizing
        draw = ImageDraw.Draw(combined)

        # Calculate text area (right side after QR code)
        text_x = qr_image.width + 20
        text_width = size[0] - text_x - 10

        # Optimized font sizing for QR+text layout (matching printer manager logic)
        max_text_width = text_width
        text_height = size[1] - 20  # Available height minus margins

        # Check if text is single line (no newlines)
        clean_text = text.strip()
        is_single_line = '\n' not in clean_text

        # For single line text in narrow labels, try to use maximum height
        if is_single_line and size[1] <= 200:  # Assume narrow label like 12mm
            # Try to use most of the available height for single line text
            max_font_height = int(text_height * 0.9)  # Use 90% of available height
            print(f"[DEBUG] Preview: Single line text detected, targeting max height: {max_font_height}px")

            # Start with height-based font size and scale down if width doesn't fit
            font_size = max_font_height
            font = None

            while font_size > 8:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                    break

                # Check if text fits within width constraint
                test_bbox = draw.textbbox((0, 0), clean_text, font=font)
                test_width = test_bbox[2] - test_bbox[0]

                print(f"[DEBUG] Preview: Testing font_size={font_size}: text_width={test_width}px, limit={max_text_width}px")

                # For single line, prioritize using maximum height if it fits width
                if test_width <= max_text_width:
                    print(f"[DEBUG] Preview: Single line text fits at font_size={font_size}")
                    break

                # Reduce font size if too wide
                font_size = int(font_size * 0.95)
        else:
            # Multi-line text or wider labels: use balanced approach
            target_height = int(text_height * 0.8)  # Use 80% of available height
            font_size = max(target_height // 3, 10)  # Start with reasonable size

            while font_size > 8:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                    break

                # Check if text fits within both width and height constraints
                test_bbox = draw.textbbox((0, 0), clean_text.replace('\n', ' '), font=font)
                test_width = test_bbox[2] - test_bbox[0]
                test_height = test_bbox[3] - test_bbox[1]

                if test_width <= max_text_width and test_height <= target_height:
                    break

                font_size = int(font_size * 0.9)

        # If we couldn't load a TrueType font, use default
        if font is None:
            font = ImageFont.load_default()
        
        # Split long text into multiple lines
        lines = self._wrap_text(text, text_width, font, draw)
        
        # Draw each line with dynamic line height
        line_height = font_size + 2
        start_y = (size[1] - len(lines) * line_height) // 2
        
        for i, line in enumerate(lines):
            y = start_y + i * line_height
            draw.text((text_x, y), line, fill='black', font=font)
        
        return combined
    
    def _wrap_text(self, text: str, max_width: int, font, draw) -> List[str]:
        """Wrap text to fit within the given width."""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines or [""]


class PreviewManager:
    """Manages multiple preview services for different printers."""
    
    def __init__(self):
        self.preview_services: dict[str, PreviewService] = {}
        self.default_service: Optional[PreviewService] = None
    
    def register_printer(self, printer_id: str, printer: PrinterInterface):
        """Register a printer for preview generation."""
        service = PreviewService(printer)
        self.preview_services[printer_id] = service
        
        # Set as default if this is the first printer
        if not self.default_service:
            self.default_service = service
    
    def get_preview_service(self, printer_id: Optional[str] = None) -> PreviewService:
        """Get preview service for a specific printer or the default."""
        if printer_id and printer_id in self.preview_services:
            return self.preview_services[printer_id]
        
        if self.default_service:
            return self.default_service
        
        raise ValueError("No preview service available")
    
    def get_registered_printers(self) -> List[str]:
        """Get list of registered printer IDs."""
        return list(self.preview_services.keys())
    
    async def preview_with_printer(self, printer_id: str, image: Image.Image, 
                                   label_size: str) -> PreviewResult:
        """Generate preview using a specific printer."""
        service = self.get_preview_service(printer_id)
        printer = service.default_printer
        return await printer.preview_label(image, label_size)


# Global preview service instance
preview_service = PreviewService()