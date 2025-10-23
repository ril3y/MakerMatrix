from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field

from MakerMatrix.models.models import LocationModel, LocationQueryModel
from MakerMatrix.models.models import LocationUpdate
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.auth.dependencies import get_current_user, oauth2_scheme
from MakerMatrix.auth.guards import require_permission, require_admin
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity, validate_service_response

# WebSocket for real-time updates
from MakerMatrix.services.system.websocket_service import websocket_manager


class LocationCreateRequest(BaseModel):
    """Request model for creating locations with required name."""

    # Existing fields
    name: str  # Required
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: str = "standard"
    image_url: Optional[str] = None
    emoji: Optional[str] = None

    # NEW: Container slot generation fields (Phase 1)
    slot_count: Optional[int] = Field(None, ge=1, le=200, description="Number of slots to auto-generate")
    slot_naming_pattern: Optional[str] = Field("Slot {n}", description="Pattern for slot names. Use {n}, {row}, {col}")
    slot_layout_type: Optional[str] = Field("simple", description="Layout type: 'simple', 'grid', or 'custom'")

    # Grid layout fields
    grid_rows: Optional[int] = Field(None, ge=1, le=20, description="Number of rows for grid layout")
    grid_columns: Optional[int] = Field(None, ge=1, le=20, description="Number of columns for grid layout")

    # Custom layout (Phase 2+ ready)
    slot_layout: Optional[Dict[str, Any]] = Field(None, description="Custom layout JSON (Phase 2+)")


router = APIRouter()
base_router = BaseRouter()


@router.get("/get_all_locations")
@standard_error_handling
async def get_all_locations(
    hide_auto_slots: bool = Query(False, description="Hide auto-generated container slots")
) -> ResponseSchema[List[Dict[str, Any]]]:
    location_service = LocationService()
    service_response = location_service.get_all_locations()

    validate_service_response(service_response)

    # Locations are already dictionaries from the service
    locations = service_response.data

    # Filter auto-generated slots if requested
    if hide_auto_slots:
        locations = [loc for loc in locations if not loc.get("is_auto_generated_slot", False)]

    location_data = []
    for location in locations:
        location_dict = {
            "id": location["id"],
            "name": location["name"],
            "description": location.get("description"),
            "parent_id": location.get("parent_id"),
            "location_type": location.get("location_type"),
            "image_url": location.get("image_url"),
            "emoji": location.get("emoji"),
            "parts_count": 0,  # Set to 0 since we don't have parts loaded in basic fetch
            # Container slot generation fields
            "slot_count": location.get("slot_count"),
            "slot_naming_pattern": location.get("slot_naming_pattern"),
            "slot_layout_type": location.get("slot_layout_type"),
            "grid_rows": location.get("grid_rows"),
            "grid_columns": location.get("grid_columns"),
            "slot_layout": location.get("slot_layout"),
            # Per-slot identification
            "is_auto_generated_slot": location.get("is_auto_generated_slot", False),
            "slot_number": location.get("slot_number"),
            "slot_metadata": location.get("slot_metadata"),
        }
        location_data.append(location_dict)

    return base_router.build_success_response(message=service_response.message, data=location_data)


@router.get("/get_location")
@standard_error_handling
async def get_location(location_id: Optional[str] = None, name: Optional[str] = None) -> ResponseSchema[Dict[str, Any]]:
    if not location_id and not name:
        raise HTTPException(status_code=400, detail="Either 'location_id' or 'name' must be provided")

    location_service = LocationService()
    location_query = LocationQueryModel(id=location_id, name=name)
    service_response = location_service.get_location(location_query)

    validate_service_response(service_response)

    return base_router.build_success_response(
        message=service_response.message, data=service_response.data  # Already a dictionary from service
    )


@router.put("/update_location/{location_id}")
@standard_error_handling
@log_activity("location_updated", "User {username} updated location")
async def update_location(
    location_id: str,
    location_data: LocationUpdate,
    request: Request,
    current_user: UserModel = Depends(require_permission("locations:update")),
) -> ResponseSchema[Dict[str, Any]]:
    """
    Update a location's fields. This endpoint can update any combination of name, description, parent_id, and location_type.

    Args:
        location_id: The ID of the location to update
        location_data: The fields to update (name, description, parent_id, location_type)
        request: FastAPI request object for activity logging
        current_user: Current authenticated user for activity logging

    Returns:
        ResponseSchema: A response containing the updated location data
    """
    # Convert the Pydantic model to a dict
    # Only include fields that were explicitly set in the request
    update_data = location_data.model_dump(exclude_unset=True)
    print(f"[DEBUG] Update data being sent to service: {update_data}")

    location_service = LocationService()
    service_response = location_service.update_location(location_id, update_data)

    validate_service_response(service_response)

    updated_location = service_response.data

    # Log activity to database for recent activity widget
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()

        # Create changes dict from the update data
        changes = {k: v for k, v in location_data.model_dump().items() if v is not None}

        await activity_service.log_location_updated(
            location_id=location_id,
            location_name=updated_location["name"],
            changes=changes,
            user=current_user,
            request=request,
        )
    except Exception as activity_error:
        print(f"Failed to log location update activity: {activity_error}")
        # Don't fail the main operation if activity logging fails

    # Broadcast location update via websocket
    try:
        # Create changes dict from the update data
        changes_dict = {k: v for k, v in location_data.model_dump().items() if v is not None}

        await websocket_manager.broadcast_crud_event(
            action="updated",
            entity_type="location",
            entity_id=location_id,
            entity_name=updated_location["name"],
            user_id=current_user.id,
            username=current_user.username,
            changes=changes_dict,
            entity_data=updated_location,
        )
    except Exception as e:
        print(f"Failed to broadcast location update: {e}")

    return base_router.build_success_response(
        message="Location updated successfully", data=updated_location  # Already a dictionary from service
    )


@router.post("/add_location")
@standard_error_handling
@log_activity("location_created", "User {username} created location")
async def add_location(
    location_data: LocationCreateRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("locations:create")),
) -> ResponseSchema[Dict[str, Any]]:
    location_service = LocationService()

    # Check if this is a container creation with slots
    if location_data.slot_count is not None and location_data.slot_count > 0:
        # Use container creation method
        service_response = location_service.create_container_with_slots(location_data.model_dump())
    else:
        # Use regular location creation
        service_response = location_service.add_location(location_data.model_dump())

    validate_service_response(service_response)

    # Handle both regular location and container creation responses
    if location_data.slot_count is not None and location_data.slot_count > 0:
        # Container creation returns {"container": {...}, "slots_created": N}
        container = service_response.data.get("container", service_response.data)
        slots_created = service_response.data.get("slots_created", 0)
        location = container
        success_message = f"Container '{location['name']}' created successfully with {slots_created} slots"
        response_data = service_response.data  # Include full response with slots_created
    else:
        # Regular location creation
        location = service_response.data
        success_message = "Location added successfully"
        response_data = location

    print(f"[DEBUG] Location created successfully: {location['id']}")

    # Log activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()
        await activity_service.log_location_created(
            location_id=location["id"], location_name=location["name"], user=current_user, request=request
        )
    except Exception as e:
        print(f"Failed to log location creation activity: {e}")

    # Broadcast location creation via websocket
    try:
        # Include slot count in entity_data for container creation
        broadcast_data = location.copy()
        if location_data.slot_count is not None and location_data.slot_count > 0:
            broadcast_data["slots_created"] = service_response.data.get("slots_created", 0)

        await websocket_manager.broadcast_crud_event(
            action="created",
            entity_type="location",
            entity_id=location["id"],
            entity_name=location["name"],
            user_id=current_user.id,
            username=current_user.username,
            entity_data=broadcast_data,
        )
    except Exception as e:
        print(f"Failed to broadcast location creation: {e}")

    return base_router.build_success_response(message=success_message, data=response_data)


@router.get("/get_location_details/{location_id}")
@standard_error_handling
async def get_location_details(location_id: str) -> ResponseSchema[Dict[str, Any]]:
    """
    Get detailed information about a location, including its children.

    Args:
        location_id (str): The ID of the location to get details for.

    Returns:
        ResponseSchema: A response containing the location details and its children.
    """
    location_service = LocationService()
    service_response = location_service.get_location_details(location_id)

    validate_service_response(service_response)

    return base_router.build_success_response(message=service_response.message, data=service_response.data)


@router.get("/get_location_path/{location_id}", response_model=ResponseSchema)
@standard_error_handling
async def get_location_path(location_id: str) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get the full path from a location to its root.

    Args:
        location_id: The ID of the location to get the path for

    Returns:
        A ResponseSchema containing the location path with parent references
    """
    location_service = LocationService()
    service_response = location_service.get_location_path(location_id)

    validate_service_response(service_response)

    return base_router.build_success_response(message=service_response.message, data=service_response.data)


@router.get("/get_container_slots/{container_id}")
@standard_error_handling
async def get_container_slots(
    container_id: str, include_occupancy: bool = Query(True, description="Include occupancy information for each slot")
) -> ResponseSchema[List[Dict[str, Any]]]:
    """
    Get all slots for a container with optional occupancy information.

    This endpoint is used by the hierarchical location picker to show slots
    when a container is selected, along with which slots are occupied by parts.

    Args:
        container_id: The ID of the container location
        include_occupancy: Whether to include occupancy data (part counts, quantities)

    Returns:
        A ResponseSchema containing a list of slot dictionaries with:
        - All slot fields (id, name, slot_number, slot_metadata, etc.)
        - occupancy object (if include_occupancy=True):
            - is_occupied: bool
            - part_count: int (number of different parts)
            - total_quantity: int (sum of all quantities)
            - parts: list of {part_id, quantity, is_primary}
    """
    location_service = LocationService()
    service_response = location_service.get_container_slots(container_id, include_occupancy)

    validate_service_response(service_response)

    return base_router.build_success_response(message=service_response.message, data=service_response.data)


@router.get("/preview-location-delete/{location_id}")
@standard_error_handling
async def preview_location_delete(location_id: str) -> ResponseSchema:
    """
    Preview what will be affected when deleting a location.

    Args:
        location_id: The ID of the location to preview deletion for

    Returns:
        ResponseSchema: A response containing the preview information
    """
    location_service = LocationService()
    service_response = location_service.preview_location_delete(location_id)

    validate_service_response(service_response)

    return base_router.build_success_response(message=service_response.message, data=service_response.data)


@router.delete("/delete_location/{location_id}")
@standard_error_handling
@log_activity("location_deleted", "User {username} deleted location")
async def delete_location(
    location_id: str, request: Request, current_user: UserModel = Depends(require_permission("locations:delete"))
) -> ResponseSchema:
    response = LocationService.delete_location(location_id)

    # Log activity to database for recent activity widget
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()

        await activity_service.log_location_deleted(
            location_id=location_id,
            location_name=response["data"]["deleted_location_name"],
            user=current_user,
            request=request,
        )
    except Exception as activity_error:
        print(f"Failed to log location deletion activity: {activity_error}")
        # Don't fail the main operation if activity logging fails

    # Broadcast location deletion via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="deleted",
            entity_type="location",
            entity_id=location_id,
            entity_name=response["data"]["deleted_location_name"],
            user_id=current_user.id,
            username=current_user.username,
            details=response["data"],  # Include details about what was affected
        )
    except Exception as e:
        print(f"Failed to broadcast location deletion: {e}")

    return base_router.build_success_response(message=response["message"], data=response["data"])


@router.delete("/cleanup-locations")
@standard_error_handling
async def cleanup_locations(current_user: UserModel = Depends(require_admin)) -> ResponseSchema[Dict[str, Any]]:
    """
    Clean up locations by removing those with invalid parent IDs and their descendants.

    Returns:
        ResponseSchema: A response containing the cleanup results.
    """
    response = LocationService.cleanup_locations()
    if response["status"] == "success":
        return base_router.build_success_response(
            message=response.get("message", "Locations cleaned up successfully"), data=response.get("data")
        )
    else:
        raise HTTPException(status_code=500, detail=response.get("message", "Failed to clean up locations"))


# Deprecated endpoint removed - use /preview-location-delete/{location_id} instead
