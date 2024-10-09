from typing import Optional

from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from models.location_model import LocationModel, LocationQueryModel
from services.location_service import LocationService

router = APIRouter()


@router.get("/all_locations/")
async def get_all_locations():
    locations = LocationService.get_all_locations()
    return {"locations": locations}


@router.post("/add_location")
async def add_location(location: LocationModel):
    try:
        response = LocationService.add_location(location)
        if response["status"] == "exists":
            return {"status": "exists", "message": response["message"], "data": response["data"]}
        return {"status": "success", "data": response["data"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location")
async def get_location(id: Optional[str] = None, name: Optional[str] = None):
    if not id and not name:
        raise HTTPException(status_code=400, detail="Either id or name must be provided")

    location_query = LocationQueryModel(id=id) if id else LocationQueryModel(name=name)

    location_data = LocationService.get_location(location_query)

    if location_data:
        return JSONResponse(content={"status": "success", "data": location_data}, status_code=200)
    else:
        raise HTTPException(status_code=404, detail="Location not found")


@router.get("/preview-delete/{location_id}")
async def preview_delete(location_id: str):
    # Fetch the number of parts affected by the deletion
    affected_parts = await LocationService.get_parts_effected_locations(location_id)
    affected_parts_count = len(affected_parts)

    # Fetch the child locations affected by the deletion
    child_locations = await LocationService.get_location_hierarchy(location_id)
    affected_children_count = len(child_locations)

    return {
        "location_id": location_id,
        "affected_parts_count": affected_parts_count,
        "affected_children_count": affected_children_count
    }


@router.put("/edit_location/{location_id}")
async def edit_location(location_id: str, name: str = None, description: str = None, parent_id: int = None):
    updated_location = await LocationService.edit_location(location_id, name, description, parent_id)
    if updated_location:
        return {"message": "Location updated", "location": updated_location}
    else:
        raise HTTPException(status_code=400, detail="Error updating location")


@router.delete("/delete_all_locations")
async def delete_all_locations():
    response = LocationService.delete_all_locations()
    if response["status"] == "success":
        return JSONResponse(content=response, status_code=200)
    else:
        # Raise an HTTP exception directly with the error message from the service
        raise HTTPException(status_code=500, detail=response["message"])


@router.delete("/delete_location/{location_id}")
async def delete_location(location_id: str):
    try:
        # Call the service to delete the location and its children
        deleted_info = LocationService.delete_location(location_id)

        if deleted_info['status'] == 'success':
            return {
                "message": "Location and its children deleted successfully",
                "deleted_location": location_id,
                "deleted_children_count": deleted_info['deleted_children_count']
            }
        else:
            raise HTTPException(status_code=404, detail="Location not found")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_location/{location_id}")
async def update_location(location_id: str, location: LocationModel):
    try:
        updated_location = LocationService.update_location(location_id, location)
        if updated_location:
            return {"status": "success", "message": "Location updated", "location": updated_location}
        else:
            # Raise a 404 error if the location is not found
            raise HTTPException(status_code=404, detail="Location not found")
    except HTTPException as http_exc:
        # Pass through any HTTP exceptions like the 404
        raise http_exc
    except Exception as e:
        # Catch any other exceptions and return a structured error response
        return {"status": "error", "message": str(e)}, 500


@router.get("/get_location_details/{location_id}")
async def get_location_details(location_id: str):
    location = LocationService.get_location_details(location_id)
    if location:
        return JSONResponse(content=location, status_code=200)
    else:
        return JSONResponse(content={"error": "Location not found"}, status_code=404)


@router.get("/get_location_path/{location_id}")
async def get_location_path(location_id: str):
    """
    Retrieves the path from a specific location to the root.

    :param location_id: The ID of the specific location.
    :return: A list of locations forming the path from the specified location to the root.
    """
    loc = LocationQueryModel(id=location_id)

    path = LocationService.get_location_path(loc)
    if path:
        return JSONResponse(content={"path": path}, status_code=200)
    else:
        return JSONResponse(content={"error": "Location path not found"}, status_code=404)


@router.delete("/cleanup-locations")
async def cleanup_locations():
    try:
        deleted_count = LocationService.cleanup_locations()
        return JSONResponse(content={
            "status": "success",
            "message": "Cleanup completed",
            "deleted_locations_count": deleted_count
        }, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
