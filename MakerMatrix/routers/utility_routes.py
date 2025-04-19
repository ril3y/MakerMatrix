import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from starlette.responses import FileResponse, JSONResponse

from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.location_service import LocationService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.schemas.response import ResponseSchema

router = APIRouter()


@router.post("/upload_image")
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


@router.get("/get_image/{image_id}")
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
        parts_count = len(PartService.get_all_parts()['data'])
        locations_count = len(LocationService.get_all_locations())
        categories_count = len(CategoryService.get_all_categories()['data'])

        return ResponseSchema(
            status="success",
            message="Counts retrieved successfully",
            data={"parts": parts_count, "locations": locations_count, "categories": categories_count}
        )
    except Exception as e:
        print(f"Error getting counts: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching counts")
