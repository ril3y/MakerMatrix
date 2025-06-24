from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import logging
import httpx
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
router = APIRouter()

# Base path for static files
STATIC_BASE_PATH = Path(__file__).parent.parent / "static"

# Legacy static image route removed - all images now served via /utility/get_image/{uuid}

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