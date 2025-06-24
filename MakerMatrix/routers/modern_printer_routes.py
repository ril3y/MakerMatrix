"""
Modern printer routes that use the new printer interface.
Provides the missing endpoints that tests expect.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel

from MakerMatrix.services.modern_printer_service import get_printer_service, ModernPrinterService
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.models.models import engine
from MakerMatrix.printers.base import PrinterNotFoundError, PrinterError, PrintJobResult
from MakerMatrix.dependencies.auth import get_current_user
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.schemas.response import ResponseSchema


router = APIRouter()


# Request/Response models
class TextPrintRequest(BaseModel):
    text: str
    printer_id: Optional[str] = None
    label_size: str = "62"
    copies: int = 1


class QRTextPrintRequest(BaseModel):
    printer_config: Dict[str, Any]
    label_data: Dict[str, Any]
    printer_id: Optional[str] = None


class PrintResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None
    error: Optional[str] = None


def _handle_printer_error(e: Exception) -> HTTPException:
    """Convert printer errors to HTTP exceptions."""
    if isinstance(e, PrinterNotFoundError):
        return HTTPException(status_code=404, detail=f"Printer not found: {e.printer_id}")
    elif isinstance(e, PrinterError):
        return HTTPException(status_code=500, detail=str(e))
    else:
        return HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def _create_success_response(result: PrintJobResult, message: str) -> PrintResponse:
    """Create a success response from a print job result."""
    return PrintResponse(
        status="success",
        message=message,
        job_id=result.job_id
    )


def _create_error_response(error: str) -> PrintResponse:
    """Create an error response."""
    return PrintResponse(
        status="error",
        message="Print job failed",
        error=error
    )


@router.post("/print_qr_code/{part_id}", response_model=PrintResponse)
async def print_qr_code_for_part(
    part_id: str,
    printer_id: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    printer_service: ModernPrinterService = Depends(get_printer_service)
) -> PrintResponse:
    """Print QR code for a specific part by ID."""
    try:
        # Get the part using session
        from sqlmodel import Session
        with Session(engine) as session:
            part = PartRepository.get_part_by_id(session, part_id)
        if not part:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")
        
        # Print QR code
        result = await printer_service.print_part_qr_code(part, printer_id)
        
        if result.success:
            return _create_success_response(result, "QR code printed successfully for part")
        else:
            return _create_error_response(result.error or "Print job failed")
            
    except (PrinterNotFoundError, PrinterError) as e:
        raise _handle_printer_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print_part_name/{part_id}", response_model=PrintResponse)
async def print_part_name(
    part_id: str,
    printer_id: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    printer_service: ModernPrinterService = Depends(get_printer_service)
) -> PrintResponse:
    """Print part name as text label for a specific part by ID."""
    try:
        # Get the part using session
        from sqlmodel import Session
        with Session(engine) as session:
            part = PartRepository.get_part_by_id(session, part_id)
        if not part:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")
        
        # Print part name
        result = await printer_service.print_part_name(part, printer_id)
        
        if result.success:
            return _create_success_response(result, "Part name printed successfully")
        else:
            return _create_error_response(result.error or "Print job failed")
            
    except (PrinterNotFoundError, PrinterError) as e:
        raise _handle_printer_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print_text", response_model=PrintResponse)
async def print_text_label(
    request: TextPrintRequest,
    current_user: UserModel = Depends(get_current_user),
    printer_service: ModernPrinterService = Depends(get_printer_service)
) -> PrintResponse:
    """Print a text label."""
    try:
        result = await printer_service.print_text_label(
            text=request.text,
            printer_id=request.printer_id,
            label_size=request.label_size,
            copies=request.copies
        )
        
        if result.success:
            return _create_success_response(result, "Text label printed successfully")
        else:
            return _create_error_response(result.error or "Print job failed")
            
    except (PrinterNotFoundError, PrinterError) as e:
        raise _handle_printer_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print_qr_and_text", response_model=PrintResponse)
async def print_qr_and_text_combined(
    request: QRTextPrintRequest,
    current_user: UserModel = Depends(get_current_user),
    printer_service: ModernPrinterService = Depends(get_printer_service)
) -> PrintResponse:
    """Print combined QR code and text label."""
    try:
        # Extract QR data and text from label_data
        qr_data = request.label_data.get("qr_data", "")
        text = request.label_data.get("text", "")
        
        # Create a mock part from QR data for compatibility
        # In a real scenario, you'd parse the QR data to get part info
        part = PartModel(
            part_number=qr_data.split("/")[-1] if "/" in qr_data else qr_data,
            part_name=text,
            description=f"Generated from QR: {qr_data}",
            quantity=0
        )
        
        result = await printer_service.print_qr_and_text(
            part=part,
            text=text,
            printer_config=request.printer_config,
            label_data=request.label_data,
            printer_id=request.printer_id
        )
        
        if result.success:
            return _create_success_response(result, "QR code and text label printed successfully")
        else:
            return _create_error_response(result.error or "Print job failed")
            
    except (PrinterNotFoundError, PrinterError) as e:
        raise _handle_printer_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Additional modern endpoints for completeness

@router.get("/printers")
async def list_printers(
    current_user: UserModel = Depends(get_current_user),
    printer_service: ModernPrinterService = Depends(get_printer_service)
) -> Dict[str, Any]:
    """List all available printers."""
    try:
        printers = printer_service.list_printers()
        printer_infos = []
        
        for printer_id, printer in printers.items():
            info = printer.get_printer_info()
            printer_infos.append({
                "id": info.id,
                "name": info.name,
                "driver": info.driver,
                "model": info.model,
                "status": info.status.value,
                "backend": info.backend,
                "identifier": info.identifier,
                "capabilities": [cap.value for cap in info.capabilities]
            })
        
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success",
            message=f"Retrieved {len(printer_infos)} printers",
            data=printer_infos
        ).dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/printers/{printer_id}/status")
async def get_printer_status(
    printer_id: str,
    current_user: UserModel = Depends(get_current_user),
    printer_service: ModernPrinterService = Depends(get_printer_service)
) -> Dict[str, Any]:
    """Get the status of a specific printer."""
    try:
        printer = printer_service.get_printer(printer_id)
        status = await printer.get_status()
        
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success",
            message=f"Retrieved status for printer {printer_id}",
            data={
                "printer_id": printer_id,
                "status": status.value
            }
        ).dict()
        
    except PrinterNotFoundError as e:
        raise _handle_printer_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/printers/{printer_id}/test")
async def test_printer(
    printer_id: str,
    current_user: UserModel = Depends(get_current_user),
    printer_service: ModernPrinterService = Depends(get_printer_service)
) -> PrintResponse:
    """Test connectivity to a specific printer."""
    try:
        printer = printer_service.get_printer(printer_id)
        test_result = await printer.test_connection()
        
        from MakerMatrix.schemas.response import ResponseSchema
        return ResponseSchema(
            status="success" if test_result.success else "warning",
            message=f"Connection test {'successful' if test_result.success else 'failed'} for {printer_id}",
            data={
                "printer_id": printer_id,
                "success": test_result.success,
                "response_time_ms": test_result.response_time_ms,
                "message": test_result.message,
                "error": test_result.error
            }
        ).dict()
        
    except PrinterNotFoundError as e:
        raise _handle_printer_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))