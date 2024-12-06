import io

from PIL import Image, ImageDraw, ImageFont, ImageOps
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster
import json

import logging

class LabelSizeError(Exception):
    """Raised when image dimensions exceed label capabilities"""

    def __init__(self, width: float, length: float, max_width: float, max_length: float):
        self.message = f"Image size ({width}\"x{length}\") exceeds maximum label size ({max_width}\"x{max_length}\")"
        super().__init__(self.message)


class Printer:
    def __init__(self, model: str = None, backend: str = None, printer_identifier: str = None, dpi: int = 300,
                 scaling_factor=1.0):

        self.model = model
        self.backend = backend
        self.printer_identifier = printer_identifier
        self.dpi = dpi
        self.qlr = BrotherQLRaster(self.model) if model else None
        self.scaling_factor = scaling_factor

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
                          max_length_inches: float = 3.0):
        """Print an image to label with size validation and max length control"""

        # Adjust requested length to compensate for printer scaling
        adjusted_length_inches = max_length_inches * self.scaling_factor
        LABEL_WIDTH_INCHES = 0.47  # 12mm in inches

        # Convert image dimensions to inches
        image_width_inches = image.width / self.dpi
        image_length_inches = image.height / self.dpi

        new_height = int(adjusted_length_inches * self.dpi)
        new_width = int(LABEL_WIDTH_INCHES * self.dpi)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Define label dimensions

        # Resize if image exceeds max length
        if image_length_inches > adjusted_length_inches:
            new_height = int(adjusted_length_inches * self.dpi)
            new_width = int(LABEL_WIDTH_INCHES * self.dpi)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert and print
        self.qlr.data = b''
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

        return send(
            instructions=instructions,
            printer_identifier=self.printer_identifier,
            backend_identifier=self.backend,
            blocking=True
        )

    def print_qr_from_memory(self, qr_image: Image.Image, label: str = '12', rotate: str = '0'):
        return self._resize_and_print(qr_image, label, rotate)

    def print_qr(self, image_path: str, label: str = '12', rotate: str = '0'):
        try:
            im = Image.open(image_path)
            return self._resize_and_print(im, label, rotate)
        except Exception as e:
            print(f"Error opening image file {image_path}: {str(e)}")
            return False

    def print_text_label(self, text: str, label: str = '12', label_len: float = 1.5):
        # Calculate exact dimensions - no reduction in label length
        label_length_pixels = int(label_len * self.dpi)
        available_height_pixels = int(0.47 * self.dpi)
        target_height = int(available_height_pixels * 0.8)

        # Find font size that fits both height and usable width (90% of label length)
        font_size = 1
        max_font = 200
        usable_width = int(label_length_pixels * 0.9)  # Text area within label

        while font_size < max_font:
            font = ImageFont.truetype("arial.ttf", font_size)
            test_bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), text, font=font)
            test_height = test_bbox[3] - test_bbox[1]
            test_width = test_bbox[2] - test_bbox[0]

            if test_height > target_height or test_width > usable_width:
                font_size -= 1
                break
            font_size += 1

        # Create image at full specified length
        text_img = Image.new('RGB', (label_length_pixels, available_height_pixels), 'white')
        draw = ImageDraw.Draw(text_img)
        font = ImageFont.truetype("arial.ttf", font_size)

        # Center the text within the full label length
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (label_length_pixels - text_width) // 2
        y = (available_height_pixels - text_height) // 2
        draw.text((x, y), text, font=font, fill='black')

        rotated_img = text_img.rotate(90, expand=True)
        return self._resize_and_print(rotated_img, label=label, rotate='0', max_length_inches=label_len)

    def save_config(self, config_path='printer_config.json'):
        config = {
            'model': self.model,
            'backend': self.backend,
            'printer_identifier': self.printer_identifier,
            'dpi': self.dpi
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

    def load_config(self, config_path='printer_config.json'):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.model = config.get('model')
                self.backend = config.get('backend')
                self.printer_identifier = config.get('printer_identifier')
                self.scaling_factor = config.get('scaling_factor', 1.0)

                self.dpi = config.get('dpi', 300)
                self.qlr = BrotherQLRaster(self.model)
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
