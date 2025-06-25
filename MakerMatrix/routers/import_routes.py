"""
Centralized Import Routes

This module handles all file import operations (CSV, Excel, JSON, etc.)
Import operations are synchronous and return imported data.
Task creation for enrichment is handled separately.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os
import json
import logging

from ..dependencies.auth import get_current_user
from ..models.user_models import UserModel
from ..schemas.response import ResponseSchema
from ..services.csv_import_service import csv_import_service
from ..services.order_service import order_service
from ..services.part_service import PartService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["import"])

# ========== Request/Response Models ==========

class CSVImportRequest(BaseModel):
    csv_content: str
    parser_type: Optional[str] = None
    order_info: Optional[Dict[str, Any]] = None

class FileImportRequest(BaseModel):
    parser_type: Optional[str] = None
    order_info: Optional[Dict[str, Any]] = None

class ImportResult(BaseModel):
    import_id: str
    status: str = Field(..., description="success, partial, or failed")
    imported_count: int
    failed_count: int
    part_ids: List[str]
    failed_items: List[Dict[str, Any]]
    warnings: List[str] = Field(default_factory=list)
    order_id: Optional[str] = None
    parser_type: str

class ImportPreviewResult(BaseModel):
    detected_type: Optional[str]
    total_rows: int
    headers: List[str]
    preview_rows: List[Dict[str, Any]]
    parser_info: Optional[Dict[str, Any]]
    warnings: List[str] = Field(default_factory=list)

# ========== CSV Import Endpoints ==========

@router.post("/csv/preview", response_model=ResponseSchema[ImportPreviewResult])
async def preview_csv_content(
    csv_content: str,
    parser_type: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Preview CSV content without importing
    
    Returns parsed data and detected parser type for review.
    """
    try:
        # Detect parser type if not provided
        if not parser_type:
            detected_type = csv_import_service.detect_parser_type(csv_content)
            parser_type = detected_type
        
        # Get parser
        parser = csv_import_service.get_parser(parser_type)
        if not parser:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown parser type: {parser_type}"
            )
        
        # Parse CSV
        parsed_data = parser.parse_csv(csv_content)
        
        # Prepare preview (first 10 rows)
        preview_rows = []
        for i, row in enumerate(parsed_data[:10]):
            preview_rows.append({
                "row_number": i + 1,
                "data": row
            })
        
        # Get headers from first row if available
        headers = list(parsed_data[0].keys()) if parsed_data else []
        
        result = ImportPreviewResult(
            detected_type=parser_type,
            total_rows=len(parsed_data),
            headers=headers,
            preview_rows=preview_rows,
            parser_info={
                "name": parser_type,
                "description": f"{parser_type.upper()} CSV parser"
            }
        )
        
        return ResponseSchema(
            status="success",
            message=f"Preview generated for {len(parsed_data)} rows",
            data=result
        )
        
    except Exception as e:
        logger.error(f"CSV preview failed: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

@router.post("/csv/execute", response_model=ResponseSchema[ImportResult])
async def import_csv_data(
    request: CSVImportRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Import CSV data into the system
    
    This endpoint ONLY handles data import. For enrichment, use the
    returned part_ids to create an enrichment task separately.
    """
    try:
        import uuid
        import_id = str(uuid.uuid4())
        
        # Detect parser type if not provided
        parser_type = request.parser_type
        if not parser_type:
            parser_type = csv_import_service.detect_parser_type(request.csv_content)
        
        # Get parser
        parser = csv_import_service.get_parser(parser_type)
        if not parser:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown parser type: {parser_type}"
            )
        
        # Parse CSV
        parsed_data = parser.parse_csv(request.csv_content)
        
        # Create order if order info provided
        order_id = None
        if request.order_info:
            order = order_service.create_order_from_dict({
                **request.order_info,
                "supplier": parser_type.upper()
            })
            order_id = order.id
        
        # Import parts
        success_parts = []
        failed_parts = []
        imported_part_ids = []
        
        for row_data in parsed_data:
            try:
                # Convert parsed data to part
                part_data = parser.map_to_internal_format(row_data)
                
                # Add part
                part_service = PartService()
                created_part = part_service.add_part(
                    part_data,
                    user=current_user.username
                )
                
                success_parts.append({
                    "part_number": created_part.part_number,
                    "part_id": created_part.id
                })
                imported_part_ids.append(created_part.id)
                
                # Link to order if exists
                if order_id:
                    order_service.link_part_to_order(created_part.id, order_id)
                    
            except Exception as e:
                failed_parts.append({
                    "part_number": row_data.get("part_number", "Unknown"),
                    "error": str(e),
                    "row_data": row_data
                })
        
        # Prepare result
        result = ImportResult(
            import_id=import_id,
            status="success" if not failed_parts else ("partial" if success_parts else "failed"),
            imported_count=len(success_parts),
            failed_count=len(failed_parts),
            part_ids=imported_part_ids,
            failed_items=failed_parts,
            order_id=order_id,
            parser_type=parser_type
        )
        
        return ResponseSchema(
            status="success" if not failed_parts else "warning",
            message=f"Imported {len(success_parts)} parts" + 
                   (f", {len(failed_parts)} failed" if failed_parts else ""),
            data=result
        )
        
    except Exception as e:
        logger.error(f"CSV import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

# ========== File Import Endpoints ==========

@router.post("/file/preview", response_model=ResponseSchema[ImportPreviewResult])
async def preview_file_import(
    file: UploadFile = File(...),
    parser_type: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Preview uploaded file (CSV, XLS, XLSX) without importing
    """
    try:
        # Validate file type
        allowed_extensions = ['.csv', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Convert to CSV if needed
        if file_extension == '.csv':
            csv_content = content.decode('utf-8')
        else:
            # Convert Excel to CSV
            try:
                import pandas as pd
                import io
                df = pd.read_excel(io.BytesIO(content))
                csv_content = df.to_csv(index=False)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read Excel file: {str(e)}"
                )
        
        # Use CSV preview logic
        return await preview_csv_content(csv_content, parser_type, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File preview failed: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

@router.post("/file/execute", response_model=ResponseSchema[ImportResult])
async def import_file_data(
    file: UploadFile = File(...),
    parser_type: Optional[str] = None,
    order_number: Optional[str] = None,
    order_date: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Import uploaded file (CSV, XLS, XLSX) into the system
    
    This endpoint ONLY handles data import. For enrichment, use the
    returned part_ids to create an enrichment task separately.
    """
    try:
        # Validate file type
        allowed_extensions = ['.csv', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Convert to CSV if needed
        if file_extension == '.csv':
            csv_content = content.decode('utf-8')
        else:
            # Convert Excel to CSV
            try:
                import pandas as pd
                import io
                df = pd.read_excel(io.BytesIO(content))
                csv_content = df.to_csv(index=False)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read Excel file: {str(e)}"
                )
        
        # Prepare order info
        order_info = {}
        if order_number:
            order_info["order_number"] = order_number
        if order_date:
            order_info["order_date"] = order_date
        if notes:
            order_info["notes"] = notes
        
        # Use CSV import logic
        request = CSVImportRequest(
            csv_content=csv_content,
            parser_type=parser_type,
            order_info=order_info if order_info else None
        )
        
        return await import_csv_data(request, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

# ========== Import Status Endpoints ==========

# In-memory storage for import status (should use database in production)
_import_status = {}

@router.get("/status/{import_id}", response_model=ResponseSchema[Dict[str, Any]])
async def get_import_status(
    import_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get status of a specific import operation
    
    Note: This is a placeholder. In production, import status should be
    stored in the database with proper user access control.
    """
    if import_id not in _import_status:
        raise HTTPException(
            status_code=404,
            detail=f"Import {import_id} not found"
        )
    
    return ResponseSchema(
        status="success",
        message="Import status retrieved",
        data=_import_status[import_id]
    )

# ========== Parser Information Endpoints ==========

@router.get("/parsers", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_available_parsers(
    current_user: UserModel = Depends(get_current_user)
):
    """Get list of available import parsers"""
    parsers = []
    
    for parser_type in csv_import_service.get_available_parsers():
        parsers.append({
            "id": parser_type,
            "name": parser_type.upper(),
            "description": f"{parser_type.upper()} file parser",
            "supported_formats": ["csv", "xls", "xlsx"] if parser_type == "mouser" else ["csv"]
        })
    
    return ResponseSchema(
        status="success",
        message=f"Found {len(parsers)} import parsers",
        data=parsers
    )