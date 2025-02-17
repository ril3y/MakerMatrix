from typing import Dict, Any

import qrcode
from PIL import Image, ImageDraw, ImageFont


class LabelService:
    def __init__(self, printer):
        self.printer = printer

    def print_text_label(self, text: str, print_config) -> Image.Image:
        # Use print_config to obtain options:
        label_len = print_config.label_len      # label length as float
        font_size = print_config.font_size        # desired font size
        font_file = print_config.font              # e.g., "arial.ttf"
        text_color = print_config.text_color       # e.g., "black"
        margin = print_config.margin               # margin fraction

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

    def generate_label(self, part_info: Dict[str, Any], style: str) -> Image:
        """Generate a label image based on the part information and style."""
        if style == "text":
            return self._generate_text_label(part_info)
        elif style == "qr_code":
            return self._generate_qr_code_label(part_info)
        else:
            raise ValueError(f"Unsupported style: {style}")

    def _generate_text_label(self, part_info: Dict[str, Any]) -> Image:
        """Generate a text-only label."""
        label = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(label)
        font = ImageFont.load_default()
        draw.text((10, 10), part_info['name'], font=font, fill='black')
        return label

    def _generate_qr_code_label(self, part_info: Dict[str, Any]) -> Image:
        """Generate a label with a QR code."""
        qr = qrcode.make(part_info['name'])
        label = Image.new('RGB', (200, 200), color='white')
        label.paste(qr, (50, 50))
        return label

    def print_label(self, part_info: Dict[str, Any], style: str):
        """Generate and print the label."""
        label_image = self.generate_label(part_info, style)

    @staticmethod
    def get_label_width_inches(label_size):
        """Extracts numeric width from a label size string like '12mm'."""
        if isinstance(label_size, int):
            width_mm = label_size  # Directly use integer if already numeric
        else:
            width_mm = int(''.join(filter(str.isdigit, str(label_size))))  # Convert to string before filtering

        return width_mm / 25.4  # Convert mm to inches
