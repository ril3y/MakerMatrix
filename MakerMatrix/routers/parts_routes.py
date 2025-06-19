from typing import Dict, Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette import status

from MakerMatrix.models.models import PartModel, AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.schemas.part_create import PartCreate, PartUpdate
from MakerMatrix.schemas.part_response import PartResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.models import PartModel, UpdateQuantityRequest, GenericPartQuery
from MakerMatrix.services.part_service import PartService
from MakerMatrix.dependencies.auth import get_current_user, require_permission
from MakerMatrix.services.supplier_config_service import SupplierConfigService
from MakerMatrix.suppliers.registry import get_available_suppliers
from MakerMatrix.services.task_service import task_service
from MakerMatrix.models.task_models import CreateTaskRequest, TaskType, TaskPriority

router = APIRouter()

import logging

logger = logging.getLogger(__name__)


@router.post("/add_part", response_model=ResponseSchema[PartResponse])
async def add_part(
    part: PartCreate, 
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[PartResponse]:
    try:
        # Convert PartCreate to dict and include category_names
        part_data = part.model_dump()
        
        # Extract enrichment parameters before processing
        auto_enrich = part_data.pop('auto_enrich', False)
        enrichment_supplier = part_data.pop('enrichment_supplier', None)
        enrichment_capabilities = part_data.pop('enrichment_capabilities', [])
        
        # Process to add part
        response = PartService.add_part(part_data)
        created_part = response["data"]
        part_id = created_part["id"]

        # Handle automatic enrichment if requested
        enrichment_message = ""
        if auto_enrich and enrichment_supplier:
            try:
                # Validate supplier exists
                available_suppliers = get_available_suppliers()
                if enrichment_supplier not in available_suppliers:
                    enrichment_message = f" Warning: Supplier '{enrichment_supplier}' not configured on backend."
                else:
                    # Check if supplier is properly configured
                    supplier_config_service = SupplierConfigService()
                    try:
                        supplier_config_service.get_supplier_config(enrichment_supplier)
                        
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
                            created_part = enriched_part
                            enrichment_message = f" Part successfully enriched from {enrichment_supplier}."
                        else:
                            enrichment_message = f" Enrichment task started but did not complete within timeout."
                            
                    except ResourceNotFoundError:
                        enrichment_message = f" Warning: Supplier '{enrichment_supplier}' not properly configured."
                    except Exception as e:
                        logger.error(f"Enrichment task creation failed: {e}")
                        enrichment_message = f" Warning: Enrichment failed - {str(e)}"
                        
            except Exception as e:
                logger.error(f"Enrichment process failed: {e}")
                enrichment_message = f" Warning: Enrichment failed - {str(e)}"

        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_part_created(
                part_id=part_id,
                part_name=created_part.get("part_name"),
                user=current_user,
                request=request
            )
        except Exception as e:
            logger.warning(f"Failed to log part creation activity: {e}")

        # noinspection PyArgumentList
        return ResponseSchema(
            status=response["status"],
            message=response["message"] + enrichment_message,
            data=PartResponse.model_validate(created_part)
        )
    except PartAlreadyExistsError as pae:
        raise HTTPException(
            status_code=409,
            detail=f"Part with name '{part_data['part_name']}' already exists"
        )
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        if "Input should be a valid string" in str(ve):
            raise HTTPException(
                status_code=422,
                detail=[{
                    "loc": ["body", "category_names", 0],
                    "msg": "Input should be a valid string",
                    "type": "string_type"
                }]
            )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_part_counts", response_model=ResponseSchema[int])
async def get_part_counts():
    try:
        response = PartService.get_part_counts()
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=response["total_parts"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


###


@router.delete("/delete_part", response_model=ResponseSchema[Dict[str, Any]])
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
    try:
        # Validate that at least one identifier is provided
        if not part_id and not part_name and not part_number:
            raise HTTPException(
                status_code=400,
                detail="At least one identifier (part_id, part_name, or part_number) must be provided"
            )
        
        # Retrieve part using details
        part = PartService.get_part_by_details(part_id=part_id, part_name=part_name, part_number=part_number)
        
        if not part:
            identifier = part_id or part_name or part_number
            raise HTTPException(
                status_code=404,
                detail=f"Part not found with the provided identifier: {identifier}"
            )

        # Store part info for activity logging before deletion
        part_info = {
            "id": part['id'],
            "name": part['part_name']
        }

        # Perform the deletion using the actual part ID
        response = PartService.delete_part(part['id'])

        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_part_deleted(
                part_id=part_info["id"],
                part_name=part_info["name"],
                user=current_user,
                request=request
            )
        except Exception as e:
            logger.warning(f"Failed to log part deletion activity: {e}")

        # Convert PartResponse to dict for the response
        part_response_obj = PartResponse.model_validate(response["data"])
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=part_response_obj.model_dump()
        )

    except HTTPException:
        # Re-raise HTTPExceptions (like our 400 and 404 errors)
        raise
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=rnfe.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete part: {str(e)}")


###

@router.get("/get_all_parts", response_model=ResponseSchema[List[PartResponse]])
async def get_all_parts(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1)
) -> ResponseSchema[List[PartResponse]]:
    try:
        response = PartService.get_all_parts(page, page_size)

        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=[PartResponse.model_validate(part) for part in response["data"]],
            page=response["page"],
            page_size=response["page_size"],
            total_parts=response["total_parts"]
        )

    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_part")
async def get_part(
        part_id: Optional[str] = Query(None),
        part_number: Optional[str] = Query(None),
        part_name: Optional[str] = Query(None),
        include: Optional[str] = Query(None, description="Comma-separated list of additional data to include (orders, datasheets, all)")
) -> ResponseSchema[PartResponse]:
    try:
        # Parse include parameter
        include_list = []
        if include:
            include_list = [item.strip() for item in include.split(",")]
        
        # Use the PartService to determine which parameter to use for fetching
        if part_id:
            response = PartService.get_part_by_id(part_id, include=include_list)
        elif part_number:
            response = PartService.get_part_by_part_number(part_number, include=include_list)
        elif part_name:
            response = PartService.get_part_by_part_name(part_name, include=include_list)
        else:
            # If no identifier is provided, return a 400 error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one identifier (part_id, part_number, or part_name) must be provided"
            )

        return ResponseSchema(

            status=response["status"],
            message=response["message"],
            data=PartResponse.model_validate(response["data"])
        )

    except ResourceNotFoundError as rnfe:
        raise rnfe

    except HTTPException as http_exc:
        # Re-raise any caught HTTP exceptions
        raise http_exc
    except Exception as e:
        # For other exceptions, raise a general HTTP error
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all_parts/")
async def get_all_parts():
    try:
        parts = PartService.get_all_parts()
        return parts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_part/{part_id}", response_model=ResponseSchema[PartResponse])
async def update_part(
    part_id: str, 
    part_data: PartUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[PartResponse]:
    try:
        # Capture original data for change tracking
        original_part = PartService.get_part_by_id(part_id)
        
        # Use part_id from the path
        response = PartService.update_part(part_id, part_data)

        if response["status"] == "error":
            raise HTTPException(status_code=404, detail=response["message"])

        # Log activity with changes
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            
            # Track what changed
            changes = {}
            update_dict = part_data.model_dump(exclude_unset=True)
            if original_part and original_part.get("status") == "success":
                original_dict = original_part["data"]  # original_part is already a dict from service
                for key, new_value in update_dict.items():
                    if key in original_dict and original_dict[key] != new_value:
                        changes[key] = {
                            "from": original_dict[key],
                            "to": new_value
                        }
            
            await activity_service.log_part_updated(
                part_id=response["data"]["id"],
                part_name=response["data"]["part_name"],
                changes=changes,
                user=current_user,
                request=request
            )
        except Exception as e:
            logger.warning(f"Failed to log part update activity: {e}")

        # noinspection PyArgumentList
        return ResponseSchema(
            status="success",
            message="Part updated successfully.",
            data=PartResponse.model_validate(response["data"])
        )

    except ResourceNotFoundError as rnfe:
        # Let the custom exception handler handle this
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#
# @router.put("/decrement_count/")
# async def decrement_count(generic_part_query: GenericPartQuery):
#     try:
#         part, part_field, previous_quantity = PartService.decrement_count_service(generic_part_query)
#         return {
#             "message": f"Quantity decremented from {previous_quantity} to {part['quantity']} part {part[part_field]}",
#             "previous_quantity": previous_quantity,
#             "new_quantity": part['quantity']}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#

#
#
# @router.put("/update_quantity/")
# def update_part_quantity(update_request: UpdateQuantityRequest):
#     try:
#         part_updated = PartService.update_quantity_service(
#             new_quantity=update_request.new_quantity,
#             part_id=update_request.part_id,
#             part_number=update_request.part_number,
#             manufacturer_pn=update_request.manufacturer_pn
#
#         )
#
#         if part_updated:
#             return {"message": f"Quantity updated to {update_request.new_quantity}"}
#         else:
#             raise HTTPException(status_code=404, detail="Part not found")
#     except ValidationError as e:
#         raise HTTPException(status_code=422, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.post("/search-parts/")
# async def search_parts(criteria: Dict[str, str] = Body(...)):
#     if not criteria:
#         raise HTTPException(status_code=400, detail="Search criteria are required")
#     results = PartService.dynamic_search(criteria)
#     return results
#
#
# @router.get("/all_parts/")
# async def get_all_parts():
#     try:
#         parts = PartService.get_all_parts()
#         return parts
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#

#
#
# @router.get("/get_parts/")
# async def get_parts(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1)):
#     try:
#         parts = PartService.get_all_parts_paginated(page=page, page_size=page_size)
#         total_count = PartService.get_total_parts_count()
#         return {"parts": parts, "page": page, "page_size": page_size, "total": total_count}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#

#
#
# @router.get("/get_part_by_details")
# def get_part_by_details(part_id: Optional[str] = None, part_number: Optional[str] = None,
#                         part_name: Optional[str] = None):
#     try:
#         # Pass the search criteria directly to the service
#         part = PartService.get_part_by_details(part_id=part_id, part_number=part_number, part_name=part_name)
#         if part:
#             return part
#         else:
#             raise HTTPException(status_code=404, detail=f"Part Details with part_number '{part_number}' not found")
#     except HTTPException as http_exc:
#         # Re-raise HTTPException (such as the 404) without catching it
#         raise http_exc
#     except Exception as e:
#         # Catch other generic exceptions and raise a 500 error
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.get("/get_parts/")
# async def get_parts(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1)):
#     try:
#         result = PartService.get_parts_paginated(page, page_size)
#
#         if "error" in result:
#             raise HTTPException(status_code=500, detail=result["error"])
#
#         return JSONResponse(
#             content=result,
#             status_code=200
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.delete("/clear_parts")
# def clear_all_parts():
#     try:
#         PartService.part_repo.clear_all_parts()
#         return {"status": "success", "message": "All parts have been cleared."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.post("/add_part")
# async def add_part(part: PartModel, overwrite: bool = False) -> Dict:
#     try:
#         response = PartService.add_part(part, overwrite)
#
#         # Check if the response asks for confirmation
#         if response.get("status") == "part exists":
#             return {
#                 "status": "pending_confirmation",
#                 "message": response.get("message"),
#                 "data": response["data"]
#             }
#
#         # Return success response if the part was added
#         return {
#             "status": "success",
#             "message": "Part added successfully",
#             "data": response["data"]
#         }
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.delete("/delete_part/{part_id}")
# async def delete_part(part_id: str):
#     try:
#         deleted_part = PartService.part_repo.delete_part(part_id)
#         if deleted_part:
#             return {"message": "Part deleted successfully", "deleted_part_id": part_id}
#         else:
#             # Properly raise the 404 error if no part was found
#             raise HTTPException(status_code=404, detail="Part not found")
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.get("/search-parts/")
# async def search(term: str):
#     min_length = 2
#     if len(term) < min_length:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Search term must be at least {min_length} characters long."
#         )
#     try:
#         results = PartService.dynamic_search(term)
#         if isinstance(results, dict) and "error" in results:
#             raise HTTPException(status_code=500, detail=results["error"])
#         # Return results directly
#         return {"status": "success", "data": results}
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.get("/get_parts_by_location/{location_id}")
# async def get_parts_by_location(location_id: str, recursive: bool = False):
#     try:
#         result = PartService.get_parts_by_location_id(location_id, recursive)
#         if result:
#             return {
#                 "status": "success",
#                 "message": f"Parts found for location {location_id}",
#                 "location_id": location_id,
#                 "data": result,
#                 "part_count": len(result)
#             }
#         else:
#             raise HTTPException(
#                 status_code=404,
#                 detail={
#                     "status": "error",
#                     "message": f"No parts found for location {location_id}",
#                     "location_id": location_id,
#                 }
#             )
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail={
#                 "status": "error",
#                 "message": f"An error occurred while retrieving parts for location {location_id}",
#                 "location_id": location_id,
#                 "error": str(e)
#             }
#         )

@router.post("/search", response_model=ResponseSchema[Dict[str, Any]])
async def advanced_search(search_params: AdvancedPartSearch) -> ResponseSchema[Dict[str, Any]]:
    """
    Perform an advanced search on parts with multiple filters and sorting options.
    """
    try:
        response = PartService.advanced_search(search_params)
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=response["data"]
        )
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search_text", response_model=ResponseSchema[List[PartResponse]])
async def search_parts_text(
    query: str = Query(..., min_length=1, description="Search term"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
) -> ResponseSchema[List[PartResponse]]:
    """
    Simple text search across part names, numbers, and descriptions.
    """
    try:
        response = PartService.search_parts_text(query, page, page_size)
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=[PartResponse.model_validate(part) for part in response["data"]["items"]],
            page=response["data"]["page"],
            page_size=response["data"]["page_size"],
            total_parts=response["data"]["total"]
        )
    except Exception as e:
        logger.error(f"Error in text search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions", response_model=ResponseSchema[List[str]])
async def get_part_suggestions(
    query: str = Query(..., min_length=3, description="Search term for suggestions"),
    limit: int = Query(default=10, ge=1, le=20)
) -> ResponseSchema[List[str]]:
    """
    Get autocomplete suggestions for part names based on search query.
    Returns up to 'limit' part names that start with or contain the query.
    """
    try:
        response = PartService.get_part_suggestions(query, limit)
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=response["data"]
        )
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/clear_all", response_model=ResponseSchema[Dict[str, Any]])
async def clear_all_parts(
    current_user: UserModel = Depends(require_permission("admin"))
) -> ResponseSchema[Dict[str, Any]]:
    """Clear all parts from the database - USE WITH CAUTION! (Admin only)"""
    try:
        result = PartService.clear_all_parts()
        return ResponseSchema(
            status="success", 
            message="All parts have been cleared successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error clearing all parts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear all parts: {str(e)}"
        )


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
