from typing import Dict, Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette import status

from MakerMatrix.models.models import AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.schemas.part_create import PartCreate, PartUpdate
from MakerMatrix.schemas.part_response import PartResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.schemas.bulk_update import BulkUpdateRequest, BulkUpdateResponse
from MakerMatrix.schemas.bulk_delete import BulkDeleteRequest, BulkDeleteResponse
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.suppliers.registry import get_available_suppliers
from MakerMatrix.services.system.task_service import task_service
from MakerMatrix.models.task_models import CreateTaskRequest, TaskType, TaskPriority
from MakerMatrix.dependencies import get_part_service
from MakerMatrix.services.system.enrichment_requirement_validator import EnrichmentRequirementValidator
from MakerMatrix.models.enrichment_requirement_models import EnrichmentRequirementCheckResponse

# BaseRouter infrastructure
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity, validate_service_response

# WebSocket for real-time updates
from MakerMatrix.services.system.websocket_service import websocket_manager

router = APIRouter()

import logging

logger = logging.getLogger(__name__)


@router.post("/add_part", response_model=ResponseSchema[PartResponse])
@standard_error_handling
async def add_part(
    part: PartCreate,
    request: Request,
    current_user: UserModel = Depends(require_permission("parts:create")),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[PartResponse]:
    # Convert PartCreate to dict and include category_names
    part_data = part.model_dump()

    # Extract enrichment parameters before processing
    auto_enrich = part_data.pop("auto_enrich", False)
    enrichment_supplier = part_data.pop("enrichment_supplier", None)
    enrichment_capabilities = part_data.pop("enrichment_capabilities", [])

    # Process to add part
    service_response = part_service.add_part(part_data)
    created_part = validate_service_response(service_response)
    part_id = created_part["id"]

    # Log part creation activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()
        await activity_service.log_part_created(
            part_id=created_part["id"], part_name=created_part["part_name"], user=current_user, request=request
        )
    except Exception as e:
        logger.warning(f"Failed to log part creation activity: {e}")

    # Broadcast part creation via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="created",
            entity_type="part",
            entity_id=created_part["id"],
            entity_name=created_part["part_name"],
            user_id=current_user.id,
            username=current_user.username,
            entity_data=created_part,
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast part creation: {e}")

    # Handle automatic enrichment if requested
    enrichment_message = ""
    if auto_enrich and enrichment_supplier:
        enrichment_message = await _handle_enrichment(
            part_id, created_part, enrichment_supplier, enrichment_capabilities, current_user
        )

    return BaseRouter.build_success_response(
        data=PartResponse.model_validate(created_part), message=service_response.message + enrichment_message
    )


@router.get("/get_part_counts", response_model=ResponseSchema[int])
@standard_error_handling
async def get_part_counts() -> ResponseSchema[int]:
    part_service = PartService()
    service_response = part_service.get_part_counts()
    data = validate_service_response(service_response)
    return BaseRouter.build_success_response(data=data["total_parts"], message=service_response.message)


###


@router.delete("/delete_part", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def delete_part(
    request: Request,
    current_user: UserModel = Depends(require_permission("parts:delete")),
    part_id: Optional[str] = Query(None, description="Part ID"),
    part_name: Optional[str] = Query(None, description="Part Name"),
    part_number: Optional[str] = Query(None, description="Part Number"),
) -> ResponseSchema[Dict[str, Any]]:
    """
    Delete a part based on ID, part name, or part number.
    Raises HTTP 400 if no identifier is provided.
    Raises HTTP 404 if the part is not found.
    """
    # Validate that at least one identifier is provided
    if not part_id and not part_name and not part_number:
        raise ValueError("At least one identifier (part_id, part_name, or part_number) must be provided")

    # Retrieve part using details
    part_service = PartService()
    service_response = part_service.get_part_by_details(part_id=part_id, part_name=part_name, part_number=part_number)
    part = validate_service_response(service_response)

    # Perform the deletion using the actual part ID
    delete_response = part_service.delete_part(part["id"])
    deleted_part = validate_service_response(delete_response)

    # Log deletion activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()
        await activity_service.log_part_deleted(
            part_id=deleted_part["id"], part_name=deleted_part["part_name"], user=current_user, request=request
        )
    except Exception as e:
        logger.warning(f"Failed to log part deletion activity: {e}")

    # Broadcast part deletion via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="deleted",
            entity_type="part",
            entity_id=deleted_part["id"],
            entity_name=deleted_part["part_name"],
            user_id=current_user.id,
            username=current_user.username,
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast part deletion: {e}")

    # Convert PartResponse to dict for the response
    part_response_obj = PartResponse.model_validate(deleted_part)
    return BaseRouter.build_success_response(data=part_response_obj.model_dump(), message=delete_response.message)


###


@router.get("/get_all_parts", response_model=ResponseSchema[List[PartResponse]])
@standard_error_handling
async def get_all_parts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[List[PartResponse]]:
    service_response = part_service.get_all_parts(page, page_size)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=[PartResponse.model_validate(part) for part in data["items"]],
        message=service_response.message,
        page=data["page"],
        page_size=data["page_size"],
        total_parts=data["total"],
    )


@router.get("/get_part")
@standard_error_handling
async def get_part(
    part_id: Optional[str] = Query(None),
    part_number: Optional[str] = Query(None),
    part_name: Optional[str] = Query(None),
    include: Optional[str] = Query(
        None, description="Comma-separated list of additional data to include (orders, datasheets, all)"
    ),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[PartResponse]:
    # Parse include parameter
    include_list = []
    if include:
        include_list = [item.strip() for item in include.split(",")]

    # Validate that at least one identifier is provided
    if not part_id and not part_number and not part_name:
        raise ValueError("At least one identifier (part_id, part_number, or part_name) must be provided")

    # Use the PartService to determine which parameter to use for fetching
    if part_id:
        service_response = part_service.get_part_by_id(part_id, include=include_list)
    elif part_number:
        service_response = part_service.get_part_by_part_number(part_number, include=include_list)
    else:  # part_name
        service_response = part_service.get_part_by_part_name(part_name, include=include_list)

    data = validate_service_response(service_response)
    return BaseRouter.build_success_response(data=PartResponse.model_validate(data), message=service_response.message)


# Duplicate endpoint removed - use /get_all_parts instead


@router.put("/update_part/{part_id}", response_model=ResponseSchema[PartResponse])
@standard_error_handling
async def update_part(
    part_id: str,
    part_data: PartUpdate,
    request: Request,
    current_user: UserModel = Depends(require_permission("parts:update")),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[PartResponse]:
    # Capture original data for change tracking
    original_part_response = part_service.get_part_by_id(part_id)
    original_part = validate_service_response(original_part_response)

    # Update the part
    service_response = part_service.update_part(part_id, part_data)
    updated_part = validate_service_response(service_response)

    # Log activity with changes
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        from MakerMatrix.services.data.location_service import LocationService

        activity_service = get_activity_service()
        location_service = LocationService()

        # Helper function to resolve location UUIDs to names
        def resolve_location_name(location_id: str) -> str:
            if not location_id:
                return "No Location"
            try:
                location_response = location_service.get_location_by_id(location_id)
                if location_response and location_response.get("data"):
                    return location_response["data"].get("name", location_id)
                return location_id
            except:
                return location_id

        # Track what changed
        changes = {}
        update_dict = part_data.model_dump(exclude_unset=True)
        for key, new_value in update_dict.items():
            if key in original_part and original_part[key] != new_value:
                # Special handling for location_id to show human-readable names
                if key == "location_id":
                    changes[key] = {
                        "from": resolve_location_name(original_part[key]),
                        "to": resolve_location_name(new_value),
                    }
                else:
                    changes[key] = {"from": original_part[key], "to": new_value}

        await activity_service.log_part_updated(
            part_id=updated_part["id"],
            part_name=updated_part["part_name"],
            changes=changes,
            user=current_user,
            request=request,
        )
    except Exception as e:
        logger.warning(f"Failed to log part update activity: {e}")

    # Broadcast part update via websocket
    try:
        # Use the tracked changes from activity logging
        changes_dict = {}
        update_dict = part_data.model_dump(exclude_unset=True)
        for key, new_value in update_dict.items():
            if key in original_part and original_part[key] != new_value:
                changes_dict[key] = {"from": original_part[key], "to": new_value}

        await websocket_manager.broadcast_crud_event(
            action="updated",
            entity_type="part",
            entity_id=updated_part["id"],
            entity_name=updated_part["part_name"],
            user_id=current_user.id,
            username=current_user.username,
            changes=changes_dict,
            entity_data=updated_part,
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast part update: {e}")

    return BaseRouter.build_success_response(
        data=PartResponse.model_validate(updated_part), message="Part updated successfully."
    )


@router.post("/search", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def advanced_search(
    search_params: AdvancedPartSearch, part_service: PartService = Depends(get_part_service)
) -> ResponseSchema[Dict[str, Any]]:
    """
    Perform an advanced search on parts with multiple filters and sorting options.
    """
    service_response = part_service.advanced_search(search_params)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=data, message=service_response.message)


@router.get("/search_text", response_model=ResponseSchema[List[PartResponse]])
@standard_error_handling
async def search_parts_text(
    query: str = Query(..., min_length=1, description="Search term"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ResponseSchema[List[PartResponse]]:
    """
    Simple text search across part names, numbers, and descriptions.
    """
    part_service = PartService()
    service_response = part_service.search_parts_text(query, page, page_size)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=[PartResponse.model_validate(part) for part in data["items"]],
        message=service_response.message,
        page=data["page"],
        page_size=data["page_size"],
        total_parts=data["total"],
    )


@router.get("/suggestions", response_model=ResponseSchema[List[str]])
@standard_error_handling
async def get_part_suggestions(
    query: str = Query(..., min_length=3, description="Search term for suggestions"),
    limit: int = Query(default=10, ge=1, le=20),
) -> ResponseSchema[List[str]]:
    """
    Get autocomplete suggestions for part names based on search query.
    Returns up to 'limit' part names that start with or contain the query.
    """
    part_service = PartService()
    service_response = part_service.get_part_suggestions(query, limit)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=data, message=service_response.message)


@router.delete("/clear_all", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
@log_activity("parts_cleared", "User {username} cleared all parts")
async def clear_all_parts(
    current_user: UserModel = Depends(require_permission("admin")),
) -> ResponseSchema[Dict[str, Any]]:
    """Clear all parts from the database - USE WITH CAUTION! (Admin only)"""
    part_service = PartService()
    service_response = part_service.clear_all_parts()
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=data, message="All parts have been cleared successfully")


async def _handle_enrichment(
    part_id: str,
    created_part: dict,
    enrichment_supplier: str,
    enrichment_capabilities: List[str],
    current_user: UserModel,
) -> str:
    """
    Handle automatic enrichment for a newly created part.

    Returns:
        String message about enrichment status
    """
    try:
        # Validate supplier exists
        available_suppliers = get_available_suppliers()
        if enrichment_supplier not in available_suppliers:
            return f" Warning: Supplier '{enrichment_supplier}' not configured on backend."

        # Check if supplier is properly configured
        supplier_config_service = SupplierConfigService()
        try:
            # Try enrichment_supplier as-is first, then try uppercase version
            try:
                supplier_config_service.get_supplier_config(enrichment_supplier)
            except ResourceNotFoundError:
                # Try uppercase version for backward compatibility
                supplier_config_service.get_supplier_config(enrichment_supplier.upper())

            # Create enrichment task
            enrichment_data = {
                "part_id": part_id,
                "supplier": enrichment_supplier,
                "capabilities": enrichment_capabilities or ["fetch_datasheet", "fetch_image", "fetch_pricing"],
            }

            task_request = CreateTaskRequest(
                task_type=TaskType.PART_ENRICHMENT,
                name=f"QR Part Enrichment - {created_part.get('part_name', 'Unknown')}",
                description=f"Auto-enrich part from {enrichment_supplier} (QR code scan)",
                priority=TaskPriority.HIGH,
                input_data=enrichment_data,
                related_entity_type="part",
                related_entity_id=part_id,
            )

            enrichment_task = await task_service.create_task(task_request, user_id=current_user.id)
            enrichment_message = f" Enrichment task created (ID: {enrichment_task.id})."

            # Wait for enrichment to complete and return enriched part
            # Note: This is a simplified approach - in production you might want to use WebSocket or polling
            import asyncio

            enriched_part = await _wait_for_enrichment_completion(part_id, enrichment_task.id, timeout=30)
            if enriched_part:
                created_part.update(enriched_part)
                return f" Part successfully enriched from {enrichment_supplier}."
            else:
                return f" Enrichment task started but did not complete within timeout."

        except ResourceNotFoundError:
            return f" Warning: Supplier '{enrichment_supplier}' not properly configured."
        except Exception as e:
            logger.error(f"Enrichment task creation failed: {e}")
            return f" Warning: Enrichment failed - {str(e)}"

    except Exception as e:
        logger.error(f"Enrichment process failed: {e}")
        return f" Warning: Enrichment failed - {str(e)}"


async def _wait_for_enrichment_completion(part_id: str, task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Wait for enrichment task to complete and return the enriched part data.

    Args:
        part_id: The part ID to check for enrichment
        task_id: The enrichment task ID to monitor
        timeout: Maximum time to wait in seconds

    Returns:
        Enriched part data if successful, None if timeout or failure
    """
    import asyncio
    from MakerMatrix.models.task_models import TaskStatus

    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            # Check task status
            task = await task_service.get_task(task_id)

            if task.status == TaskStatus.COMPLETED:
                # Task completed, fetch the enriched part
                response = PartService.get_part_by_id(part_id)
                if response["status"] == "success":
                    return response["data"]
                else:
                    logger.error(f"Failed to fetch enriched part {part_id}: {response.get('message')}")
                    return None

            elif task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                logger.warning(f"Enrichment task {task_id} failed or was cancelled")
                return None

            # Task still running, wait a bit
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error checking enrichment task status: {e}")
            return None

    # Timeout reached
    logger.warning(f"Enrichment task {task_id} did not complete within {timeout} seconds")
    return None


# === ALLOCATION TRANSFER ENDPOINTS ===


@router.post("/parts/{part_id}/transfer", response_model=ResponseSchema[PartResponse])
@standard_error_handling
async def transfer_part_quantity(
    part_id: str,
    from_location_id: str = Query(..., description="Source location ID"),
    to_location_id: str = Query(..., description="Destination location ID"),
    quantity: int = Query(..., gt=0, description="Quantity to transfer"),
    notes: Optional[str] = Query(None, description="Transfer notes"),
    current_user: UserModel = Depends(require_permission("parts:update")),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[PartResponse]:
    """
    Transfer quantity from one location to another for a part.

    Example:
        POST /api/parts/{part_id}/transfer?from_location_id=xxx&to_location_id=yyy&quantity=100

    This will:
    - Reduce quantity at source location
    - Increase (or create) quantity at destination location
    - Track transfer in allocation notes
    """
    try:
        response = part_service.transfer_quantity(
            part_id=part_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            notes=notes,
        )

        if not response.success:
            raise HTTPException(status_code=400, detail=response.message)

        return BaseRouter.build_success_response(
            data=PartResponse.model_validate(response.data), message=response.message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transferring quantity: {e}")
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")


@router.get(
    "/parts/{part_id}/enrichment-requirements/{supplier}",
    response_model=ResponseSchema[EnrichmentRequirementCheckResponse],
)
async def check_enrichment_requirements(
    part_id: str,
    supplier: str,
    current_user: UserModel = Depends(get_current_user),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[EnrichmentRequirementCheckResponse]:
    """
    Check if a part meets the requirements for enrichment from a specific supplier.

    This endpoint validates that a part has the necessary fields (like supplier_part_number)
    before attempting enrichment. It returns detailed information about:
    - Required fields and whether they're present
    - Recommended fields for better enrichment results
    - Helpful suggestions for what to add

    Args:
        part_id: UUID of the part to check
        supplier: Supplier name (e.g., 'lcsc', 'digikey')
        current_user: Current authenticated user
        part_service: Injected part service

    Returns:
        ResponseSchema containing EnrichmentRequirementCheckResponse with validation results

    Example:
        GET /api/parts/123e4567-e89b-12d3-a456-426614174000/enrichment-requirements/lcsc

        Response:
        {
            "status": "success",
            "message": "Enrichment requirements check completed",
            "data": {
                "supplier_name": "lcsc",
                "part_id": "123e4567-e89b-12d3-a456-426614174000",
                "can_enrich": false,
                "required_checks": [...],
                "missing_required": ["supplier_part_number"],
                "suggestions": ["Add LCSC Part Number (e.g., C25804): Required to look up part details"]
            }
        }
    """
    try:
        # Get the part
        part_response = part_service.get_part_by_details(part_id=part_id)

        if not part_response.success:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_response.message}")

        part = part_response.data

        # Create validator and check requirements
        validator = EnrichmentRequirementValidator()
        check_result = validator.validate_part_for_enrichment(part, supplier)

        # Convert to response format
        response_data = EnrichmentRequirementCheckResponse(
            supplier_name=check_result.supplier_name,
            part_id=check_result.part_id,
            can_enrich=check_result.can_enrich,
            required_checks=[
                {
                    "field_name": check.field_name,
                    "display_name": check.display_name,
                    "is_present": check.is_present,
                    "current_value": check.current_value,
                    "validation_passed": check.validation_passed,
                    "validation_message": check.validation_message,
                }
                for check in check_result.required_checks
            ],
            recommended_checks=[
                {
                    "field_name": check.field_name,
                    "display_name": check.display_name,
                    "is_present": check.is_present,
                    "current_value": check.current_value,
                }
                for check in check_result.recommended_checks
            ],
            missing_required=check_result.missing_required,
            missing_recommended=check_result.missing_recommended,
            warnings=check_result.warnings,
            suggestions=check_result.suggestions,
        )

        message = (
            "Part can be enriched" if check_result.can_enrich else "Part is missing required fields for enrichment"
        )

        return BaseRouter.build_success_response(data=response_data, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking enrichment requirements: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check enrichment requirements: {str(e)}")


@router.get("/enrichment-requirements/{supplier}", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier_enrichment_requirements(
    supplier: str, current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """
    Get enrichment requirements for a specific supplier.

    This endpoint returns what part fields are required/recommended for enrichment
    from a specific supplier. Useful for displaying requirements when creating a new part.

    Args:
        supplier: Supplier name (e.g., 'lcsc', 'digikey')
        current_user: Current authenticated user

    Returns:
        ResponseSchema containing enrichment requirements

    Example:
        GET /api/parts/enrichment-requirements/lcsc

        Response:
        {
            "status": "success",
            "data": {
                "supplier_name": "lcsc",
                "display_name": "LCSC Electronics",
                "description": "...",
                "required_fields": [
                    {
                        "field_name": "supplier_part_number",
                        "display_name": "LCSC Part Number",
                        "description": "...",
                        "example": "C25804"
                    }
                ]
            }
        }
    """
    try:
        validator = EnrichmentRequirementValidator()
        requirements = validator.get_supplier_requirements(supplier)

        if not requirements:
            raise HTTPException(status_code=404, detail=f"Enrichment requirements not found for supplier '{supplier}'")

        # Convert to dict for response
        response_data = {
            "supplier_name": requirements.supplier_name,
            "display_name": requirements.display_name,
            "description": requirements.description,
            "required_fields": [
                {
                    "field_name": field.field_name,
                    "display_name": field.display_name,
                    "description": field.description,
                    "example": field.example,
                    "validation_pattern": field.validation_pattern,
                }
                for field in requirements.required_fields
            ],
            "recommended_fields": [
                {
                    "field_name": field.field_name,
                    "display_name": field.display_name,
                    "description": field.description,
                    "example": field.example,
                }
                for field in requirements.recommended_fields
            ],
        }

        return BaseRouter.build_success_response(
            data=response_data, message=f"Retrieved enrichment requirements for {supplier}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enrichment requirements for {supplier}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get enrichment requirements: {str(e)}")


@router.post("/enrich-from-supplier", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def enrich_part_from_supplier(
    supplier_name: str,
    part_identifier: str,
    force_refresh: bool = False,
    current_user: UserModel = Depends(require_permission("parts:update")),
) -> ResponseSchema[Dict[str, Any]]:
    """
    Instant Enrichment endpoint - enrich part data immediately from supplier.

    This endpoint handles URL-based and part number-based enrichment by:
    1. Detecting if the identifier is a URL and extracting the part identifier
    2. Using the unified EnrichmentEngine to fetch and standardize data
    3. Returning enriched data ready for form population

    This endpoint uses the SAME enrichment logic as the background enrichment
    task (Enrich button), ensuring maximum code reuse and consistency.

    Args:
        supplier_name: Supplier name (e.g., 'digikey', 'mouser', 'mcmaster-carr')
        part_identifier: URL or part number/MPN
        force_refresh: Force refresh of cached data
        current_user: Current authenticated user

    Returns:
        ResponseSchema containing standardized part data

    Example:
        POST /api/parts/enrich-from-supplier?supplier_name=digikey&part_identifier=https://www.digikey.com/...

        Response:
        {
            "status": "success",
            "data": {
                "part_name": "STM32F103C8T6",
                "manufacturer": "STMicroelectronics",
                "manufacturer_part_number": "STM32F103C8T6",
                "description": "...",
                "unit_price": 6.08,
                "currency": "USD",
                "additional_properties": {
                    "Core Processor": "ARM® Cortex®-M3",
                    "Speed": "72MHz",
                    ...
                }
            }
        }
    """
    try:
        from MakerMatrix.suppliers.registry import get_supplier
        from MakerMatrix.services.system.enrichment_engine import enrichment_engine
        import re

        # Get supplier instance to check URL patterns and configure credentials
        try:
            supplier = get_supplier(supplier_name)
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"Supplier '{supplier_name}' not configured or available: {str(e)}"
            )

        # Configure supplier with credentials from database/env
        try:
            config_service = SupplierConfigService()

            # Get supplier config and credentials
            supplier_config = config_service.get_supplier_config(supplier_name)
            credentials = config_service.get_supplier_credentials(supplier_name)

            # Build config dict
            config_dict = {
                "base_url": supplier_config.get("base_url", ""),
                "request_timeout": supplier_config.get("timeout_seconds", 30),
                "max_retries": supplier_config.get("max_retries", 3),
                "rate_limit_per_minute": supplier_config.get("rate_limit_per_minute", 60),
            }

            # Add custom parameters if available
            custom_params = supplier_config.get("custom_parameters", {})
            if custom_params:
                config_dict.update(custom_params)

            # Configure the supplier
            supplier.configure(credentials or {}, config_dict)
            logger.info(f"Configured {supplier_name} supplier with credentials")

        except Exception as e:
            logger.warning(f"Could not load credentials for {supplier_name}: {e}")
            # Continue anyway - some suppliers may work without credentials via scraping

        # Check if part_identifier is a URL and extract part identifier if needed
        extracted_identifier = part_identifier
        if part_identifier.startswith("http"):
            # Try to extract part identifier from URL using enrichment field mappings
            field_mappings = supplier.get_enrichment_field_mappings()

            for mapping in field_mappings:
                for pattern in mapping.url_patterns:
                    match = re.search(pattern, part_identifier)
                    if match:
                        extracted_identifier = match.group(1)
                        logger.info(f"Extracted '{extracted_identifier}' from URL using pattern: {pattern}")
                        break
                if extracted_identifier != part_identifier:
                    break

            if extracted_identifier == part_identifier:
                logger.warning(f"Could not extract part identifier from URL: {part_identifier}")
                # Continue anyway - supplier might handle URLs directly (like McMaster-Carr)
                extracted_identifier = part_identifier

        # Use EnrichmentEngine for unified enrichment logic
        # This is the SAME code path used by background enrichment
        enrichment_result = await enrichment_engine.enrich_part(
            supplier_name=supplier_name, part_identifier=extracted_identifier, force_refresh=force_refresh
        )

        if not enrichment_result["success"]:
            error_msg = enrichment_result.get("error", "Unknown error")
            logger.error(f"Enrichment failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Failed to enrich part: {error_msg}")

        standardized_data = enrichment_result["data"]
        enrichment_method = enrichment_result.get("enrichment_method", "unknown")

        logger.info(
            f"✓ Instant enrichment successful via {enrichment_method}: {standardized_data.get('part_name', 'Unknown')}"
        )

        return BaseRouter.build_success_response(
            data=standardized_data, message=f"Part data enriched from {supplier_name} via {enrichment_method}"
        )

    except ValueError as e:
        # Handle configuration errors (no credentials/scraper) as 400 Bad Request
        logger.warning(f"Enrichment configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enriching part from supplier: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enrich part data: {str(e)}")


@router.post("/bulk_update", response_model=ResponseSchema[BulkUpdateResponse])
@standard_error_handling
async def bulk_update_parts(
    request: BulkUpdateRequest,
    current_user: UserModel = Depends(require_permission("parts:update")),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[BulkUpdateResponse]:
    """
    Bulk update multiple parts with shared field values.

    Only enabled fields will be updated. Supports:
    - Updating supplier
    - Updating primary location
    - Setting minimum quantity
    - Adding categories to parts
    - Removing categories from parts
    """
    try:
        # Validate that at least one update field is provided
        has_updates = (
            request.supplier is not None
            or request.location_id is not None
            or request.minimum_quantity is not None
            or (request.add_categories and len(request.add_categories) > 0)
            or (request.remove_categories and len(request.remove_categories) > 0)
        )

        if not has_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided for update"
            )

        if not request.part_ids or len(request.part_ids) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Part IDs list cannot be empty")

        # Call service layer for bulk update
        service_response = part_service.bulk_update_parts(request.model_dump())
        result = validate_service_response(service_response)

        # Broadcast bulk update via websocket for successfully updated parts
        try:
            # Build change details from request
            changes_info = {}
            if request.supplier is not None:
                changes_info["supplier"] = request.supplier
            if request.location_id is not None:
                changes_info["location_id"] = request.location_id
            if request.minimum_quantity is not None:
                changes_info["minimum_quantity"] = request.minimum_quantity
            if request.add_categories:
                changes_info["categories_added"] = request.add_categories
            if request.remove_categories:
                changes_info["categories_removed"] = request.remove_categories

            await websocket_manager.broadcast_crud_event(
                action="bulk_updated",
                entity_type="part",
                entity_id="bulk",  # Special ID for bulk operations
                entity_name=f"{result['updated_count']} parts",
                user_id=current_user.id,
                username=current_user.username,
                details={
                    "part_ids": request.part_ids,
                    "updated_count": result["updated_count"],
                    "failed_count": result["failed_count"],
                    "changes": changes_info,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast bulk update: {e}")

        return BaseRouter.build_success_response(
            data=result, message=f"Successfully updated {result['updated_count']} part(s)"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")


@router.post("/bulk_delete", response_model=ResponseSchema[BulkDeleteResponse])
@standard_error_handling
async def bulk_delete_parts(
    request: BulkDeleteRequest,
    current_user: UserModel = Depends(require_permission("parts:delete")),
    part_service: PartService = Depends(get_part_service),
) -> ResponseSchema[BulkDeleteResponse]:
    """
    Bulk delete multiple parts with associated file cleanup.

    This endpoint will:
    - Delete all specified parts from the database
    - Clean up associated image files
    - Clean up associated datasheet files
    - Return a summary of the operation
    """
    try:
        if not request.part_ids or len(request.part_ids) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Part IDs list cannot be empty")

        # Call service layer for bulk delete
        service_response = part_service.bulk_delete_parts(request.part_ids)
        result = validate_service_response(service_response)

        # Broadcast bulk delete via websocket
        try:
            await websocket_manager.broadcast_crud_event(
                action="bulk_deleted",
                entity_type="part",
                entity_id="bulk",  # Special ID for bulk operations
                entity_name=f"{result['deleted_count']} parts",
                user_id=current_user.id,
                username=current_user.username,
                details={
                    "part_ids": request.part_ids,
                    "deleted_count": result["deleted_count"],
                    "files_deleted": result["files_deleted"],
                    "failed_count": result["failed_count"],
                },
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast bulk delete: {e}")

        return BaseRouter.build_success_response(
            data=result,
            message=f"Successfully deleted {result['deleted_count']} part(s) and {result['files_deleted']} file(s)",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")
