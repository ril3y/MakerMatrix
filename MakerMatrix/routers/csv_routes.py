"""
CSV/File Import Routes - Using Supplier-Based Import System

This module handles CSV and file imports by delegating to supplier implementations.
Each supplier handles its own file parsing and import logic.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os
import logging
import uuid
from datetime import datetime

from ..dependencies.auth import get_current_user
from ..models.user_models import UserModel
from ..schemas.response import ResponseSchema
from ..suppliers.registry import get_supplier_registry
from ..services.part_service import PartService
from ..services.order_service import order_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Import"])

# ========== Request/Response Models ==========

class ImportPreviewResult(BaseModel):
    detected_supplier: Optional[str]
    total_rows: int
    headers: List[str]
    preview_rows: List[Dict[str, Any]]
    is_supported: bool
    warnings: List[str] = Field(default_factory=list)

class ImportExecuteResult(BaseModel):
    import_id: str
    status: str  # success, partial, failed
    supplier: str
    imported_count: int
    failed_count: int
    part_ids: List[str]
    failed_items: List[Dict[str, Any]]
    warnings: List[str]
    order_id: Optional[str] = None

# ========== Endpoints ==========

@router.post("/preview-file", response_model=ResponseSchema[ImportPreviewResult])
async def preview_file(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """Preview an uploaded file and auto-detect which supplier can handle it"""
    try:
        # Read file content
        content = await file.read()
        filename = file.filename
        file_type = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Check each supplier to see who can handle this file
        supplier_registry = get_supplier_registry()
        detected_supplier = None
        preview_data = None
        
        for supplier_name, supplier_class in supplier_registry.items():
            try:
                supplier = supplier_class()
                if supplier.can_import_file(filename, content):
                    detected_supplier = supplier_name
                    preview_data = supplier.get_import_file_preview(content, file_type)
                    break
            except Exception as e:
                logger.debug(f"Supplier {supplier_name} cannot handle file: {e}")
                continue
        
        if not detected_supplier:
            return ResponseSchema(
                status="warning",
                message="No supplier found that can import this file",
                data=ImportPreviewResult(
                    detected_supplier=None,
                    total_rows=0,
                    headers=[],
                    preview_rows=[],
                    is_supported=False,
                    warnings=["File format not recognized by any supplier"]
                )
            )
        
        # Build preview result
        preview_result = ImportPreviewResult(
            detected_supplier=detected_supplier,
            total_rows=preview_data.get('total_rows', 0),
            headers=preview_data.get('headers', []),
            preview_rows=preview_data.get('preview_rows', []),
            is_supported=preview_data.get('is_supported', True),
            warnings=preview_data.get('warnings', [])
        )
        
        return ResponseSchema(
            status="success",
            message=f"File preview generated successfully. Detected supplier: {detected_supplier}",
            data=preview_result
        )
        
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {str(e)}")


@router.post("/import-file", response_model=ResponseSchema[ImportExecuteResult])
async def import_file(
    file: UploadFile = File(...),
    supplier_name: Optional[str] = Form(None),
    order_number: Optional[str] = Form(None),
    order_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: UserModel = Depends(get_current_user)
):
    """Import a file using the appropriate supplier"""
    try:
        # Read file content
        content = await file.read()
        filename = file.filename
        file_type = filename.split('.')[-1].lower() if '.' in filename else ''
        
        supplier_registry = get_supplier_registry()
        
        # If supplier specified, use it directly
        if supplier_name:
            if supplier_name not in supplier_registry:
                raise HTTPException(status_code=400, detail=f"Unknown supplier: {supplier_name}")
            
            supplier_class = supplier_registry[supplier_name]
            supplier = supplier_class()
            
            # Check if supplier can handle this file
            if not supplier.can_import_file(filename, content):
                raise HTTPException(
                    status_code=400, 
                    detail=f"{supplier_name} cannot import this file type"
                )
        else:
            # Auto-detect supplier
            supplier = None
            for name, supplier_class in supplier_registry.items():
                try:
                    s = supplier_class()
                    if s.can_import_file(filename, content):
                        supplier = s
                        supplier_name = name
                        break
                except Exception:
                    continue
            
            if not supplier:
                raise HTTPException(
                    status_code=400,
                    detail="No supplier found that can import this file"
                )
        
        # Check if supplier has import capability available
        from ..suppliers.base import SupplierCapability
        if not supplier.is_capability_available(SupplierCapability.IMPORT_ORDERS):
            missing_creds = supplier.get_missing_credentials_for_capability(SupplierCapability.IMPORT_ORDERS)
            if missing_creds:
                raise HTTPException(
                    status_code=403,
                    detail=f"Import capability requires credentials: {', '.join(missing_creds)}"
                )
        
        # Import using supplier
        import_result = await supplier.import_order_file(content, file_type, filename)
        
        if not import_result.success:
            raise HTTPException(
                status_code=400,
                detail=import_result.error_message or "Import failed"
            )
        
        # Process imported parts
        part_service = PartService()
        part_ids = []
        failed_items = []
        
        # Prepare order info
        order_info = {
            'supplier': supplier_name.upper(),
            'order_number': order_number,
            'order_date': order_date,
            'notes': notes
        }
        
        # Merge with order info from import if available
        if import_result.order_info:
            for key, value in import_result.order_info.items():
                if key not in order_info or not order_info[key]:
                    order_info[key] = value
        
        # Create order if we have order info
        order_id = None
        if order_info.get('order_number') or order_info.get('order_date'):
            try:
                order = await order_service.create_order(
                    order_number=order_info.get('order_number', f"IMP-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"),
                    supplier=order_info['supplier'],
                    order_date=order_info.get('order_date'),
                    notes=order_info.get('notes', '')
                )
                order_id = order.id
            except Exception as e:
                logger.warning(f"Failed to create order: {e}")
        
        # Import each part
        for part_data in import_result.parts:
            try:
                # Add supplier if not present
                if 'supplier' not in part_data:
                    part_data['supplier'] = supplier_name.upper()
                
                # Create part
                created_part = await part_service.create_part(part_data)
                part_ids.append(created_part.id)
                
                # Link to order if we have one
                if order_id and created_part:
                    try:
                        await order_service.add_order_item(
                            order_id=order_id,
                            part_id=created_part.id,
                            quantity=part_data.get('quantity', 1),
                            unit_price=part_data.get('unit_price', 0)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to link part to order: {e}")
                        
            except Exception as e:
                failed_items.append({
                    'part_data': part_data,
                    'error': str(e)
                })
        
        # Build result
        result = ImportExecuteResult(
            import_id=str(uuid.uuid4()),
            status="success" if not failed_items else "partial",
            supplier=supplier_name,
            imported_count=len(part_ids),
            failed_count=len(failed_items),
            part_ids=part_ids,
            failed_items=failed_items,
            warnings=import_result.warnings,
            order_id=order_id
        )
        
        return ResponseSchema(
            status="success",
            message=f"Imported {len(part_ids)} parts from {supplier_name}",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/supported-suppliers", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_suppliers_with_import_capability(
    current_user: UserModel = Depends(get_current_user)
):
    """Get list of suppliers that support file imports"""
    try:
        from ..suppliers.base import SupplierCapability
        supplier_registry = get_supplier_registry()
        
        supported_suppliers = []
        for name, supplier_class in supplier_registry.items():
            try:
                supplier = supplier_class()
                if SupplierCapability.IMPORT_ORDERS in supplier.get_capabilities():
                    info = supplier.get_supplier_info()
                    requirements = supplier.get_capability_requirements().get(SupplierCapability.IMPORT_ORDERS)
                    
                    supported_suppliers.append({
                        'name': name,
                        'display_name': info.display_name,
                        'supported_file_types': info.supported_file_types,
                        'requires_credentials': bool(requirements and requirements.required_credentials),
                        'required_credentials': requirements.required_credentials if requirements else []
                    })
            except Exception as e:
                logger.warning(f"Error checking supplier {name}: {e}")
                continue
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(supported_suppliers)} suppliers with import capability",
            data=supported_suppliers
        )
        
    except Exception as e:
        logger.error(f"Error getting import suppliers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get suppliers")


class CSVPreviewRequest(BaseModel):
    csv_content: str

@router.post("/preview-text", response_model=ResponseSchema[ImportPreviewResult]) 
async def preview_csv_text(
    request: CSVPreviewRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Preview CSV text content - for backwards compatibility"""
    try:
        # Convert to bytes and use file preview
        content_bytes = request.csv_content.encode('utf-8')
        
        # Check each supplier for CSV support
        supplier_registry = get_supplier_registry()
        detected_supplier = None
        preview_data = None
        
        for supplier_name, supplier_class in supplier_registry.items():
            try:
                supplier = supplier_class()
                # Use a generic CSV filename for detection
                if supplier.can_import_file("import.csv", content_bytes):
                    detected_supplier = supplier_name
                    preview_data = supplier.get_import_file_preview(content_bytes, "csv")
                    break
            except Exception as e:
                logger.debug(f"Supplier {supplier_name} cannot handle CSV: {e}")
                continue
        
        if not detected_supplier:
            return ResponseSchema(
                status="warning",
                message="No supplier found that can import this CSV",
                data=ImportPreviewResult(
                    detected_supplier=None,
                    total_rows=0,
                    headers=[],
                    preview_rows=[],
                    is_supported=False,
                    warnings=["CSV format not recognized by any supplier"]
                )
            )
        
        preview_result = ImportPreviewResult(
            detected_supplier=detected_supplier,
            total_rows=preview_data.get('total_rows', 0),
            headers=preview_data.get('headers', []),
            preview_rows=preview_data.get('preview_rows', []),
            is_supported=preview_data.get('is_supported', True),
            warnings=preview_data.get('warnings', [])
        )
        
        return ResponseSchema(
            status="success",
            message=f"CSV preview generated. Detected supplier: {detected_supplier}",
            data=preview_result
        )
        
    except Exception as e:
        logger.error(f"Error previewing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview CSV: {str(e)}")


# Keep some legacy endpoints for compatibility but simplified

@router.get("/config", response_model=ResponseSchema[Dict[str, Any]])
async def get_import_config(
    current_user: UserModel = Depends(get_current_user)
):
    """Get import configuration"""
    # Return a simplified config since enrichment is handled separately
    return ResponseSchema(
        status="success",
        message="Import configuration retrieved",
        data={
            "auto_detect_supplier": True,
            "create_order_records": True,
            "merge_duplicate_parts": False
        }
    )