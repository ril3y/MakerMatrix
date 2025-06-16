from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Body, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from MakerMatrix.services.printer_manager_service import printer_manager
from MakerMatrix.services.preview_service import preview_service
from MakerMatrix.printers.base import PrinterStatus, PrinterCapability
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.dependencies.auth import get_current_user

router = APIRouter()


# Request/Response models
class PrintRequest(BaseModel):
    printer_id: str
    label_size: str
    copies: int = 1
    text: Optional[str] = None


class QRCodeRequest(BaseModel):
    printer_id: str
    data: str
    label_size: str
    copies: int = 1


class TextLabelRequest(BaseModel):
    printer_id: str
    text: str
    label_size: str
    copies: int = 1


class PrinterRegistration(BaseModel):
    printer_id: str
    name: str
    driver_type: str
    model: str
    backend: str
    identifier: str
    dpi: int = 300
    scaling_factor: float = 1.1


class PreviewRequest(BaseModel):
    label_size: str
    text: Optional[str] = None
    qr_data: Optional[str] = None


class AdvancedLabelRequest(BaseModel):
    printer_id: str
    template: str
    text: str
    label_size: str
    label_length: Optional[int] = None
    options: dict = {}
    data: Optional[dict] = None


class AdvancedPreviewRequest(BaseModel):
    template: str
    text: str
    label_size: str
    label_length: Optional[int] = None
    options: dict = {}
    data: Optional[dict] = None


# Printer Management Endpoints
@router.get("/drivers")
async def list_supported_drivers():
    """Get list of supported printer drivers."""
    return {
        "drivers": [
            {
                "driver_type": "brother_ql",
                "name": "Brother QL Series",
                "description": "Support for Brother QL label printers",
                "supported_models": ["QL-800", "QL-810W", "QL-820NWB", "QL-1100", "QL-1110NWB"],
                "backends": ["network", "usb"],
                "default_dpi": 300,
                "recommended_scaling": 1.1
            }
        ]
    }


@router.get("/printers")
async def list_printers():
    """Get list of all registered printers."""
    try:
        from MakerMatrix.services.printer_persistence_service import get_printer_persistence_service
        
        print(f"[DEBUG] NEW list_printers endpoint called with persistence")
        print(f"[DEBUG] This is the updated version of the endpoint")
        
        # Get persistence service
        persistence_service = get_printer_persistence_service()
        
        # First check if there are printers in memory
        printers = await printer_manager.list_printers()
        print(f"[DEBUG] Retrieved {len(printers)} printers from memory")
        
        # If no printers in memory, try to restore from database
        if len(printers) == 0:
            print(f"[DEBUG] No printers in memory, checking database...")
            db_printers = persistence_service.get_persistent_printers()
            print(f"[DEBUG] Found {len(db_printers)} printers in database")
            
            # Restore printers from database if found
            if len(db_printers) > 0:
                print(f"[DEBUG] Restoring printers from database...")
                restored = await persistence_service.restore_printers_from_database()
                print(f"[DEBUG] Restored {len(restored)} printers")
                
                # Get the updated list after restoration
                printers = await printer_manager.list_printers()
                print(f"[DEBUG] After restoration: {len(printers)} printers in memory")
        
        printer_list = []
        
        for p in printers:
            try:
                info = p.get_printer_info()
                print(f"[DEBUG] Processing printer: {info.id} - {info.name}")
                status = await p.get_status()
                capabilities = await p.get_capabilities()
                
                printer_data = {
                    "printer_id": info.id,
                    "name": info.name,
                    "model": info.model,
                    "status": status.value,
                    "capabilities": [cap.value for cap in capabilities]
                }
                printer_list.append(printer_data)
                print(f"[DEBUG] Added printer to list: {printer_data}")
            except Exception as e:
                print(f"Error processing printer {p}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[DEBUG] Returning {len(printer_list)} printers")
        return {
            "printers": printer_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/printers/{printer_id}")
async def get_printer_info(printer_id: str):
    """Get detailed information about a specific printer."""
    try:
        printer = await printer_manager.get_printer(printer_id)
        if not printer:
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        info = printer.get_printer_info()
        status = await printer.get_status()
        capabilities = await printer.get_capabilities()
        supported_sizes = printer.get_supported_label_sizes()
        
        return {
            "printer_id": info.id,
            "name": info.name,
            "model": info.model,
            "status": status.value,
            "capabilities": [cap.value for cap in capabilities],
            "supported_sizes": [
                {
                    "name": size.name,
                    "width_mm": size.width_mm,
                    "height_mm": size.height_mm,
                    "is_continuous": size.is_continuous()
                }
                for size in supported_sizes
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/printers/{printer_id}/status")
async def get_printer_status(printer_id: str):
    """Get current status of a printer."""
    try:
        printer = await printer_manager.get_printer(printer_id)
        if not printer:
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        status = await printer.get_status()
        return {"printer_id": printer_id, "status": status.value}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/printers/{printer_id}/test")
async def test_printer_connection(printer_id: str):
    """Test printer connectivity."""
    try:
        print(f"Testing connection for printer: {printer_id}")
        printer = await printer_manager.get_printer(printer_id)
        if not printer:
            print(f"Printer {printer_id} not found")
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        print(f"Found printer, testing connection...")
        result = await printer.test_connection()
        print(f"Test result: {result}")
        
        response = {
            "printer_id": printer_id,
            "success": result.success,
            "message": result.message,
            "response_time_ms": result.response_time_ms
        }
        print(f"Returning response: {response}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in test_printer_connection: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register_printer(registration: PrinterRegistration, request: Request = None):
    """Register a new printer with persistence."""
    try:
        from MakerMatrix.services.printer_persistence_service import get_printer_persistence_service
        from MakerMatrix.services.activity_service import get_activity_service
        from MakerMatrix.dependencies.auth import get_current_user_optional
        
        # Get current user if authenticated
        current_user = None
        try:
            current_user = await get_current_user_optional(request)
        except:
            pass  # Anonymous registration allowed for debug
        
        # Prepare printer data for persistence
        printer_data = {
            "printer_id": registration.printer_id,
            "name": registration.name,
            "driver_type": registration.driver_type,
            "model": registration.model,
            "backend": registration.backend,
            "identifier": registration.identifier,
            "dpi": registration.dpi,
            "scaling_factor": registration.scaling_factor
        }
        
        # Register with persistence service (handles both memory and database)
        persistence_service = get_printer_persistence_service()
        result = await persistence_service.register_printer_with_persistence(printer_data)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown registration error'))
        
        # Log activity
        activity_service = get_activity_service()
        await activity_service.log_printer_registered(
            printer_id=registration.printer_id,
            printer_name=registration.name,
            user=current_user,
            request=request
        )
        
        response = {
            "success": True,
            "message": f"Printer '{registration.name}' registered successfully",
            "printer_id": registration.printer_id,
            "persisted": result.get('persisted', False)
        }
        
        # Add warning if persistence failed but memory registration succeeded
        if not result.get('persisted'):
            response['warning'] = 'Printer registered but may not survive server restart'
            if 'persistence_error' in result:
                response['persistence_error'] = result['persistence_error']
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register printer: {str(e)}")


@router.post("/test-setup")
async def test_printer_setup(setup_data: dict):
    """Test printer setup without registering."""
    try:
        printer_data = setup_data.get('printer', {})
        
        if printer_data.get('driver_type') == "brother_ql":
            from MakerMatrix.printers.drivers.brother_ql.driver import BrotherQLModern
            
            # Create temporary printer for testing
            temp_printer = BrotherQLModern(
                printer_id="temp_test",
                name="Test Setup",
                model=printer_data.get('model', 'QL-800'),
                backend=printer_data.get('backend', 'network'),
                identifier=printer_data.get('identifier', ''),
                dpi=printer_data.get('dpi', 300),
                scaling_factor=printer_data.get('scaling_factor', 1.1)
            )
            
            # Test connection
            result = await temp_printer.test_connection()
            
            return {
                "success": result.success,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "recommendations": {
                    "scaling_factor": 1.1 if printer_data.get('model') == 'QL-800' else 1.0,
                    "recommended_dpi": 300,
                    "optimal_label_size": "12"
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported driver type: {printer_data.get('driver_type')}")
    except Exception as e:
        return {
            "success": False,
            "message": f"Test failed: {str(e)}",
            "response_time_ms": 0
        }


@router.get("/discover")
async def discover_printers():
    """Discover available printers on the network."""
    try:
        # Basic network discovery for Brother QL printers
        import socket
        import threading
        import time
        
        discovered_printers = []
        
        def check_ip(ip):
            try:
                sock = socket.create_connection((ip, 9100), timeout=1)
                sock.close()
                discovered_printers.append({
                    "ip": ip,
                    "port": 9100,
                    "identifier": f"tcp://{ip}:9100",
                    "type": "brother_ql",
                    "status": "available"
                })
            except:
                pass
        
        # Check common IP ranges (basic discovery)
        threads = []
        base_ip = "192.168.1."
        
        for i in range(1, 255):
            ip = base_ip + str(i)
            thread = threading.Thread(target=check_ip, args=(ip,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Wait for discovery (max 3 seconds)
        time.sleep(3)
        
        return {
            "discovered_printers": discovered_printers,
            "discovery_time_ms": 3000,
            "message": f"Found {len(discovered_printers)} potential printers"
        }
    except Exception as e:
        return {
            "discovered_printers": [],
            "discovery_time_ms": 0,
            "message": f"Discovery failed: {str(e)}"
        }


# Printing Endpoints
@router.post("/print/text")
async def print_text_label(
    request: TextLabelRequest,
    http_request: Request = None,
    current_user: UserModel = Depends(get_current_user)
):
    """Print a text label."""
    try:
        print(f"Print request: {request}")
        result = await printer_manager.print_text_label(
            printer_id=request.printer_id,
            text=request.text,
            label_size=request.label_size,
            copies=request.copies
        )
        print(f"Print result: {result}")
        
        # Log activity if print was successful
        if result.success:
            try:
                from MakerMatrix.services.activity_service import get_activity_service
                activity_service = get_activity_service()
                
                # Get printer name
                printer = await printer_manager.get_printer(request.printer_id)
                printer_name = "Unknown Printer"
                if printer:
                    printer_info = printer.get_printer_info()
                    printer_name = printer_info.name
                
                await activity_service.log_label_printed(
                    printer_id=request.printer_id,
                    printer_name=printer_name,
                    label_type=f"Text: {request.text[:20]}{'...' if len(request.text) > 20 else ''}",
                    user=current_user,
                    request=http_request
                )
            except Exception as e:
                print(f"Failed to log print activity: {e}")
        
        response = {
            "success": result.success,
            "job_id": result.job_id,
            "message": result.message,
            "error": result.error
        }
        print(f"Returning print response: {response}")
        return response
    except Exception as e:
        print(f"Error in print_text_label: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print/qr")
async def print_qr_code(request: QRCodeRequest):
    """Print a QR code label."""
    try:
        result = await printer_manager.print_qr_code(
            printer_id=request.printer_id,
            data=request.data,
            label_size=request.label_size,
            copies=request.copies
        )
        
        return {
            "success": result.success,
            "job_id": result.job_id,
            "message": result.message,
            "error": result.error
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print/image")
async def print_image_label(
    printer_id: str = Body(...),
    label_size: str = Body(...),
    copies: int = Body(1),
    image: UploadFile = File(...)
):
    """Print an image label."""
    try:
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        image_data = await image.read()
        
        result = await printer_manager.print_image(
            printer_id=printer_id,
            image_data=image_data,
            label_size=label_size,
            copies=copies
        )
        
        return {
            "success": result.success,
            "job_id": result.job_id,
            "message": result.message,
            "error": result.error
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print/advanced")
async def print_advanced_label(
    request: AdvancedLabelRequest,
    http_request: Request = None,
    current_user: UserModel = Depends(get_current_user)
):
    """Print an advanced label with template processing."""
    try:
        print(f"Advanced print request: {request}")
        
        # Extract data from the request or use mock data for testing
        data = request.data or {
            'part_name': 'Test Part',
            'part_number': 'TP-001', 
            'location': 'A1-B2',
            'category': 'Electronics',
            'quantity': '10'
        }
        
        # Use the new advanced label printing method
        result = await printer_manager.print_advanced_label(
            printer_id=request.printer_id,
            template=request.template,
            data=data,
            label_size=request.label_size,
            label_length=request.label_length,
            options=request.options,
            copies=1
        )
        print(f"Advanced print result: {result}")
        
        # Log activity if print was successful
        if result.success:
            try:
                from MakerMatrix.services.activity_service import get_activity_service
                activity_service = get_activity_service()
                
                # Get printer name
                printer = await printer_manager.get_printer(request.printer_id)
                printer_name = "Unknown Printer"
                if printer:
                    printer_info = printer.get_printer_info()
                    printer_name = printer_info.name
                
                # Create a descriptive label type
                template_preview = request.template[:30] + "..." if len(request.template) > 30 else request.template
                label_type = f"Advanced: {template_preview}"
                
                await activity_service.log_label_printed(
                    printer_id=request.printer_id,
                    printer_name=printer_name,
                    label_type=label_type,
                    user=current_user,
                    request=http_request
                )
            except Exception as e:
                print(f"Failed to log advanced print activity: {e}")
        
        response = {
            "success": result.success,
            "job_id": result.job_id,
            "message": result.message,
            "error": result.error
        }
        print(f"Returning advanced print response: {response}")
        return response
    except Exception as e:
        print(f"Error in print_advanced_label: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Preview Endpoints
@router.post("/preview/text")
async def preview_text_label(request: PreviewRequest):
    """Generate preview of text label."""
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="Text is required for text preview")
        
        # Get default printer from printer manager
        default_printer = await printer_manager.get_printer()
        if not default_printer:
            raise HTTPException(status_code=400, detail="No printer available for preview")
        
        result = await preview_service.preview_text_label(
            text=request.text,
            label_size=request.label_size,
            printer=default_printer
        )
        
        return StreamingResponse(
            io.BytesIO(result.image_data),
            media_type=f"image/{result.format}",
            headers={"Content-Disposition": "inline; filename=preview.png"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview/qr")
async def preview_qr_code(request: PreviewRequest):
    """Generate preview of QR code label."""
    try:
        if not request.qr_data:
            raise HTTPException(status_code=400, detail="QR data is required for QR preview")
        
        # Get default printer from printer manager
        default_printer = await printer_manager.get_printer()
        if not default_printer:
            raise HTTPException(status_code=400, detail="No printer available for preview")
        
        # Generate QR code image
        from MakerMatrix.services.qr_service import QRService
        qr_service = QRService()
        qr_image = qr_service.generate_qr_code(request.qr_data, size=(200, 200))
        
        # Use printer's preview method directly
        result = await default_printer.preview_label(qr_image, request.label_size)
        
        return StreamingResponse(
            io.BytesIO(result.image_data),
            media_type=f"image/{result.format}",
            headers={"Content-Disposition": "inline; filename=qr_preview.png"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview/advanced")
async def preview_advanced_label(request: AdvancedPreviewRequest):
    """Generate preview of advanced label with template processing."""
    try:
        print(f"Advanced preview request: {request}")
        
        # Use data from request or create mock data for preview
        data = request.data or {
            'part_name': 'Test Part',
            'part_number': 'TP-001', 
            'location': 'A1-B2',
            'category': 'Electronics',
            'quantity': '10'
        }
        
        # Use the preview-specific label image creation method (with rotation)
        label_image = await printer_manager._create_advanced_label_image_for_preview(
            template=request.template,
            data=data,
            label_size=request.label_size,
            label_length=request.label_length,
            options=request.options
        )
        
        # Convert PIL image to bytes for streaming
        img_byte_arr = io.BytesIO()
        label_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return StreamingResponse(
            img_byte_arr,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=advanced_preview.png"}
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in preview_advanced_label: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _generate_text_image_for_preview(text: str, size: tuple[int, int]):
    """Generate a PIL image with the given text for preview."""
    from PIL import Image, ImageDraw, ImageFont
    
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)
    
    try:
        # Try to use a proper font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        # Fall back to default font
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    draw.text((x, y), text, fill='black', font=font)
    return image
