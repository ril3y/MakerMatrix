import os
import requests
import hashlib
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from urllib.parse import urlparse, unquote
import re

logger = logging.getLogger(__name__)

class FileDownloadService:
    """Service for downloading and managing datasheets and component images"""
    
    def __init__(self, download_config=None):
        self.base_path = Path(__file__).parent.parent / "static"
        self.datasheets_path = self.base_path / "datasheets"
        # All images now use uploaded_images directory for consistency
        self.uploaded_images_path = Path(__file__).parent.parent / "uploaded_images"
        
        # Store download configuration
        self.download_config = download_config or {}
        
        # Create directories if they don't exist
        self.datasheets_path.mkdir(parents=True, exist_ok=True)
        self.uploaded_images_path.mkdir(parents=True, exist_ok=True)
        
        # Common headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def download_datasheet(self, url: str, part_number: str, supplier: str = "", file_uuid: str = None) -> Optional[Dict[str, Any]]:
        """Download datasheet and return file info with UUID-based filename"""
        try:
            logger.info(f"Downloading datasheet for {part_number} from {url}")
            
            # Generate UUID for filename if not provided
            if not file_uuid:
                file_uuid = str(uuid.uuid4())
            
            # Determine file extension
            parsed_url = urlparse(url)
            path = unquote(parsed_url.path)
            
            # Try to determine extension from URL
            if path.lower().endswith('.pdf'):
                extension = '.pdf'
            elif 'pdf' in url.lower() or 'datasheet' in url.lower():
                extension = '.pdf'
            else:
                extension = '.pdf'  # Default to PDF for datasheets
            
            # Use UUID-based filename
            filename = f"{file_uuid}{extension}"
            file_path = self.datasheets_path / filename
            
            # Generate original filename for reference
            safe_part_number = self._sanitize_filename(part_number)
            safe_supplier = self._sanitize_filename(supplier) if supplier else "unknown"
            original_filename = f"{safe_supplier}_{safe_part_number}_datasheet{extension}"
            
            # Check if file already exists
            if file_path.exists():
                logger.info(f"Datasheet already exists: {filename}")
                return {
                    'filename': filename,
                    'file_path': str(file_path),
                    'original_filename': original_filename,
                    'file_uuid': file_uuid,
                    'url': url,
                    'size': file_path.stat().st_size,
                    'extension': extension,
                    'exists': True
                }
            
            # Download the file with configurable timeout
            timeout = self.download_config.get('download_timeout_seconds', 30)
            response = requests.get(url, headers=self.headers, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' in content_type:
                extension = '.pdf'
            elif 'html' in content_type:
                # This might be a webpage, not a direct PDF link
                logger.warning(f"Datasheet URL appears to be HTML page, not direct PDF: {url}")
                return None
            
            # Update filename with correct extension
            filename = f"{file_uuid}{extension}"
            file_path = self.datasheets_path / filename
            original_filename = f"{safe_supplier}_{safe_part_number}_datasheet{extension}"
            
            # Save the file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = file_path.stat().st_size
            
            # Verify it's not an error page (very small files are suspicious)
            if file_size < 1024:  # Less than 1KB
                logger.warning(f"Downloaded file is very small ({file_size} bytes), might be an error page")
                file_path.unlink()  # Delete the small file
                return None
            
            logger.info(f"Successfully downloaded datasheet: {filename} ({file_size} bytes)")
            
            return {
                'filename': filename,
                'file_path': str(file_path),
                'original_filename': original_filename,
                'file_uuid': file_uuid,
                'url': url,
                'size': file_size,
                'extension': extension,
                'exists': False
            }
            
        except Exception as e:
            logger.error(f"Error downloading datasheet from {url}: {e}")
            return None
    
    def download_image(self, url: str, part_number: str, supplier: str = "") -> Optional[Dict[str, Any]]:
        """Download component image and return file info with UUID-based storage"""
        try:
            logger.info(f"Downloading image for {part_number} from {url}")
            
            # Determine file extension from URL
            parsed_url = urlparse(url)
            path = unquote(parsed_url.path)
            
            # Extract extension
            extension = '.jpg'  # Default
            if path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                extension = Path(path).suffix.lower()
            elif 'jpg' in url.lower() or 'jpeg' in url.lower():
                extension = '.jpg'
            elif 'png' in url.lower():
                extension = '.png'
            elif 'gif' in url.lower():
                extension = '.gif'
            elif 'webp' in url.lower():
                extension = '.webp'
            
            # Always use UUID-based filename for consistency
            image_uuid = str(uuid.uuid4())
            filename = f"{image_uuid}{extension}"
            file_path = self.uploaded_images_path / filename
            
            # Check if file already exists
            if file_path.exists():
                logger.info(f"Image already exists: {filename}")
                return {
                    'filename': filename,
                    'file_path': str(file_path),
                    'image_uuid': image_uuid,
                    'url': url,
                    'size': file_path.stat().st_size,
                    'exists': True
                }
            
            # Download the file with configurable timeout
            timeout = self.download_config.get('download_timeout_seconds', 30)
            response = requests.get(url, headers=self.headers, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type:
                logger.warning(f"URL doesn't appear to be an image: {url} (content-type: {content_type})")
                return None
            
            # Update extension based on content type
            if 'jpeg' in content_type:
                extension = '.jpg'
            elif 'png' in content_type:
                extension = '.png'
            elif 'gif' in content_type:
                extension = '.gif'
            elif 'webp' in content_type:
                extension = '.webp'
            
            # Update filename with correct extension
            filename = f"{safe_supplier}_{safe_part_number}_image{extension}"
            file_path = self.images_path / filename
            
            # Save the file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = file_path.stat().st_size
            
            # Verify it's a valid image (very small files are suspicious)
            if file_size < 100:  # Less than 100 bytes
                logger.warning(f"Downloaded image is very small ({file_size} bytes), might be invalid")
                file_path.unlink()  # Delete the small file
                return None
            
            logger.info(f"Successfully downloaded image: {filename} ({file_size} bytes)")
            
            return {
                'filename': filename,
                'file_path': str(file_path),
                'image_uuid': image_uuid,
                'url': url,
                'size': file_size,
                'exists': False
            }
            
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        # Remove multiple underscores
        filename = re.sub(r'_+', '_', filename)
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        return filename
    
    def get_image_url(self, image_uuid: str) -> str:
        """Generate URL for serving images via utility API"""
        return f"/utility/get_image/{image_uuid}"
    
    def get_datasheet_url(self, filename: str) -> str:
        """Generate URL for serving datasheets via static route"""
        return f"/static/datasheets/{filename}"
    
    def cleanup_old_files(self, days_old: int = 30):
        """Clean up files older than specified days"""
        import time
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        # Only cleanup datasheets and uploaded_images (new unified image storage)
        for directory in [self.datasheets_path, self.uploaded_images_path]:
            if directory.exists():
                for file_path in directory.glob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                        logger.info(f"Removing old file: {file_path}")
                        file_path.unlink()


# Function to get file download service with optional config
def get_file_download_service(download_config=None):
    """Get file download service with optional configuration"""
    return FileDownloadService(download_config=download_config)

# Default singleton instance for backward compatibility
file_download_service = FileDownloadService()