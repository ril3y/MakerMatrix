"""
Modern Brother QL printer driver implementing the new printer interface.
"""

import asyncio
import io
import socket
import time
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont
from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.raster import BrotherQLRaster

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
    PrintJobError,
    PrinterConnectionError,
    PrinterOfflineError,
)


class BrotherQLModern(BasePrinter):
    """
    Modern Brother QL printer driver implementing the new printer interface.
    Supports all Brother QL models with network and USB backends.
    """

    # Brother QL supported label sizes (name, width_mm, height_mm, width_px, height_px)
    SUPPORTED_SIZES = [
        LabelSize("12", 12.0, 29.0, 106, 164),
        LabelSize("29", 29.0, 90.0, 306, 991),
        LabelSize("38", 38.0, 90.0, 413, 991),
        LabelSize("50", 50.0, 30.0, 554, 331),
        LabelSize("54", 54.0, 30.0, 590, 331),
        LabelSize("62", 62.0, 29.0, 696, 271),
        LabelSize("102", 102.0, 51.0, 1164, 565),
        LabelSize("17x54", 17.0, 54.0, 201, 614),
        LabelSize("17x87", 17.0, 87.0, 201, 956),
        LabelSize("23x23", 23.0, 23.0, 202, 202),
        # Continuous labels
        LabelSize("12mm", 12.0, None, 106, None),
        LabelSize("29mm", 29.0, None, 306, None),
        LabelSize("38mm", 38.0, None, 413, None),
        LabelSize("50mm", 50.0, None, 554, None),
        LabelSize("54mm", 54.0, None, 590, None),
        LabelSize("62mm", 62.0, None, 696, None),
    ]

    def __init__(
        self,
        printer_id: str,
        name: str,
        model: str,
        backend: str,
        identifier: str,
        dpi: int = 300,
        scaling_factor: float = 1.0,
        additional_settings: Optional[dict] = None,
    ):
        super().__init__(printer_id, name, model, backend, identifier)
        self.dpi = dpi
        self.scaling_factor = scaling_factor
        self.additional_settings = additional_settings or {}

        # Initialize Brother QL components
        try:
            self.qlr = BrotherQLRaster(model) if model else None
            self._status = PrinterStatus.READY
        except Exception as e:
            self._status = PrinterStatus.ERROR
            self._last_error = f"Failed to initialize Brother QL: {str(e)}"

        self._current_job_id: Optional[str] = None
        self._print_history: List[dict] = []

    async def print_label(self, image: Image.Image, label_size: str, copies: int = 1) -> PrintJobResult:
        """Print a label image using Brother QL hardware."""
        job_id = self._generate_job_id()

        try:
            # Validate label size
            if not self._is_valid_label_size(label_size):
                supported = [size.name for size in self.SUPPORTED_SIZES]
                raise InvalidLabelSizeError(label_size, self.printer_id, supported)

            # Check printer availability
            if not await self._check_printer_ready():
                raise PrinterOfflineError(self.printer_id, "Printer is not ready or available")

            self._set_status(PrinterStatus.PRINTING)
            self._current_job_id = job_id

            # Apply scaling factor if needed (compensates for printer shrinkage)
            if self.scaling_factor != 1.0:
                scaled_width = int(image.width * self.scaling_factor)
                scaled_height = int(image.height * self.scaling_factor)
                image = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

            # Convert image to printer instructions
            instructions = self._convert_image_to_instructions(image, label_size)

            # Send to printer (with retry for multiple copies)
            success = True
            error_msg = None

            for copy_num in range(copies):
                try:
                    result = send(
                        instructions=instructions,
                        printer_identifier=self.identifier,
                        backend_identifier=self.backend,
                        blocking=True,
                    )
                    if not result:
                        success = False
                        error_msg = f"Print failed on copy {copy_num + 1}"
                        break
                except Exception as e:
                    success = False
                    error_msg = f"Print error on copy {copy_num + 1}: {str(e)}"
                    break

            # Record print job
            self._print_history.append(
                {
                    "job_id": job_id,
                    "label_size": label_size,
                    "copies": copies,
                    "image_size": image.size,
                    "timestamp": time.time(),
                    "success": success,
                }
            )

            self._set_status(PrinterStatus.READY)
            self._current_job_id = None

            if success:
                return PrintJobResult(
                    success=True, job_id=job_id, message=f"Printed {copies} label(s) on {label_size}mm Brother QL"
                )
            else:
                return PrintJobResult(success=False, job_id=job_id, error=error_msg or "Unknown print error")

        except (InvalidLabelSizeError, PrinterOfflineError) as e:
            # Re-raise known exceptions
            self._set_status(PrinterStatus.READY)
            self._current_job_id = None
            raise e
        except Exception as e:
            self._set_status(PrinterStatus.ERROR, str(e))
            self._current_job_id = None
            raise PrintJobError(f"Brother QL print error: {str(e)}", self.printer_id, job_id)

    async def preview_label(self, image: Image.Image, label_size: str) -> PreviewResult:
        """Generate a preview of what the label will look like when printed."""
        if not self._is_valid_label_size(label_size):
            supported = [size.name for size in self.SUPPORTED_SIZES]
            raise InvalidLabelSizeError(label_size, self.printer_id, supported)

        # Get label dimensions
        label_info = self._get_label_size_info(label_size)

        # Create preview with Brother QL styling
        border_width = 15
        header_height = 40
        preview_width = image.width + 2 * border_width
        preview_height = image.height + 2 * border_width + header_height

        preview = Image.new("RGB", (preview_width, preview_height), "white")
        draw = ImageDraw.Draw(preview)

        # Draw Brother QL style border
        draw.rectangle([0, 0, preview_width - 1, preview_height - 1], outline="#00458B", width=3)
        draw.rectangle(
            [
                border_width - 1,
                border_width + header_height - 1,
                preview_width - border_width,
                preview_height - border_width,
            ],
            outline="#333333",
            width=1,
        )

        # Add Brother QL header
        try:
            font = ImageFont.load_default()
        except:
            font = None

        header_text = f"Brother QL {self.model} - {label_size}mm"
        draw.rectangle(
            [border_width, border_width, preview_width - border_width, border_width + header_height], fill="#00458B"
        )
        draw.text((border_width + 10, border_width + 10), header_text, fill="white", font=font)

        # Paste the label image
        preview.paste(image, (border_width, border_width + header_height))

        # Add label info
        info_text = f"Size: {label_info.width_mm}x{label_info.height_mm}mm | DPI: {self.dpi}"
        if label_info.is_continuous():
            info_text = f"Size: {label_info.width_mm}mm continuous | DPI: {self.dpi}"

        draw.text((border_width, preview_height - 25), info_text, fill="#666666", font=font)

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        preview.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        return PreviewResult(
            image_data=img_byte_arr,
            format="png",
            width_px=preview_width,
            height_px=preview_height,
            label_size=label_info,
            message=f"Brother QL preview for {label_size}mm label",
        )

    async def get_status(self) -> PrinterStatus:
        """Get current printer status."""
        # For network printers, try a quick connectivity check
        if self.backend == "network" and self._status == PrinterStatus.READY:
            try:
                host = self.identifier.replace("tcp://", "").split(":")[0]
                sock = socket.create_connection((host, 9100), timeout=1)
                sock.close()
            except:
                self._set_status(PrinterStatus.OFFLINE, "Network connection failed")

        return self._status

    async def get_capabilities(self) -> List[PrinterCapability]:
        """Get Brother QL printer capabilities."""
        return [
            PrinterCapability.QR_CODES,
            PrinterCapability.BARCODES,
            PrinterCapability.IMAGES,
            PrinterCapability.DIE_CUT_LABELS,
            PrinterCapability.CONTINUOUS_LABELS,
        ]

    async def test_connection(self) -> TestResult:
        """Test Brother QL printer connectivity."""
        start_time = time.time()

        try:
            if self.backend == "network":
                # Test network connection
                host = self.identifier.replace("tcp://", "").split(":")[0]
                port = int(self.identifier.split(":")[-1]) if ":" in self.identifier.split("//")[-1] else 9100

                sock = socket.create_connection((host, port), timeout=5)
                sock.close()

                response_time = (time.time() - start_time) * 1000
                return TestResult(
                    success=True, response_time_ms=response_time, message=f"Connected to Brother QL at {host}:{port}"
                )

            elif self.backend == "usb":
                # For USB, we'd need to check if the device is available
                # This is platform-specific and would need proper implementation
                response_time = (time.time() - start_time) * 1000
                return TestResult(
                    success=True, response_time_ms=response_time, message=f"USB Brother QL connection assumed available"
                )

            else:
                return TestResult(success=False, error=f"Unsupported backend: {self.backend}")

        except socket.timeout:
            return TestResult(
                success=False, response_time_ms=(time.time() - start_time) * 1000, error="Connection timeout"
            )
        except Exception as e:
            return TestResult(
                success=False, response_time_ms=(time.time() - start_time) * 1000, error=f"Connection failed: {str(e)}"
            )

    def get_supported_label_sizes(self) -> List[LabelSize]:
        """Get Brother QL supported label sizes."""
        return self.SUPPORTED_SIZES.copy()

    def get_printer_info(self) -> PrinterInfo:
        """Get Brother QL printer information."""
        info = super().get_printer_info()
        info.capabilities = [
            PrinterCapability.QR_CODES,
            PrinterCapability.BARCODES,
            PrinterCapability.IMAGES,
            PrinterCapability.DIE_CUT_LABELS,
            PrinterCapability.CONTINUOUS_LABELS,
        ]
        return info

    async def cancel_current_job(self) -> bool:
        """Cancel current print job."""
        if self._current_job_id:
            # Brother QL doesn't have a direct cancel command, but we can try to reset
            self._set_status(PrinterStatus.READY)
            self._current_job_id = None
            return True
        return False

    # Private helper methods
    def _convert_image_to_instructions(self, image: Image.Image, label_size: str) -> bytes:
        """Convert PIL image to Brother QL printer instructions."""
        if not self.qlr:
            raise PrintJobError("Brother QL raster not initialized", self.printer_id)

        # Reset raster data
        self.qlr.data = b""

        # Convert image to printer instructions
        # Map our label sizes to Brother QL library label names
        brother_ql_label_map = {
            "12": "12",
            "29": "29",
            "38": "38",
            "50": "50",
            "54": "54",
            "62": "62",
            "102": "102",
            "17x54": "17x54",
            "17x87": "17x87",
            "23x23": "23x23",
            # Continuous labels map to their die-cut equivalents for Brother QL library
            "12mm": "12",
            "29mm": "29",
            "38mm": "38",
            "50mm": "50",
            "54mm": "54",
            "62mm": "62",
        }

        brother_ql_label = brother_ql_label_map.get(label_size, label_size)

        instructions = convert(
            qlr=self.qlr,
            images=[image],
            label=brother_ql_label,
            rotate="0",  # Rotation should be handled before this
            threshold=70.0,
            dither=False,
            compress=False,
            red=False,
            dpi_600=(self.dpi == 600),
            hq=True,
            cut=True,
        )

        return instructions

    async def _check_printer_ready(self) -> bool:
        """Check if printer is ready for printing."""
        if self._status in [PrinterStatus.ERROR, PrinterStatus.OFFLINE]:
            return False

        # For network printers, do a quick connectivity check
        # Use a shorter timeout to avoid blocking print jobs
        if self.backend == "network":
            try:
                host = self.identifier.replace("tcp://", "").split(":")[0]
                sock = socket.create_connection((host, 9100), timeout=1)
                sock.close()
                return True
            except:
                # Don't fail the print job if the quick check fails
                # The actual print operation will reveal connection issues
                print(f"Quick connectivity check failed for {host}, but proceeding with print")
                return True

        return True

    def _is_valid_label_size(self, label_size: str) -> bool:
        """Check if label size is supported by Brother QL."""
        return any(size.name == label_size for size in self.SUPPORTED_SIZES)

    def _get_label_size_info(self, label_size: str) -> LabelSize:
        """Get label size information."""
        for size in self.SUPPORTED_SIZES:
            if size.name == label_size:
                return size
        raise InvalidLabelSizeError(label_size, self.printer_id)

    # Additional Brother QL specific methods for debugging/testing
    def get_print_history(self) -> List[dict]:
        """Get print job history (for testing/debugging)."""
        return self._print_history.copy()

    def clear_print_history(self):
        """Clear print history (for testing)."""
        self._print_history.clear()

    def get_brother_ql_info(self) -> dict:
        """Get Brother QL specific information."""
        return {
            "model": self.model,
            "backend": self.backend,
            "identifier": self.identifier,
            "dpi": self.dpi,
            "scaling_factor": self.scaling_factor,
            "qlr_initialized": self.qlr is not None,
            "additional_settings": self.additional_settings,
        }
