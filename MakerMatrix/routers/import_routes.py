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
    skipped_count: int = 0
    part_ids: List[str]
    failed_items: List[Dict[str, Any]]
    skipped_items: List[Dict[str, Any]] = []
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
            # Try multiple case variations to find the supplier config
            supplier_config = None
            name_variations = [
                supplier_name,                    # Original case (e.g., "digikey")
                supplier_name.upper(),           # Uppercase (e.g., "DIGIKEY")
                supplier_name.lower(),           # Lowercase (e.g., "digikey")
                supplier_name.capitalize()       # Capitalized (e.g., "Digikey")
            ]
            
            for name_variant in name_variations:
                try:
                    supplier_config = config_service.get_supplier_config(name_variant)
                    logger.info(f"Found supplier config for '{name_variant}' (original: '{supplier_name}')")
                    break
                except:
                    continue
            
            # Supplier must be configured and enabled
            if not supplier_config or not supplier_config.enabled:
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
            error_msg = import_result.error_message or "Import failed"
            logger.error(f"Import failed for {supplier_name}: {error_msg}")
            if import_result.warnings:
                logger.error(f"Import warnings: {import_result.warnings}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
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
        skipped_parts = []  # Track parts that already exist
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
                error_message = str(e)
                # Check if this is a duplicate part error
                if 'already exists' in error_message.lower():
                    skipped_parts.append({
                        'part_data': part_data,
                        'reason': f"Part '{part_data.get('part_name', 'unknown')}' already exists"
                    })
                    logger.info(f"Skipped duplicate part: {part_data.get('part_name', 'unknown')}")
                else:
                    failed_items.append({
                        'part_data': part_data,
                        'error': error_message
                    })
                    logger.error(f"Failed to import part: {error_message}")
        
        # Build response
        total_processed = len(part_ids) + len(skipped_parts) + len(failed_items)
        result = ImportResult(
            import_id=str(uuid.uuid4()),
            status="success" if not failed_items else "partial",
            supplier=supplier_name,
            imported_count=len(part_ids),
            failed_count=len(failed_items),
            skipped_count=len(skipped_parts),
            part_ids=part_ids,
            failed_items=failed_items,
            skipped_items=skipped_parts,
            warnings=import_result.warnings,
            order_id=order_id
        )
        
        # Build message
        message_parts = []
        if len(part_ids) > 0:
            message_parts.append(f"{len(part_ids)} parts imported")
        if len(skipped_parts) > 0:
            message_parts.append(f"{len(skipped_parts)} parts skipped (already exist)")
        if len(failed_items) > 0:
            message_parts.append(f"{len(failed_items)} parts failed")
        
        message = f"Processed {total_processed} parts from {supplier_name}: " + ", ".join(message_parts)
        
        return ResponseSchema(
            status="success",
            message=message,
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


