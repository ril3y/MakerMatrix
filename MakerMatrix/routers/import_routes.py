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

from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers
from MakerMatrix.suppliers.base import SupplierCapability
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.services.data.order_service import order_service
from MakerMatrix.models.order_models import CreateOrderRequest

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
    is_configured: bool = False
    configuration_status: str = "not_configured"  # "configured", "not_configured", "partial"

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
        
        # NEW: Check if supplier is configured in the system
        try:
            from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
            config_service = SupplierConfigService()
            supplier_config = config_service.get_supplier_config(supplier_name)
            
            # Supplier must be configured and enabled
            if not supplier_config or not supplier_config.get('enabled', False):
                raise HTTPException(
                    status_code=403,
                    detail=f"Supplier {supplier_name} is not configured or enabled. Please configure the supplier in Settings -> Suppliers before importing files."
                )
                
        except ImportError:
            # Fallback if config service not available
            logger.warning("SupplierConfigService not available, skipping configuration check")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Error checking supplier configuration: {e}")
            # For non-configured suppliers, check basic credentials
            if not supplier.is_capability_available(SupplierCapability.IMPORT_ORDERS):
                missing = supplier.get_missing_credentials_for_capability(SupplierCapability.IMPORT_ORDERS)
                if missing:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Supplier {supplier_name} is not configured. Please configure the supplier in Settings -> Suppliers before importing files."
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
        
        logger.info(f"Supplier import result: success={import_result.success}, parts_count={len(import_result.parts) if import_result.parts else 0}")
        
        if not import_result.success:
            raise HTTPException(
                status_code=400,
                detail=import_result.error_message or "Import failed"
            )
        
        if not import_result.parts:
            logger.warning(f"No parts found in {filename} for supplier {supplier_name}")
            raise HTTPException(
                status_code=400,
                detail=f"No parts found in file. Check that the file format matches {supplier_name} requirements."
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
                order_request = CreateOrderRequest(
                    order_number=order_info.get('order_number', f"IMP-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"),
                    supplier=order_info['supplier'],
                    order_date=order_info.get('order_date'),
                    notes=order_info.get('notes', ''),
                    import_source=f"File import: {filename}",
                    status="imported"
                )
                order = await order_service.create_order(order_request)
                order_id = order.id
            except Exception as e:
                logger.warning(f"Failed to create order: {e}")
        
        # Import parts
        logger.info(f"Starting to import {len(import_result.parts)} parts")
        for i, part_data in enumerate(import_result.parts):
            try:
                logger.info(f"Processing part {i+1}/{len(import_result.parts)}: {part_data}")
                
                # Ensure supplier is set
                if 'supplier' not in part_data:
                    part_data['supplier'] = supplier_name.upper()
                
                # Create part using the correct method
                logger.info(f"Creating part with data: {part_data}")
                created_part_response = part_service.add_part(part_data)
                logger.info(f"Part creation response: {created_part_response}")
                if created_part_response.get('status') == 'success':
                    created_part = created_part_response.get('data')
                    if created_part and created_part.get('id'):
                        part_ids.append(created_part['id'])
                    else:
                        logger.warning(f"Part created but no ID returned: {created_part_response}")
                else:
                    raise Exception(f"Failed to create part: {created_part_response.get('message', 'Unknown error')}")
                
                # Link to order if we have one
                if order_id and created_part and created_part.get('id'):
                    try:
                        from MakerMatrix.models.order_models import CreateOrderItemRequest
                        order_item_request = CreateOrderItemRequest(
                            supplier_part_number=part_data.get('part_number', ''),
                            manufacturer_part_number=part_data.get('manufacturer_part_number'),
                            description=part_data.get('description', ''),
                            manufacturer=part_data.get('manufacturer'),
                            quantity_ordered=part_data.get('quantity', 1),
                            unit_price=part_data.get('unit_price', 0.0),
                            extended_price=part_data.get('quantity', 1) * part_data.get('unit_price', 0.0)
                        )
                        await order_service.add_order_item(order_id, order_item_request)
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


@router.post("/preview")
async def preview_csv_content(
    csv_content: Dict[str, str],
    current_user: UserModel = Depends(get_current_user)
):
    """
    Preview CSV content without importing.
    
    Analyzes CSV text content and returns headers, row count, and preview data.
    """
    try:
        content = csv_content.get('csv_content', '')
        if not content:
            raise HTTPException(status_code=400, detail="No CSV content provided")
        
        # Try to detect supplier from CSV content
        detected_supplier = None
        content_lower = content.lower()
        
        # Check for supplier-specific patterns in CSV headers/content
        if 'lcsc part number' in content_lower or 'customer no.' in content_lower:
            detected_supplier = 'lcsc'
        elif 'digi-key part number' in content_lower or 'quantity available' in content_lower:
            detected_supplier = 'digikey'
        elif 'mouser part no' in content_lower or 'mouser part number' in content_lower:
            detected_supplier = 'mouser'
        
        if detected_supplier:
            try:
                supplier = get_supplier(detected_supplier)
                # Use supplier's preview method if available
                if hasattr(supplier, 'get_import_file_preview'):
                    preview_data = supplier.get_import_file_preview(
                        content.encode('utf-8'), 'csv'
                    )
                    preview_data['detected_parser'] = detected_supplier
                    return ResponseSchema(
                        status="success",
                        message="CSV preview generated",
                        data=preview_data
                    )
            except Exception as e:
                logger.warning(f"Error using supplier preview for {detected_supplier}: {e}")
        
        # Fallback to basic CSV parsing
        import csv
        import io
        
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames or []
        
        # Get preview rows
        preview_rows = []
        total_rows = 0
        for i, row in enumerate(reader):
            total_rows += 1
            if i < 5:  # Only keep first 5 for preview
                preview_rows.append(row)
        
        return ResponseSchema(
            status="success",
            message="CSV preview generated",
            data={
                "headers": headers,
                "preview_rows": preview_rows,
                "total_rows": total_rows,
                "detected_parser": detected_supplier,
                "is_supported": detected_supplier is not None
            }
        )
        
    except Exception as e:
        logger.error(f"Error previewing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/preview-file")
async def preview_file_upload(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Preview uploaded file without importing.
    
    Supports CSV and XLS files, returns headers, row count, and preview data.
    """
    try:
        content = await file.read()
        filename = file.filename or ''
        file_type = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Try to auto-detect supplier from filename
        detected_supplier = None
        filename_lower = filename.lower()
        
        if 'lcsc' in filename_lower:
            detected_supplier = 'lcsc'
        elif 'digikey' in filename_lower or 'dk_' in filename_lower:
            detected_supplier = 'digikey'
        elif 'mouser' in filename_lower:
            detected_supplier = 'mouser'
        
        # Try each supplier's preview method
        for supplier_name in get_available_suppliers():
            try:
                supplier = get_supplier(supplier_name)
                
                # Check if supplier can handle this file
                if hasattr(supplier, 'can_import_file') and supplier.can_import_file(filename, content):
                    detected_supplier = supplier_name
                    
                    # Use supplier's preview method
                    if hasattr(supplier, 'get_import_file_preview'):
                        preview_data = supplier.get_import_file_preview(content, file_type)
                        preview_data['detected_parser'] = detected_supplier
                        return ResponseSchema(
                            status="success",
                            message="File preview generated",
                            data=preview_data
                        )
                    break
                    
            except Exception as e:
                logger.warning(f"Error checking supplier {supplier_name}: {e}")
                continue
        
        # Fallback preview for CSV files
        if file_type == 'csv':
            import csv
            import io
            
            try:
                content_str = content.decode('utf-8')
                csv_file = io.StringIO(content_str)
                reader = csv.DictReader(csv_file)
                headers = reader.fieldnames or []
                
                # Get preview rows
                preview_rows = []
                total_rows = 0
                for i, row in enumerate(reader):
                    total_rows += 1
                    if i < 5:  # Only keep first 5 for preview
                        preview_rows.append(row)
                
                return ResponseSchema(
                    status="success",
                    message="File preview generated",
                    data={
                        "headers": headers,
                        "preview_rows": preview_rows,
                        "total_rows": total_rows,
                        "detected_parser": detected_supplier,
                        "is_supported": detected_supplier is not None
                    }
                )
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Unable to decode CSV file")
        
        # If we get here, we couldn't preview the file
        return ResponseSchema(
            status="error",
            message="Unable to preview this file type",
            data={
                "headers": [],
                "preview_rows": [],
                "total_rows": 0,
                "detected_parser": detected_supplier,
                "is_supported": False,
                "error": f"Unsupported file type: {file_type}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.get("/suppliers", response_model=ResponseSchema[List[SupplierImportInfo]])
async def get_import_suppliers(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get list of suppliers that support file imports.
    
    Shows which suppliers can import files and what configuration they need.
    """
    try:
        suppliers_info = []
        
        # Get configured suppliers from database
        configured_suppliers = {}
        try:
            from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
            config_service = SupplierConfigService()
            configs = config_service.get_all_supplier_configs()
            configured_suppliers = {
                config['supplier_name'].lower(): config 
                for config in configs 
                if config.get('enabled', False)
            }
            logger.info(f"Found {len(configured_suppliers)} configured suppliers: {list(configured_suppliers.keys())}")
        except Exception as e:
            logger.warning(f"Could not load configured suppliers: {e}")
            configured_suppliers = {}
        
        for supplier_name in get_available_suppliers():
            try:
                supplier = get_supplier(supplier_name)
                
                # Check if supplier supports imports
                if SupplierCapability.IMPORT_ORDERS not in supplier.get_capabilities():
                    continue
                
                info = supplier.get_supplier_info()
                
                # Check if supplier is configured
                is_configured = supplier_name.lower() in configured_suppliers
                config_status = "configured" if is_configured else "not_configured"
                
                # Check basic import capability (file parsing)
                import_capable = supplier.is_capability_available(SupplierCapability.IMPORT_ORDERS)
                missing_creds = supplier.get_missing_credentials_for_capability(SupplierCapability.IMPORT_ORDERS)
                
                # Import available if: configured AND technically capable
                # OR technically capable AND no credentials required
                import_available = is_configured and import_capable
                
                # If not configured but no credentials needed, still allow import
                if not is_configured and import_capable and len(missing_creds) == 0:
                    import_available = True
                    config_status = "partial"  # Can import but not fully configured
                
                suppliers_info.append(SupplierImportInfo(
                    name=supplier_name,
                    display_name=info.display_name,
                    supported_file_types=info.supported_file_types,
                    import_available=import_available,
                    missing_credentials=missing_creds if not is_configured else [],
                    is_configured=is_configured,
                    configuration_status=config_status
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


@router.post("/extract-filename-info")
async def extract_filename_info(
    request: Dict[str, str],
    current_user: UserModel = Depends(get_current_user)
):
    """
    Extract order information from filename patterns.
    
    Analyzes filename to detect supplier and extract order details.
    """
    try:
        filename = request.get('filename', '')
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Extract file info
        filename_lower = filename.lower()
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Detect supplier from filename patterns
        detected_supplier = None
        order_info = {}
        
        if 'lcsc' in filename_lower:
            detected_supplier = 'lcsc'
        elif 'digikey' in filename_lower or 'dk_' in filename_lower or 'digi-key' in filename_lower:
            detected_supplier = 'digikey'
        elif 'mouser' in filename_lower:
            detected_supplier = 'mouser'
        
        # Extract order number patterns
        import re
        
        # Common order number patterns
        order_patterns = [
            r'order[_-]?(\w+)',
            r'ord[_-]?(\w+)', 
            r'po[_-]?(\w+)',
            r'(\d{8,})',  # 8+ digit numbers
            r'([A-Z]{2,}\d{4,})',  # Letter prefix with numbers
        ]
        
        for pattern in order_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                order_info['order_number'] = match.group(1).upper()
                break
        
        # Extract date patterns (YYYYMMDD, YYYY-MM-DD, etc.)
        date_patterns = [
            r'(\d{4}[-_]?\d{2}[-_]?\d{2})',
            r'(\d{2}[-_]?\d{2}[-_]?\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                order_info['order_date'] = match.group(1)
                break
        
        return ResponseSchema(
            status="success",
            message="Filename info extracted",
            data={
                "detected_supplier": detected_supplier,
                "file_type": file_ext.upper(),
                "order_info": order_info,
                "filename": filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting filename info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract filename info: {str(e)}")