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
async def get_location(location_id: Optional[str] = None, name: Optional[str] = None):
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
        if "Parent Location" in rnfe.message:
            raise HTTPException(status_code=404, detail="Parent Location not found")
        raise HTTPException(status_code=404, detail="Location not found")
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_location")
async def add_location(location_data: LocationModel) -> ResponseSchema[LocationModel]:
    try:
        location = LocationService.add_location(location_data.model_dump())
        # noinspection PyArgumentList
        # noinspection PyArgumentList
        return ResponseSchema(


            status="success",
            message="Location added successfully",
            data=location.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location_details/{location_id}")
async def get_location_details(location_id: str):
    """
    Get detailed information about a location, including its children.

    Args:
        location_id (str): The ID of the location to get details for.

    Returns:
        JSONResponse: A JSON response containing the location details and its children.
    """
    response = LocationService.get_location_details(location_id)
    if response["status"] == "success":
        return JSONResponse(content=response, status_code=200)
    else:
        return JSONResponse(content=response, status_code=404)


@router.get("/get_location_path/{location_id}", response_model=ResponseSchema)
async def get_location_path(location_id: str):
    """Get the full path from a location to its root.
    
    Args:
        location_id: The ID of the location to get the path for
        
    Returns:
        A ResponseSchema containing the location path with parent references
    """
    return LocationService.get_location_path(location_id)

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
        JSONResponse: A JSON response containing the cleanup results.
    """
    response = LocationService.cleanup_locations()
    if response["status"] == "success":
        return JSONResponse(content=response, status_code=200)
    else:
        return JSONResponse(content=response, status_code=500)


@router.put("/edit_location/{location_id}")
async def edit_location(location_id: str, name: Optional[str] = None, 
                       description: Optional[str] = None, parent_id: Optional[str] = None):
    """
    Edit specific fields of a location.
    
    Args:
        location_id: The ID of the location to edit
        name: Optional new name for the location
        description: Optional new description
        parent_id: Optional new parent ID
        
    Returns:
        JSONResponse: A JSON response containing the updated location.
    """
    response = LocationService.edit_location(location_id, name, description, parent_id)
    if response["status"] == "success":
        return JSONResponse(content=response, status_code=200)
    else:
        return JSONResponse(content=response, status_code=404)


@router.get("/preview-delete/{location_id}")
async def preview_delete(location_id: str):
    """
    Preview what will be affected when deleting a location.
    
    Args:
        location_id: The ID of the location to preview deletion for
        
    Returns:
        JSONResponse: A JSON response containing the preview information.
    """
    response = LocationService.preview_delete(location_id)
    if response["status"] == "success":
        return JSONResponse(content=response, status_code=200)
    else:
        return JSONResponse(content=response, status_code=404)


# @router.get("/all_locations/")
# async def get_all_locations():
#     locations = LocationService.get_all_locations()
#     return {"locations": locations}


# @router.post("/add_location")
# async def add_location(location: LocationModel):
#     try:
#         response = LocationService.add_location(location)
#         if response["status"] == "exists":
#             return {"status": "exists", "message": response["message"], "data": response["data"]}
#         return {"status": "success", "data": response["data"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/get_location")
# async def get_location(id: Optional[str] = None, name: Optional[str] = None):
#     if not id and not name:
#         raise HTTPException(status_code=400, detail="Either id or name must be provided")

#     location_query = LocationQueryModel(id=id) if id else LocationQueryModel(name=name)

#     location_data = LocationService.get_location(location_query)

#     if location_data:
#         return JSONResponse(content={"status": "success", "data": location_data}, status_code=200)
#     else:
#         raise HTTPException(status_code=404, detail="Location not found")


# @router.get("/preview-delete/{location_id}")
# async def preview_delete(location_id: str):
#     # Fetch the number of parts affected by the deletion
#     affected_parts = await LocationService.get_parts_effected_locations(location_id)
#     affected_parts_count = len(affected_parts)

#     # Fetch the child locations affected by the deletion
#     child_locations = await LocationService.get_location_hierarchy(location_id)
#     affected_children_count = len(child_locations)

#     return {
#         "location_id": location_id,
#         "affected_parts_count": affected_parts_count,
#         "affected_children_count": affected_children_count
#     }


# @router.put("/edit_location/{location_id}")
# async def edit_location(location_id: str, name: str = None, description: str = None, parent_id: int = None):
#     updated_location = await LocationService.edit_location(location_id, name, description, parent_id)
#     if updated_location:
#         return {"message": "Location updated", "location": updated_location}
#     else:
#         raise HTTPException(status_code=400, detail="Error updating location")


# @router.delete("/delete_all_locations")
# async def delete_all_locations():
#     response = LocationService.delete_all_locations()
#     if response["status"] == "success":
#         return JSONResponse(content=response, status_code=200)
#     else:
#         # Raise an HTTP exception directly with the error message from the service
#         raise HTTPException(status_code=500, detail=response["message"])


# @router.delete("/delete_location/{location_id}")
# async def delete_location(location_id: str):
#     try:
#         # Call the service to delete the location and its children
#         deleted_info = LocationService.delete_location(location_id)

#         if deleted_info['status'] == 'success':
#             return {
#                 "message": "Location and its children deleted successfully",
#                 "deleted_location": location_id,
#                 "deleted_children_count": deleted_info['deleted_children_count']
#             }
#         else:
#             raise HTTPException(status_code=404, detail="Location not found")
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.put("/update_location/{location_id}")
# async def update_location(location_id: str, location: LocationModel):
#     try:
#         updated_location = LocationService.update_location(location_id, location)
#         if updated_location:
#             return {"status": "success", "message": "Location updated", "location": updated_location}
#         else:
#             # Raise a 404 error if the location is not found
#             raise HTTPException(status_code=404, detail="Location not found")
#     except HTTPException as http_exc:
#         # Pass through any HTTP exceptions like the 404
#         raise http_exc
#     except Exception as e:
#         # Catch any other exceptions and return a structured error response
#         return {"status": "error", "message": str(e)}, 500


# @router.get("/get_location_details/{location_id}")
# async def get_location_details(location_id: str):
#     location = LocationService.get_location_details(location_id)
#     if location:
#         return JSONResponse(content=location, status_code=200)
#     else:
#         return JSONResponse(content={"error": "Location not found"}, status_code=404)


# @router.get("/get_location_path/{location_id}")
# async def get_location_path(location_id: str):
#     """
#     Retrieves the path from a specific location to the root.

#     :param location_id: The ID of the specific location.
#     :return: A list of locations forming the path from the specified location to the root.
#     """
#     loc = LocationQueryModel(id=location_id)

#     path = LocationService.get_location_path(loc)
#     if path:
#         return JSONResponse(content={"path": path}, status_code=200)
#     else:
#         return JSONResponse(content={"error": "Location path not found"}, status_code=404)


# @router.delete("/cleanup-locations")
# async def cleanup_locations():
#     try:
#         deleted_count = LocationService.cleanup_locations()
#         return JSONResponse(content={
#             "status": "success",
#             "message": "Cleanup completed",
#             "deleted_locations_count": deleted_count
#         }, status_code=200)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
