"""
Modern printer service that supports the new printer interface while maintaining
backward compatibility with existing functionality.
"""

from typing import Optional, Dict, Any
from PIL import Image

from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.models.models import PartModel
from MakerMatrix.printers.base import PrinterInterface, PrintJobResult, PrinterNotFoundError, PrinterError
from MakerMatrix.printers.drivers.mock import MockPrinter
from MakerMatrix.services.printer.label_service import LabelService


class ModernPrinterService:
    """
    Modern printer service supporting the new printer interface.
    Can work with both mock and real printers.
    """

    def __init__(self, default_printer: Optional[PrinterInterface] = None):
        # Use mock printer as default if none provided
        self._default_printer = default_printer or MockPrinter()
        self._printers: Dict[str, PrinterInterface] = {}

        # Register default printer
        if self._default_printer:
            printer_info = self._default_printer.get_printer_info()
            self._printers[printer_info.id] = self._default_printer

    def get_default_printer(self) -> PrinterInterface:
        """Get the default printer."""
        if not self._default_printer:
            raise PrinterNotFoundError("No default printer configured")
        return self._default_printer

    def get_printer(self, printer_id: Optional[str] = None) -> PrinterInterface:
        """Get printer by ID or return default."""
        if not printer_id:
            return self.get_default_printer()

        if printer_id not in self._printers:
            raise PrinterNotFoundError(printer_id)

        return self._printers[printer_id]

    async def print_part_qr_code(self, part: PartModel, printer_id: Optional[str] = None) -> PrintJobResult:
        """Print QR code for a part."""
        printer = self.get_printer(printer_id)

        try:
            # Create print settings with defaults for QR code
            print_settings = PrintSettings(label_size=62, dpi=300, copies=1)  # Default to 62mm

            # Generate QR + text label
            label_image = LabelService.generate_combined_label(part=part, print_settings=print_settings)

            # Rotate if needed (Brother QL typically needs 90-degree rotation)
            rotated_image = label_image.rotate(90, expand=True)

            return await printer.print_label(rotated_image, str(print_settings.label_size), print_settings.copies)

        except Exception as e:
            raise PrinterError(f"Failed to print part QR code: {str(e)}", printer_id)

    async def print_part_name(self, part: PartModel, printer_id: Optional[str] = None) -> PrintJobResult:
        """Print part name as text label."""
        printer = self.get_printer(printer_id)

        try:
            # Create print settings for text label
            print_settings = PrintSettings(label_size=62, dpi=300, copies=1)  # Default to 62mm

            # Generate text-only label
            available_height = LabelService.get_available_height_pixels(print_settings)
            label_image = LabelService.generate_text_label(
                text=part.part_name,
                print_settings=print_settings,
                allowed_width=600,  # Default width
                allowed_height=available_height,
            )

            # Rotate for Brother QL
            rotated_image = label_image.rotate(90, expand=True)

            return await printer.print_label(rotated_image, str(print_settings.label_size), print_settings.copies)

        except Exception as e:
            raise PrinterError(f"Failed to print part name: {str(e)}", printer_id)

    async def print_text_label(
        self, text: str, printer_id: Optional[str] = None, label_size: str = "62", copies: int = 1
    ) -> PrintJobResult:
        """Print a text label."""
        printer = self.get_printer(printer_id)

        try:
            # Create print settings - convert label_size to int
            print_settings = PrintSettings(label_size=int(label_size), dpi=300, copies=copies)

            # Generate text label
            available_height = LabelService.get_available_height_pixels(print_settings)
            label_image = LabelService.generate_text_label(
                text=text,
                print_settings=print_settings,
                allowed_width=600,  # Default width
                allowed_height=available_height,
            )

            # Rotate for Brother QL
            rotated_image = label_image.rotate(90, expand=True)

            return await printer.print_label(rotated_image, str(label_size), copies)

        except Exception as e:
            raise PrinterError(f"Failed to print text label: {str(e)}", printer_id)

    async def print_qr_and_text(
        self,
        part: PartModel,
        text: str,
        printer_config: Dict[str, Any],
        label_data: Dict[str, Any],
        printer_id: Optional[str] = None,
    ) -> PrintJobResult:
        """Print combined QR and text label with custom settings."""
        printer = self.get_printer(printer_id)

        try:
            # Create print settings from the provided config
            print_settings = PrintSettings(
                label_size=int(label_data.get("label_width", 62)), dpi=printer_config.get("dpi", 300), copies=1
            )
            scaling_factor = printer_config.get("scaling_factor", 1.0)

            # Generate combined label
            label_image = LabelService.generate_combined_label(
                part=part, print_settings=print_settings, custom_text=text
            )

            # Apply scaling if specified
            if scaling_factor != 1.0:
                scaled_width = int(label_image.width * scaling_factor)
                scaled_height = int(label_image.height * scaling_factor)
                label_image = label_image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

            return await printer.print_label(label_image, str(print_settings.label_size), print_settings.copies)

        except Exception as e:
            raise PrinterError(f"Failed to print QR and text: {str(e)}", printer_id)

    # Printer management methods
    def add_printer(self, printer: PrinterInterface) -> str:
        """Add a printer to the service."""
        printer_info = printer.get_printer_info()
        self._printers[printer_info.id] = printer
        return printer_info.id

    def remove_printer(self, printer_id: str) -> bool:
        """Remove a printer from the service."""
        if printer_id in self._printers:
            del self._printers[printer_id]
            return True
        return False

    def list_printers(self) -> Dict[str, PrinterInterface]:
        """List all available printers."""
        return self._printers.copy()


# Global instance for backward compatibility
_default_service: Optional[ModernPrinterService] = None


def get_printer_service() -> ModernPrinterService:
    """Get the global printer service instance."""
    global _default_service
    if _default_service is None:
        _default_service = ModernPrinterService()
    return _default_service


def set_printer_service(service: ModernPrinterService):
    """Set the global printer service instance."""
    global _default_service
    _default_service = service
