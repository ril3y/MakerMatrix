from typing import Dict, Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette import status

from MakerMatrix.models.models import AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.schemas.part_create import PartCreate, PartUpdate
from MakerMatrix.schemas.part_response import PartResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.suppliers.registry import get_available_suppliers
from MakerMatrix.services.system.task_service import task_service
from MakerMatrix.models.task_models import CreateTaskRequest, TaskType, TaskPriority

# BaseRouter infrastructure
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity, validate_service_response

router = APIRouter()

import logging

logger = logging.getLogger(__name__)


@router.post("/add_part", response_model=ResponseSchema[PartResponse])
@standard_error_handling
@log_activity("part_created", "User {username} created part")
async def add_part(
    part: PartCreate, 
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[PartResponse]:
    # Convert PartCreate to dict and include category_names
    part_data = part.model_dump()
    
    # Extract enrichment parameters before processing
    auto_enrich = part_data.pop('auto_enrich', False)
    enrichment_supplier = part_data.pop('enrichment_supplier', None)
    enrichment_capabilities = part_data.pop('enrichment_capabilities', [])
    
    # Process to add part
    part_service = PartService()
    service_response = part_service.add_part(part_data)
    created_part = validate_service_response(service_response)
    part_id = created_part["id"]

    # Handle automatic enrichment if requested
    enrichment_message = ""
    if auto_enrich and enrichment_supplier:
        enrichment_message = await _handle_enrichment(
            part_id, created_part, enrichment_supplier, enrichment_capabilities, current_user
        )

    return BaseRouter.build_success_response(
        data=PartResponse.model_validate(created_part),
        message=service_response.message + enrichment_message
    )


@router.get("/get_part_counts", response_model=ResponseSchema[int])
@standard_error_handling
async def get_part_counts() -> ResponseSchema[int]:
    part_service = PartService()
    service_response = part_service.get_part_counts()
    data = validate_service_response(service_response)
    return BaseRouter.build_success_response(
        data=data["total_parts"],
        message=service_response.message
    )


###


@router.delete("/delete_part", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
@log_activity("part_deleted", "User {username} deleted part")
async def delete_part(
        request: Request,
        current_user: UserModel = Depends(get_current_user),
        part_id: Optional[str] = Query(None, description="Part ID"),
        part_name: Optional[str] = Query(None, description="Part Name"),
        part_number: Optional[str] = Query(None, description="Part Number")
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
    delete_response = part_service.delete_part(part['id'])
    deleted_part = validate_service_response(delete_response)
    
    # Convert PartResponse to dict for the response
    part_response_obj = PartResponse.model_validate(deleted_part)
    return BaseRouter.build_success_response(
        data=part_response_obj.model_dump(),
        message=delete_response.message
    )


###

@router.get("/get_all_parts", response_model=ResponseSchema[List[PartResponse]])
@standard_error_handling
async def get_all_parts(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1)
) -> ResponseSchema[List[PartResponse]]:
    part_service = PartService()
    service_response = part_service.get_all_parts(page, page_size)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=[PartResponse.model_validate(part) for part in data["items"]],
        message=service_response.message,
        page=data["page"],
        page_size=data["page_size"],
        total_parts=data["total"]
    )


@router.get("/get_part")
@standard_error_handling
async def get_part(
        part_id: Optional[str] = Query(None),
        part_number: Optional[str] = Query(None),
        part_name: Optional[str] = Query(None),
        include: Optional[str] = Query(None, description="Comma-separated list of additional data to include (orders, datasheets, all)")
) -> ResponseSchema[PartResponse]:
    # Parse include parameter
    include_list = []
    if include:
        include_list = [item.strip() for item in include.split(",")]
    
    # Validate that at least one identifier is provided
    if not part_id and not part_number and not part_name:
        raise ValueError("At least one identifier (part_id, part_number, or part_name) must be provided")
    
    # Use the PartService to determine which parameter to use for fetching
    part_service = PartService()
    if part_id:
        service_response = part_service.get_part_by_id(part_id, include=include_list)
    elif part_number:
        service_response = part_service.get_part_by_part_number(part_number, include=include_list)
    else:  # part_name
        service_response = part_service.get_part_by_part_name(part_name, include=include_list)
    
    data = validate_service_response(service_response)
    return BaseRouter.build_success_response(
        data=PartResponse.model_validate(data),
        message=service_response.message
    )


# Duplicate endpoint removed - use /get_all_parts instead


@router.put("/update_part/{part_id}", response_model=ResponseSchema[PartResponse])
@standard_error_handling
async def update_part(
    part_id: str, 
    part_data: PartUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[PartResponse]:
    # Capture original data for change tracking
    part_service = PartService()
    original_part_response = part_service.get_part_by_id(part_id)
    original_part = validate_service_response(original_part_response)
    
    # Update the part
    service_response = part_service.update_part(part_id, part_data)
    updated_part = validate_service_response(service_response)

    # Log activity with changes
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()
        
        # Track what changed
        changes = {}
        update_dict = part_data.model_dump(exclude_unset=True)
        for key, new_value in update_dict.items():
            if key in original_part and original_part[key] != new_value:
                changes[key] = {
                    "from": original_part[key],
                    "to": new_value
                }
        
        await activity_service.log_part_updated(
            part_id=updated_part["id"],
            part_name=updated_part["part_name"],
            changes=changes,
            user=current_user,
            request=request
        )
    except Exception as e:
        logger.warning(f"Failed to log part update activity: {e}")

    return BaseRouter.build_success_response(
        data=PartResponse.model_validate(updated_part),
        message="Part updated successfully."
    )

@router.post("/search", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def advanced_search(search_params: AdvancedPartSearch) -> ResponseSchema[Dict[str, Any]]:
    """
    Perform an advanced search on parts with multiple filters and sorting options.
    """
    part_service = PartService()
    service_response = part_service.advanced_search(search_params)
    data = validate_service_response(service_response)
    
    return BaseRouter.build_success_response(
        data=data,
        message=service_response.message
    )


@router.get("/search_text", response_model=ResponseSchema[List[PartResponse]])
@standard_error_handling
async def search_parts_text(
    query: str = Query(..., min_length=1, description="Search term"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
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
        total_parts=data["total"]
    )


@router.get("/suggestions", response_model=ResponseSchema[List[str]])
@standard_error_handling
async def get_part_suggestions(
    query: str = Query(..., min_length=3, description="Search term for suggestions"),
    limit: int = Query(default=10, ge=1, le=20)
) -> ResponseSchema[List[str]]:
    """
    Get autocomplete suggestions for part names based on search query.
    Returns up to 'limit' part names that start with or contain the query.
    """
    part_service = PartService()
    service_response = part_service.get_part_suggestions(query, limit)
    data = validate_service_response(service_response)
    
    return BaseRouter.build_success_response(
        data=data,
        message=service_response.message
    )



@router.delete("/clear_all", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
@log_activity("parts_cleared", "User {username} cleared all parts")
async def clear_all_parts(
    current_user: UserModel = Depends(require_permission("admin"))
) -> ResponseSchema[Dict[str, Any]]:
    """Clear all parts from the database - USE WITH CAUTION! (Admin only)"""
    part_service = PartService()
    service_response = part_service.clear_all_parts()
    data = validate_service_response(service_response)
    
    return BaseRouter.build_success_response(
        data=data,
        message="All parts have been cleared successfully"
    )


async def _handle_enrichment(
    part_id: str, 
    created_part: dict, 
    enrichment_supplier: str, 
    enrichment_capabilities: List[str], 
    current_user: UserModel
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
                'part_id': part_id,
                'supplier': enrichment_supplier,
                'capabilities': enrichment_capabilities or ['fetch_datasheet', 'fetch_image', 'fetch_pricing']
            }
            
            task_request = CreateTaskRequest(
                task_type=TaskType.PART_ENRICHMENT,
                name=f"QR Part Enrichment - {created_part.get('part_name', 'Unknown')}",
                description=f"Auto-enrich part from {enrichment_supplier} (QR code scan)",
                priority=TaskPriority.HIGH,
                input_data=enrichment_data,
                related_entity_type="part",
                related_entity_id=part_id
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
