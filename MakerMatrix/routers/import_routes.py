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
from MakerMatrix.auth.guards import require_permission
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
    # New enrichment capability fields
    enrichment_capabilities: List[str] = Field(default_factory=list)
    enrichment_available: bool = False
    enrichment_missing_credentials: List[str] = Field(default_factory=list)


# ========== Endpoints ==========


@router.post("/file", response_model=ResponseSchema[ImportResult])
async def import_file(
    supplier_name: str = Form(..., description="Supplier name (e.g., lcsc, digikey, mouser)"),
    file: UploadFile = File(..., description="Order file to import"),
    order_number: Optional[str] = Form(None, description="Order number (optional)"),
    order_date: Optional[str] = Form(None, description="Order date (optional)"),
    notes: Optional[str] = Form(None, description="Order notes (optional)"),
    enable_enrichment: Optional[bool] = Form(False, description="Enable automatic enrichment after import"),
    enrichment_capabilities: Optional[str] = Form(
        None, description="Comma-separated list of enrichment capabilities (e.g., 'get_part_details,fetch_datasheet')"
    ),
    current_user: UserModel = Depends(require_permission("parts:create")),
):
    """
    Import parts from a supplier file.

    The supplier will handle all parsing and validation.
    Supports various file formats depending on the supplier (CSV, XLS, etc).
    """
    supplier = None
    try:
        # Get the supplier
        try:
            supplier = get_supplier(supplier_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unknown supplier: {supplier_name}")

        # Check if supplier supports imports
        if SupplierCapability.IMPORT_ORDERS not in supplier.get_capabilities():
            raise HTTPException(status_code=400, detail=f"{supplier_name} does not support file imports")

        # NEW: Check if supplier is configured in the system
        try:
            from MakerMatrix.services.system.supplier_config_service import SupplierConfigService

            config_service = SupplierConfigService()
            # Try multiple case variations to find the supplier config
            supplier_config_dict = None
            name_variations = [
                supplier_name,  # Original case (e.g., "digikey")
                supplier_name.upper(),  # Uppercase (e.g., "DIGIKEY")
                supplier_name.lower(),  # Lowercase (e.g., "digikey")
                supplier_name.capitalize(),  # Capitalized (e.g., "Digikey")
            ]

            for name_variant in name_variations:
                try:
                    # The get_supplier_config method should return a dictionary
                    supplier_config_dict = config_service.get_supplier_config(name_variant)
                    logger.info(f"Found supplier config for '{name_variant}' (original: '{supplier_name}')")
                    break
                except Exception as e:
                    logger.debug(f"Config not found for variant '{name_variant}': {e}")
                    continue

            # Supplier must be configured and enabled
            if not supplier_config_dict:
                raise HTTPException(
                    status_code=403,
                    detail=f"Supplier {supplier_name} is not configured. Please configure the supplier in Settings -> Suppliers before importing files.",
                )

            # At this point supplier_config_dict should be a dictionary from the service
            # The service guarantees it returns a dict via the to_dict() conversion
            enabled = supplier_config_dict.get("enabled", False)
            if not enabled:
                raise HTTPException(
                    status_code=403,
                    detail=f"Supplier {supplier_name} is not enabled. Please enable the supplier in Settings -> Suppliers before importing files.",
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
                        detail=f"Supplier {supplier_name} is not configured. Please configure the supplier in Settings -> Suppliers before importing files.",
                    )

        # Check if import capability is available (credentials check)
        if not supplier.is_capability_available(SupplierCapability.IMPORT_ORDERS):
            missing = supplier.get_missing_credentials_for_capability(SupplierCapability.IMPORT_ORDERS)
            raise HTTPException(status_code=403, detail=f"Import requires credentials: {', '.join(missing)}")

        # Read file
        content = await file.read()
        filename = file.filename
        file_type = filename.split(".")[-1].lower() if "." in filename else ""

        # Check if supplier can handle this file
        if not supplier.can_import_file(filename, content):
            info = supplier.get_supplier_info()
            supported = info.supported_file_types
            raise HTTPException(
                status_code=400,
                detail=f"{supplier_name} cannot import {file_type} files. Supported: {', '.join(supported)}",
            )

        # Import using supplier
        import_result = await supplier.import_order_file(content, file_type, filename)

        logger.info(
            f"Supplier import result: success={import_result.success}, parts_count={len(import_result.parts) if import_result.parts else 0}"
        )

        if not import_result.success:
            error_msg = import_result.error_message or "Import failed"
            logger.error(f"Import failed for {supplier_name}: {error_msg}")
            if import_result.warnings:
                logger.error(f"Import warnings: {import_result.warnings}")
            raise HTTPException(status_code=400, detail=error_msg)

        if not import_result.parts:
            logger.warning(f"No parts found in {filename} for supplier {supplier_name}")
            raise HTTPException(
                status_code=400,
                detail=f"No parts found in file. Check that the file format matches {supplier_name} requirements.",
            )

        # Create parts in database
        part_service = PartService()
        part_ids = []
        failed_items = []

        # Prepare order info
        order_info = {
            "supplier": supplier_name.upper(),
            "order_number": order_number,
            "order_date": order_date,
            "notes": notes,
        }

        # Merge with order info from import if available
        if import_result.order_info:
            for key, value in import_result.order_info.items():
                if key not in order_info or not order_info[key]:
                    order_info[key] = value

        # Create order record if we have order info
        order_id = None
        if order_info.get("order_number") or order_info.get("order_date"):
            try:
                order_request = CreateOrderRequest(
                    order_number=order_info.get("order_number", f"IMP-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"),
                    supplier=order_info["supplier"],
                    order_date=order_info.get("order_date"),
                    notes=order_info.get("notes", ""),
                    import_source=f"File import: {filename}",
                    status="imported",
                )
                order_response = await order_service.create_order(order_request)
                if order_response.success:
                    order_dict = order_response.data
                    # Order service returns order dict in ServiceResponse.data (from order.to_dict())
                    order_id = order_dict["id"]  # Access 'id' key from dict
                    logger.info(f"Created order with ID: {order_id}")
                else:
                    logger.warning(f"Failed to create order: {order_response.message}")
                    order_id = None
            except Exception as e:
                logger.warning(f"Failed to create order: {e}")

        # Import parts
        skipped_parts = []  # Track parts that already exist
        logger.info(f"Starting to import {len(import_result.parts)} parts")
        for i, part_data in enumerate(import_result.parts):
            try:
                logger.info(f"Processing part {i+1}/{len(import_result.parts)}: {part_data}")

                # Ensure supplier is set
                if "supplier" not in part_data:
                    part_data["supplier"] = supplier_name.upper()

                # SupplierDataMapper will handle flattening into clean custom_fields
                # No need for import-level flattening as it creates unwanted string concatenations

                # Create part using the correct method
                logger.info(f"Creating part with data: {part_data}")
                created_part_response = part_service.add_part(part_data)
                logger.info(f"Part creation response: {created_part_response}")

                # ServiceResponse uses attributes, not dictionary-style access
                if created_part_response.success:
                    created_part = created_part_response.data
                    if created_part and hasattr(created_part, "id"):
                        part_ids.append(created_part.id)
                    elif isinstance(created_part, dict) and created_part.get("id"):
                        part_ids.append(created_part["id"])
                    else:
                        logger.warning(f"Part created but no ID returned: {created_part_response}")
                else:
                    error_msg = created_part_response.message or "Unknown error"
                    raise Exception(f"Failed to create part: {error_msg}")

                # Link to order if we have one
                part_id = None
                if hasattr(created_part, "id"):
                    part_id = created_part.id
                elif isinstance(created_part, dict) and created_part.get("id"):
                    part_id = created_part["id"]

                if order_id and part_id:
                    try:
                        from MakerMatrix.models.order_models import CreateOrderItemRequest

                        order_item_request = CreateOrderItemRequest(
                            supplier_part_number=part_data.get("part_number", ""),
                            manufacturer_part_number=part_data.get("manufacturer_part_number"),
                            description=part_data.get("description", ""),
                            manufacturer=part_data.get("manufacturer"),
                            quantity_ordered=part_data.get("quantity", 1),
                            unit_price=part_data.get("unit_price", 0.0),
                            extended_price=part_data.get("quantity", 1) * part_data.get("unit_price", 0.0),
                        )
                        await order_service.add_order_item(order_id, order_item_request)
                    except Exception as e:
                        logger.warning(f"Failed to link part to order: {e}")

            except Exception as e:
                error_message = str(e)
                # Check if this is a duplicate part error
                if "already exists" in error_message.lower():
                    skipped_parts.append(
                        {
                            "part_data": part_data,
                            "reason": f"Part '{part_data.get('part_name', 'unknown')}' already exists",
                        }
                    )
                    logger.info(f"Skipped duplicate part: {part_data.get('part_name', 'unknown')}")
                else:
                    failed_items.append({"part_data": part_data, "error": error_message})
                    logger.error(f"Failed to import part: {error_message}")

        # Create enrichment task if requested and parts were imported
        enrichment_task_id = None
        if enable_enrichment and part_ids and enrichment_capabilities:
            try:
                # Parse capabilities from comma-separated string
                requested_capabilities = [cap.strip() for cap in enrichment_capabilities.split(",") if cap.strip()]

                # Validate capabilities against supplier
                supplier_capabilities = [cap.value for cap in supplier.get_capabilities()]
                valid_capabilities = [cap for cap in requested_capabilities if cap in supplier_capabilities]

                if valid_capabilities:
                    # Create enrichment task
                    from MakerMatrix.services.system.task_service import TaskService
                    from MakerMatrix.models.task_models import TaskType, TaskPriority, CreateTaskRequest

                    task_service = TaskService()

                    # Prepare input data for enrichment task
                    enrichment_input = {
                        "part_ids": part_ids,
                        "supplier": supplier_name,
                        "capabilities": valid_capabilities,
                        "import_source": f"File import: {filename}",
                        "order_id": order_id,
                    }

                    # Create the enrichment task
                    task_request = CreateTaskRequest(
                        task_type=TaskType.BULK_ENRICHMENT,
                        name=f"Enrich imported parts from {supplier_name}",
                        description=f"Enriching {len(part_ids)} parts imported from {filename}",
                        priority=TaskPriority.NORMAL,
                        input_data=enrichment_input,
                        timeout_seconds=3600,  # 1 hour timeout
                    )
                    enrichment_task_response = await task_service.create_task(task_request, current_user.id)

                    if enrichment_task_response.success:
                        # Task service returns a dict in ServiceResponse.data (from task.to_dict())
                        task_data = enrichment_task_response.data
                        enrichment_task_id = task_data["id"]  # Access 'id' key from dict
                        logger.info(f"Created enrichment task with ID: {enrichment_task_id}")
                    else:
                        raise Exception(f"Task creation failed: {enrichment_task_response.message}")
                    logger.info(f"Created enrichment task {enrichment_task_id} for {len(part_ids)} parts")

                    # Add task info to warnings
                    import_result.warnings.append(f"Enrichment task created: {enrichment_task_id}")

                else:
                    logger.warning(
                        f"No valid enrichment capabilities found for {supplier_name}: requested={requested_capabilities}, available={supplier_capabilities}"
                    )
                    import_result.warnings.append(f"No valid enrichment capabilities found for {supplier_name}")

            except Exception as e:
                logger.error(f"Failed to create enrichment task: {e}")
                import_result.warnings.append(f"Failed to create enrichment task: {str(e)}")

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
            order_id=order_id,
        )

        # Add enrichment task ID to result if created
        if enrichment_task_id:
            result.warnings.append(f"Enrichment task ID: {enrichment_task_id}")

        # Build message
        message_parts = []
        if len(part_ids) > 0:
            message_parts.append(f"{len(part_ids)} parts imported")
        if len(skipped_parts) > 0:
            message_parts.append(f"{len(skipped_parts)} parts skipped (already exist)")
        if len(failed_items) > 0:
            message_parts.append(f"{len(failed_items)} parts failed")

        message = f"Processed {total_processed} parts from {supplier_name}: " + ", ".join(message_parts)

        # Log import activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service

            activity_service = get_activity_service()
            await activity_service.log_activity(
                action="imported",
                entity_type="order",
                entity_id=order_id,
                entity_name=f"{filename} ({len(part_ids)} parts)",
                user=current_user,
                details={
                    "supplier": supplier_name,
                    "imported_count": len(part_ids),
                    "failed_count": len(failed_items),
                    "skipped_count": len(skipped_parts),
                    "file_name": filename,
                    "enrichment_enabled": enable_enrichment,
                },
            )
        except Exception as log_error:
            logger.warning(f"Failed to log import activity: {log_error}")

        return ResponseSchema(status="success", message=message, data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Always clean up supplier resources
        if supplier:
            try:
                await supplier.close()
                logger.info(f"Cleaned up supplier {supplier_name} resources")
            except Exception as e:
                logger.warning(f"Error closing supplier {supplier_name}: {e}")


@router.get("/suppliers", response_model=ResponseSchema[List[SupplierImportInfo]])
async def get_import_suppliers(current_user: UserModel = Depends(get_current_user)):
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
                config["supplier_name"].lower(): config for config in configs if config.get("enabled", False)
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

                # Check if supplier is actually configured (has working credentials)
                # First check if supplier has a config record in the database
                supplier_in_db = supplier_name.lower() in configured_suppliers

                # Debug logging for DigiKey
                if supplier_name.lower() == "digikey":
                    logger.info(f"🔍 DigiKey DB check:")
                    logger.info(f"  supplier_name={supplier_name}")
                    logger.info(f"  supplier_name.lower()={supplier_name.lower()}")
                    logger.info(f"  supplier_in_db={supplier_in_db}")
                    logger.info(f"  configured_suppliers keys={list(configured_suppliers.keys())}")

                # Test connection to determine if supplier is properly configured
                # But don't fail completely if connection test fails - some suppliers need OAuth
                connection_result = {}
                connection_success = False
                try:
                    connection_result = await supplier.test_connection()
                    connection_success = connection_result.get("success", False)

                    # A supplier is "configured" if:
                    # 1. It exists in the database configuration AND
                    # 2. Either connection succeeds OR it requires OAuth (connection test returns oauth details)
                    is_configured = supplier_in_db and (
                        connection_success or connection_result.get("details", {}).get("oauth_required", False)
                    )

                    if is_configured:
                        config_status = "configured"
                    elif supplier_in_db:
                        # Config exists but connection failed (might need credentials)
                        config_status = "partial"
                    else:
                        config_status = "not_configured"

                except Exception as e:
                    logger.debug(f"Connection test failed for {supplier_name}: {e}")
                    # If config exists in DB, consider it at least partially configured
                    is_configured = supplier_in_db
                    config_status = "partial" if supplier_in_db else "not_configured"
                    connection_result = {}  # Ensure it's defined for later use

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

                # Check enrichment capabilities
                enrichment_capabilities = []
                enrichment_available = False
                enrichment_missing_credentials = []

                # Get all enrichment-related capabilities
                enrichment_capability_types = [
                    SupplierCapability.GET_PART_DETAILS,
                    SupplierCapability.FETCH_DATASHEET,
                    SupplierCapability.FETCH_PRICING_STOCK,
                ]

                # Debug logging for DigiKey
                if supplier_name.lower() == "digikey":
                    logger.info(f"🔍 DigiKey enrichment check:")
                    logger.info(f"  is_configured={is_configured}")
                    logger.info(f"  connection_success={connection_success}")
                    logger.info(f"  connection_result={connection_result}")
                    logger.info(f"  oauth_required={connection_result.get('details', {}).get('oauth_required', False)}")

                # If supplier is configured and connection test indicated OAuth is required but working,
                # consider enrichment capabilities as available (they'll work after OAuth flow)
                if is_configured and connection_success:
                    # Connection test passed, enrichment should work
                    logger.info(f"✅ {supplier_name}: Connection test passed, enrichment available")
                    for cap in enrichment_capability_types:
                        if cap in supplier.get_capabilities():
                            enrichment_capabilities.append(cap.value)
                            enrichment_available = True
                elif is_configured and connection_result.get("details", {}).get("oauth_required", False):
                    # OAuth required but not yet completed - still show capabilities as available
                    # since the supplier IS configured, just needs OAuth flow
                    logger.info(f"✅ {supplier_name}: OAuth configured, enrichment available")
                    for cap in enrichment_capability_types:
                        if cap in supplier.get_capabilities():
                            enrichment_capabilities.append(cap.value)
                            enrichment_available = True
                else:
                    # Not configured or connection failed - check actual availability
                    logger.info(f"⚠️ {supplier_name}: Not configured or connection failed, checking credentials")
                    for cap in enrichment_capability_types:
                        if cap in supplier.get_capabilities():
                            cap_available = supplier.is_capability_available(cap)
                            if cap_available:
                                enrichment_capabilities.append(cap.value)
                                enrichment_available = True
                            else:
                                # Get missing credentials for this capability
                                missing_for_cap = supplier.get_missing_credentials_for_capability(cap)
                                enrichment_missing_credentials.extend(missing_for_cap)

                # Remove duplicates from missing credentials
                enrichment_missing_credentials = list(set(enrichment_missing_credentials))

                suppliers_info.append(
                    SupplierImportInfo(
                        name=supplier_name,
                        display_name=info.display_name,
                        supported_file_types=info.supported_file_types,
                        import_available=import_available,
                        missing_credentials=missing_creds if not is_configured else [],
                        is_configured=is_configured,
                        configuration_status=config_status,
                        enrichment_capabilities=enrichment_capabilities,
                        enrichment_available=enrichment_available,
                        enrichment_missing_credentials=enrichment_missing_credentials if not is_configured else [],
                    )
                )

            except Exception as e:
                logger.warning(f"Error checking supplier {supplier_name}: {e}")
                continue

        return ResponseSchema(
            status="success",
            message=f"Found {len(suppliers_info)} suppliers with import capability",
            data=suppliers_info,
        )

    except Exception as e:
        logger.error(f"Error getting import suppliers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get suppliers")


# ========== Helper Functions ==========


def _flatten_nested_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten nested objects in additional_properties to ensure clean key-value pairs.

    This ensures that imported parts show simple key-value pairs instead of
    nested objects like {"specifications": {...}} or {"supplier_data": {...}}.

    Args:
        data: Dictionary that may contain nested objects

    Returns:
        Flattened dictionary with simple key-value pairs
    """
    if not isinstance(data, dict):
        return {}

    flattened = {}

    try:
        for key, value in data.items():
            if isinstance(value, dict):
                # Flatten nested dictionaries
                for nested_key, nested_value in value.items():
                    # Create clean key name
                    clean_key = str(nested_key).lower().replace(" ", "_").replace("-", "_")

                    # Convert value to string for display
                    if nested_value is not None:
                        if isinstance(nested_value, (dict, list)):
                            # For complex nested objects, create a summary string
                            if isinstance(nested_value, dict) and len(nested_value) > 0:
                                # Try to create meaningful key-value string
                                pairs = []
                                for k, v in nested_value.items():
                                    if not isinstance(v, (dict, list)):
                                        pairs.append(f"{k}: {v}")
                                if pairs:
                                    flattened[clean_key] = "; ".join(pairs)
                                else:
                                    flattened[clean_key] = str(nested_value)
                            else:
                                flattened[clean_key] = str(nested_value)
                        else:
                            flattened[clean_key] = str(nested_value)
                    else:
                        flattened[clean_key] = ""
            elif isinstance(value, list):
                # Handle lists by converting to string
                if value:
                    # Convert list items to strings
                    string_items = []
                    for item in value:
                        if isinstance(item, dict):
                            # For dict items in list, try to extract meaningful info
                            if "name" in item:
                                string_items.append(str(item["name"]))
                            elif "value" in item:
                                string_items.append(str(item["value"]))
                            else:
                                string_items.append(str(item))
                        else:
                            string_items.append(str(item))
                    flattened[key] = ", ".join(string_items)
                else:
                    flattened[key] = ""
            else:
                # Keep simple key-value pairs
                flattened[key] = str(value) if value is not None else ""

    except Exception as e:
        logger.warning(f"Error flattening nested objects: {e}")
        # Return original data if flattening fails
        return data

    return flattened
