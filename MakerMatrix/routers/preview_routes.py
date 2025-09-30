"""
Preview routes for generating label previews without printing.
"""
import base64
import re
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


class AdvancedPreviewOptions(BaseModel):
    """Options for advanced preview."""
    fit_to_label: bool = True
    include_qr: bool = False
    qr_data: Optional[str] = None


class AdvancedPreviewRequest(BaseModel):
    """Request model for advanced preview."""
    template: str
    text: str
    label_size: str = "12"
    label_length: Optional[int] = None
    options: AdvancedPreviewOptions = AdvancedPreviewOptions()
    data: Optional[Dict[str, Any]] = None
    printer_id: Optional[str] = None


# Global preview manager instance
preview_manager = PreviewManager()

# Initialize with default printers
def get_preview_manager():
    """Get or initialize the preview manager."""
    try:
        print(f"[DEBUG] get_preview_manager called, registered printers: {preview_manager.get_registered_printers()}")

        if not preview_manager.get_registered_printers():
            print(f"[DEBUG] No printers registered, initializing default printers...")

            # Register mock printer for testing
            try:
                print(f"[DEBUG] Creating mock printer...")
                mock_printer = MockPrinter(
                    printer_id="mock_preview",
                    name="Mock Preview Printer",
                    model="MockQL-800",
                    backend="mock",
                    identifier="mock://preview"
                )
                print(f"[DEBUG] Mock printer created, registering...")
                preview_manager.register_printer("mock_preview", mock_printer)
                print(f"[DEBUG] Mock printer registered successfully")
            except Exception as e:
                print(f"[ERROR] Failed to register mock printer: {e}")
                import traceback
                traceback.print_exc()
                raise Exception(f"Failed to initialize mock printer: {str(e)}")

            # Register Brother QL printer if configured
            try:
                print(f"[DEBUG] Attempting to register Brother QL printer...")
                brother_ql = BrotherQLModern(
                    printer_id="brother_ql_preview",
                    name="Brother QL Preview",
                    model="QL-800",
                    backend="network",
                    identifier="tcp://192.168.1.100:9100"
                )
                preview_manager.register_printer("brother_ql_preview", brother_ql)
                print(f"[DEBUG] Brother QL printer registered successfully")
            except Exception as e:
                # Brother QL not available, use mock only
                print(f"[DEBUG] Brother QL not available, using mock only: {e}")
                pass

        print(f"[DEBUG] Preview manager ready with {len(preview_manager.get_registered_printers())} printers")
        return preview_manager

    except Exception as e:
        print(f"[ERROR] Fatal error in get_preview_manager: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Preview manager initialization failed: {str(e)}")


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


@router.get("/health")
@standard_error_handling
async def preview_system_health() -> ResponseSchema[Dict[str, Any]]:
    """Health check endpoint for the preview system."""
    health_data = {
        "status": "unknown",
        "preview_manager": "not_initialized",
        "registered_printers": [],
        "dependencies": {
            "pil": "not_checked",
            "fonts": "not_checked"
        },
        "errors": []
    }

    try:
        # Check preview manager initialization
        print(f"[DEBUG] Health check: Testing preview manager initialization")
        manager = get_preview_manager()
        health_data["preview_manager"] = "initialized"
        health_data["registered_printers"] = manager.get_registered_printers()
        print(f"[DEBUG] Health check: Preview manager OK, printers: {health_data['registered_printers']}")

        # Check PIL dependency
        try:
            from PIL import Image, ImageDraw, ImageFont
            health_data["dependencies"]["pil"] = "available"
            print(f"[DEBUG] Health check: PIL available")
        except ImportError as e:
            health_data["dependencies"]["pil"] = "missing"
            health_data["errors"].append(f"PIL import failed: {str(e)}")
            print(f"[ERROR] Health check: PIL missing: {e}")

        # Check font availability
        try:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]

            fonts_found = []
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, 12)
                    fonts_found.append(font_path)
                except:
                    continue

            # Try default font as fallback
            try:
                default_font = ImageFont.load_default()
                fonts_found.append("default_font")
            except:
                pass

            if fonts_found:
                health_data["dependencies"]["fonts"] = f"available ({len(fonts_found)} found)"
                health_data["available_fonts"] = fonts_found
                print(f"[DEBUG] Health check: Fonts available: {fonts_found}")
            else:
                health_data["dependencies"]["fonts"] = "none_available"
                health_data["errors"].append("No fonts available for text rendering")
                print(f"[ERROR] Health check: No fonts available")

        except Exception as e:
            health_data["dependencies"]["fonts"] = "error"
            health_data["errors"].append(f"Font check failed: {str(e)}")
            print(f"[ERROR] Health check: Font check failed: {e}")

        # Test basic preview generation if possible
        if health_data["registered_printers"]:
            try:
                print(f"[DEBUG] Health check: Testing basic preview generation")
                service = manager.get_preview_service()

                # Create a simple test image
                test_image = Image.new('RGB', (100, 50), 'white')
                draw = ImageDraw.Draw(test_image)
                draw.text((10, 10), "TEST", fill='black')

                # Try to generate preview
                result = await service.preview_text_label("Test", "12")
                health_data["test_preview"] = {
                    "status": "success",
                    "image_size": f"{result.width_px}x{result.height_px}",
                    "format": result.format
                }
                print(f"[DEBUG] Health check: Preview generation successful")

            except Exception as e:
                health_data["test_preview"] = {
                    "status": "failed",
                    "error": str(e)
                }
                health_data["errors"].append(f"Preview generation test failed: {str(e)}")
                print(f"[ERROR] Health check: Preview generation failed: {e}")

        # Determine overall status
        if not health_data["errors"]:
            health_data["status"] = "healthy"
        elif health_data["preview_manager"] == "initialized" and health_data["dependencies"]["pil"] == "available":
            health_data["status"] = "degraded"
        else:
            health_data["status"] = "unhealthy"

        print(f"[DEBUG] Health check completed: {health_data['status']}")

    except Exception as e:
        health_data["status"] = "error"
        health_data["errors"].append(f"Health check failed: {str(e)}")
        print(f"[ERROR] Health check: Unexpected error: {e}")
        import traceback
        traceback.print_exc()

    return base_router.build_success_response(
        data=health_data,
        message=f"Preview system health check completed - Status: {health_data['status']}"
    )


@router.post("/advanced", response_model=PreviewResponse)
@standard_error_handling
async def preview_advanced_label(request: AdvancedPreviewRequest):
    """Generate preview of an advanced label with template processing."""
    try:
        print(f"[DEBUG] Received preview_advanced_label request: {request}")
        print(f"[DEBUG] Request template: {request.template}")
        print(f"[DEBUG] Request options: {request.options}")
        print(f"[DEBUG] Request printer_id: {request.printer_id}")

        # Initialize preview manager with comprehensive error handling
        print(f"[DEBUG] Initializing preview manager...")
        try:
            manager = get_preview_manager()
            print(f"[DEBUG] Preview manager initialized successfully")
            print(f"[DEBUG] Registered printers: {manager.get_registered_printers()}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize preview manager: {e}")
            import traceback
            traceback.print_exc()
            return PreviewResponse(
                success=False,
                error=f"Preview system initialization failed: {str(e)}",
                message="Failed to initialize preview system"
            )

        # Get preview service with error handling
        print(f"[DEBUG] Getting preview service for printer_id: {request.printer_id}")
        try:
            service = manager.get_preview_service(request.printer_id)
            print(f"[DEBUG] Preview service obtained successfully")
        except Exception as e:
            print(f"[ERROR] Failed to get preview service: {e}")
            return PreviewResponse(
                success=False,
                error=f"No preview service available: {str(e)}",
                message="Preview service not available"
            )

        # Process template with data
        print(f"[DEBUG] Processing template...")
        processed_text = request.template

        # Check if template contains {qr} placeholder (auto-enable QR)
        has_qr_placeholder = '{qr}' in processed_text or re.search(r'\{qr=[^}]+\}', processed_text)
        print(f"[DEBUG] Template has QR placeholder: {has_qr_placeholder}")

        # Extract QR field name if specified (e.g., {qr=description})
        qr_field = None
        qr_field_match = re.search(r'\{qr=([^}]+)\}', processed_text)
        if qr_field_match:
            qr_field = qr_field_match.group(1)
            print(f"[DEBUG] QR field specified: {qr_field}")

        # Remove QR placeholders from text (they will be rendered as actual QR codes)
        if has_qr_placeholder:
            processed_text = re.sub(r'\{qr=[^}]+\}', '', processed_text)
            processed_text = processed_text.replace('{qr}', '')

        if request.data:
            print(f"[DEBUG] Applying template data: {request.data}")
            for key, value in request.data.items():
                processed_text = processed_text.replace(f"{{{key}}}", str(value))
        print(f"[DEBUG] Processed text: {processed_text}")

        # Check if QR code is requested (via option or {qr} placeholder)
        include_qr = (request.options.include_qr if request.options else False) or has_qr_placeholder
        print(f"[DEBUG] Include QR code: {include_qr} (option: {request.options.include_qr if request.options else False}, placeholder: {has_qr_placeholder})")

        # Generate preview based on whether QR is requested
        print(f"[DEBUG] Generating preview with label_size: {request.label_size}")
        try:
            if include_qr:
                # For QR + text, use the existing combined label method
                print(f"[DEBUG] Using existing preview_combined_label method for QR + text")

                # Generate QR code data based on specified field or default
                if qr_field:
                    # User specified a field like {qr=description}
                    if qr_field not in request.data:
                        return PreviewResponse(
                            success=False,
                            error=f"Field '{qr_field}' not found in data. Available fields: {', '.join(request.data.keys())}",
                            message=f"QR field '{qr_field}' does not exist in part data"
                        )
                    qr_data = str(request.data[qr_field])
                    print(f"[DEBUG] Using custom QR field '{qr_field}': {qr_data}")

                    # Check QR data size constraints (11mm x 11mm QR code)
                    # At 300 DPI, 11mm = ~130 pixels
                    # QR code capacity: ~2953 chars (version 40, error correction L)
                    # But for 11mm practical limit is much lower (~100-200 chars max for reliable scanning)
                    max_qr_length = 200
                    if len(qr_data) > max_qr_length:
                        return PreviewResponse(
                            success=False,
                            error=f"QR data too long: {len(qr_data)} characters (max {max_qr_length} for 11mm QR code)",
                            message=f"QR code data exceeds size limit for 11mm label"
                        )
                else:
                    # Default to MM:id format
                    part_id = request.data.get('id') or request.data.get('part_id') or 'UNKNOWN'
                    qr_data = f"MM:{part_id}"
                    print(f"[DEBUG] Using default MM:id format: {qr_data}")

                # Create a mock part object for preview generation
                from dataclasses import dataclass

                @dataclass
                class MockPart:
                    id: str
                    part_name: str
                    part_number: str
                    quantity: int = 0

                # Extract part info from request data
                part_name = request.data.get('part_name', 'Unknown Part')
                part_number = request.data.get('part_number', 'UNKNOWN')

                mock_part = MockPart(
                    id=qr_data,  # Use the QR data as the ID (will be used for QR generation)
                    part_name=part_name,
                    part_number=part_number
                )

                # Use existing combined label preview method
                result = await service.preview_combined_label(mock_part, processed_text, request.label_size)
            else:
                # Generate text-only preview
                print(f"[DEBUG] Generating text-only preview")
                result = await service.preview_text_label(processed_text, request.label_size)

            print(f"[DEBUG] Preview generated successfully: {result.width_px}x{result.height_px}")
        except Exception as e:
            print(f"[ERROR] Failed to generate preview: {e}")
            import traceback
            traceback.print_exc()
            return PreviewResponse(
                success=False,
                error=f"Preview generation failed: {str(e)}",
                message="Failed to generate preview image"
            )

        # Encode image data as base64
        print(f"[DEBUG] Encoding image data to base64...")
        try:
            preview_data = base64.b64encode(result.image_data).decode('utf-8')
            print(f"[DEBUG] Base64 encoding successful, length: {len(preview_data)}")
        except Exception as e:
            print(f"[ERROR] Failed to encode image data: {e}")
            return PreviewResponse(
                success=False,
                error=f"Image encoding failed: {str(e)}",
                message="Failed to encode preview image"
            )

        print(f"[DEBUG] Returning successful preview response")
        return PreviewResponse(
            success=True,
            preview_data=preview_data,
            format=result.format,
            width_px=result.width_px,
            height_px=result.height_px,
            message=result.message
        )

    except Exception as e:
        print(f"[ERROR] Unexpected error in preview_advanced_label: {e}")
        import traceback
        traceback.print_exc()
        return PreviewResponse(
            success=False,
            error=f"Unexpected error: {str(e)}",
            message="Internal server error during preview generation"
        )