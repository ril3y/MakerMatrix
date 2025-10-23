"""
Task Route Factory

Centralized factory for generating quick task creation endpoints with standardized patterns.
This eliminates 200+ lines of duplication across task_routes.py quick endpoints.

Step 12.4: Task Architecture Optimization
"""

from typing import Dict, Any, List, Optional, Callable
from fastapi import HTTPException, Depends
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
from MakerMatrix.services.system.task_service import task_service
import logging

logger = logging.getLogger(__name__)


class TaskRouteFactory:
    """
    Factory for generating standardized quick task creation endpoints.
    
    ARCHITECTURE IMPROVEMENT: This factory eliminates massive duplication in task_routes.py
    by providing a unified pattern for quick task creation with consistent:
    - Error handling
    - Validation
    - Logging
    - Response formatting
    """
    
    @staticmethod
    def create_quick_task_endpoint(
        task_type: TaskType,
        task_name_template: str,
        description_template: str,
        required_fields: List[str] = None,
        validation_func: Optional[Callable] = None,
        permission: str = "tasks:create",
        default_priority: TaskPriority = TaskPriority.NORMAL,
        admin_only: bool = False
    ):
        """
        Generate a standardized quick task creation endpoint.
        
        Args:
            task_type: TaskType enum value
            task_name_template: Template for task name (can use {field} placeholders)
            description_template: Template for description (can use {field} placeholders)
            required_fields: List of required fields in request
            validation_func: Optional custom validation function
            permission: Required permission (default: "tasks:create")
            default_priority: Default task priority
            admin_only: Whether this requires admin permission
        
        Returns:
            FastAPI endpoint function
        """
        required_fields = required_fields or []
        actual_permission = "admin" if admin_only else permission
        
        async def endpoint_handler(
            request: Dict[str, Any],
            current_user: UserModel = Depends(require_permission(actual_permission))
        ):
            try:
                # Validate required fields
                missing_fields = [field for field in required_fields if not request.get(field)]
                if missing_fields:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Missing required fields: {', '.join(missing_fields)}"
                    )
                
                # Custom validation if provided
                if validation_func:
                    validation_result = await validation_func(request)
                    if validation_result is not True:
                        raise HTTPException(status_code=400, detail=validation_result)
                
                # Build task name and description from templates with safe formatting
                try:
                    # Handle special cases like array length
                    format_data = dict(request)
                    if "part_ids" in request and isinstance(request["part_ids"], list):
                        format_data["part_ids|length"] = len(request["part_ids"])
                    
                    task_name = task_name_template.format(**format_data)
                    description = description_template.format(**format_data)
                except KeyError as e:
                    # Fallback for missing template variables
                    task_name = f"{task_type.value} task"
                    description = f"Task type: {task_type.value}"
                
                # Create task request with automatic relationship detection
                related_entity_type = request.get("related_entity_type")
                related_entity_id = request.get("related_entity_id")
                
                # Auto-detect relationships for part-based tasks
                if not related_entity_type and "part_id" in request:
                    related_entity_type = "part"
                    related_entity_id = request["part_id"]
                elif not related_entity_type and task_type in [TaskType.BACKUP_CREATION]:
                    related_entity_type = "system"
                    related_entity_id = "database"
                
                task_request = CreateTaskRequest(
                    task_type=task_type,
                    name=task_name,
                    description=description,
                    priority=request.get("priority", default_priority),
                    input_data=TaskRouteFactory._extract_input_data(request),
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id
                )
                
                # Create the task
                task_response = await task_service.create_task(task_request, user_id=current_user.id)

                if not task_response.success:
                    # CRITICAL SECURITY FIX (CVE-009): Use status_code from ServiceResponse
                    # This allows rate limiting (429) and permission errors (403) to return proper codes
                    status_code = task_response.status_code if hasattr(task_response, 'status_code') and task_response.status_code else 500
                    raise HTTPException(status_code=status_code, detail=task_response.message)
                
                logger.info(f"Created {task_type.value} task {task_response.data['id']} for user {current_user.username}")
                
                return {
                    "status": "success",
                    "message": f"{task_type.value.replace('_', ' ').title()} task created successfully",
                    "data": task_response.data
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to create {task_type.value} task: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to create {task_type.value} task: {str(e)}"
                )
        
        return endpoint_handler
    
    @staticmethod
    def _extract_input_data(request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract input data from request, excluding metadata fields.
        
        This standardizes which fields go into the task's input_data vs. task metadata.
        """
        metadata_fields = {
            "priority", "related_entity_type", "related_entity_id", 
            "timeout_seconds", "max_retries"
        }
        
        return {
            key: value for key, value in request.items() 
            if key not in metadata_fields
        }


class TaskValidators:
    """
    Collection of validation functions for different task types.
    
    STANDARDIZATION: Centralizes validation logic that was scattered
    across individual endpoint implementations.
    """
    
    @staticmethod
    async def validate_supplier_enrichment(request: Dict[str, Any]) -> bool:
        """Validate supplier-based enrichment requests"""
        try:
            from MakerMatrix.suppliers.registry import SupplierRegistry
            import re

            supplier = request.get("supplier", "").lower()
            capabilities = request.get("capabilities", [])
            part_id = request.get("part_id", "")

            if not supplier:
                return "supplier is required"

            if not capabilities:
                return "capabilities are required"

            # CRITICAL SECURITY FIX (CVE-004): Path traversal protection in part_id
            if part_id:
                if not isinstance(part_id, str):
                    return "part_id must be a string"

                # Block path traversal sequences
                if '..' in part_id or '/' in part_id or '\\' in part_id:
                    return "part_id cannot contain path traversal sequences (.., /, \\)"

                # Validate format - only alphanumeric, dash, underscore, and colon (for supplier part numbers like "LM358:DIP")
                if not re.match(r'^[a-zA-Z0-9_:-]+$', part_id):
                    return "part_id can only contain letters, numbers, dash, underscore, and colon"

            # CRITICAL SECURITY FIX (CVE-007): Capability whitelist validation
            valid_capabilities = [
                "fetch_datasheet",
                "fetch_image",
                "fetch_pricing",
                "fetch_stock",
                "fetch_specifications",
                "fetch_description",
                "fetch_all",
                "get_part_details",  # McMaster-Carr and other suppliers use this for comprehensive enrichment
                "scrape_part_details",  # Web scraping fallback capability
            ]
            for cap in capabilities:
                if cap not in valid_capabilities:
                    return f"Invalid capability: {cap}. Allowed: {', '.join(valid_capabilities)}"

            # Validate that the supplier has an actual enrichment implementation
            if not SupplierRegistry.is_supplier_available(supplier):
                available_suppliers = SupplierRegistry.get_available_suppliers()
                return f"Supplier '{supplier}' has no enrichment implementation. Available suppliers: {', '.join(available_suppliers)}"

            return True

        except Exception as e:
            logger.error(f"Supplier validation failed: {e}")
            return f"Supplier validation failed: {str(e)}"
    
    @staticmethod
    async def validate_bulk_operation(request: Dict[str, Any]) -> bool:
        """Validate bulk operation requests"""
        part_ids = request.get("part_ids", [])
        
        if not part_ids:
            return "part_ids are required"
        
        if not isinstance(part_ids, list):
            return "part_ids must be a list"
        
        if len(part_ids) > 1000:  # Reasonable limit
            return "part_ids list cannot exceed 1000 items"
        
        return True
    
    @staticmethod
    async def validate_backup_request(request: Dict[str, Any]) -> bool:
        """Validate database backup requests with strict security checks"""
        backup_name = request.get("backup_name", "")

        # Validate backup_name if provided
        if backup_name:
            # Type check
            if not isinstance(backup_name, str):
                return "backup_name must be a string"

            # Length check
            if len(backup_name) > 255:
                return "backup_name exceeds maximum length (255 characters)"

            # CRITICAL SECURITY FIX (CVE-002): Strict alphanumeric whitelist
            # Only allow letters, numbers, dash, and underscore to prevent command injection
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', backup_name):
                return "backup_name can only contain letters, numbers, dash, and underscore (no special characters or spaces)"

            # Block path traversal sequences
            if '..' in backup_name:
                return "backup_name cannot contain path traversal sequences (..)"

        return True
    
    
    @staticmethod
    async def validate_file_import_enrichment(request: Dict[str, Any]) -> bool:
        """Validate file import enrichment requests with security checks"""
        file_name = request.get("file_name", "")
        file_type = request.get("file_type", "")

        # CRITICAL SECURITY FIX (CVE-006): Path traversal protection
        if file_name:
            if not isinstance(file_name, str):
                return "file_name must be a string"

            # Block path traversal sequences
            if '..' in file_name or '/' in file_name or '\\' in file_name:
                return "file_name cannot contain path traversal sequences (.., /, \\)"

            # Validate file extension
            allowed_extensions = ['.csv', '.xls', '.xlsx']
            if not any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                return f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"

        if file_type and file_type not in ["csv", "xls", "xlsx"]:
            return "file_type must be one of: csv, xls, xlsx"

        return True

    @staticmethod
    async def validate_datasheet_download(request: Dict[str, Any]) -> bool:
        """
        Validate datasheet download requests with SSRF protection

        CRITICAL SECURITY FIX (CVE-003): Server-Side Request Forgery (SSRF) protection
        """
        import ipaddress
        import socket
        from urllib.parse import urlparse

        datasheet_url = request.get("datasheet_url", "")
        part_id = request.get("part_id", "")

        if not datasheet_url:
            return "datasheet_url is required"

        if not part_id:
            return "part_id is required"

        # Validate part_id for path traversal (CVE-004)
        if '..' in part_id or '/' in part_id or '\\' in part_id:
            return "part_id cannot contain path traversal sequences"

        try:
            parsed = urlparse(datasheet_url)

            # Only allow HTTPS (not HTTP, file://, ftp://, etc.)
            ALLOWED_SCHEMES = ['https']
            if parsed.scheme not in ALLOWED_SCHEMES:
                return f"Invalid URL scheme. Only HTTPS allowed (got: {parsed.scheme})"

            # Block file:// protocol explicitly
            if parsed.scheme == 'file':
                return "file:// URLs are not allowed"

            # Get hostname
            hostname = parsed.hostname
            if not hostname:
                return "Invalid URL: no hostname"

            # Block localhost/loopback addresses
            localhost_variants = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
            if hostname.lower() in localhost_variants:
                return f"Blocked hostname: {hostname} (localhost/loopback not allowed)"

            # Resolve DNS and check IP address
            try:
                ip_str = socket.gethostbyname(hostname)
                ip_obj = ipaddress.ip_address(ip_str)

                # Define blocked network ranges
                BLOCKED_NETWORKS = [
                    ipaddress.ip_network('127.0.0.0/8'),      # Loopback
                    ipaddress.ip_network('10.0.0.0/8'),       # Private Class A
                    ipaddress.ip_network('172.16.0.0/12'),    # Private Class B
                    ipaddress.ip_network('192.168.0.0/16'),   # Private Class C
                    ipaddress.ip_network('169.254.0.0/16'),   # Link-local (AWS metadata)
                    ipaddress.ip_network('224.0.0.0/4'),      # Multicast
                    ipaddress.ip_network('240.0.0.0/4'),      # Reserved
                ]

                # Check if IP is in any blocked network
                for blocked_net in BLOCKED_NETWORKS:
                    if ip_obj in blocked_net:
                        return f"Blocked IP address: {ip_str} (internal/private network)"

            except socket.gaierror:
                return f"Cannot resolve hostname: {hostname}"
            except ValueError as e:
                return f"Invalid IP address: {str(e)}"

            # Only allow standard HTTPS port (443) or no port specified
            if parsed.port and parsed.port != 443:
                return f"Non-standard port not allowed: {parsed.port} (only port 443 or default allowed)"

            # Domain whitelist (optional but recommended for production)
            # Uncomment and customize for your trusted supplier domains
            ALLOWED_DOMAINS = [
                'digikey.com',
                'mouser.com',
                'lcsc.com',
                'seeedstudio.com',
                'adafruit.com',
                'sparkfun.com',
                'pololu.com',
                'jameco.com',
                'newark.com',
                'element14.com',
                'arrow.com',
                'alliedelec.com',
                'mcmaster.com'
            ]

            # Check if hostname ends with any allowed domain
            if not any(hostname.endswith(domain) for domain in ALLOWED_DOMAINS):
                logger.warning(f"Datasheet download from non-whitelisted domain: {hostname}")
                # For now, just log warning. To enforce, uncomment the next line:
                # return f"Domain {hostname} is not in allowlist. Allowed: {', '.join(ALLOWED_DOMAINS)}"

            return True

        except Exception as e:
            logger.error(f"Datasheet URL validation error: {e}")
            return f"URL validation failed: {str(e)}"


# Pre-configured task endpoint generators
def create_part_enrichment_endpoint():
    """Generate part enrichment endpoint"""
    return TaskRouteFactory.create_quick_task_endpoint(
        task_type=TaskType.PART_ENRICHMENT,
        task_name_template="Enrich part {part_id}",
        description_template="Enrich part using {supplier} with capabilities: {capabilities}",
        required_fields=["part_id", "supplier", "capabilities"],
        validation_func=TaskValidators.validate_supplier_enrichment
    )


def create_datasheet_fetch_endpoint():
    """Generate datasheet fetch endpoint"""
    async def datasheet_handler(request: Dict[str, Any], current_user):
        # Auto-add capabilities if not provided
        if "capabilities" not in request:
            request["capabilities"] = ["fetch_datasheet"]
        
        factory_handler = TaskRouteFactory.create_quick_task_endpoint(
            task_type=TaskType.DATASHEET_FETCH,
            task_name_template="Fetch datasheet for part {part_id}",
            description_template="Fetch datasheet using {supplier}",
            required_fields=["part_id"]
        )
        return await factory_handler(request, current_user)
    
    return datasheet_handler


def create_image_fetch_endpoint():
    """Generate image fetch endpoint"""
    async def image_handler(request: Dict[str, Any], current_user):
        # Auto-add capabilities if not provided
        if "capabilities" not in request:
            request["capabilities"] = ["fetch_image"]
        
        factory_handler = TaskRouteFactory.create_quick_task_endpoint(
            task_type=TaskType.IMAGE_FETCH,
            task_name_template="Fetch image for part {part_id}",
            description_template="Fetch image using {supplier}",
            required_fields=["part_id"]
        )
        return await factory_handler(request, current_user)
    
    return image_handler


def create_bulk_enrichment_endpoint():
    """Generate bulk enrichment endpoint"""
    return TaskRouteFactory.create_quick_task_endpoint(
        task_type=TaskType.BULK_ENRICHMENT,
        task_name_template="Bulk enrich {part_ids|length} parts",
        description_template="Bulk enrich parts using {supplier} with capabilities: {capabilities}",
        required_fields=["part_ids"],
        validation_func=TaskValidators.validate_bulk_operation
    )


def create_price_update_endpoint():
    """Generate price update endpoint"""
    async def price_handler(request: Dict[str, Any], current_user):
        # Auto-add capabilities if not provided
        if "capabilities" not in request:
            request["capabilities"] = ["fetch_pricing"]
        
        factory_handler = TaskRouteFactory.create_quick_task_endpoint(
            task_type=TaskType.PRICE_UPDATE,
            task_name_template="Update prices for {part_ids|length} parts",
            description_template="Update part prices using {supplier}",
            required_fields=["part_ids"],
            validation_func=TaskValidators.validate_bulk_operation
        )
        return await factory_handler(request, current_user)
    
    return price_handler


def create_database_backup_endpoint():
    """Generate database backup endpoint"""
    return TaskRouteFactory.create_quick_task_endpoint(
        task_type=TaskType.BACKUP_CREATION,
        task_name_template="Database Backup: {backup_name}",
        description_template="Create comprehensive backup including database, datasheets: {include_datasheets}, images: {include_images}",
        required_fields=[],
        validation_func=TaskValidators.validate_backup_request,
        admin_only=True,
        default_priority=TaskPriority.HIGH
    )


def create_datasheet_download_endpoint():
    """Generate datasheet download endpoint with SSRF protection"""
    return TaskRouteFactory.create_quick_task_endpoint(
        task_type=TaskType.DATASHEET_DOWNLOAD,
        task_name_template="Download datasheet for part {part_id}",
        description_template="Download datasheet from {supplier} for part",
        required_fields=["part_id", "datasheet_url", "supplier"],
        validation_func=TaskValidators.validate_datasheet_download,  # CVE-003 fix
        default_priority=TaskPriority.NORMAL
    )




def create_file_import_enrichment_endpoint():
    """Generate file import enrichment endpoint (modern replacement for CSV enrichment)"""
    async def file_import_handler(request: Dict[str, Any], current_user):
        # Auto-add default values
        request.setdefault("enrichment_enabled", True)
        
        factory_handler = TaskRouteFactory.create_quick_task_endpoint(
            task_type=TaskType.FILE_IMPORT_ENRICHMENT,
            task_name_template="File Import Enrichment: {file_name}",
            description_template="Enrich parts imported from {file_name} ({file_type})",
            required_fields=[],
            validation_func=TaskValidators.validate_file_import_enrichment
        )
        return await factory_handler(request, current_user)
    
    return file_import_handler