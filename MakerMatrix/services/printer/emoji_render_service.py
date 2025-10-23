"""
Emoji Render Service

Printer-agnostic service for converting emoji characters to raster images.
Uses bundled emoji fonts for cross-platform compatibility.

This service is designed to work with any printer driver that accepts PIL Images.
"""

from typing import Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import emoji as emoji_lib

# Get bundled fonts directory
FONTS_DIR = Path(__file__).parent.parent.parent / "fonts"


class EmojiRenderService:
    """Service for rendering emoji characters as PIL Images"""

    @staticmethod
    def render_emoji(
        emoji_char: str, size_px: int = 100, background_color: str = "white", convert_shortcode: bool = True
    ) -> Image.Image:
        """
        Render an emoji character as a PIL Image using Twemoji SVG assets.

        Uses Twitter's open source Twemoji graphics for consistent cross-platform emoji rendering.

        Args:
            emoji_char: Unicode emoji (e.g., '🔩') or shortcode (e.g., ':screw:')
            size_px: Desired size in pixels (square image)
            background_color: Background color for the image
            convert_shortcode: If True, convert emoji shortcodes to Unicode

        Returns:
            PIL Image containing the rendered emoji

        Raises:
            ValueError: If emoji_char is empty or invalid
        """
        if not emoji_char or not emoji_char.strip():
            raise ValueError("Emoji character cannot be empty")

        # Convert shortcode to Unicode if needed
        if convert_shortcode and emoji_char.startswith(":") and emoji_char.endswith(":"):
            emoji_char = emoji_lib.emojize(emoji_char, language="alias")

        # Try to fetch emoji from Twemoji CDN
        try:
            import requests
            from io import BytesIO

            # Get Unicode codepoint in hex format
            codepoint = "-".join(f"{ord(c):x}" for c in emoji_char)
            twemoji_url = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/{codepoint}.png"

            print(f"[DEBUG] EmojiRenderService: Fetching Twemoji for '{emoji_char}' from {twemoji_url}")

            response = requests.get(twemoji_url, timeout=3)
            if response.status_code == 200:
                # Load the emoji image
                emoji_img = Image.open(BytesIO(response.content))

                # Resize to requested size
                emoji_img = emoji_img.resize((size_px, size_px), Image.Resampling.LANCZOS)

                # Convert to RGBA to preserve transparency
                if emoji_img.mode != "RGBA":
                    emoji_img = emoji_img.convert("RGBA")

                # Extract the alpha channel (transparency)
                r, g, b, alpha = emoji_img.split()

                # Convert RGB to grayscale
                gray = emoji_img.convert("L")

                # Apply contrast enhancement to make light grays darker
                # This prevents light areas from appearing white on thermal printers
                # Thermal printers use threshold ~70/255, so we need to push grays below this
                from PIL import ImageEnhance

                enhancer = ImageEnhance.Contrast(gray)
                gray = enhancer.enhance(1.5)  # Increase contrast by 50%

                # Apply brightness adjustment to darken overall
                brightness = ImageEnhance.Brightness(gray)
                gray = brightness.enhance(0.6)  # Darken by 40% (pushes light grays below printer threshold)

                # Create a new RGBA image with adjusted grayscale + original alpha
                bw_emoji = Image.merge("RGBA", (gray, gray, gray, alpha))

                # Create white background
                bg = Image.new("RGB", (size_px, size_px), background_color)

                # Paste the B&W emoji with transparency
                bg.paste(bw_emoji, (0, 0), bw_emoji)

                print(f"[DEBUG] EmojiRenderService: Successfully loaded Twemoji (B&W, enhanced) for '{emoji_char}'")
                return bg
            else:
                print(
                    f"[WARN] EmojiRenderService: Twemoji not found (HTTP {response.status_code}), falling back to text rendering"
                )
        except Exception as e:
            print(f"[WARN] EmojiRenderService: Failed to fetch Twemoji: {e}, falling back to text rendering")

        # Fallback: render as text with border (original behavior)
        img = Image.new("RGB", (size_px, size_px), "white")
        draw = ImageDraw.Draw(img)

        # Draw a simple bordered box to make it visible
        border_width = max(2, size_px // 20)
        draw.rectangle(
            [border_width, border_width, size_px - border_width, size_px - border_width],
            outline="black",
            width=border_width,
        )

        # Try to render the emoji with available fonts
        font_size = int(size_px * 0.6)

        # Try bundled fonts first
        font_paths = [
            str(FONTS_DIR / "arial.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"[DEBUG] EmojiRenderService: Loaded fallback font: {font_path}")
                break
            except (OSError, IOError):
                continue

        if font is None:
            print(f"[WARN] EmojiRenderService: No TrueType fonts available, using default")
            font = ImageFont.load_default()

        # Render emoji as text
        try:
            bbox = draw.textbbox((0, 0), emoji_char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (size_px - text_width) // 2
            y = (size_px - text_height) // 2
            draw.text((x, y), emoji_char, font=font, fill="black")
            print(f"[DEBUG] EmojiRenderService: Rendered emoji '{emoji_char}' as text fallback")
        except Exception as e:
            print(f"[ERROR] EmojiRenderService: Failed to render emoji: {e}")
            draw.text((size_px // 4, size_px // 3), emoji_char, font=font, fill="black")

        return img

    @staticmethod
    def render_emoji_with_auto_size(
        emoji_char: str,
        max_width: int,
        max_height: int,
        background_color: str = "white",
        convert_shortcode: bool = True,
    ) -> Image.Image:
        """
        Render an emoji with automatic sizing to fit within specified dimensions.

        Args:
            emoji_char: Unicode emoji or shortcode
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            background_color: Background color for the image
            convert_shortcode: If True, convert emoji shortcodes to Unicode

        Returns:
            PIL Image containing the rendered emoji, sized to fit

        Raises:
            ValueError: If emoji_char is empty or invalid
        """
        # Use the smaller dimension to ensure the emoji fits
        size = min(max_width, max_height)
        return EmojiRenderService.render_emoji(
            emoji_char, size_px=size, background_color=background_color, convert_shortcode=convert_shortcode
        )

    @staticmethod
    def is_emoji(text: str) -> bool:
        """
        Check if a string contains emoji characters.

        Args:
            text: String to check

        Returns:
            True if the string contains at least one emoji character
        """
        if not text:
            return False

        # Check for Unicode emoji using the emoji library
        try:
            return emoji_lib.is_emoji(text) or bool(emoji_lib.emoji_count(text))
        except:
            # Fallback: check for emoji shortcodes
            if text.startswith(":") and text.endswith(":"):
                return True
            return False

    @staticmethod
    def validate_emoji(emoji_char: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an emoji character or shortcode.

        Args:
            emoji_char: Unicode emoji or shortcode to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
        """
        if not emoji_char or not emoji_char.strip():
            return False, "Emoji character cannot be empty"

        # Check if it's a valid shortcode
        if emoji_char.startswith(":") and emoji_char.endswith(":"):
            converted = emoji_lib.emojize(emoji_char, language="alias")
            if converted == emoji_char:
                return False, f"Invalid emoji shortcode: {emoji_char}"
            return True, None

        # Check if it's a valid Unicode emoji
        if EmojiRenderService.is_emoji(emoji_char):
            return True, None

        return False, f"Invalid emoji: {emoji_char}"
