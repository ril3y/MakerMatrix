"""
File System Service for enrichment operations.
Provides centralized file operations for datasheet and image handling.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import uuid

# Optional imports for async functionality
try:
    import aiofiles
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileSystemService:
    """Centralized file operations for enrichment services"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize FileSystemService with configuration.
        
        Args:
            config: Configuration dictionary with file paths and settings
        """
        self.config = config
        self.base_datasheet_path = config.get('datasheet_path', 'datasheets')
        self.base_image_path = config.get('image_path', 'images')
        self.max_file_size = config.get('max_file_size', 10 * 1024 * 1024)  # 10MB default
        self.allowed_image_extensions = config.get('allowed_image_extensions', ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
        self.allowed_datasheet_extensions = config.get('allowed_datasheet_extensions', ['.pdf', '.doc', '.docx', '.txt'])
        
        # Ensure base directories exist
        self.ensure_directory_exists(self.base_datasheet_path)
        self.ensure_directory_exists(self.base_image_path)
    
    def save_file(self, content: bytes, file_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Save file content to the specified path.
        
        Args:
            content: File content as bytes
            file_path: Target file path
            overwrite: Whether to overwrite existing files
            
        Returns:
            Dict with success status and file info
        """
        try:
            # Validate file size
            if len(content) > self.max_file_size:
                return {
                    'success': False,
                    'error': f'File size {len(content)} exceeds maximum {self.max_file_size}',
                    'file_path': file_path
                }
            
            # Check if file exists and overwrite setting
            if os.path.exists(file_path) and not overwrite:
                return {
                    'success': False,
                    'error': f'File already exists: {file_path}',
                    'file_path': file_path,
                    'exists': True
                }
            
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if not self.ensure_directory_exists(directory):
                return {
                    'success': False,
                    'error': f'Failed to create directory: {directory}',
                    'file_path': file_path
                }
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            file_extension = os.path.splitext(file_path)[1].lower()
            
            logger.info(f"Successfully saved file: {file_path} ({file_size} bytes)")
            
            return {
                'success': True,
                'file_path': file_path,
                'file_size': file_size,
                'file_extension': file_extension,
                'overwritten': os.path.exists(file_path) and overwrite
            }
            
        except Exception as e:
            logger.error(f"Failed to save file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    async def download_and_save_file(self, url: str, file_path: str, overwrite: bool = False, 
                                   timeout: int = 30) -> Dict[str, Any]:
        """
        Download file from URL and save to specified path.
        
        Args:
            url: URL to download from
            file_path: Target file path
            overwrite: Whether to overwrite existing files
            timeout: Download timeout in seconds
            
        Returns:
            Dict with success status and file info
        """
        if not ASYNC_AVAILABLE:
            return {
                'success': False,
                'error': 'Async functionality not available. Install aiohttp and aiofiles.',
                'url': url,
                'file_path': file_path
            }
        
        try:
            # Check if file exists and overwrite setting
            if os.path.exists(file_path) and not overwrite:
                return {
                    'success': False,
                    'error': f'File already exists: {file_path}',
                    'file_path': file_path,
                    'exists': True
                }
            
            # Download file
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}: {response.reason}',
                            'url': url,
                            'file_path': file_path
                        }
                    
                    # Check content length
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_file_size:
                        return {
                            'success': False,
                            'error': f'File size {content_length} exceeds maximum {self.max_file_size}',
                            'url': url,
                            'file_path': file_path
                        }
                    
                    # Read content
                    content = await response.read()
                    
                    # Save file
                    return self.save_file(content, file_path, overwrite)
                    
        except Exception as e:
            logger.error(f"Failed to download and save file from {url} to {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'file_path': file_path
            }
    
    def get_datasheet_file_path(self, supplier: str, part_number: str, file_extension: str = '.pdf') -> str:
        """
        Generate file path for datasheet storage.
        
        Args:
            supplier: Supplier name
            part_number: Part number
            file_extension: File extension (default: .pdf)
            
        Returns:
            Full file path for datasheet
        """
        # Sanitize supplier and part number for filesystem
        safe_supplier = self._sanitize_filename(supplier)
        safe_part_number = self._sanitize_filename(part_number)
        
        # Create hierarchical path: datasheets/supplier/part_number.ext
        file_path = os.path.join(
            self.base_datasheet_path,
            safe_supplier,
            f"{safe_part_number}{file_extension}"
        )
        
        return file_path
    
    def get_image_file_path(self, supplier: str, part_number: str, file_extension: str = '.jpg') -> str:
        """
        Generate file path for image storage.
        
        Args:
            supplier: Supplier name
            part_number: Part number
            file_extension: File extension (default: .jpg)
            
        Returns:
            Full file path for image
        """
        # Sanitize supplier and part number for filesystem
        safe_supplier = self._sanitize_filename(supplier)
        safe_part_number = self._sanitize_filename(part_number)
        
        # Create hierarchical path: images/supplier/part_number.ext
        file_path = os.path.join(
            self.base_image_path,
            safe_supplier,
            f"{safe_part_number}{file_extension}"
        )
        
        return file_path
    
    def get_unique_file_path(self, base_path: str, extension: str = '') -> str:
        """
        Generate unique file path by appending UUID if file exists.
        
        Args:
            base_path: Base file path
            extension: File extension
            
        Returns:
            Unique file path
        """
        if extension and not extension.startswith('.'):
            extension = '.' + extension
            
        file_path = base_path + extension
        
        # If file doesn't exist, return as-is
        if not os.path.exists(file_path):
            return file_path
        
        # Generate unique path with UUID
        base_name = os.path.splitext(base_path)[0]
        unique_id = str(uuid.uuid4())[:8]
        unique_path = f"{base_name}_{unique_id}{extension}"
        
        return unique_path
    
    def validate_file_path(self, file_path: str) -> Dict[str, Any]:
        """
        Validate file path for security and constraints.
        
        Args:
            file_path: File path to validate
            
        Returns:
            Dict with validation results
        """
        try:
            # Normalize path
            normalized_path = os.path.normpath(file_path)
            
            # Check for path traversal attempts
            if '..' in normalized_path or normalized_path.startswith('/'):
                return {
                    'valid': False,
                    'error': 'Path traversal attempt detected',
                    'path': file_path
                }
            
            # Check file extension
            file_extension = os.path.splitext(normalized_path)[1].lower()
            allowed_extensions = self.allowed_datasheet_extensions + self.allowed_image_extensions
            
            if file_extension and file_extension not in allowed_extensions:
                return {
                    'valid': False,
                    'error': f'File extension {file_extension} not allowed',
                    'path': file_path,
                    'allowed_extensions': allowed_extensions
                }
            
            # Check path length
            if len(normalized_path) > 255:
                return {
                    'valid': False,
                    'error': 'Path too long (max 255 characters)',
                    'path': file_path
                }
            
            return {
                'valid': True,
                'normalized_path': normalized_path,
                'file_extension': file_extension
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'path': file_path
            }
    
    def ensure_directory_exists(self, directory_path: str) -> bool:
        """
        Ensure directory exists, create if necessary.
        
        Args:
            directory_path: Directory path to create
            
        Returns:
            True if directory exists or was created successfully
        """
        try:
            if not directory_path:
                return False
                
            Path(directory_path).mkdir(parents=True, exist_ok=True)
            return True
            
        except Exception as e:
            logger.error(f"Failed to create directory {directory_path}: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict with file information or None if file doesn't exist
        """
        try:
            if not os.path.exists(file_path):
                return None
                
            stat = os.stat(file_path)
            
            return {
                'file_path': file_path,
                'file_size': stat.st_size,
                'file_extension': os.path.splitext(file_path)[1].lower(),
                'created_at': stat.st_ctime,
                'modified_at': stat.st_mtime,
                'is_file': os.path.isfile(file_path),
                'is_directory': os.path.isdir(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None
    
    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            Dict with success status
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File does not exist: {file_path}',
                    'file_path': file_path
                }
            
            os.remove(file_path)
            logger.info(f"Successfully deleted file: {file_path}")
            
            return {
                'success': True,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for filesystem compatibility.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove/replace problematic characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        # Ensure not empty
        if not sanitized:
            sanitized = 'unnamed'
        
        return sanitized