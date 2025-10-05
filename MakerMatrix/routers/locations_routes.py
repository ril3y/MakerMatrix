from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Request
from starlette.responses import JSONResponse
from pydantic import BaseModel

from MakerMatrix.models.models import LocationModel, LocationQueryModel
from MakerMatrix.models.models import LocationUpdate
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.auth.dependencies import get_current_user, oauth2_scheme
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity, validate_service_response

# WebSocket for real-time updates
from MakerMatrix.services.system.websocket_service import websocket_manager


class LocationCreateRequest(BaseModel):
    """Request model for creating locations with required name."""
    name: str  # Required
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: str = "standard"
    image_url: Optional[str] = None
    emoji: Optional[str] = None

router = APIRouter()
base_router = BaseRouter()


@router.get("/get_all_locations")
@standard_error_handling
async def get_all_locations() -> ResponseSchema[List[Dict[str, Any]]]:
    location_service = LocationService()
    service_response = location_service.get_all_locations()
    
    validate_service_response(service_response)
    
    # Locations are already dictionaries from the service
    locations = service_response.data
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
            "parts_count": 0  # Set to 0 since we don't have parts loaded in basic fetch
        }
        location_data.append(location_dict)
    
    return base_router.build_success_response(
        message=service_response.message,
        data=location_data
    )


@router.get("/get_location")
@standard_error_handling
async def get_location(
    location_id: Optional[str] = None, 
    name: Optional[str] = None
) -> ResponseSchema[Dict[str, Any]]:
    if not location_id and not name:
        raise HTTPException(status_code=400, detail="Either 'location_id' or 'name' must be provided")
    
    location_service = LocationService()
    location_query = LocationQueryModel(id=location_id, name=name)
    service_response = location_service.get_location(location_query)
    
    validate_service_response(service_response)
    
    return base_router.build_success_response(
        message=service_response.message,
        data=service_response.data  # Already a dictionary from service
    )


@router.put("/update_location/{location_id}")
@standard_error_handling
@log_activity("location_updated", "User {username} updated location")
async def update_location(
    location_id: str, 
    location_data: LocationUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
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
    # Allow None for emoji and image_url (to clear them), but exclude None for other fields
    all_data = location_data.model_dump(exclude_unset=False)  # Include all fields, even None
    print(f"[DEBUG] All data from request: {all_data}")

    update_data = {}
    for k, v in all_data.items():
        # Include field if it has a value, or if it's emoji/image_url being explicitly cleared
        if v is not None or k in ['emoji', 'image_url']:
            update_data[k] = v

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
            location_name=updated_location['name'],
            changes=changes,
            user=current_user,
            request=request
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
            entity_name=updated_location['name'],
            user_id=current_user.id,
            username=current_user.username,
            changes=changes_dict,
            entity_data=updated_location
        )
    except Exception as e:
        print(f"Failed to broadcast location update: {e}")

    return base_router.build_success_response(
        message="Location updated successfully",
        data=updated_location  # Already a dictionary from service
    )


@router.post("/add_location")
@standard_error_handling
@log_activity("location_created", "User {username} created location")
async def add_location(
    location_data: LocationCreateRequest, 
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    location_service = LocationService()
    service_response = location_service.add_location(location_data.model_dump())
    
    validate_service_response(service_response)
    
    location = service_response.data
    print(f"[DEBUG] Location created successfully: {location['id']}")
    
    # Log activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()
        await activity_service.log_location_created(
            location_id=location['id'],
            location_name=location['name'],
            user=current_user,
            request=request
        )
    except Exception as e:
        print(f"Failed to log location creation activity: {e}")

    # Broadcast location creation via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="created",
            entity_type="location",
            entity_id=location['id'],
            entity_name=location['name'],
            user_id=current_user.id,
            username=current_user.username,
            entity_data=location
        )
    except Exception as e:
        print(f"Failed to broadcast location creation: {e}")

    # Location data is already a dictionary from the service
    response_data = location

    return base_router.build_success_response(
        message="Location added successfully",
        data=response_data
    )


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
    
    return base_router.build_success_response(
        message=service_response.message,
        data=service_response.data
    )


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
    
    return base_router.build_success_response(
        message=service_response.message,
        data=service_response.data
    )

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
    
    return base_router.build_success_response(
        message=service_response.message,
        data=service_response.data
    )


@router.delete("/delete_location/{location_id}")
@standard_error_handling
@log_activity("location_deleted", "User {username} deleted location")
async def delete_location(
    location_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema:
    response = LocationService.delete_location(location_id)
    
    # Log activity to database for recent activity widget
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()

        await activity_service.log_location_deleted(
            location_id=location_id,
            location_name=response['data']['deleted_location_name'],
            user=current_user,
            request=request
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
            entity_name=response['data']['deleted_location_name'],
            user_id=current_user.id,
            username=current_user.username,
            details=response['data']  # Include details about what was affected
        )
    except Exception as e:
        print(f"Failed to broadcast location deletion: {e}")

    return base_router.build_success_response(
        message=response['message'],
        data=response['data']
    )


@router.delete("/cleanup-locations")
@standard_error_handling
async def cleanup_locations() -> ResponseSchema[Dict[str, Any]]:
    """
    Clean up locations by removing those with invalid parent IDs and their descendants.
    
    Returns:
        ResponseSchema: A response containing the cleanup results.
    """
    response = LocationService.cleanup_locations()
    if response["status"] == "success":
        return base_router.build_success_response(
            message=response.get("message", "Locations cleaned up successfully"),
            data=response.get("data")
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to clean up locations")
        )


# Deprecated endpoint removed - use /preview-location-delete/{location_id} instead
