from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Body, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from MakerMatrix.services.printer.printer_manager_service import printer_manager
from MakerMatrix.services.printer.preview_service import PreviewService
from MakerMatrix.printers.base import PrinterStatus, PrinterCapability
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.auth.dependencies import get_current_user

router = APIRouter()


async def get_preview_service() -> PreviewService:
    """Get a preview service with a default printer if available."""
    try:
        # Try to get a printer from the printer manager
        printers = await printer_manager.list_printers()
        if printers:
            # Use the first available printer as default
            first_printer = printers[0]
            return PreviewService(first_printer)
        else:
            # Create a mock printer for preview if no real printers available
            from MakerMatrix.printers.drivers.mock.driver import MockPrinter
            mock_printer = MockPrinter(
                printer_id="preview_mock",
                name="Preview Mock Printer",
                model="MockQL-800",
                backend="mock",
                identifier="mock://preview"
            )
            return PreviewService(mock_printer)
    except Exception as e:
        # Fallback to mock printer
        from MakerMatrix.printers.drivers.mock.driver import MockPrinter
        mock_printer = MockPrinter(
            printer_id="preview_mock",
            name="Preview Mock Printer", 
            model="MockQL-800",
            backend="mock",
            identifier="mock://preview"
        )
        return PreviewService(mock_printer)


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
    from MakerMatrix.schemas.response import ResponseSchema
    
    drivers_data = [
            {
                "id": "brother_ql",
                "driver_type": "brother_ql",
                "name": "Brother QL Series",
                "description": "Support for Brother QL label printers",
                "supported_models": ["QL-800"],
                "backends": ["network", "linux_kernel", "pyusb"],
                "default_dpi": 300,
                "recommended_scaling": 1.1,
                "required_fields": ["identifier"],
                "optional_fields": ["dpi", "scaling_factor"],
                "backend_options": {
                    "network": {
                        "identifier_format": "tcp://IP:PORT or IP",
                        "default_port": 9100,
                        "example": "tcp://192.168.1.100:9100",
                    },
                    "linux_kernel": {
                        "identifier_format": "/dev/usb/lp* device path",
                        "example": "/dev/usb/lp0",
                    },
                    "pyusb": {
                        "identifier_format": "USB device identifier",
                        "example": "usb://0x04f9:0x2042",
                    }
                }
            },
            {
                "id": "mock_thermal",
                "driver_type": "mock_thermal",
                "name": "Mock Thermal Printer",
                "description": "Mock thermal printer for testing (non-functional)",
                "supported_models": ["ThermalPrint-X1", "ThermalPrint-X2", "ThermalPrint-Pro"],
                "backends": ["serial", "network", "usb"],
                "default_dpi": 203,
                "recommended_scaling": 1.0,
                "required_fields": ["identifier", "baud_rate", "paper_width"],
                "optional_fields": ["dpi", "scaling_factor", "cut_mode", "heat_setting"],
                "backend_options": {
                    "serial": {
                        "identifier_format": "COM port or /dev/ttyUSB*",
                        "example": "/dev/ttyUSB0",
                        "additional_fields": ["baud_rate", "parity", "stop_bits"],
                    },
                    "network": {
                        "identifier_format": "IP:PORT",
                        "default_port": 9100,
                        "example": "192.168.1.200:9100",
                    },
                    "usb": {
                        "identifier_format": "USB device path",
                        "example": "/dev/usb/lp1",
                    }
                },
                "custom_fields": {
                    "baud_rate": {
                        "type": "select",
                        "options": [9600, 19200, 38400, 57600, 115200],
                        "default": 9600,
                        "label": "Baud Rate"
                    },
                    "paper_width": {
                        "type": "select", 
                        "options": ["58mm", "80mm", "112mm"],
                        "default": "80mm",
                        "label": "Paper Width"
                    },
                    "cut_mode": {
                        "type": "select",
                        "options": ["auto", "manual", "none"],
                        "default": "auto",
                        "label": "Cut Mode"
                    },
                    "heat_setting": {
                        "type": "range",
                        "min": 1,
                        "max": 10,
                        "default": 5,
                        "label": "Heat Setting"
                    },
                    "parity": {
                        "type": "select",
                        "options": ["none", "even", "odd"],
                        "default": "none",
                        "label": "Parity"
                    },
                    "stop_bits": {
                        "type": "select",
                        "options": [1, 2],
                        "default": 1,
                        "label": "Stop Bits"
                    }
                }
            }
        ]
    
    return ResponseSchema(
        status="success",
        message="Supported drivers retrieved successfully",
        data={"drivers": drivers_data}
    ).dict()


@router.get("/drivers/{driver_type}")
async def get_driver_info(driver_type: str):
    """Get detailed information about a specific driver."""
    from MakerMatrix.schemas.response import ResponseSchema
    
    # Get all drivers first
    drivers_response = await list_supported_drivers()
    drivers = drivers_response["data"]["drivers"]
    
    # Find the specific driver
    driver = next((d for d in drivers if d["id"] == driver_type), None)
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver '{driver_type}' not found")
    
    return ResponseSchema(
        status="success",
        message=f"Driver information for {driver_type}",
        data=driver
    ).dict()


@router.get("/printers")
async def list_printers():
    """Get list of all registered printers."""
    try:
        from MakerMatrix.services.printer.printer_persistence_service import get_printer_persistence_service
        
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
                
                # Get complete configuration from persistence
                persistent_config = None
                try:
                    db_printers = persistence_service.get_persistent_printers()
                    persistent_config = next((db_p for db_p in db_printers if db_p.get('printer_id') == info.id), None)
                except Exception as e:
                    print(f"[DEBUG] Failed to get persistent config for {info.id}: {e}")
                
                printer_data = {
                    "printer_id": info.id,
                    "name": info.name,
                    "model": info.model,
                    "status": status.value,
                    "capabilities": [cap.value for cap in capabilities]
                }
                
                # Add configuration details from database if available
                if persistent_config:
                    printer_data.update({
                        "driver_type": persistent_config.get("driver_type"),
                        "backend": persistent_config.get("backend"),
                        "identifier": persistent_config.get("identifier"),
                        "dpi": persistent_config.get("dpi"),
                        "scaling_factor": persistent_config.get("scaling_factor"),
                        "config": persistent_config.get("config") or {},
                        "is_active": persistent_config.get("is_active"),
                        "last_seen": persistent_config.get("last_seen"),
                        "created_at": persistent_config.get("created_at"),
                        "updated_at": persistent_config.get("updated_at")
                    })
                else:
                    # Fallback to basic info if no persistence data
                    print(f"[DEBUG] No persistent config found for {info.id}")
                
                printer_list.append(printer_data)
                print(f"[DEBUG] Added printer to list: {printer_data}")
            except Exception as e:
                print(f"Error processing printer {p}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[DEBUG] Returning {len(printer_list)} printers")
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success",
            message=f"Retrieved {len(printer_list)} printers",
            data=printer_list
        ).dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/printers/{printer_id}")
async def get_printer_info(printer_id: str):
    """Get detailed information about a specific printer."""
    try:
        from MakerMatrix.services.printer.printer_persistence_service import get_printer_persistence_service
        
        printer = await printer_manager.get_printer(printer_id)
        if not printer:
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        info = printer.get_printer_info()
        status = await printer.get_status()
        capabilities = await printer.get_capabilities()
        supported_sizes = printer.get_supported_label_sizes()
        
        # Get complete configuration from persistence
        persistence_service = get_printer_persistence_service()
        persistent_config = None
        try:
            db_printers = persistence_service.get_persistent_printers()
            persistent_config = next((db_p for db_p in db_printers if db_p.get('printer_id') == info.id), None)
        except Exception as e:
            print(f"[DEBUG] Failed to get persistent config for {info.id}: {e}")
        
        printer_data = {
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
        
        # Add configuration details from database if available
        if persistent_config:
            printer_data.update({
                "driver_type": persistent_config.get("driver_type"),
                "backend": persistent_config.get("backend"),
                "identifier": persistent_config.get("identifier"),
                "dpi": persistent_config.get("dpi"),
                "scaling_factor": persistent_config.get("scaling_factor"),
                "config": persistent_config.get("config") or {},
                "is_active": persistent_config.get("is_active"),
                "last_seen": persistent_config.get("last_seen"),
                "created_at": persistent_config.get("created_at"),
                "updated_at": persistent_config.get("updated_at")
            })
        
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success",
            message=f"Retrieved printer information for {printer_id}",
            data=printer_data
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/printers/{printer_id}")
async def update_printer(printer_id: str, update_data: PrinterRegistration):
    """Update an existing printer configuration."""
    try:
        from MakerMatrix.services.printer.printer_persistence_service import get_printer_persistence_service
        from MakerMatrix.services.activity_service import get_activity_service
        from MakerMatrix.auth.dependencies import get_current_user_optional
        from MakerMatrix.schemas.response import ResponseSchema
        
        # Check if printer exists
        existing_printer = await printer_manager.get_printer(printer_id)
        if not existing_printer:
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        # Update printer data
        printer_data = {
            "printer_id": printer_id,  # Keep the same ID
            "name": update_data.name,
            "driver_type": update_data.driver_type,
            "model": update_data.model,
            "backend": update_data.backend,
            "identifier": update_data.identifier,
            "dpi": update_data.dpi,
            "scaling_factor": update_data.scaling_factor
        }
        
        # Update via persistence service (handles both memory and database)
        persistence_service = get_printer_persistence_service()
        
        # First unregister the old printer
        await printer_manager.unregister_printer(printer_id)
        
        # Then register with new configuration
        result = await persistence_service.register_printer_with_persistence(printer_data)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown update error'))
        
        # Log activity
        try:
            from MakerMatrix.auth.dependencies import get_current_user_optional
            
            activity_service = get_activity_service()
            current_user = None
            try:
                current_user = await get_current_user_optional(None)  # TODO: Pass request if available
            except:
                pass  # Anonymous update allowed for debug
                
            await activity_service.log_printer_updated(
                printer_id=printer_id,
                printer_name=update_data.name,
                changes=printer_data,
                user=current_user,
                request=None  # TODO: Add request parameter to endpoint
            )
        except Exception as e:
            print(f"Failed to log update activity: {e}")
        
        return ResponseSchema(
            status="success",
            message=f"Printer '{update_data.name}' updated successfully",
            data={"printer_id": printer_id}
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update printer: {str(e)}")


@router.delete("/printers/{printer_id}")
async def delete_printer(printer_id: str, request: Request = None):
    """Delete a registered printer."""
    try:
        from MakerMatrix.services.printer.printer_persistence_service import get_printer_persistence_service
        from MakerMatrix.schemas.response import ResponseSchema
        from MakerMatrix.services.activity_service import get_activity_service
        from MakerMatrix.auth.dependencies import get_current_user_optional
        
        # Get printer info before deletion for logging
        printer_name = printer_id  # fallback
        try:
            printer = await printer_manager.get_printer(printer_id)
            if printer:
                printer_info = printer.get_printer_info()
                printer_name = printer_info.name
        except:
            pass
        
        # Remove from memory
        success = await printer_manager.unregister_printer(printer_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        # Remove from database
        persistence_service = get_printer_persistence_service()
        await persistence_service.remove_printer_with_persistence(printer_id)
        
        # Log activity
        try:
            activity_service = get_activity_service()
            current_user = None
            try:
                current_user = await get_current_user_optional(request)
            except:
                pass  # Anonymous deletion allowed for debug
            
            await activity_service.log_printer_deleted(
                printer_id=printer_id,
                printer_name=printer_name,
                user=current_user,
                request=request
            )
        except Exception as e:
            print(f"Failed to log delete activity: {e}")
        
        return ResponseSchema(
            status="success",
            message=f"Printer {printer_id} deleted successfully",
            data={"printer_id": printer_id}
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete printer: {str(e)}")


@router.get("/printers/{printer_id}/status")
async def get_printer_status(printer_id: str):
    """Get current status of a printer."""
    try:
        printer = await printer_manager.get_printer(printer_id)
        if not printer:
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        status = await printer.get_status()
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success",
            message=f"Retrieved status for printer {printer_id}",
            data={"printer_id": printer_id, "status": status.value}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/printers/{printer_id}/test")
async def test_printer_connection(printer_id: str, request: Request = None):
    """Test printer connectivity."""
    try:
        print(f"Testing connection for printer: {printer_id}")
        printer = await printer_manager.get_printer(printer_id)
        
        # If printer not found in memory, try to restore from database first
        if not printer:
            print(f"Printer {printer_id} not found in memory, checking database...")
            from MakerMatrix.services.printer.printer_persistence_service import get_printer_persistence_service
            persistence_service = get_printer_persistence_service()
            
            # Try to restore all printers from database
            try:
                restored = await persistence_service.restore_printers_from_database()
                print(f"Restored {len(restored)} printers from database")
                # Try to get the printer again
                printer = await printer_manager.get_printer(printer_id)
            except Exception as restore_error:
                print(f"Failed to restore printers: {restore_error}")
        
        if not printer:
            print(f"Printer {printer_id} not found even after database restore")
            raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
        
        print(f"Found printer, testing connection...")
        result = await printer.test_connection()
        print(f"Test result: {result}")
        
        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            from MakerMatrix.auth.dependencies import get_current_user_optional
            
            activity_service = get_activity_service()
            current_user = None
            try:
                current_user = await get_current_user_optional(request)
            except:
                pass  # Anonymous test allowed
            
            printer_info = printer.get_printer_info()
            await activity_service.log_printer_tested(
                printer_id=printer_id,
                printer_name=printer_info.name,
                test_result=result.success,
                user=current_user,
                request=request
            )
        except Exception as e:
            print(f"Failed to log test activity: {e}")
        
        response_data = {
            "printer_id": printer_id,
            "success": result.success,
            "message": result.message,
            "response_time_ms": result.response_time_ms
        }
        print(f"Returning response: {response_data}")
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success" if result.success else "warning",
            message=f"Connection test {'successful' if result.success else 'failed'} for {printer_id}",
            data=response_data
        ).dict()
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
        from MakerMatrix.services.printer.printer_persistence_service import get_printer_persistence_service
        from MakerMatrix.services.activity_service import get_activity_service
        from MakerMatrix.auth.dependencies import get_current_user_optional
        
        # Get current user if authenticated
        current_user = None
        try:
            current_user = await get_current_user_optional(request)
        except:
            pass  # Anonymous registration allowed for debug
        
        # Check if printer already exists
        existing_printer = await printer_manager.get_printer(registration.printer_id)
        if existing_printer:
            raise HTTPException(
                status_code=409, 
                detail=f"Printer with ID '{registration.printer_id}' already exists"
            )
        
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
        
        response_data = {
            "success": True,
            "printer_id": registration.printer_id,
            "persisted": result.get('persisted', False)
        }
        
        # Add warning if persistence failed but memory registration succeeded
        if not result.get('persisted'):
            response_data['warning'] = 'Printer registered but may not survive server restart'
            if 'persistence_error' in result:
                response_data['persistence_error'] = result['persistence_error']
        
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success",
            message=f"Printer '{registration.name}' registered successfully",
            data=response_data
        ).dict()
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
            
            response_data = {
                "success": result.success,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "recommendations": {
                    "scaling_factor": 1.1 if printer_data.get('model') == 'QL-800' else 1.0,
                    "recommended_dpi": 300,
                    "optimal_label_size": "12"
                }
            }
            from MakerMatrix.schemas.response import ResponseSchema
            return ResponseSchema(
                status="success" if result.success else "warning",
                message=f"Test setup {'successful' if result.success else 'failed'}",
                data=response_data
            ).dict()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported driver type: {printer_data.get('driver_type')}")
    except Exception as e:
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="error",
            message="Test setup failed",
            data={
                "success": False,
                "message": f"Test failed: {str(e)}",
                "response_time_ms": 0
            }
        ).dict()


# Discovery endpoints removed - caused issues with printer routing
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
        
        response_data = {
            "success": result.success,
            "job_id": result.job_id,
            "message": result.message,
            "error": result.error
        }
        print(f"Returning print response: {response_data}")
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success" if result.success else "error",
            message=f"Text label print {'successful' if result.success else 'failed'}",
            data=response_data
        ).dict()
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
        
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success" if result.success else "error",
            message=f"QR code print {'successful' if result.success else 'failed'}",
            data={
                "success": result.success,
                "job_id": result.job_id,
                "message": result.message,
                "error": result.error
            }
        ).dict()
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
        
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success" if result.success else "error",
            message=f"Image print {'successful' if result.success else 'failed'}",
            data={
                "success": result.success,
                "job_id": result.job_id,
                "message": result.message,
                "error": result.error
            }
        ).dict()
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
        
        response_data = {
            "success": result.success,
            "job_id": result.job_id,
            "message": result.message,
            "error": result.error
        }
        print(f"Returning advanced print response: {response_data}")
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success" if result.success else "error",
            message=f"Advanced label print {'successful' if result.success else 'failed'}",
            data=response_data
        ).dict()
    except Exception as e:
        print(f"Error in print_advanced_label: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Note: Preview endpoints have been moved to /api/preview/* in preview_routes.py
# This consolidates all preview functionality in one place with better API design

# Backward compatibility endpoints for frontend
from fastapi.responses import StreamingResponse
import io

@router.post("/preview/text")
async def preview_text_label_compat(
    text: str = Body(...),
    label_size: str = Body("12")
):
    """Preview a text label (backward compatibility endpoint)."""
    try:
        # Create a preview using the preview service
        preview_svc = await get_preview_service()
        result = await preview_svc.preview_text_label(text, label_size)
        
        # Return the image as a streaming response
        return StreamingResponse(
            io.BytesIO(result.image_data),
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=label_preview.png"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")


@router.post("/preview/advanced")
async def preview_advanced_label_compat(request: AdvancedPreviewRequest):
    """Preview an advanced label (backward compatibility endpoint)."""
    try:
        # Extract data from the request or use mock data for testing
        data = request.data or {
            'part_name': 'Test Part',
            'part_number': 'TP-001', 
            'location': 'A1-B2',
            'category': 'Electronics',
            'quantity': '10'
        }
        
        # Create a preview using the preview service
        preview_svc = await get_preview_service()
        result = await preview_svc.preview_advanced_label(
            template=request.template,
            data=data,
            label_size=request.label_size,
            label_length=request.label_length,
            options=request.options
        )
        
        # Return the image as a streaming response
        return StreamingResponse(
            io.BytesIO(result.image_data),
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=advanced_label_preview.png"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate advanced preview: {str(e)}")



