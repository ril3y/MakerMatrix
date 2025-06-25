from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Request
from starlette.responses import JSONResponse
from pydantic import BaseModel

from MakerMatrix.models.models import LocationModel, LocationQueryModel
from MakerMatrix.models.models import LocationUpdate
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.schemas.location_response import LocationResponse
from MakerMatrix.services.location_service import LocationService
from MakerMatrix.dependencies import oauth2_scheme
from MakerMatrix.dependencies.auth import get_current_user
from MakerMatrix.models.user_models import UserModel


class LocationCreateRequest(BaseModel):
    """Request model for creating locations with required name."""
    name: str  # Required
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: str = "standard"
    image_url: Optional[str] = None
    emoji: Optional[str] = None

router = APIRouter()


@router.get("/get_all_locations")
async def get_all_locations() -> ResponseSchema[List[Dict[str, Any]]]:
    try:
        locations = LocationService.get_all_locations()
        # Convert LocationModel objects to dictionaries
        location_data = []
        for location in locations:
            location_dict = {
                "id": location.id,
                "name": location.name,
                "description": location.description,
                "parent_id": location.parent_id,
                "location_type": location.location_type,
                "image_url": location.image_url,
                "emoji": getattr(location, 'emoji', None),
                "parts_count": len(location.parts) if location.parts else 0
            }
            # Add parent info if available
            if location.parent:
                location_dict["parent"] = {
                    "id": location.parent.id,
                    "name": location.parent.name
                }
            # Add children info if available
            if hasattr(location, 'children') and location.children:
                location_dict["children"] = [
                    {"id": child.id, "name": child.name} 
                    for child in location.children
                ]
            location_data.append(location_dict)
        
        # noinspection PyArgumentList
        return ResponseSchema(
            status="success",
            message="All locations retrieved successfully",
            data=location_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location")
async def get_location(
    location_id: Optional[str] = None, 
    name: Optional[str] = None
) -> ResponseSchema[Dict[str, Any]]:
    try:
        if not location_id and not name:
            raise HTTPException(status_code=400, detail="Either 'location_id' or 'name' must be provided")
        location_query = LocationQueryModel(id=location_id, name=name)
        location = LocationService.get_location(location_query)
        if location:
            # noinspection PyArgumentList
            return ResponseSchema(
                status="success",
                message="Location retrieved successfully",
                data=location.to_dict()
            )

    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_location/{location_id}")
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
    try:
        # Convert the Pydantic model to a dict and remove None values
        update_data = {k: v for k, v in location_data.model_dump().items() if v is not None}
        updated_location = LocationService.update_location(location_id, update_data)
        
        # Log activity to database for recent activity widget
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            
            # Create changes dict from the update data
            changes = {k: v for k, v in location_data.model_dump().items() if v is not None}
            
            await activity_service.log_location_updated(
                location_id=location_id,
                location_name=updated_location.name,
                changes=changes,
                user=current_user,
                request=request
            )
        except Exception as activity_error:
            print(f"Failed to log location update activity: {activity_error}")
            # Don't fail the main operation if activity logging fails
        
        return ResponseSchema(
            status="success",
            message="Location updated successfully",
            data=updated_location.model_dump()
        )
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_location")
async def add_location(
    location_data: LocationCreateRequest, 
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    try:
        # Check if a location with the same name and parent_id already exists
        existing_location = None
        try:
            location_query = LocationQueryModel(name=location_data.name)
            existing_location = LocationService.get_location(location_query)
            
            # If we found a location with the same name, check if it has the same parent_id
            if existing_location and existing_location.parent_id == location_data.parent_id:
                return JSONResponse(
                    status_code=409,
                    content={
                        "status": "error",
                        "message": f"Location with name '{location_data.name}' already exists under the same parent"
                    }
                )
        except ResourceNotFoundError:
            # If no location with this name exists, we can proceed
            pass
            
        location = LocationService.add_location(location_data.model_dump())
        print(f"[DEBUG] Location created successfully: {location.id}")
        
        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_location_created(
                location_id=location.id,
                location_name=location.name,
                user=current_user,
                request=request
            )
        except Exception as e:
            print(f"Failed to log location creation activity: {e}")
        
        # Create response data manually to avoid serialization issues
        response_data = {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "parent_id": location.parent_id,
            "location_type": location.location_type
        }
        
        return ResponseSchema(
            status="success",
            message="Location added successfully",
            data=response_data
        )
    except Exception as e:
        print(f"[DEBUG] Error creating location: {str(e)}")
        print(f"[DEBUG] Error type: {type(e)}")
        
        # Check if this is an integrity error (likely a duplicate name + parent_id)
        if "UNIQUE constraint failed" in str(e) or "unique constraint" in str(e).lower():
            return JSONResponse(
                status_code=409,
                content={
                    "status": "error",
                    "message": f"Location with name '{location_data.name}' already exists under the same parent"
                }
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location_details/{location_id}")
async def get_location_details(location_id: str) -> ResponseSchema[Dict[str, Any]]:
    """
    Get detailed information about a location, including its children.

    Args:
        location_id (str): The ID of the location to get details for.

    Returns:
        ResponseSchema: A response containing the location details and its children.
    """
    response = LocationService.get_location_details(location_id)
    if response["status"] == "success":
        return ResponseSchema(
            status=response["status"],
            message=response.get("message", "Location details retrieved successfully"),
            data=response.get("data")
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=response.get("message", "Location not found")
        )


@router.get("/get_location_path/{location_id}", response_model=ResponseSchema)
async def get_location_path(location_id: str) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get the full path from a location to its root.
    
    Args:
        location_id: The ID of the location to get the path for
        
    Returns:
        A ResponseSchema containing the location path with parent references
    """
    try:
        response = LocationService.get_location_path(location_id)
        return response
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview-location-delete/{location_id}")
async def preview_location_delete(location_id: str) -> ResponseSchema:
    """
    Preview what will be affected when deleting a location.
    
    Args:
        location_id: The ID of the location to preview deletion for
        
    Returns:
        ResponseSchema: A response containing the preview information
    """
    try:
        preview_response = LocationService.preview_location_delete(location_id)
        return ResponseSchema(
            status="success",
            message="Delete preview generated",
            data=preview_response
        )
    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete_location/{location_id}")
async def delete_location(
    location_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema:
    try:
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
        
        return ResponseSchema(
            status=response['status'],
            message=response['message'],
            data=response['data']
        )
    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup-locations")
async def cleanup_locations() -> ResponseSchema[Dict[str, Any]]:
    """
    Clean up locations by removing those with invalid parent IDs and their descendants.
    
    Returns:
        ResponseSchema: A response containing the cleanup results.
    """
    response = LocationService.cleanup_locations()
    if response["status"] == "success":
        return ResponseSchema(
            status=response["status"],
            message=response.get("message", "Locations cleaned up successfully"),
            data=response.get("data")
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to clean up locations")
        )


@router.get("/preview-delete/{location_id}")
async def preview_delete(location_id: str) -> ResponseSchema[Dict[str, Any]]:
    """
    DEPRECATED: Use /preview-location-delete/{location_id} instead.
    Preview what will be affected when deleting a location.
    
    Args:
        location_id: The ID of the location to preview deletion for
        
    Returns:
        JSONResponse: A JSON response containing the preview information.
    """
    return await preview_location_delete(location_id)
