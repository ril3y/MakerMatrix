"""
Import Routes - Generic file import system

This module provides a simple interface for importing parts from supplier files.
All parsing and import logic is delegated to the supplier implementations.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import uuid
from datetime import datetime

from ..dependencies.auth import get_current_user
from ..models.user_models import UserModel
from ..schemas.response import ResponseSchema
from ..suppliers.registry import get_supplier, get_available_suppliers
from ..suppliers.base import SupplierCapability
from ..services.part_service import PartService
from ..services.order_service import order_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Import"])

# ========== Response Models ==========

class ImportResult(BaseModel):
    import_id: str
    status: str  # success, partial, failed
    supplier: str
    imported_count: int
    failed_count: int
    part_ids: List[str]
    failed_items: List[Dict[str, Any]]
    warnings: List[str]
    order_id: Optional[str] = None

class SupplierImportInfo(BaseModel):
    name: str
    display_name: str
    supported_file_types: List[str]
    import_available: bool
    missing_credentials: List[str] = Field(default_factory=list)

# ========== Endpoints ==========

@router.post("/file", response_model=ResponseSchema[ImportResult])
async def import_file(
    supplier_name: str = Form(..., description="Supplier name (e.g., lcsc, digikey, mouser)"),
    file: UploadFile = File(..., description="Order file to import"),
    order_number: Optional[str] = Form(None, description="Order number (optional)"),
    order_date: Optional[str] = Form(None, description="Order date (optional)"),
    notes: Optional[str] = Form(None, description="Order notes (optional)"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Import parts from a supplier file.
    
    The supplier will handle all parsing and validation.
    Supports various file formats depending on the supplier (CSV, XLS, etc).
    """
    try:
        # Get the supplier
        try:
            supplier = get_supplier(supplier_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unknown supplier: {supplier_name}")
        
        # Check if supplier supports imports
        if SupplierCapability.IMPORT_ORDERS not in supplier.get_capabilities():
            raise HTTPException(
                status_code=400,
                detail=f"{supplier_name} does not support file imports"
            )
        
        # Check if import capability is available (credentials check)
        if not supplier.is_capability_available(SupplierCapability.IMPORT_ORDERS):
            missing = supplier.get_missing_credentials_for_capability(SupplierCapability.IMPORT_ORDERS)
            raise HTTPException(
                status_code=403,
                detail=f"Import requires credentials: {', '.join(missing)}"
            )
        
        # Read file
        content = await file.read()
        filename = file.filename
        file_type = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Check if supplier can handle this file
        if not supplier.can_import_file(filename, content):
            info = supplier.get_supplier_info()
            supported = info.supported_file_types
            raise HTTPException(
                status_code=400,
                detail=f"{supplier_name} cannot import {file_type} files. Supported: {', '.join(supported)}"
            )
        
        # Import using supplier
        import_result = await supplier.import_order_file(content, file_type, filename)
        
        if not import_result.success:
            raise HTTPException(
                status_code=400,
                detail=import_result.error_message or "Import failed"
            )
        
        # Create parts in database
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
        
        # Create order record if we have order info
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
        
        # Import parts
        for part_data in import_result.parts:
            try:
                # Ensure supplier is set
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
        
        # Build response
        result = ImportResult(
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


@router.get("/suppliers", response_model=ResponseSchema[List[SupplierImportInfo]])
async def get_import_suppliers(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get list of suppliers that support file imports.
    
    Shows which suppliers can import files and what credentials they need.
    """
    try:
        suppliers_info = []
        
        for supplier_name in get_available_suppliers():
            try:
                supplier = get_supplier(supplier_name)
                
                # Check if supplier supports imports
                if SupplierCapability.IMPORT_ORDERS not in supplier.get_capabilities():
                    continue
                
                info = supplier.get_supplier_info()
                
                # Check what's needed for import
                import_available = supplier.is_capability_available(SupplierCapability.IMPORT_ORDERS)
                missing_creds = supplier.get_missing_credentials_for_capability(SupplierCapability.IMPORT_ORDERS)
                
                suppliers_info.append(SupplierImportInfo(
                    name=supplier_name,
                    display_name=info.display_name,
                    supported_file_types=info.supported_file_types,
                    import_available=import_available,
                    missing_credentials=missing_creds
                ))
                
            except Exception as e:
                logger.warning(f"Error checking supplier {supplier_name}: {e}")
                continue
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(suppliers_info)} suppliers with import capability",
            data=suppliers_info
        )
        
    except Exception as e:
        logger.error(f"Error getting import suppliers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get suppliers")