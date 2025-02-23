import traceback
import socket

from PIL import Image, ImageDraw, ImageFont
from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.raster import BrotherQLRaster

from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.printers.abstract_printer import AbstractPrinter
from MakerMatrix.services.label_service import LabelService
from PIL import Image


class LabelSizeError(Exception):
    """Raised when image dimensions exceed label capabilities"""

    def __init__(self, width: float, length: float, max_width: float, max_length: float):
        self.message = f"Image size ({width}\"x{length}\") exceeds maximum label size ({max_width}\"x{max_length}\")"
        super().__init__(self.message)


class BrotherQL(AbstractPrinter):
    def __init__(self, model: str = None, backend: str = None, printer_identifier: str = None, dpi: int = 300,
                 scaling_factor: float = 1.0, additional_settings: dict = None):
        super().__init__(dpi=dpi, scaling_factor=scaling_factor, name="BrotherQL")
        self.model = model
        self.backend = backend
        self.printer_identifier = printer_identifier
        self.additional_settings = additional_settings or {}
        self.qlr = BrotherQLRaster(self.model) if model else None

    # def print_label(self, image: Image, pconf: PrintSettings):
    #     print("[DEBUG] Converting image to printer instructions")
    #     instructions = convert(
    #         qlr=self.qlr,
    #         images=[image],
    #         label=str(pconf.label_size),
    #         rotate=pconf.rotation,
    #         threshold=70.0,
    #         dither=False,
    #         compress=False,
    #         red=False,
    #         dpi_600=(self.dpi == 600),
    #         hq=True,
    #         cut=True
    #     )
    #
    #     print("[DEBUG] Sending print job")
    #     result = send(
    #         instructions=instructions,
    #         printer_identifier=self.printer_identifier,
    #         backend_identifier=self.backend,
    #         blocking=True
    #     )
    #
    #     print("[DEBUG] Print job sent successfully")
    #     return result

    def print_text_label(self, text: str, print_settings: PrintSettings) -> bool:
        """
        Print a text-only label. If label_len is not set, auto-calculate the label
        length in mm based on the text width plus margins. Then generate the final
        text image and print it.
        """
        dpi = print_settings.dpi
        available_height_pixels = LabelService.get_available_height_pixels(print_settings)

        # We'll use a 5% margin, just like in generate_combined_label.
        margin_fraction = 0.05
        margin_pixels = int(margin_fraction * available_height_pixels)

        # If label_len is None, compute it based on measured text size.
        if print_settings.label_len is None:
            # 1) Measure text size for the given height.
            text_width_px, _ = LabelService.measure_text_size(
                text=text,
                print_settings=print_settings,
                allowed_height=available_height_pixels
            )
            # 2) Convert text+margin to mm (no QR in text-only labels).
            label_len_mm = LabelService.compute_label_len_mm_for_text_and_qr(
                text_width_px=text_width_px,
                margin_px=margin_pixels,
                dpi=dpi,
                qr_width_px=0
            )
        else:
            label_len_mm = float(print_settings.label_len)

        # Convert mm -> final px, apply a scaling factor (e.g. 1.1 for printer shrinkage).
        total_label_width_px = LabelService.finalize_label_width_px(
            label_len_mm=label_len_mm,
            print_settings=print_settings,
            scaling_factor=1.1
        )

        # Now generate the text label image with the computed width/height.
        text_label_img = LabelService.generate_text_label(
            text=text,
            print_settings=print_settings,
            allowed_width=total_label_width_px,
            allowed_height=available_height_pixels
        )

        # Rotate if needed (90 degrees, etc.).
        rotated_label_img = text_label_img.rotate(90, expand=True)

        # Finally, send to your printer or do whatever "print" means in your app.
        return self._resize_and_print(rotated_label_img)

    def set_backend(self, backend: str):
        self.backend = backend

    def set_printer_identifier(self, printer_identifier: str):
        self.printer_identifier = printer_identifier

    def set_dpi(self, dpi: int):
        if dpi not in [300, 600]:
            raise ValueError("DPI must be 300 or 600.")
        self.dpi = dpi

    def set_model(self, model: str):
        self.model = model
        self.qlr = BrotherQLRaster(self.model)

    def _resize_and_print(self, image: Image.Image, label: str = '12', rotate: str = '0',
                          max_length_inches: float = None):
        """Convert the provided image to printer instructions and send it.
        Since LabelService already produces a correctly sized image, no additional resizing is performed.
        """
        try:
            print(f"[DEBUG] Starting _resize_and_print() with label: {label}, rotate: {rotate}")
            self.qlr.data = b''
            print("[DEBUG] Converting image to printer instructions")
            instructions = convert(
                qlr=self.qlr,
                images=[image],
                label=label,
                rotate=rotate,
                threshold=70.0,
                dither=False,
                compress=False,
                red=False,
                dpi_600=(self.dpi == 600),
                hq=True,
                cut=True
            )
            print("[DEBUG] Sending print job")
            result = send(
                instructions=instructions,
                printer_identifier=self.printer_identifier,
                backend_identifier=self.backend,
                blocking=True
            )
            print("[DEBUG] Print job sent successfully")
            return result
        except Exception as e:
            print(f"[ERROR] Exception in _resize_and_print: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def check_availability(self) -> bool:
        """
        Check if the printer is available.

        For network printers (backend=="network"), this attempts to connect
        to the printer's IP (extracted from self.printer_identifier) on port 9100.

        For USB printers (backend=="usb"), this implementation simply returns True,
        but you could extend it with platform-specific checks.
        """
        try:
            if self.backend == "network":
                # Assuming printer_identifier is in the format "tcp://192.168.1.71"
                host = self.printer_identifier.replace("tcp://", "").split(":")[0]
                port = 9100  # default port for many network printers
                # Attempt a connection with a short timeout
                sock = socket.create_connection((host, port), timeout=5)
                sock.close()
                return True
            elif self.backend == "usb":
                # TODO: Implement USB availability check if needed.
                return True
            else:
                return False
        except Exception as e:
            print(f"Availability check failed: {e}")
            return False

    def print_image(self, image: Image, label: str = "") -> None:
        self._resize_and_print(image, label)

    def configure_printer(self, config: dict) -> None:
        self.model = config.get('model', self.model)
        self.backend = config.get('backend', self.backend)
        self.printer_identifier = config.get('printer_identifier', self.printer_identifier)
        self.dpi = config.get('dpi', self.dpi)
        self.scaling_factor = config.get('scaling_factor', self.scaling_factor)
        if self.model:
            self.qlr = BrotherQLRaster(self.model)

    def get_status(self) -> str:
        return "Ready"

    def cancel_print(self) -> None:
        print("Print job cancelled")

    def print_qr_and_text(self, text: str, part, print_settings):
        try:
            # Generate the combined label image using LabelService.
            combined_img = LabelService.generate_combined_label(part, print_settings, custom_text=text)
            # For debugging, you can save the image.
            combined_img.save("test_label.png")

            # Apply the printer's scaling factor (from printer_config, i.e. self.scaling_factor)
            if self.scaling_factor != 1.0:
                scaled_width = int(combined_img.width * self.scaling_factor)
                scaled_height = int(combined_img.height * self.scaling_factor)
                combined_img = combined_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                combined_img.save("scaled_label.png")

            # Now send the image to print (using print_settings.label_size for the label parameter).
            return self._resize_and_print(combined_img, label=str(print_settings.label_size))
        except Exception as e:
            print(f"[ERROR] Exception in print_qr_and_text: {e}")
            import traceback
            print(traceback.format_exc())
            return False


