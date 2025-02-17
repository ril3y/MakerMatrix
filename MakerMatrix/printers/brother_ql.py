import traceback

from PIL import Image, ImageDraw, ImageFont
from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.raster import BrotherQLRaster

from MakerMatrix.lib.print_config import PrintJobConfig
from MakerMatrix.models.models import PartModel
from MakerMatrix.printers.abstract_printer import AbstractPrinter
from MakerMatrix.services.label_service import LabelService


class LabelSizeError(Exception):
    """Raised when image dimensions exceed label capabilities"""

    def __init__(self, width: float, length: float, max_width: float, max_length: float):
        self.message = f"Image size ({width}\"x{length}\") exceeds maximum label size ({max_width}\"x{max_length}\")"
        super().__init__(self.message)


class BrotherQL(AbstractPrinter):
    def __init__(self, model: str = None, backend: str = None, printer_identifier: str = None, dpi: int = 300,
                 scaling_factor=1.0):
        super().__init__(dpi=dpi, scaling_factor=scaling_factor)
        self.model = model
        self.backend = backend
        self.printer_identifier = printer_identifier
        self.qlr = BrotherQLRaster(self.model) if model else None

    def print_label(self, image: Image):
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
    def print_text_label(self, text: str, print_config) -> Image.Image:

        # Use print_config to obtain options:
        label_len = print_config.label_len  # label length as float
        font_size = print_config.font_size  # desired font size
        font_file = print_config.font  # e.g., "arial.ttf"
        text_color = print_config.text_color  # e.g., "black"
        margin = print_config.margin  # margin fraction

        # Calculate dimensions based on DPI and label_len:
        label_length_pixels = int(label_len * self.dpi)
        available_height_pixels = int(0.47 * self.dpi)
        target_height = int(available_height_pixels * 0.8)

        # Optionally, adjust font size based on target dimensions.
        # For simplicity, we'll use the print_config font_size.
        font = ImageFont.truetype(font_file, font_size)

        # Create a dummy image to measure text dimensions
        dummy_img = Image.new('RGB', (1, 1), 'white')
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate margins in pixels:
        margin_x = int(text_width * margin)
        margin_y = int(text_height * margin)

        # Define final image dimensions:
        final_width = text_width + 2 * margin_x
        final_height = text_height + 2 * margin_y

        # Create the final image and center the text:
        text_img = Image.new('RGB', (final_width, final_height), 'white')
        draw = ImageDraw.Draw(text_img)
        x = (final_width - text_width) // 2
        y = (final_height - text_height) // 2
        draw.text((x, y), text, font=font, fill=text_color)

        # Rotate the image if needed
        rotated_img = text_img.rotate(90, expand=True)
        return rotated_img

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

    from PIL import Image

    def _resize_and_print(self, image: Image.Image, label: str = '12', rotate: str = '0',
                          max_length_inches: float = 3.0):
        """Resize and print an image while handling potential errors."""
        try:
            print(f"[DEBUG] Starting _resize_and_print() with label: {label}, rotate: {rotate}")

            adjusted_length_inches = max_length_inches * self.scaling_factor
            label_width_inches = LabelService.get_label_width_inches(label)
            image_width_inches = image.width / self.dpi
            image_length_inches = image.height / self.dpi

            new_height = int(adjusted_length_inches * self.dpi)
            new_width = int(label_width_inches * self.dpi)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            print(f"[DEBUG] Resized image to: {image.size}")

            if image_length_inches > adjusted_length_inches:
                print("[DEBUG] Image length exceeds max length, resizing again")
                new_height = int(adjusted_length_inches * self.dpi)
                new_width = int(label_width_inches * self.dpi)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

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
            print(traceback.format_exc())  # Print full stack trace for debugging
            return False  # Ensure the function doesn't crash the program

    def check_availability(self) -> bool:
        pass

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

    def print_qr_and_text(self, qr_image: Image.Image, text: str, job_config: PrintJobConfig):
        available_height_pixels = self._get_available_height_pixels()
        qr_size = int(available_height_pixels * 0.9)
        qr_resized = qr_image.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        margin_pixels = int(0.1 * self.dpi)
        text_length = 1.0
        total_length = (qr_size / self.dpi) + (margin_pixels / self.dpi) + text_length

        combined_image = Image.new('RGB',
                                   (int(total_length * self.dpi), available_height_pixels),
                                   'white')
        combined_image.paste(qr_resized, (0, int((available_height_pixels - qr_size) / 2)))

        font_size = job_config.font_size
        max_font = 200
        target_height = int(available_height_pixels * 0.8)
        text_area_width = int(text_length * self.dpi)

        while font_size < max_font:
            try:
                font = ImageFont.truetype(job_config.font, font_size)
                test_bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), text, font=font)
                test_height = test_bbox[3] - test_bbox[1]
                test_width = test_bbox[2] - test_bbox[0]

                if test_height > target_height or test_width > text_area_width:
                    font_size -= 1
                    break
                font_size += 1
            except Exception:
                break

        draw = ImageDraw.Draw(combined_image)
        font = ImageFont.truetype("arial.ttf", font_size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        x = qr_size + margin_pixels + (text_area_width - text_width) // 2
        y = (available_height_pixels - text_height) // 2
        draw.text((x, y), text, font=font, fill='black')

        rotated_img = combined_image.rotate(90, expand=True)

        return self._resize_and_print(rotated_img,
                                      max_length_inches=total_length)
