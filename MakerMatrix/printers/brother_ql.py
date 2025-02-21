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

    def print_label(self, image: Image, pconf: PrintSettings):
        print("[DEBUG] Converting image to printer instructions")
        instructions = convert(
            qlr=self.qlr,
            images=[image],
            label=str(pconf.label_size),
            rotate=pconf.rotation,
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

    def print_text_label(self, text: str, print_config) -> Image.Image:
        label = LabelService.print_text_label(text, print_config=print_config)
        self._resize_and_print(label)
        #
        # # Use print_config to obtain options:
        # label_len = print_config.label_len  # label length as float
        # font_size = print_config.font_size  # desired font size
        # font_file = print_config.font  # e.g., "arial.ttf"
        # text_color = print_config.text_color  # e.g., "black"
        # margin = print_config.margin  # margin fraction
        #
        # # Calculate dimensions based on DPI and label_len:
        # label_length_pixels = int(label_len * self.dpi)
        # available_height_pixels = int(0.47 * self.dpi)
        # target_height = int(available_height_pixels * 0.8)
        #
        # # Optionally, adjust font size based on target dimensions.
        # # For simplicity, we'll use the print_config font_size.
        # font = ImageFont.truetype(font_file, font_size)
        #
        # # Create a dummy image to measure text dimensions
        # dummy_img = Image.new('RGB', (1, 1), 'white')
        # draw = ImageDraw.Draw(dummy_img)
        # bbox = draw.textbbox((0, 0), text, font=font)
        # text_width = bbox[2] - bbox[0]
        # text_height = bbox[3] - bbox[1]
        #
        # # Calculate margins in pixels:
        # margin_x = int(text_width * margin)
        # margin_y = int(text_height * margin)
        #
        # # Define final image dimensions:
        # final_width = text_width + 2 * margin_x
        # final_height = text_height + 2 * margin_y
        #
        # # Create the final image and center the text:
        # text_img = Image.new('RGB', (final_width, final_height), 'white')
        # draw = ImageDraw.Draw(text_img)
        # x = (final_width - text_width) // 2
        # y = (final_height - text_height) // 2
        # draw.text((x, y), text, font=font, fill=text_color)
        #
        # # Rotate the image if needed
        # rotated_img = text_img.rotate(90, expand=True)
        #
        # self.print_label(rotated_img, print_config)
        # return rotated_img

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

    def print_qr_from_memory(self, qr_image: Image.Image, label: str = '12', rotate: str = '0'):
        return self._resize_and_print(qr_image, label, rotate)

    def print_qr(self, image_path: str, label: str = '12', rotate: str = '0'):
        try:
            im = Image.open(image_path)
            return self._resize_and_print(im, label, rotate)
        except Exception as e:
            print(f"Error opening image file {image_path}: {str(e)}")
            return False

    def _get_available_height_pixels(self):
        return int(0.47 * self.dpi)

    def print_qr_and_text(self, text: str, part, print_settings):
        try:
            # Generate the combined label image using LabelService.
            combined_img = LabelService.generate_combined_label(part, print_settings, custom_text=text)
            # Save preview (for debugging)
            combined_img.save("test_label.png")

            # Now apply the printer's scaling factor (from printer_config, i.e. self.scaling_factor)
            if self.scaling_factor != 1.0:
                scaled_width = int(combined_img.width * self.scaling_factor)
                scaled_height = int(combined_img.height * self.scaling_factor)
                combined_img = combined_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

            # Use print_settings.label_size (which represents the label height in mm) as the label parameter.
            return self._resize_and_print(combined_img, label=str(print_settings.label_size))
        except Exception as e:
            print(f"[ERROR] Exception in print_qr_and_text: {e}")
            import traceback
            print(traceback.format_exc())
            return False

