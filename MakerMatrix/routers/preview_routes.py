"""
Preview routes for generating label previews without printing.
"""
import base64
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.printer.preview_service import PreviewService, PreviewManager
from MakerMatrix.printers.drivers.mock.driver import MockPrinter
from MakerMatrix.printers.drivers.brother_ql.driver import BrotherQLModern
from MakerMatrix.models.models import engine
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.routers.base import BaseRouter, standard_error_handling


router = APIRouter(tags=["Label Preview"])
base_router = BaseRouter()


class PreviewResponse(BaseModel):
    """Response model for preview operations."""
    success: bool
    preview_data: Optional[str] = None  # Base64 encoded image
    format: Optional[str] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class TextPreviewRequest(BaseModel):
    """Request model for text preview."""
    text: str
    label_size: str = "12"
    printer_id: Optional[str] = None


# Global preview manager instance
preview_manager = PreviewManager()

# Initialize with default printers
def get_preview_manager():
    """Get or initialize the preview manager."""
    if not preview_manager.get_registered_printers():
        # Register mock printer for testing
        mock_printer = MockPrinter(
            printer_id="mock_preview",
            name="Mock Preview Printer",
            model="MockQL-800",
            backend="mock",
            identifier="mock://preview"
        )
        preview_manager.register_printer("mock_preview", mock_printer)
        
        # Register Brother QL printer if configured
        try:
            brother_ql = BrotherQLModern(
                printer_id="brother_ql_preview",
                name="Brother QL Preview",
                model="QL-800",
                backend="network",
                identifier="tcp://192.168.1.100:9100"
            )
            preview_manager.register_printer("brother_ql_preview", brother_ql)
        except Exception:
            # Brother QL not available, use mock only
            pass
    
    return preview_manager


@router.get("/printers")
@standard_error_handling
async def get_available_printers() -> ResponseSchema[Dict[str, Any]]:
    """Get list of available printers for preview."""
    manager = get_preview_manager()
    data = {
        "printers": manager.get_registered_printers(),
        "default": "mock_preview" if "mock_preview" in manager.get_registered_printers() else None
    }
    return base_router.build_success_response(
        data=data,
        message="Available printers retrieved successfully"
    )


@router.get("/labels/sizes")
@standard_error_handling
async def get_label_sizes(printer_id: Optional[str] = None) -> ResponseSchema[Dict[str, Any]]:
    """Get available label sizes for preview."""
    manager = get_preview_manager()
    service = manager.get_preview_service(printer_id)
    sizes = service.get_available_label_sizes()
    
    data = {
        "sizes": [
            {
                "name": size.name,
                "width_mm": size.width_mm,
                "height_mm": size.height_mm,
                "width_px": size.width_px,
                "height_px": size.height_px,
                "is_continuous": size.is_continuous()
            }
            for size in sizes
        ]
    }
    
    return base_router.build_success_response(
        data=data,
        message="Available label sizes retrieved successfully"
    )


@router.post("/part/qr_code/{part_id}", response_model=PreviewResponse)
@standard_error_handling
async def preview_part_qr_code(part_id: str, label_size: str = "12", printer_id: Optional[str] = None):
    """Generate preview of a part QR code label."""
    # Get part from database
    with engine.begin() as session:
        part = PartRepository.get_part_by_id(session, part_id)
        if not part:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")
    
    # Generate preview
    manager = get_preview_manager()
    service = manager.get_preview_service(printer_id)
    
    result = await service.preview_part_qr_code(part, label_size)
    
    # Encode image data as base64
    preview_data = base64.b64encode(result.image_data).decode('utf-8')
    
    return PreviewResponse(
        success=True,
        preview_data=preview_data,
        format=result.format,
        width_px=result.width_px,
        height_px=result.height_px,
        message=result.message
    )


@router.post("/part/name/{part_id}", response_model=PreviewResponse)
@standard_error_handling
async def preview_part_name(part_id: str, label_size: str = "12", printer_id: Optional[str] = None):
    """Generate preview of a part name label."""
    # Get part from database
    with engine.begin() as session:
        part = PartRepository.get_part_by_id(session, part_id)
        if not part:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")
    
    # Generate preview
    manager = get_preview_manager()
    service = manager.get_preview_service(printer_id)
    
    result = await service.preview_part_name(part, label_size)
    
    # Encode image data as base64
    preview_data = base64.b64encode(result.image_data).decode('utf-8')
    
    return PreviewResponse(
        success=True,
        preview_data=preview_data,
        format=result.format,
        width_px=result.width_px,
        height_px=result.height_px,
        message=result.message
    )


@router.post("/text", response_model=PreviewResponse)
@standard_error_handling
async def preview_text_label(request: TextPreviewRequest):
    """Generate preview of a custom text label."""
    # Generate preview
    manager = get_preview_manager()
    service = manager.get_preview_service(request.printer_id)
    
    result = await service.preview_text_label(request.text, request.label_size)
    
    # Encode image data as base64
    preview_data = base64.b64encode(result.image_data).decode('utf-8')
    
    return PreviewResponse(
        success=True,
        preview_data=preview_data,
        format=result.format,
        width_px=result.width_px,
        height_px=result.height_px,
        message=result.message
    )


@router.post("/part/combined/{part_id}", response_model=PreviewResponse)
@standard_error_handling
async def preview_combined_label(part_id: str, custom_text: Optional[str] = None, 
                                 label_size: str = "12", printer_id: Optional[str] = None):
    """Generate preview of a combined QR code + text label."""
    # Get part from database
    with engine.begin() as session:
        part = PartRepository.get_part_by_id(session, part_id)
        if not part:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")
    
    # Generate preview
    manager = get_preview_manager()
    service = manager.get_preview_service(printer_id)
    
    result = await service.preview_combined_label(part, custom_text, label_size)
    
    # Encode image data as base64
    preview_data = base64.b64encode(result.image_data).decode('utf-8')
    
    return PreviewResponse(
        success=True,
        preview_data=preview_data,
        format=result.format,
        width_px=result.width_px,
        height_px=result.height_px,
        message=result.message
    )


@router.get("/validate/size/{label_size}")
@standard_error_handling
async def validate_label_size(label_size: str, printer_id: Optional[str] = None) -> ResponseSchema[Dict[str, Any]]:
    """Validate if a label size is supported."""
    manager = get_preview_manager()
    service = manager.get_preview_service(printer_id)
    
    is_valid = service.validate_label_size(label_size)
    sizes = service.get_available_label_sizes()
    
    data = {
        "valid": is_valid,
        "label_size": label_size,
        "supported_sizes": [size.name for size in sizes]
    }
    
    return base_router.build_success_response(
        data=data,
        message="Label size validation completed"
    )