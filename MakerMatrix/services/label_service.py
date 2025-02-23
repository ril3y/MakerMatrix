import math
from typing import Dict, Optional, Any

import qrcode
from PIL import Image, ImageOps, ImageDraw, ImageFont

from MakerMatrix.lib.print_settings import PrintSettings


class LabelService:
    @staticmethod
    def get_label_width_inches(label_size: int | str) -> float:
        """
        Convert a label size (in mm or a string containing mm) to inches.

        Args:
            label_size (int | str): The label size in mm or a string representation.

        Returns:
            float: The label width in inches.
        """
        if isinstance(label_size, int):
            width_mm = label_size
        else:
            width_mm = int(''.join(filter(str.isdigit, str(label_size))))
        return width_mm / 25.4

    @staticmethod
    def get_available_height_pixels(print_settings: PrintSettings) -> int:
        """
        Convert label height (in mm) from print_settings to pixels.
        """
        inches = print_settings.label_size / 25.4
        return round(inches * print_settings.dpi)

    @staticmethod
    def measure_text_size(
        text: str,
        print_settings: PrintSettings,
        allowed_height: int
    ) -> (int, int):
        """
        Measure the width/height of a text block given the label's allowed height.
        Returns the final text width and text height in pixels (after auto-scaling).

        We ignore allowed_width here and just find the maximum font size that
        fits the provided allowed_height. Then we measure the text's width
        at that font size.

        Returns:
            (max_line_width_px, total_text_height_px)
        """
        dummy_img = Image.new("RGB", (1, 1), "white")
        draw = ImageDraw.Draw(dummy_img)

        lines = text.split("\n") if text.strip() else [""]
        font_file = print_settings.font
        spacing_factor = 0.1  # 10% of font size for spacing

        candidate_font_size = print_settings.font_size
        max_font_size = 300
        best_font_size = candidate_font_size
        best_metrics = None

        while candidate_font_size < max_font_size:
            try:
                font = ImageFont.truetype(font_file, candidate_font_size)
            except Exception as e:
                print(
                    f"[ERROR] Could not load font '{font_file}' "
                    f"at size {candidate_font_size}: {e}. Using default font."
                )
                font = ImageFont.load_default()

            # Font metrics
            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * candidate_font_size) if len(lines) > 1 else 0

            # Calculate total height needed
            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            # We only check the height constraint here
            if total_text_height <= allowed_height:
                # Now find the max line width
                max_line_width = 0
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, line_width)

                best_font_size = candidate_font_size
                best_metrics = (max_line_width, total_text_height, line_height, inter_line)
                candidate_font_size += 1
            else:
                break

        # If no suitable size was found, use the original font size
        if best_metrics is None:
            best_font_size = print_settings.font_size
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0

            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            best_metrics = (max_line_width, total_text_height, line_height, inter_line)
        else:
            # Recreate the font with the best size to measure final width accurately
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            # Re-measure width with that final best size
            max_line_width = 0
            lines = text.split("\n") if text.strip() else [""]
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            # Update the best_metrics
            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0
            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)
            best_metrics = (max_line_width, total_text_height, line_height, inter_line)

        max_line_width, total_text_height, _, _ = best_metrics
        return max_line_width, total_text_height

    @staticmethod
    def generate_qr(part: Dict[str, Any], print_settings: PrintSettings) -> Image.Image:
        """
        Generate a QR code image using the part's unique identifier.
        """
        qr_data = getattr(part, "id", None) or part.get("id", "UNKNOWN")
        qr_image = qrcode.make(str(qr_data))

        # If there's a specified qr_size, resize
        if hasattr(print_settings, "qr_size") and print_settings.qr_size is not None:
            qr_image = qr_image.resize(
                (print_settings.qr_size, print_settings.qr_size),
                Image.Resampling.LANCZOS
            )
        return qr_image

    @staticmethod
    def compute_label_len_mm_for_text_and_qr(
        text_width_px: int,
        margin_px: int,
        dpi: int,
        qr_width_px: int = 0
    ) -> float:
        """
        Given the measured text width (in pixels), optional QR width (in pixels),
        and margin (in pixels), compute the total label length in mm.
        """
        total_width_px = qr_width_px + margin_px + text_width_px + margin_px
        return (total_width_px / dpi) * 25.4  # px -> mm

    @staticmethod
    def finalize_label_width_px(
        label_len_mm: float,
        print_settings: PrintSettings,
        scaling_factor: float = 1.1
    ) -> int:
        """
        Converts a label length (in mm) to a final pixel width, applying
        a scaling factor to compensate for printing shrinkage.
        """
        return int((label_len_mm * scaling_factor / 25.4) * print_settings.dpi)

    @staticmethod
    def generate_text_label(
        text: str,
        print_settings: PrintSettings,
        allowed_width: int,
        allowed_height: int
    ) -> Image.Image:
        """
        Generate a text label image that scales its font size to fit within the allowed area.
        Uses the font's ascent + descent to avoid clipping descenders.
        Centers the resulting text block in the final image.
        """
        dummy_img = Image.new("RGB", (1, 1), "white")
        draw = ImageDraw.Draw(dummy_img)

        lines = text.split("\n") if text.strip() else [""]
        font_file = print_settings.font
        spacing_factor = 0.1  # 10% of font size for spacing

        candidate_font_size = print_settings.font_size
        max_font_size = 300
        best_font_size = candidate_font_size
        best_metrics = None

        while candidate_font_size < max_font_size:
            try:
                font = ImageFont.truetype(font_file, candidate_font_size)
            except Exception as e:
                print(
                    f"[ERROR] Could not load font '{font_file}' at size {candidate_font_size}: {e}. "
                    f"Using default font."
                )
                font = ImageFont.load_default()

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * candidate_font_size) if len(lines) > 1 else 0

            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            # Measure max line width
            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            # Check if this fits in allowed_width, allowed_height
            if max_line_width <= allowed_width and total_text_height <= allowed_height:
                best_font_size = candidate_font_size
                best_metrics = (max_line_width, total_text_height, line_height, inter_line)
                candidate_font_size += 1
            else:
                break

        # If we never updated best_metrics, revert to the original font size
        if best_metrics is None:
            best_font_size = print_settings.font_size
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0

            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            best_metrics = (max_line_width, total_text_height, line_height, inter_line)
        else:
            # Recreate the font at the best found size
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            # Re-check final width
            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0
            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)
            best_metrics = (max_line_width, total_text_height, line_height, inter_line)

        max_line_width, total_text_height, line_height, inter_line = best_metrics

        # Create the text block
        text_block = Image.new("RGB", (max_line_width, total_text_height), "white")
        draw_block = ImageDraw.Draw(text_block)

        y_cursor = 0
        for i, line in enumerate(lines):
            draw_block.text((0, y_cursor), line, font=font, fill=print_settings.text_color)
            y_cursor += line_height
            if i < len(lines) - 1:
                y_cursor += inter_line

        # Center this text block in the final image
        final_img = Image.new("RGB", (allowed_width, allowed_height), "white")
        x_offset = (allowed_width - max_line_width) // 2
        y_offset = (allowed_height - total_text_height) // 2
        final_img.paste(text_block, (x_offset, y_offset))

        return final_img

    @staticmethod
    def generate_combined_label(
        part: Dict[str, Any],
        print_settings: PrintSettings,
        custom_text: Optional[str] = None
    ) -> Image.Image:
        """
        Generate a combined label with a QR code and text. If label_len is not set,
        we auto-calculate the label length in mm based on the text size + QR code size
        with a small margin.
        """
        dpi = print_settings.dpi
        available_height_pixels = LabelService.get_available_height_pixels(print_settings)

        # Decide on the text
        if custom_text is None:
            if custom_text is None:
                custom_text = part.part_number or part.part_name

        # Calculate the QR code size
        qr_scale_factor = getattr(print_settings, "qr_scale", 0.99)
        qr_size_px = int(available_height_pixels * qr_scale_factor)

        # We'll use a 5% margin around the content
        margin_fraction = 0.05
        margin_pixels = int(margin_fraction * available_height_pixels)

        # If label_len is None, auto-calculate based on text + QR width
        if print_settings.label_len is None:
            # 1) Measure text size given the allowed height
            text_width_px, _ = LabelService.measure_text_size(
                text=custom_text,
                print_settings=print_settings,
                allowed_height=available_height_pixels
            )
            # 2) Compute the label length in mm (text + QR + margins)
            label_len_mm = LabelService.compute_label_len_mm_for_text_and_qr(
                text_width_px=text_width_px,
                margin_px=margin_pixels,
                dpi=dpi,
                qr_width_px=qr_size_px
            )
        else:
            # Otherwise, just use the provided label_len
            label_len_mm = float(print_settings.label_len)

        # Convert mm -> final px (with a scaling factor for shrinkage)
        total_label_width_px = LabelService.finalize_label_width_px(
            label_len_mm=label_len_mm,
            print_settings=print_settings,
            scaling_factor=1.1
        )

        # Create the QR code image
        qr_image = LabelService.generate_qr(part, print_settings)
        qr_image = ImageOps.fit(qr_image, (qr_size_px, qr_size_px), Image.Resampling.LANCZOS)

        # Create a blank canvas for the label
        combined_img = Image.new('RGB', (total_label_width_px, available_height_pixels), 'white')

        # Paste the QR code, centered vertically
        qr_y = (available_height_pixels - qr_size_px) // 2
        combined_img.paste(qr_image, (0, qr_y))

        # Now we know how much space remains for text
        qr_total_width = qr_size_px + margin_pixels
        remaining_text_width = max(1, total_label_width_px - qr_total_width)

        # Generate the text label image
        text_img = LabelService.generate_text_label(
            text=custom_text,
            print_settings=print_settings,
            allowed_width=remaining_text_width,
            allowed_height=available_height_pixels
        )

        # Center the text vertically in the remaining area
        text_x = qr_total_width
        text_y = (available_height_pixels - text_img.height) // 2
        combined_img.paste(text_img, (text_x, text_y))

        # Rotate if needed (e.g., 90 degrees)
        rotated_img = combined_img.rotate(90, expand=True)
        return rotated_img

    # -------------------------------------------------------------------
    # EXAMPLE: A text-only print method that reuses the same dimension logic
    # -------------------------------------------------------------------
    @staticmethod
    def print_text_label(text: str, print_settings: PrintSettings) -> Image.Image:
        """
        Example text-only label. If label_len is not set, auto-calculate the label
        length in mm based on the text width plus margins. Then generate the final
        text image.
        """
        dpi = print_settings.dpi
        available_height_pixels = LabelService.get_available_height_pixels(print_settings)

        margin_fraction = 0.05
        margin_pixels = int(margin_fraction * available_height_pixels)

        if print_settings.label_len is None:
            # Measure text size for the given height
            text_width_px, _ = LabelService.measure_text_size(
                text=text,
                print_settings=print_settings,
                allowed_height=available_height_pixels
            )
            # Convert to mm with margins
            label_len_mm = LabelService.compute_label_len_mm_for_text_and_qr(
                text_width_px=text_width_px,
                margin_px=margin_pixels,
                dpi=dpi,
                qr_width_px=0  # no QR code in text-only label
            )
        else:
            label_len_mm = float(print_settings.label_len)

        # Convert mm -> final px (with a scaling factor)
        total_label_width_px = LabelService.finalize_label_width_px(
            label_len_mm=label_len_mm,
            print_settings=print_settings,
            scaling_factor=1.1
        )

        # Generate the text label
        text_label_img = LabelService.generate_text_label(
            text=text,
            print_settings=print_settings,
            allowed_width=total_label_width_px,
            allowed_height=available_height_pixels
        )

        # Rotate if needed
        rotated_label_img = text_label_img.rotate(90, expand=True)

        # In practice, you'd send this to your printer. For now, return the image.
        return rotated_label_img
