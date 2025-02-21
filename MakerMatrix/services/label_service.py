import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps


class LabelService:
    @staticmethod
    def get_label_width_inches(label_size):
        if isinstance(label_size, int):
            width_mm = label_size
        else:
            width_mm = int(''.join(filter(str.isdigit, str(label_size))))
        return width_mm / 25.4  # convert mm to inches

    @staticmethod
    def get_available_height_pixels(print_settings) -> int:
        # Use print_settings.label_size (in mm) to determine label height in pixels.
        inches = print_settings.label_size / 25.4
        return int(inches * print_settings.dpi)

    @staticmethod
    def generate_qr(part: dict, print_settings) -> Image.Image:
        """
        Generate a QR code image using the part's unique identifier.
        The part is expected to be a dict with a 'data' key.
        """
        part_data = part.get("data", {})
        qr_data = {"id": part_data.get("id")}
        qr_image = qrcode.make(str(qr_data))
        if hasattr(print_settings, "qr_size"):
            qr_image = qr_image.resize(
                (print_settings.qr_size, print_settings.qr_size),
                Image.Resampling.LANCZOS
            )
        return qr_image

    @staticmethod
    def generate_text_label(text: str, print_settings) -> Image.Image:
        """
        Generate a text-only label image using options from print_settings.
        """
        dpi = print_settings.dpi
        font_size = print_settings.font_size
        font_file = print_settings.font
        text_color = print_settings.text_color
        margin = print_settings.margin

        try:
            font = ImageFont.truetype(font_file, font_size)
        except Exception as e:
            print(f"[ERROR] Could not load font '{font_file}': {e}. Using default font.")
            font = ImageFont.load_default()

        dummy_img = Image.new('RGB', (1, 1), 'white')
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        margin_x = int(text_width * margin)
        margin_y = int(text_height * margin)
        final_width = text_width + 2 * margin_x
        final_height = text_height + 2 * margin_y

        text_img = Image.new('RGB', (final_width, final_height), 'white')
        draw = ImageDraw.Draw(text_img)
        x = (final_width - text_width) // 2
        y = (final_height - text_height) // 2
        draw.text((x, y), text, font=font, fill=text_color)
        # Rotate 90° as in our previous examples.
        rotated_img = text_img.rotate(90, expand=True)
        return rotated_img

    @staticmethod
    def get_available_height_pixels(print_settings) -> int:
        # Use print_settings.label_size (in mm) for the physical label height.
        # For a 12mm label:
        inches = print_settings.label_size / 25.4
        return int(inches * print_settings.dpi)

    @staticmethod
    def generate_combined_label(part: dict, print_settings, custom_text: str = None) -> Image.Image:
        dpi = print_settings.dpi
        # Calculate available label height based on the measured label_size (12mm)
        available_height_pixels = LabelService.get_available_height_pixels(print_settings)

        # Generate the QR code image.
        qr_image = LabelService.generate_qr(part, print_settings)

        # Instead of a fixed 0.9 multiplier, use a higher factor (e.g., 0.98) so the QR fills nearly all available height.
        qr_scale_factor = 0.98
        qr_size = int(available_height_pixels * qr_scale_factor)
        # Optionally, save for debugging:
        qr_image.save("qr_before_resize.png")
        qr_image = ImageOps.fit(qr_image, (qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_image.save("qr_after_resize.png")

        margin_pixels = int(0.1 * dpi)
        # Reserve text area width based on print_settings.label_len (in inches converted to pixels).
        text_area_width = int(print_settings.label_len * dpi)
        total_width = qr_size + margin_pixels + text_area_width

        combined_img = Image.new('RGB', (total_width, available_height_pixels), 'white')
        # Paste the QR code on the left, centered vertically.
        qr_y = (available_height_pixels - qr_size) // 2
        combined_img.paste(qr_image, (0, qr_y))

        # Determine text to display.
        if custom_text is None:
            custom_text = part.get("data", {}).get("part_name", "")

        text_img = LabelService.generate_text_label(custom_text, print_settings)
        # Scale the text image proportionally so it fits within the reserved text area.
        text_img_width, text_img_height = text_img.size
        scaling_factor = min(text_area_width / text_img_width, available_height_pixels / text_img_height)
        new_text_width = int(text_img_width * scaling_factor)
        new_text_height = int(text_img_height * scaling_factor)
        text_img = text_img.resize((new_text_width, new_text_height), Image.Resampling.LANCZOS)

        # Center the text image in the reserved area.
        text_x = qr_size + margin_pixels + (text_area_width - new_text_width) // 2
        text_y = (available_height_pixels - new_text_height) // 2
        combined_img.paste(text_img, (text_x, text_y))

        # Rotate the entire label if needed.
        rotated_img = combined_img.rotate(90, expand=True)
        return rotated_img

