import os
import shutil
import uuid
import sqlite3
import json
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import FileResponse, JSONResponse
from pathlib import Path
import logging
import httpx
from urllib.parse import urlparse

from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.database.db import DATABASE_URL
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Base path for static files
STATIC_BASE_PATH = Path(__file__).parent.parent / "services" / "static"

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
        upload_dir = STATIC_BASE_PATH / "images"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename with original extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if not file_extension:
            # Default to .jpg if no extension
            file_extension = ".jpg"
        
        image_id = str(uuid.uuid4())
        file_path = upload_dir / f"{image_id}{file_extension}"
        
        # Save file
        with open(str(file_path), "wb") as buffer:
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
    import glob
    
    # Use static images directory
    uploaded_images_dir = STATIC_BASE_PATH / "images"
    
    # First try with the image_id as-is (might include extension)
    file_path = uploaded_images_dir / image_id
    if file_path.exists():
        return FileResponse(str(file_path))
    
    # If not found, try to find the file with any extension
    pattern = str(uploaded_images_dir / f"{image_id}.*")
    matching_files = glob.glob(pattern)
    
    if matching_files:
        # Return the first matching file
        return FileResponse(matching_files[0])
    
    raise HTTPException(status_code=404, detail="Image not found")


@router.get("/debug/server-info")
async def debug_server_info():
    """Debug endpoint to check server working directory and file paths"""
    import glob
    
    current_dir = os.getcwd()
    uploaded_images_dir = STATIC_BASE_PATH / "images"
    uploaded_images_exists = uploaded_images_dir.exists()
    uploaded_images_abs = str(uploaded_images_dir) if uploaded_images_exists else None
    
    files_in_uploaded = []
    if uploaded_images_exists:
        try:
            files_in_uploaded = os.listdir(uploaded_images_dir)
        except Exception as e:
            files_in_uploaded = [f"Error: {e}"]
    
    return {
        "current_working_directory": current_dir,
        "uploaded_images_exists": uploaded_images_exists,
        "uploaded_images_absolute_path": uploaded_images_abs,
        "files_in_uploaded_images": files_in_uploaded
    }

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

@router.api_route("/static/datasheets/{filename}", methods=["GET", "HEAD"])
async def serve_datasheet(filename: str):
    """Serve component datasheets"""
    file_path = STATIC_BASE_PATH / "datasheets" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Datasheet not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Invalid file")
    
    # Security check - make sure the file is within the datasheets directory
    try:
        file_path.resolve().relative_to((STATIC_BASE_PATH / "datasheets").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename
    )

@router.get("/static/proxy-pdf")
async def proxy_pdf(url: str = Query(..., description="URL of the PDF to proxy")):
    """
    Proxy external PDF URLs to avoid CORS issues.
    
    This endpoint fetches PDFs from external sources and streams them 
    to the client, bypassing browser CORS restrictions.
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL provided")
        
        # Security check - only allow certain domains for safety
        allowed_domains = [
            'lcsc.com', 'www.lcsc.com', 
            'digikey.com', 'www.digikey.com',
            'mouser.com', 'www.mouser.com',
            'easyeda.com', 'datasheet.lcsc.com'
        ]
        
        if not any(domain in parsed_url.netloc.lower() for domain in allowed_domains):
            logger.warning(f"Attempted to proxy PDF from unauthorized domain: {parsed_url.netloc}")
            raise HTTPException(status_code=403, detail="Domain not allowed for PDF proxying")
        
        logger.info(f"Proxying PDF from: {url}")
        
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "MakerMatrix/1.0.0 (Component Management System)",
                "Accept": "application/pdf,*/*"
            }
        ) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch PDF: HTTP {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Failed to fetch PDF: HTTP {response.status_code}"
                )
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                logger.warning(f"Response doesn't appear to be a PDF: {content_type}")
                # Still proceed as some servers don't set correct content-type
            
            # Stream the PDF content
            def iter_content():
                for chunk in response.iter_bytes(chunk_size=8192):
                    yield chunk
            
            return StreamingResponse(
                iter_content(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "inline",
                    "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
                }
            )
            
    except HTTPException:
        # Re-raise HTTPExceptions (like domain validation errors)
        raise
    except httpx.TimeoutException:
        logger.error(f"Timeout while fetching PDF from: {url}")
        raise HTTPException(status_code=408, detail="Timeout while fetching PDF")
    except httpx.RequestError as e:
        logger.error(f"Request error while fetching PDF: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch PDF from source")
    except Exception as e:
        logger.error(f"Unexpected error while proxying PDF: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while proxying PDF")