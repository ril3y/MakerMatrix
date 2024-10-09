import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.responses import FileResponse, JSONResponse

from services.category_service import CategoryService
from services.location_service import LocationService
from services.part_service import PartService

router = APIRouter()


@router.post("/upload_image/")
async def upload_image(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1]
    image_id = str(uuid.uuid4())
    file_path = f"uploaded_images/{image_id}{file_extension}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"image_id": image_id}


@router.get("/")
async def serve_index_html():
    return FileResponse("static/part_inventory_ui/build/index.html")


@router.get("/get_image/{image_id}/")
async def get_image(image_id: str):
    file_path = f"uploaded_images/{image_id}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Image not found")


@router.get("/get_counts")
async def get_counts():
    """
    Returns all counts for parts, locations, and categories
    """
    # db_manager = DatabaseManager.get_instance()
    try:
        parts = PartService.part_repo.get_all_parts()
        locations = LocationService.location_repo.get_all_locations()
        categories = CategoryService.category_repo.get_all_categories()

        parts_count = len(parts)
        locations_count = len(locations)
        categories_count = len(categories)
        return JSONResponse(
            content={"parts": parts_count, "locations": locations_count, "categories": categories_count},
            status_code=200)
    except Exception as e:
        print(f"Error getting counts: {e}")
        return JSONResponse(content={"error": "An error occurred while fetching counts"}, status_code=500)
