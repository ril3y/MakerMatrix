from typing import Optional

from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from MakerMatrix.models.models import LocationModel, LocationQueryModel
from MakerMatrix.models.models import LocationUpdate
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.location_service import LocationService

router = APIRouter()


@router.get("/get_all_locations")
async def get_all_locations():
    try:
        locations = LocationService.get_all_locations()
        # noinspection PyArgumentList
        return ResponseSchema(
            status="success",
            message="All locations retrieved successfully",
            data=locations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location")
async def get_location(
    location_id: Optional[str] = None, 
    name: Optional[str] = None
):
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


@router.put("/update_location/{location_id}", response_model=ResponseSchema[LocationModel])
async def update_location(location_id: str, location_data: LocationUpdate) -> ResponseSchema[LocationModel]:
    """
    Update a location's fields. This endpoint can update any combination of name, description, parent_id, and location_type.
    
    Args:
        location_id: The ID of the location to update
        location_data: The fields to update (name, description, parent_id, location_type)
        
    Returns:
        ResponseSchema: A response containing the updated location data
    """
    try:
        # Convert the Pydantic model to a dict and remove None values
        update_data = {k: v for k, v in location_data.model_dump().items() if v is not None}
        updated_location = LocationService.update_location(location_id, update_data)
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
async def add_location(location_data: LocationModel) -> ResponseSchema[LocationModel]:
    try:
        # Check if a location with the same name and parent_id already exists
        existing_location = None
        try:
            location_query = LocationQueryModel(name=location_data.name)
            existing_location = LocationService.get_location(location_query)
            
            # If we found a location with the same name, check if it has the same parent_id
            if existing_location and existing_location.parent_id == location_data.parent_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Location with name '{location_data.name}' already exists under the same parent"
                )
        except ResourceNotFoundError:
            # If no location with this name exists, we can proceed
            pass
            
        location = LocationService.add_location(location_data.model_dump())
        return ResponseSchema(
            status="success",
            message="Location added successfully",
            data=location.to_dict()
        )
    except Exception as e:
        # Check if this is an integrity error (likely a duplicate name + parent_id)
        if "UNIQUE constraint failed" in str(e) or "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Location with name '{location_data.name}' already exists under the same parent"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location_details/{location_id}")
async def get_location_details(location_id: str):
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
async def get_location_path(location_id: str):
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
async def delete_location(location_id: str) -> ResponseSchema:
    try:
        response = LocationService.delete_location(location_id)
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
async def cleanup_locations():
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
async def preview_delete(location_id: str):
    """
    DEPRECATED: Use /preview-location-delete/{location_id} instead.
    Preview what will be affected when deleting a location.
    
    Args:
        location_id: The ID of the location to preview deletion for
        
    Returns:
        JSONResponse: A JSON response containing the preview information.
    """
    return await preview_location_delete(location_id)
