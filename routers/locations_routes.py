from fastapi import APIRouter, HTTPException
from models.location_model import LocationModel
from services.location_service import LocationService

router = APIRouter()


@router.get("/all_locations/")
async def get_all_locations():
    locations = LocationService.get_all_locations()
    return {"locations": locations}


@router.get("/get_location/{location_id}")
async def get_location(location_id: str):
    location = await LocationService.get_location(location_id)
    if location:
        return location
    else:
        raise HTTPException(status_code=404, detail="Location not found")


@router.post("/add_location/")
async def add_location(location: LocationModel):
    added_location = await LocationService.add_location(location.dict())
    if "error" in added_location:
        raise HTTPException(status_code=409, detail=added_location["error"])
    return added_location


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


@router.delete("/delete_location/{location_id}")
async def delete_location(location_id: str):
    deleted_location = await LocationService.delete_location(location_id)
    if deleted_location:
        return {"message": "Location and its children deleted successfully", "deleted_location": location_id}
    else:
        raise HTTPException(status_code=400, detail="Error deleting location")
