from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
from MakerMatrix.services.csv_import_service import csv_import_service
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.order_service import order_service
from MakerMatrix.dependencies.auth import require_permission
from MakerMatrix.models.user_models import UserModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["csv"])

# Request models
class CSVPreviewRequest(BaseModel):
    csv_content: str

class FilenameExtractionRequest(BaseModel):
    filename: str

class CSVImportRequest(BaseModel):
    csv_content: str
    parser_type: str
    order_info: Dict[str, Any]

# Response models
class CSVPreviewResponse(BaseModel):
    detected_type: str | None
    type_info: str
    headers: List[str]
    preview_rows: List[Dict[str, Any]]
    parsed_preview: List[Dict[str, Any]]
    total_rows: int
    is_supported: bool
    validation_errors: List[str]
    error: str | None = None

class CSVImportResponse(BaseModel):
    success_parts: List[str]
    failed_parts: List[str]
    order_id: str | None = None


@router.get("/supported-types")
async def get_supported_types():
    """Get list of supported CSV file types"""
    try:
        types = csv_import_service.get_supported_types()
        return {"supported_types": types}
    except Exception as e:
        logger.error(f"Error getting supported types: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported types")


@router.post("/preview", response_model=CSVPreviewResponse)
async def preview_csv(
    request: CSVPreviewRequest,
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Preview CSV content and detect file type"""
    try:
        preview_data = csv_import_service.preview_csv(request.csv_content)
        
        return CSVPreviewResponse(
            detected_type=preview_data.get("detected_type"),
            type_info=preview_data.get("type_info", "Unknown"),
            headers=preview_data.get("headers", []),
            preview_rows=preview_data.get("preview_rows", []),
            parsed_preview=preview_data.get("parsed_preview", []),
            total_rows=preview_data.get("total_rows", 0),
            is_supported=preview_data.get("is_supported", False),
            validation_errors=preview_data.get("validation_errors", []),
            error=preview_data.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error previewing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview CSV: {str(e)}")


@router.post("/import", response_model=CSVImportResponse)
async def import_csv(
    request: CSVImportRequest,
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """Import parts from CSV file with order tracking"""
    try:
        # Parse CSV to parts data
        parts_data, parsing_errors = csv_import_service.parse_csv_to_parts(
            request.csv_content, 
            request.parser_type
        )
        
        if parsing_errors:
            logger.warning(f"CSV parsing errors: {parsing_errors}")
        
        if not parts_data:
            return CSVImportResponse(
                success_parts=[],
                failed_parts=["No valid parts data found in CSV"],
                order_id=None
            )
        
        # Import parts with order tracking
        part_service = PartService()
        success_parts, failed_parts = await csv_import_service.import_parts_with_order(
            parts_data,
            part_service,
            request.order_info
        )
        
        # Add parsing errors to failed parts if any
        if parsing_errors:
            failed_parts.extend([f"Parsing error: {error}" for error in parsing_errors])
        
        logger.info(f"CSV import completed: {len(success_parts)} success, {len(failed_parts)} failed")
        
        return CSVImportResponse(
            success_parts=success_parts,
            failed_parts=failed_parts,
            order_id=None  # Could include order ID in future if needed
        )
        
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import CSV: {str(e)}")


@router.post("/parse")
async def parse_csv_only(
    request: CSVImportRequest,
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Parse CSV content into parts data without importing"""
    try:
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            request.csv_content, 
            request.parser_type
        )
        
        return {
            "parts_data": parts_data,
            "errors": errors,
            "total_parts": len(parts_data)
        }
        
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse CSV: {str(e)}")


@router.post("/extract-filename-info")
async def extract_filename_info(
    request: FilenameExtractionRequest,
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Extract order information from filename"""
    try:
        order_info = csv_import_service.extract_order_info_from_filename(request.filename)
        
        if order_info:
            return {
                "success": True,
                "order_info": order_info
            }
        else:
            return {
                "success": False,
                "message": "No order information could be extracted from filename"
            }
        
    except Exception as e:
        logger.error(f"Error extracting filename info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract filename info: {str(e)}")


@router.get("/parsers/{parser_type}/info")
async def get_parser_info(parser_type: str):
    """Get information about a specific parser"""
    try:
        parser = csv_import_service.get_parser(parser_type)
        if not parser:
            raise HTTPException(status_code=404, detail=f"Parser '{parser_type}' not found")
        
        return parser.get_info()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parser info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get parser information")