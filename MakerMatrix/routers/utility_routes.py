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
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.services.activity_service import get_activity_service
from MakerMatrix.models.models import *
from sqlmodel import Session, select
from MakerMatrix.models.models import engine

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
    Returns all counts for parts, locations, and categories using efficient SQL COUNT queries
    """
    try:
        # Use repositories directly for efficient counting (SQL COUNT instead of fetching all records)
        from MakerMatrix.repositories.parts_repositories import PartRepository
        from sqlalchemy import func
        
        with Session(engine) as session:
            # Use existing efficient count method for parts
            parts_count = PartRepository.get_part_counts(session)
            
            # Use direct SQL COUNT for locations and categories (more efficient than fetching all)
            locations_count = session.exec(select(func.count()).select_from(LocationModel)).one()
            categories_count = session.exec(select(func.count()).select_from(CategoryModel)).one()

        return ResponseSchema(
            status="success",
            message="Counts retrieved successfully",
            data={"parts": parts_count, "locations": locations_count, "categories": categories_count}
        )
    except Exception as e:
        logger.error(f"Get counts error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching counts: {str(e)}")


@router.post("/backup/create")
async def create_database_backup_task(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Create a comprehensive database backup task and return task information for monitoring"""
    try:
        from MakerMatrix.services.system.task_service import task_service
        from MakerMatrix.models.task_models import CreateTaskRequest, TaskType, TaskPriority
        
        # Generate backup name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"makermatrix_backup_{timestamp}"
        
        # Create backup task
        task_request = CreateTaskRequest(
            task_type=TaskType.BACKUP_CREATION,
            name=f"Database Backup: {backup_name}",
            description="Create comprehensive backup including database, datasheets, and images",
            priority=TaskPriority.HIGH,
            input_data={
                "backup_name": backup_name,
                "include_datasheets": True,
                "include_images": True
            },
            related_entity_type="system",
            related_entity_id="database"
        )
        
        task = await task_service.create_task(task_request, user_id=current_user.id)
        
        return ResponseSchema(
            status="success",
            message="Database backup task created successfully. Monitor progress via WebSocket or task endpoints.",
            data={
                "task_id": task.id,
                "task_type": task.task_type,
                "task_name": task.name,
                "status": task.status,
                "priority": task.priority,
                "backup_name": backup_name,
                "monitor_url": f"/api/tasks/{task.id}",
                "expected_backup_location": f"/MakerMatrix/backups/{backup_name}.zip"
            }
        )
        
    except Exception as e:
        logger.error(f"Backup task creation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create backup task: {str(e)}")


@router.get("/backup/download")
async def create_database_backup_task_legacy(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Legacy GET endpoint for backup creation - redirects to new task-based system"""
    # For backward compatibility with existing frontend
    return await create_database_backup_task(current_user)


@router.get("/backup/download/{backup_filename}")
async def download_completed_backup(
    backup_filename: str,
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Download a completed backup file"""
    try:
        # Validate filename (security check)
        if not backup_filename.endswith('.zip') or '..' in backup_filename or '/' in backup_filename:
            raise HTTPException(status_code=400, detail="Invalid backup filename")
        
        # Define backup directory
        base_path = Path(__file__).parent.parent.parent
        backups_dir = base_path / "backups"
        backup_file_path = backups_dir / backup_filename
        
        if not backup_file_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        return FileResponse(
            path=str(backup_file_path),
            filename=backup_filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={backup_filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backup download error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download backup: {str(e)}")


@router.get("/backup/list")
async def list_available_backups(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """List all available backup files"""
    try:
        base_path = Path(__file__).parent.parent.parent
        backups_dir = base_path / "backups"
        
        if not backups_dir.exists():
            return ResponseSchema(
                status="success",
                message="No backups directory found",
                data={"backups": []}
            )
        
        backups = []
        for backup_file in backups_dir.glob("*.zip"):
            if backup_file.is_file():
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "download_url": f"/api/utility/backup/download/{backup_file.name}"
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(backups)} backup files",
            data={"backups": backups}
        )
        
    except Exception as e:
        logger.error(f"List backups error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


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
        # Get database path - try multiple resolution strategies
        db_path_raw = DATABASE_URL.replace("sqlite:///", "")
        
        # Try multiple possible database locations
        possible_db_paths = [
            db_path_raw,  # Relative to current working directory
            os.path.join(os.getcwd(), db_path_raw),  # Explicitly relative to cwd
            f"/home/ril3y/MakerMatrix/{db_path_raw}",  # Project root
            str(Path(__file__).parent.parent.parent / db_path_raw),  # Relative to this file
            # Try common filename variations
            "makers_matrix.db",  # The actual filename
            "/home/ril3y/MakerMatrix/makers_matrix.db",  # Project root with correct name
            str(Path(__file__).parent.parent.parent / "makers_matrix.db"),  # Relative with correct name
        ]
        
        db_path = None
        for path in possible_db_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if not db_path:
            raise HTTPException(status_code=404, detail="Database file not found")
        
        # Get file stats
        stat = os.stat(db_path)
        file_size = stat.st_size
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Get table counts using repositories directly (more efficient than services)
        from MakerMatrix.repositories.parts_repositories import PartRepository
        from MakerMatrix.repositories.location_repositories import LocationRepository  
        from MakerMatrix.repositories.category_repositories import CategoryRepository
        from sqlalchemy import func
        
        with Session(engine) as session:
            # Use existing efficient count method for parts
            parts_count = PartRepository.get_part_counts(session)
            
            # Use direct SQL COUNT for locations and categories (more efficient)
            locations_count = session.exec(select(func.count()).select_from(LocationModel)).one()
            categories_count = session.exec(select(func.count()).select_from(CategoryModel)).one()
        
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
        logger.error(f"Backup status error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get backup status: {str(e)}")


@router.delete("/clear_suppliers", response_model=ResponseSchema[Dict[str, Any]])
async def clear_suppliers_data(
    current_user: UserModel = Depends(require_permission("admin"))
) -> ResponseSchema[Dict[str, Any]]:
    """Clear all supplier-related data from the database - USE WITH CAUTION! (Admin only)"""
    try:
        result = {
            "supplier_configs": 0,
            "supplier_credentials": 0,
            "supplier_usage_tracking": 0,
            "supplier_usage_summary": 0,
            "supplier_rate_limits": 0,
            "enrichment_profiles": 0,
            "parts_supplier_cleared": 0
        }
        
        activity_service = get_activity_service()
        
        with Session(engine) as session:
            # Clear supplier configurations
            supplier_configs = session.exec(select(SupplierConfigModel)).all()
            for config in supplier_configs:
                session.delete(config)
            result["supplier_configs"] = len(supplier_configs)
            
            # Clear supplier credentials
            supplier_credentials = session.exec(select(SupplierCredentialsModel)).all()
            for cred in supplier_credentials:
                session.delete(cred)
            result["supplier_credentials"] = len(supplier_credentials)
            
            # Clear supplier usage tracking
            usage_tracking = session.exec(select(SupplierUsageTrackingModel)).all()
            for usage in usage_tracking:
                session.delete(usage)
            result["supplier_usage_tracking"] = len(usage_tracking)
            
            # Clear supplier usage summary
            usage_summary = session.exec(select(SupplierUsageSummaryModel)).all()
            for summary in usage_summary:
                session.delete(summary)
            result["supplier_usage_summary"] = len(usage_summary)
            
            # Clear supplier rate limits
            rate_limits = session.exec(select(SupplierRateLimitModel)).all()
            for limit in rate_limits:
                session.delete(limit)
            result["supplier_rate_limits"] = len(rate_limits)
            
            # Clear enrichment profiles
            enrichment_profiles = session.exec(select(EnrichmentProfileModel)).all()
            for profile in enrichment_profiles:
                session.delete(profile)
            result["enrichment_profiles"] = len(enrichment_profiles)
            
            # Clear supplier data from parts (set to None)
            parts_with_suppliers = session.exec(select(PartModel).where(PartModel.supplier.is_not(None))).all()
            for part in parts_with_suppliers:
                part.supplier = None
                part.supplier_part_number = None
                part.supplier_url = None
            result["parts_supplier_cleared"] = len(parts_with_suppliers)
            
            session.commit()
        
        # Log the activity
        try:
            await activity_service.log_activity(
                action="cleared",
                entity_type="supplier_data",
                entity_name="All supplier data",
                user=current_user,
                details=result
            )
        except Exception as activity_error:
            logger.warning(f"Failed to log supplier clear activity: {activity_error}")
        
        return ResponseSchema(
            status="success",
            message="All supplier data has been cleared successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error clearing supplier data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear supplier data: {str(e)}"
        )

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