"""
Font Management Service

Manages bundled and system fonts for label printing and emoji rendering.
Provides APIs for listing, selecting, and configuring fonts.
"""

from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
import os


# Get bundled fonts directory
FONTS_DIR = Path(__file__).parent.parent.parent / "fonts"


@dataclass
class FontInfo:
    """Information about an available font"""

    name: str
    path: str
    is_bundled: bool
    supports_emoji: bool
    file_size_kb: int
    description: str


class FontService:
    """Service for managing fonts used in label printing"""

    @staticmethod
    def get_bundled_fonts_dir() -> Path:
        """Get the path to the bundled fonts directory."""
        return FONTS_DIR

    @staticmethod
    def list_bundled_fonts() -> List[FontInfo]:
        """List all bundled fonts in the repo."""
        fonts = []

        if not FONTS_DIR.exists():
            return fonts

        font_files = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))

        for font_file in font_files:
            size_kb = os.path.getsize(font_file) // 1024

            # Determine font characteristics based on filename
            name = font_file.stem
            supports_emoji = "emoji" in name.lower() or "color" in name.lower()

            description = FontService._get_font_description(name)

            fonts.append(
                FontInfo(
                    name=name,
                    path=str(font_file),
                    is_bundled=True,
                    supports_emoji=supports_emoji,
                    file_size_kb=size_kb,
                    description=description,
                )
            )

        return fonts

    @staticmethod
    def list_system_fonts() -> List[FontInfo]:
        """List available system fonts (for reference/fallback)."""
        fonts = []

        # Common system font paths
        system_font_paths = [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Apple Color Emoji.ttc",
        ]

        for font_path in system_font_paths:
            if os.path.exists(font_path):
                path_obj = Path(font_path)
                name = path_obj.stem
                size_kb = os.path.getsize(font_path) // 1024
                supports_emoji = "emoji" in name.lower() or "color" in name.lower()

                fonts.append(
                    FontInfo(
                        name=name,
                        path=font_path,
                        is_bundled=False,
                        supports_emoji=supports_emoji,
                        file_size_kb=size_kb,
                        description=f"System font: {name}",
                    )
                )

        return fonts

    @staticmethod
    def get_all_fonts() -> List[FontInfo]:
        """Get all available fonts (bundled + system)."""
        bundled = FontService.list_bundled_fonts()
        system = FontService.list_system_fonts()
        return bundled + system

    @staticmethod
    def get_preferred_emoji_font() -> Optional[str]:
        """Get the preferred emoji font path (bundled first, then system)."""
        # Try bundled emoji font first
        bundled_emoji = FONTS_DIR / "NotoColorEmoji.ttf"
        if bundled_emoji.exists():
            return str(bundled_emoji)

        # Fall back to system emoji fonts
        system_fonts = [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/System/Library/Fonts/Apple Color Emoji.ttc",
        ]

        for font_path in system_fonts:
            if os.path.exists(font_path):
                return font_path

        return None

    @staticmethod
    def get_preferred_text_font() -> Optional[str]:
        """Get the preferred text font path for labels."""
        # Try bundled font first
        bundled_arial = FONTS_DIR / "arial.ttf"
        if bundled_arial.exists():
            return str(bundled_arial)

        # Fall back to system fonts
        system_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]

        for font_path in system_fonts:
            if os.path.exists(font_path):
                return font_path

        return None

    @staticmethod
    def _get_font_description(font_name: str) -> str:
        """Get a human-readable description for a font."""
        descriptions = {
            "NotoColorEmoji": "Google Noto Color Emoji - Full emoji support",
            "arial": "Arial - Standard sans-serif font",
            "DejaVuSans": "DejaVu Sans - Open source sans-serif",
            "LiberationSans": "Liberation Sans - Open source sans-serif",
        }

        return descriptions.get(font_name, f"Font: {font_name}")

    @staticmethod
    def validate_font_path(font_path: str) -> bool:
        """Validate that a font file exists and is readable."""
        try:
            path = Path(font_path)
            return path.exists() and path.is_file() and path.suffix in [".ttf", ".otf", ".ttc"]
        except:
            return False
