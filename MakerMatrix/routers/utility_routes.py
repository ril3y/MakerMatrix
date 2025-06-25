import os
import shutil
import uuid
import sqlite3
import json
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from starlette.responses import FileResponse, JSONResponse

from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.location_service import LocationService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.database.db import DATABASE_URL
from MakerMatrix.dependencies.auth import get_current_user
from MakerMatrix.models.user_models import UserModel

router = APIRouter()


@router.post("/upload_image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Upload an image file and return the image ID for later retrieval.
    Supports PNG, JPG, JPEG, GIF, WebP formats with max 5MB file size.
    """
    try:
        # Validate file type
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Supported types: PNG, JPG, JPEG, GIF, WebP"
            )
        
        # Validate file size (5MB max)
        MAX_SIZE = 5 * 1024 * 1024  # 5MB in bytes
        if file.size and file.size > MAX_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file.size} bytes. Maximum size: 5MB"
            )
        
        # Ensure upload directory exists
        upload_dir = "uploaded_images"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename with original extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if not file_extension:
            # Default to .jpg if no extension
            file_extension = ".jpg"
        
        image_id = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f"{image_id}{file_extension}")
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"image_id": image_id, "message": "Image uploaded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.get("/")
async def serve_index_html():
    return FileResponse("static/part_inventory_ui/build/index.html")


@router.get("/get_image/{image_id}")
async def get_image(
    image_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    # First try with the image_id as-is (might include extension)
    file_path = f"uploaded_images/{image_id}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    # If not found, try to find the file with any extension
    import glob
    pattern = f"uploaded_images/{image_id}.*"
    matching_files = glob.glob(pattern)
    
    if matching_files:
        # Return the first matching file
        return FileResponse(matching_files[0])
    
    raise HTTPException(status_code=404, detail="Image not found")


@router.get("/get_counts")
async def get_counts():
    """
    Returns all counts for parts, locations, and categories
    """
    # db_manager = DatabaseManager.get_instance()
    try:
        parts_result = PartService.get_all_parts()
        parts_count = len(parts_result['data'])
        
        locations_result = LocationService.get_all_locations()
        locations_count = len(locations_result)
        
        categories_result = CategoryService.get_all_categories()
        categories_count = len(categories_result['data']['categories'])

        return ResponseSchema(
            status="success",
            message="Counts retrieved successfully",
            data={"parts": parts_count, "locations": locations_count, "categories": categories_count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching counts: {str(e)}")


@router.get("/backup/download")
async def download_database_backup():
    """Download a backup of the database"""
    try:
        # Get the database path from DATABASE_URL
        db_path = DATABASE_URL.replace("sqlite:///", "")
        
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail="Database file not found")
        
        # Create a timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"makermatrix_backup_{timestamp}.db"
        
        return FileResponse(
            path=db_path,
            filename=backup_filename,
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")


@router.get("/backup/export")
async def export_data_json():
    """Export all data as JSON"""
    try:
        # Get all data
        parts_data = PartService.get_all_parts()
        locations_data = LocationService.get_all_locations()
        categories_data = CategoryService.get_all_categories()
        
        export_data = {
            "export_date": datetime.now().isoformat(),
            "parts": parts_data.get('data', []),
            "locations": locations_data,
            "categories": categories_data.get('data', {}).get('categories', [])
        }
        
        # Create temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = f"temp_export_{timestamp}.json"
        
        with open(temp_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return FileResponse(
            path=temp_file,
            filename=f"makermatrix_export_{timestamp}.json",
            media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")


@router.get("/backup/status")
async def get_backup_status():
    """Get backup status and database information"""
    try:
        db_path = DATABASE_URL.replace("sqlite:///", "")
        
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail="Database file not found")
        
        # Get file stats
        stat = os.stat(db_path)
        file_size = stat.st_size
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Get table counts
        parts_count = len(PartService.get_all_parts()['data'])
        locations_count = len(LocationService.get_all_locations())
        categories_count = len(CategoryService.get_all_categories()['data']['categories'])
        
        return ResponseSchema(
            status="success",
            message="Backup status retrieved successfully",
            data={
                "database_size": file_size,
                "last_modified": last_modified.isoformat(),
                "total_records": parts_count + locations_count + categories_count,
                "parts_count": parts_count,
                "locations_count": locations_count,
                "categories_count": categories_count
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup status: {str(e)}")
