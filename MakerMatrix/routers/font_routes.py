"""
Font Management API Routes

Provides endpoints for listing and managing fonts used in label printing.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel

from MakerMatrix.services.printer.font_service import FontService, FontInfo
from MakerMatrix.routers.base import ResponseSchema


router = APIRouter(prefix="/fonts", tags=["fonts"])


class FontInfoResponse(BaseModel):
    """Font information response model"""
    name: str
    path: str
    is_bundled: bool
    supports_emoji: bool
    file_size_kb: int
    description: str


@router.get("/list", response_model=ResponseSchema)
async def list_fonts(bundled_only: bool = False):
    """
    List available fonts for label printing.

    Args:
        bundled_only: If True, only return bundled fonts (default: False)

    Returns:
        List of available fonts with metadata
    """
    try:
        if bundled_only:
            fonts = FontService.list_bundled_fonts()
        else:
            fonts = FontService.get_all_fonts()

        # Convert to response format
        font_data = [
            {
                "name": font.name,
                "path": font.path,
                "is_bundled": font.is_bundled,
                "supports_emoji": font.supports_emoji,
                "file_size_kb": font.file_size_kb,
                "description": font.description
            }
            for font in fonts
        ]

        return ResponseSchema(
            status="success",
            message=f"Found {len(font_data)} font(s)",
            data=font_data
        )

    except Exception as e:
        return ResponseSchema(
            status="error",
            message=f"Failed to list fonts: {str(e)}",
            data=None
        )


@router.get("/bundled", response_model=ResponseSchema)
async def list_bundled_fonts():
    """
    List only bundled fonts (guaranteed cross-platform).

    Returns:
        List of bundled fonts in the repository
    """
    try:
        fonts = FontService.list_bundled_fonts()

        font_data = [
            {
                "name": font.name,
                "path": font.path,
                "is_bundled": font.is_bundled,
                "supports_emoji": font.supports_emoji,
                "file_size_kb": font.file_size_kb,
                "description": font.description
            }
            for font in fonts
        ]

        return ResponseSchema(
            status="success",
            message=f"Found {len(font_data)} bundled font(s)",
            data=font_data
        )

    except Exception as e:
        return ResponseSchema(
            status="error",
            message=f"Failed to list bundled fonts: {str(e)}",
            data=None
        )


@router.get("/system", response_model=ResponseSchema)
async def list_system_fonts():
    """
    List available system fonts (for reference).

    Returns:
        List of system fonts detected on this machine
    """
    try:
        fonts = FontService.list_system_fonts()

        font_data = [
            {
                "name": font.name,
                "path": font.path,
                "is_bundled": font.is_bundled,
                "supports_emoji": font.supports_emoji,
                "file_size_kb": font.file_size_kb,
                "description": font.description
            }
            for font in fonts
        ]

        return ResponseSchema(
            status="success",
            message=f"Found {len(font_data)} system font(s)",
            data=font_data
        )

    except Exception as e:
        return ResponseSchema(
            status="error",
            message=f"Failed to list system fonts: {str(e)}",
            data=None
        )


@router.get("/preferred/emoji", response_model=ResponseSchema)
async def get_preferred_emoji_font():
    """
    Get the preferred emoji font path.

    Returns:
        Path to the best available emoji font (bundled first, then system)
    """
    try:
        font_path = FontService.get_preferred_emoji_font()

        if not font_path:
            return ResponseSchema(
                status="warning",
                message="No emoji font available",
                data=None
            )

        return ResponseSchema(
            status="success",
            message="Preferred emoji font found",
            data={"path": font_path}
        )

    except Exception as e:
        return ResponseSchema(
            status="error",
            message=f"Failed to get preferred emoji font: {str(e)}",
            data=None
        )


@router.get("/preferred/text", response_model=ResponseSchema)
async def get_preferred_text_font():
    """
    Get the preferred text font path for labels.

    Returns:
        Path to the best available text font (bundled first, then system)
    """
    try:
        font_path = FontService.get_preferred_text_font()

        if not font_path:
            return ResponseSchema(
                status="warning",
                message="No text font available",
                data=None
            )

        return ResponseSchema(
            status="success",
            message="Preferred text font found",
            data={"path": font_path}
        )

    except Exception as e:
        return ResponseSchema(
            status="error",
            message=f"Failed to get preferred text font: {str(e)}",
            data=None
        )


@router.get("/validate/{font_name}", response_model=ResponseSchema)
async def validate_font(font_name: str):
    """
    Validate that a font exists and is usable.

    Args:
        font_name: Name of the font to validate

    Returns:
        Validation status and font path if valid
    """
    try:
        # Check bundled fonts first
        bundled_fonts = FontService.list_bundled_fonts()
        for font in bundled_fonts:
            if font.name.lower() == font_name.lower():
                is_valid = FontService.validate_font_path(font.path)
                return ResponseSchema(
                    status="success" if is_valid else "error",
                    message="Font is valid" if is_valid else "Font file not readable",
                    data={"path": font.path, "valid": is_valid}
                )

        return ResponseSchema(
            status="error",
            message=f"Font '{font_name}' not found",
            data=None
        )

    except Exception as e:
        return ResponseSchema(
            status="error",
            message=f"Failed to validate font: {str(e)}",
            data=None
        )
