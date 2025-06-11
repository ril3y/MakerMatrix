from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Base path for static files
STATIC_BASE_PATH = Path(__file__).parent.parent / "static"

@router.get("/static/images/{filename}")
async def serve_image(filename: str):
    """Serve component images"""
    file_path = STATIC_BASE_PATH / "images" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Invalid file")
    
    # Security check - make sure the file is within the images directory
    try:
        file_path.resolve().relative_to((STATIC_BASE_PATH / "images").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",  # Will be detected automatically by FastAPI
        filename=filename
    )

@router.get("/static/datasheets/{filename}")
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