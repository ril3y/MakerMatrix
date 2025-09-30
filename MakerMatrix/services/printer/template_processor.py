"""
Template Processing Engine

Core engine for processing label templates with advanced features including:
- Text rotation (0°, 90°, 180°, 270°)
- Multi-line text with optimal sizing
- QR code positioning (8 positions)
- Template-aware layout generation
- Vertical text layouts (character-per-line)
"""

import math
import qrcode
import re
from typing import Dict, Optional, Any, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageOps
from dataclasses import dataclass
from enum import Enum

from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.services.printer.label_service import LabelService
from MakerMatrix.models.label_template_models import (
    LabelTemplateModel,
    TextRotation,
    QRPosition,
    TextAlignment,
    LayoutType
)


@dataclass
class ProcessingContext:
    """Context for template processing operations"""
    template: LabelTemplateModel
    data: Dict[str, Any]
    print_settings: PrintSettings
    label_width_px: int
    label_height_px: int
    dpi: int


@dataclass
class LayoutDimensions:
    """Calculated dimensions for label layout"""
    qr_size_px: int
    qr_x: int
    qr_y: int
    text_area_x: int
    text_area_y: int
    text_area_width: int
    text_area_height: int
    margins: Dict[str, int]


class TemplateProcessor:
    """Main template processing engine"""

    def __init__(self):
        self.label_service = LabelService()

    def process_template(
        self,
        template: LabelTemplateModel,
        data: Dict[str, Any],
        print_settings: PrintSettings
    ) -> Image.Image:
        """
        Process a template with given data and generate a label image.

        Args:
            template: The label template to process
            data: Data to fill template placeholders
            print_settings: Print configuration settings

        Returns:
            PIL Image ready for printing
        """
        # Detect if template text contains {qr} placeholder
        has_qr_in_text = '{qr}' in template.text_template or re.search(r'\{qr=[^}]+\}', template.text_template)

        # Dynamically enable QR if found in text (for custom templates)
        if has_qr_in_text and not template.qr_enabled:
            # Create a modified template with QR enabled
            template.qr_enabled = True
            # Default to LEFT position if not set
            if not template.qr_position or template.qr_position == 'NONE':
                template.qr_position = 'LEFT'

        # Create processing context
        context = self._create_context(template, data, print_settings)

        # Process template text with placeholders
        processed_text = self._process_template_text(template.text_template, data)

        # Calculate layout dimensions
        layout = self._calculate_layout(context)

        # Generate label based on layout type
        if template.layout_type == LayoutType.TEXT_ONLY:
            return self._generate_text_only_label(context, processed_text, layout)
        elif template.layout_type == LayoutType.QR_ONLY:
            return self._generate_qr_only_label(context, layout)
        else:
            return self._generate_combined_label(context, processed_text, layout)

    def _create_context(
        self,
        template: LabelTemplateModel,
        data: Dict[str, Any],
        print_settings: PrintSettings
    ) -> ProcessingContext:
        """Create processing context with calculated dimensions"""

        # Calculate label dimensions in pixels
        label_width_px = round((template.label_width_mm / 25.4) * print_settings.dpi)
        label_height_px = round((template.label_height_mm / 25.4) * print_settings.dpi)

        return ProcessingContext(
            template=template,
            data=data,
            print_settings=print_settings,
            label_width_px=label_width_px,
            label_height_px=label_height_px,
            dpi=print_settings.dpi
        )

    def _process_template_text(self, template_text: str, data: Dict[str, Any]) -> str:
        """
        Process template text with placeholders.

        Supports placeholders like:
        - {part_name}
        - {part_number}
        - {description}
        - {qr} or {qr=field_name} (removed from text, rendered as actual QR code)
        - etc.
        """
        processed = template_text

        # Remove QR placeholders from text (they will be rendered as actual QR codes)
        # Handle {qr=field_name} pattern
        processed = re.sub(r'\{qr=[^}]+\}', '', processed)
        # Handle plain {qr} pattern
        processed = processed.replace('{qr}', '')

        # Replace placeholders with actual data
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in processed:
                processed = processed.replace(placeholder, str(value))

        # Handle common formatting
        processed = processed.replace("\\n", "\n")  # Handle newlines in templates

        return processed

    def _calculate_layout(self, context: ProcessingContext) -> LayoutDimensions:
        """Calculate layout dimensions based on template configuration"""
        template = context.template

        # Get margins from template config
        margins_config = template.layout_config.get("margins", {})
        margin_mm = template.spacing_config.get("margin_mm", 1.0)

        # Convert margins to pixels
        margin_px = round((margin_mm / 25.4) * context.dpi)
        margins = {
            "top": round(((margins_config.get("top", 1) / 25.4) * context.dpi)),
            "bottom": round(((margins_config.get("bottom", 1) / 25.4) * context.dpi)),
            "left": round(((margins_config.get("left", 1) / 25.4) * context.dpi)),
            "right": round(((margins_config.get("right", 1) / 25.4) * context.dpi))
        }

        # Calculate QR code size if enabled
        qr_size_px = 0
        qr_x = 0
        qr_y = 0

        if template.qr_enabled:
            # Calculate optimal QR size respecting minimum size requirement
            min_qr_px = round((template.qr_min_size_mm / 25.4) * context.dpi)
            max_qr_size = min(
                context.label_width_px - margins["left"] - margins["right"],
                context.label_height_px - margins["top"] - margins["bottom"]
            )
            qr_size_px = max(min_qr_px, round(max_qr_size * template.qr_scale))

            # Calculate QR position
            qr_x, qr_y = self._calculate_qr_position(
                template.qr_position,
                context.label_width_px,
                context.label_height_px,
                qr_size_px,
                margins
            )

        # Calculate text area dimensions
        text_area = self._calculate_text_area(
            context.label_width_px,
            context.label_height_px,
            qr_size_px,
            template.qr_position if template.qr_enabled else QRPosition.CENTER,
            margins,
            template.layout_config.get("spacing", {}).get("qr_text_gap", 2)
        )

        return LayoutDimensions(
            qr_size_px=qr_size_px,
            qr_x=qr_x,
            qr_y=qr_y,
            text_area_x=text_area[0],
            text_area_y=text_area[1],
            text_area_width=text_area[2],
            text_area_height=text_area[3],
            margins=margins
        )

    def _calculate_qr_position(
        self,
        position: QRPosition,
        label_width: int,
        label_height: int,
        qr_size: int,
        margins: Dict[str, int]
    ) -> Tuple[int, int]:
        """Calculate QR code position based on QRPosition enum"""

        if position == QRPosition.LEFT:
            return margins["left"], (label_height - qr_size) // 2
        elif position == QRPosition.RIGHT:
            return label_width - margins["right"] - qr_size, (label_height - qr_size) // 2
        elif position == QRPosition.TOP:
            return (label_width - qr_size) // 2, margins["top"]
        elif position == QRPosition.BOTTOM:
            return (label_width - qr_size) // 2, label_height - margins["bottom"] - qr_size
        elif position == QRPosition.TOP_LEFT:
            return margins["left"], margins["top"]
        elif position == QRPosition.TOP_RIGHT:
            return label_width - margins["right"] - qr_size, margins["top"]
        elif position == QRPosition.BOTTOM_LEFT:
            return margins["left"], label_height - margins["bottom"] - qr_size
        elif position == QRPosition.BOTTOM_RIGHT:
            return label_width - margins["right"] - qr_size, label_height - margins["bottom"] - qr_size
        else:  # CENTER
            return (label_width - qr_size) // 2, (label_height - qr_size) // 2

    def _calculate_text_area(
        self,
        label_width: int,
        label_height: int,
        qr_size: int,
        qr_position: QRPosition,
        margins: Dict[str, int],
        qr_text_gap_mm: float
    ) -> Tuple[int, int, int, int]:
        """
        Calculate available text area considering QR code position.
        Returns (x, y, width, height) of text area.
        """
        gap_px = round((qr_text_gap_mm / 25.4) * 300)  # Assuming 300 DPI for gap calculation

        if qr_size == 0:
            # No QR code, full text area
            return (
                margins["left"],
                margins["top"],
                label_width - margins["left"] - margins["right"],
                label_height - margins["top"] - margins["bottom"]
            )

        # Calculate text area based on QR position
        if qr_position == QRPosition.LEFT:
            return (
                margins["left"] + qr_size + gap_px,
                margins["top"],
                label_width - margins["left"] - margins["right"] - qr_size - gap_px,
                label_height - margins["top"] - margins["bottom"]
            )
        elif qr_position == QRPosition.RIGHT:
            return (
                margins["left"],
                margins["top"],
                label_width - margins["left"] - margins["right"] - qr_size - gap_px,
                label_height - margins["top"] - margins["bottom"]
            )
        elif qr_position == QRPosition.TOP:
            return (
                margins["left"],
                margins["top"] + qr_size + gap_px,
                label_width - margins["left"] - margins["right"],
                label_height - margins["top"] - margins["bottom"] - qr_size - gap_px
            )
        elif qr_position == QRPosition.BOTTOM:
            return (
                margins["left"],
                margins["top"],
                label_width - margins["left"] - margins["right"],
                label_height - margins["top"] - margins["bottom"] - qr_size - gap_px
            )
        else:
            # For corner positions, use remaining space more intelligently
            if qr_position in [QRPosition.TOP_LEFT, QRPosition.BOTTOM_LEFT]:
                # QR on left, text on right
                return (
                    margins["left"] + qr_size + gap_px,
                    margins["top"],
                    label_width - margins["left"] - margins["right"] - qr_size - gap_px,
                    label_height - margins["top"] - margins["bottom"]
                )
            else:  # TOP_RIGHT, BOTTOM_RIGHT
                # QR on right, text on left
                return (
                    margins["left"],
                    margins["top"],
                    label_width - margins["left"] - margins["right"] - qr_size - gap_px,
                    label_height - margins["top"] - margins["bottom"]
                )

    def generate_rotated_text_image(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        rotation: TextRotation,
        text_color: str = "black"
    ) -> Image.Image:
        """
        Generate text image with specified rotation.

        Args:
            text: Text to render
            font: Font to use
            rotation: Rotation angle (0°, 90°, 180°, 270°)
            text_color: Text color

        Returns:
            Rotated text image
        """
        # Create text image without rotation first
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Create image with some padding
        padding = 10
        img = Image.new('RGBA', (text_width + padding * 2, text_height + padding * 2), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Draw text
        draw.text((padding, padding), text, font=font, fill=text_color)

        # Apply rotation
        if rotation == TextRotation.QUARTER:  # 90°
            img = img.rotate(90, expand=True)
        elif rotation == TextRotation.HALF:  # 180°
            img = img.rotate(180, expand=True)
        elif rotation == TextRotation.THREE_QUARTER:  # 270°
            img = img.rotate(270, expand=True)
        # TextRotation.NONE (0°) needs no rotation

        return img

    def calculate_multiline_optimal_sizing(
        self,
        text: str,
        available_width: int,
        available_height: int,
        font_config: Dict[str, Any],
        enable_auto_sizing: bool = True
    ) -> Tuple[List[str], ImageFont.FreeTypeFont, int]:
        """
        Calculate optimal font size and line breaks for multi-line text.

        Returns:
            Tuple of (lines, font, line_height)
        """
        min_size = font_config.get("min_size", 8)
        max_size = font_config.get("max_size", 72)
        font_family = font_config.get("family", "DejaVu Sans")

        lines = text.split('\n')

        if not enable_auto_sizing:
            # Use a fixed size
            font_size = font_config.get("size", 12)
            font = self._get_font(font_family, font_size)
            line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
            return lines, font, line_height

        # Binary search for optimal font size
        best_font = None
        best_size = min_size

        for font_size in range(max_size, min_size - 1, -1):
            font = self._get_font(font_family, font_size)

            # Check if all lines fit within available dimensions
            line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
            total_height = len(lines) * line_height

            if total_height > available_height:
                continue

            # Check if each line fits within available width
            all_lines_fit = True
            for line in lines:
                if line.strip():  # Skip empty lines
                    bbox = font.getbbox(line)
                    line_width = bbox[2] - bbox[0]
                    if line_width > available_width:
                        all_lines_fit = False
                        break

            if all_lines_fit:
                best_font = font
                best_size = font_size
                break

        if best_font is None:
            # Fallback to minimum size
            best_font = self._get_font(font_family, min_size)
            best_size = min_size

        line_height = best_font.getbbox("Ay")[3] - best_font.getbbox("Ay")[1]
        return lines, best_font, line_height

    def process_vertical_text(
        self,
        text: str,
        available_width: int,
        available_height: int,
        font_config: Dict[str, Any]
    ) -> Image.Image:
        """
        Process vertical text layout (character-per-line: "EASY" -> "E\nA\nS\nY").

        Args:
            text: Text to process
            available_width: Available width in pixels
            available_height: Available height in pixels
            font_config: Font configuration

        Returns:
            Vertical text image
        """
        # Convert text to vertical layout
        if '\n' not in text:
            # Convert horizontal text to vertical (character per line)
            vertical_text = '\n'.join(list(text))
        else:
            vertical_text = text

        # Calculate optimal sizing for vertical layout
        lines, font, line_height = self.calculate_multiline_optimal_sizing(
            vertical_text,
            available_width,
            available_height,
            font_config,
            True
        )

        # Create vertical text image
        total_height = len(lines) * line_height
        img = Image.new('RGBA', (available_width, total_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        y_offset = 0
        for line in lines:
            if line.strip():  # Skip empty lines
                # Center text horizontally
                bbox = font.getbbox(line)
                text_width = bbox[2] - bbox[0]
                x_offset = (available_width - text_width) // 2

                draw.text((x_offset, y_offset), line, font=font, fill="black")
            y_offset += line_height

        return img

    def _get_font(self, font_family: str, size: int) -> ImageFont.FreeTypeFont:
        """Get font with fallback handling"""
        try:
            return ImageFont.truetype(font_family, size)
        except (OSError, IOError):
            try:
                # Try with .ttf extension
                return ImageFont.truetype(f"{font_family}.ttf", size)
            except (OSError, IOError):
                try:
                    # Try common font paths
                    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{font_family}.ttf", size)
                except (OSError, IOError):
                    # Fallback to default font
                    return ImageFont.load_default()

    def _generate_text_only_label(
        self,
        context: ProcessingContext,
        text: str,
        layout: LayoutDimensions
    ) -> Image.Image:
        """Generate a text-only label"""
        # Create label image
        img = Image.new('RGB', (context.label_width_px, context.label_height_px), 'white')
        draw = ImageDraw.Draw(img)

        # Calculate optimal text sizing
        lines, font, line_height = self.calculate_multiline_optimal_sizing(
            text,
            layout.text_area_width,
            layout.text_area_height,
            context.template.font_config,
            context.template.enable_auto_sizing
        )

        # Handle text rotation
        if context.template.text_rotation != TextRotation.NONE:
            text_img = self.generate_rotated_text_image(text, font, context.template.text_rotation)
            # Paste rotated text
            paste_x = layout.text_area_x + (layout.text_area_width - text_img.width) // 2
            paste_y = layout.text_area_y + (layout.text_area_height - text_img.height) // 2
            img.paste(text_img, (paste_x, paste_y), text_img)
        else:
            # Draw multi-line text
            y_offset = layout.text_area_y
            for line in lines:
                if line.strip():
                    # Apply text alignment
                    bbox = font.getbbox(line)
                    text_width = bbox[2] - bbox[0]

                    if context.template.text_alignment == TextAlignment.CENTER:
                        x_offset = layout.text_area_x + (layout.text_area_width - text_width) // 2
                    elif context.template.text_alignment == TextAlignment.RIGHT:
                        x_offset = layout.text_area_x + layout.text_area_width - text_width
                    else:  # LEFT
                        x_offset = layout.text_area_x

                    draw.text((x_offset, y_offset), line, font=font, fill="black")
                y_offset += line_height

        return img

    def _generate_qr_only_label(
        self,
        context: ProcessingContext,
        layout: LayoutDimensions
    ) -> Image.Image:
        """Generate a QR-only label"""
        # Create label image
        img = Image.new('RGB', (context.label_width_px, context.label_height_px), 'white')

        # Generate QR code
        qr_data = self._get_qr_data(context.data, context.template.text_template)
        qr_img = self._generate_qr_image(qr_data, layout.qr_size_px)

        # Paste QR code
        img.paste(qr_img, (layout.qr_x, layout.qr_y))

        return img

    def _generate_combined_label(
        self,
        context: ProcessingContext,
        text: str,
        layout: LayoutDimensions
    ) -> Image.Image:
        """Generate a combined QR + text label"""
        # Create label image
        img = Image.new('RGB', (context.label_width_px, context.label_height_px), 'white')
        draw = ImageDraw.Draw(img)

        # Generate and paste QR code if enabled
        if context.template.qr_enabled:
            qr_data = self._get_qr_data(context.data, context.template.text_template)
            qr_img = self._generate_qr_image(qr_data, layout.qr_size_px)
            img.paste(qr_img, (layout.qr_x, layout.qr_y))

        # Generate and paste text
        if text.strip():
            if context.template.supports_vertical_text and '\n' not in text and len(text) > 1:
                # Use vertical text processing
                text_img = self.process_vertical_text(
                    text,
                    layout.text_area_width,
                    layout.text_area_height,
                    context.template.font_config
                )
                paste_x = layout.text_area_x + (layout.text_area_width - text_img.width) // 2
                paste_y = layout.text_area_y + (layout.text_area_height - text_img.height) // 2
                img.paste(text_img, (paste_x, paste_y), text_img)

            elif context.template.text_rotation != TextRotation.NONE:
                # Use rotated text
                lines, font, _ = self.calculate_multiline_optimal_sizing(
                    text,
                    layout.text_area_width,
                    layout.text_area_height,
                    context.template.font_config,
                    context.template.enable_auto_sizing
                )
                text_img = self.generate_rotated_text_image('\n'.join(lines), font, context.template.text_rotation)
                paste_x = layout.text_area_x + (layout.text_area_width - text_img.width) // 2
                paste_y = layout.text_area_y + (layout.text_area_height - text_img.height) // 2
                img.paste(text_img, (paste_x, paste_y), text_img)

            else:
                # Use standard multi-line text
                lines, font, line_height = self.calculate_multiline_optimal_sizing(
                    text,
                    layout.text_area_width,
                    layout.text_area_height,
                    context.template.font_config,
                    context.template.enable_auto_sizing
                )

                y_offset = layout.text_area_y
                for line in lines:
                    if line.strip():
                        bbox = font.getbbox(line)
                        text_width = bbox[2] - bbox[0]

                        if context.template.text_alignment == TextAlignment.CENTER:
                            x_offset = layout.text_area_x + (layout.text_area_width - text_width) // 2
                        elif context.template.text_alignment == TextAlignment.RIGHT:
                            x_offset = layout.text_area_x + layout.text_area_width - text_width
                        else:  # LEFT
                            x_offset = layout.text_area_x

                        draw.text((x_offset, y_offset), line, font=font, fill="black")
                    y_offset += line_height

        return img

    def _get_qr_data(self, data: Dict[str, Any], template_text: str = '') -> str:
        """
        Generate QR code data from context data.
        Returns MM:id format by default (MakerMatrix ID format).
        Supports {qr=field_name} syntax to use specific field.
        """
        # Check if template specifies which field to use for QR
        qr_field_match = re.search(r'\{qr=([^}]+)\}', template_text)
        if qr_field_match:
            field_name = qr_field_match.group(1)
            if field_name in data:
                return str(data[field_name])
            else:
                return field_name  # Return the field name if not in data

        # Default: Prefer ID for QR code in MM:id format
        if 'id' in data:
            return f"MM:{data['id']}"
        elif 'part_id' in data:
            return f"MM:{data['part_id']}"
        elif 'part_number' in data:
            return str(data['part_number'])
        elif 'location_id' in data:
            return str(data['location_id'])
        else:
            # Use first available data value
            return str(next(iter(data.values()))) if data else "DEFAULT_QR"

    def _generate_qr_image(self, data: str, size_px: int) -> Image.Image:
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Resize to exact pixel size
        qr_img = qr_img.resize((size_px, size_px), Image.Resampling.NEAREST)

        return qr_img