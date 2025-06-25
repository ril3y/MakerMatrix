"""
Base Supplier Interface

Defines the abstract interface that all supplier implementations must follow.
This ensures consistency and makes it easy to add new suppliers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp
import functools
import time
import logging
from datetime import datetime

class FieldType(Enum):
    """Types of configuration/credential fields"""
    TEXT = "text"
    PASSWORD = "password"
    EMAIL = "email"
    URL = "url"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    TEXTAREA = "textarea"
    INFO = "info"        # Display-only informational text
    HIDDEN = "hidden"    # Hidden field for internal values

class SupplierCapability(Enum):
    """Capabilities that suppliers can support"""
    SEARCH_PARTS = "search_parts"
    GET_PART_DETAILS = "get_part_details"
    FETCH_DATASHEET = "fetch_datasheet"
    FETCH_IMAGE = "fetch_image"
    FETCH_PRICING = "fetch_pricing"
    FETCH_STOCK = "fetch_stock"
    FETCH_SPECIFICATIONS = "fetch_specifications"
    BULK_SEARCH = "bulk_search"
    PARAMETRIC_SEARCH = "parametric_search"
    IMPORT_ORDERS = "import_orders"  # Import order files (CSV, XLS, etc.)

@dataclass
class FieldDefinition:
    """Definition of a configuration or credential field"""
    name: str
    label: str
    field_type: FieldType
    required: bool = True
    description: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    options: Optional[List[Dict[str, str]]] = None  # For SELECT type
    validation: Optional[Dict[str, Any]] = None  # min_length, max_length, pattern, etc.

@dataclass
class PartSearchResult:
    """Result from part search"""
    supplier_part_number: str
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    stock_quantity: Optional[int] = None
    pricing: Optional[List[Dict[str, Any]]] = None  # [{"quantity": 1, "price": 1.23, "currency": "USD"}]
    specifications: Optional[Dict[str, Any]] = None
    additional_data: Optional[Dict[str, Any]] = None

@dataclass
class ConfigurationOption:
    """A configuration option for a supplier (e.g., sandbox vs production)"""
    name: str
    label: str
    description: str
    schema: List['FieldDefinition']
    is_default: bool = False
    requirements: Optional[Dict[str, Any]] = None  # Additional requirements like OAuth setup

@dataclass
class CapabilityRequirement:
    """Defines what credentials/config a capability requires"""
    capability: SupplierCapability
    required_credentials: List[str] = None  # e.g., ["api_key"], ["client_id", "client_secret"]
    optional_credentials: List[str] = None  # Credentials that enhance but aren't required
    description: str = ""
    
    def __post_init__(self):
        if self.required_credentials is None:
            self.required_credentials = []
        if self.optional_credentials is None:
            self.optional_credentials = []

@dataclass
class ImportResult:
    """Result from importing an order file"""
    success: bool
    imported_count: int = 0
    failed_count: int = 0
    parts: List[Dict[str, Any]] = None  # List of part data dictionaries
    failed_items: List[Dict[str, Any]] = None  # Failed items with error reasons
    warnings: List[str] = None
    order_info: Optional[Dict[str, Any]] = None  # Extracted order metadata
    parser_type: Optional[str] = None  # Which parser was used
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.parts is None:
            self.parts = []
        if self.failed_items is None:
            self.failed_items = []
        if self.warnings is None:
            self.warnings = []

@dataclass 
class SupplierInfo:
    """Information about a supplier"""
    name: str
    display_name: str
    description: str
    website_url: Optional[str] = None
    api_documentation_url: Optional[str] = None
    supports_oauth: bool = False
    rate_limit_info: Optional[str] = None
    supports_multiple_environments: bool = False
    supported_file_types: List[str] = None  # e.g., ["csv", "xls", "xlsx"]
    
    def __post_init__(self):
        if self.supported_file_types is None:
            self.supported_file_types = []

logger = logging.getLogger(__name__)

class BaseSupplier(ABC):
    """
    Abstract base class for all supplier implementations.
    
    Each supplier must implement these methods to provide a consistent interface
    for discovering capabilities, configuring credentials, and fetching data.
    
    Automatically tracks API usage for all supplier methods.
    """
    
    def __init__(self):
        self._configured = False
        self._credentials: Dict[str, Any] = {}
        self._config: Dict[str, Any] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_service = None  # Lazy loaded to avoid circular imports
    
    def _get_rate_limit_service(self):
        """Lazy load rate limit service to avoid circular imports"""
        if self._rate_limit_service is None:
            try:
                # Lazy import to avoid circular dependency
                from ..services.rate_limit_service import RateLimitService
                from ..models.models import engine
                self._rate_limit_service = RateLimitService(engine)
            except ImportError as e:
                logger.warning(f"Could not import RateLimitService: {e}")
                self._rate_limit_service = None
        return self._rate_limit_service
    
    def _track_api_call(self, endpoint_type: str):
        """Decorator to track API calls with rate limiting and usage statistics"""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                supplier_name = self.get_supplier_info().name
                rate_service = self._get_rate_limit_service()
                
                if not rate_service:
                    # If rate limiting service is not available, just call the function
                    return await func(*args, **kwargs)
                
                start_time = time.time()
                success = False
                error_message = None
                result = None
                
                try:
                    # Check rate limits before making the request
                    rate_status = await rate_service.check_rate_limit(supplier_name, endpoint_type)
                    if not rate_status.get("allowed", True):
                        from ..suppliers.exceptions import SupplierRateLimitError
                        raise SupplierRateLimitError(
                            f"Rate limit exceeded for {supplier_name}",
                            supplier_name=supplier_name
                        )
                    
                    # Make the actual API call
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                    
                except Exception as e:
                    error_message = str(e)
                    logger.error(f"API call failed for {supplier_name}.{endpoint_type}: {e}")
                    raise
                
                finally:
                    # Record the request regardless of success/failure
                    try:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        await rate_service.record_request(
                            supplier_name=supplier_name,
                            endpoint_type=endpoint_type,
                            success=success,
                            response_time_ms=response_time_ms,
                            error_message=error_message,
                            request_metadata={
                                "method": func.__name__,
                                "args_count": len(args),
                                "kwargs_keys": list(kwargs.keys())
                            }
                        )
                    except Exception as tracking_error:
                        logger.error(f"Failed to record API usage: {tracking_error}")
                        # Don't let tracking errors affect the main functionality
                        pass
            
            return wrapper
        return decorator
    
    # ========== Supplier Information ==========
    
    @abstractmethod
    def get_supplier_info(self) -> SupplierInfo:
        """Get basic information about this supplier"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[SupplierCapability]:
        """Get list of capabilities this supplier supports"""
        pass
    
    @abstractmethod
    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Get requirements for each capability"""
        pass
    
    # ========== Schema Definitions ==========
    
    @abstractmethod
    def get_credential_schema(self) -> List[FieldDefinition]:
        """Get the schema for credentials this supplier requires"""
        pass
    
    @abstractmethod 
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        """
        Get the schema for configuration fields this supplier needs.
        
        Returns:
            List of FieldDefinition objects defining configuration options.
            For suppliers with multiple configuration methods, return all options
            and let the frontend handle showing appropriate fields based on user selection.
        
        Args:
            **kwargs: Optional parameters for dynamic schema generation
        """
        pass
    
    def get_configuration_options(self) -> List[ConfigurationOption]:
        """
        Get all possible configuration options for this supplier.
        
        Returns:
            List of ConfigurationOption objects defining different configuration methods.
            
        Default implementation returns a single configuration option.
        Suppliers with multiple methods (like DigiKey sandbox vs production) should override this.
        """
        return [
            ConfigurationOption(
                name='default',
                label=f'{self.get_supplier_info().display_name} Configuration',
                description=f'Standard configuration for {self.get_supplier_info().display_name}',
                schema=self.get_configuration_schema(),
                is_default=True
            )
        ]
    
    def get_configuration_options_dict(self) -> List[Dict[str, Any]]:
        """
        Get configuration options as dictionaries for backward compatibility.
        
        Returns configuration options in the legacy dictionary format.
        """
        options = []
        for config_option in self.get_configuration_options():
            options.append({
                'name': config_option.name,
                'label': config_option.label,
                'description': config_option.description,
                'schema': config_option.schema,
                'is_default': config_option.is_default,
                'requirements': config_option.requirements
            })
        return options
    
    def validate_configuration_option(self, option_name: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a configuration option against its schema.
        
        Args:
            option_name: Name of the configuration option to validate
            config_data: Configuration data to validate
            
        Returns:
            Dictionary with 'valid' boolean and 'errors' list
        """
        # Find the configuration option
        config_option = None
        for option in self.get_configuration_options():
            if option.name == option_name:
                config_option = option
                break
        
        if not config_option:
            return {
                'valid': False,
                'errors': [f'Unknown configuration option: {option_name}']
            }
        
        errors = []
        
        # Validate each field in the schema
        for field in config_option.schema:
            value = config_data.get(field.name)
            
            # Check required fields
            if field.required and (value is None or value == ''):
                errors.append(f'{field.label} is required')
                continue
            
            # Skip validation for non-required empty fields
            if not field.required and (value is None or value == ''):
                continue
            
            # Type-specific validation
            if field.field_type == FieldType.EMAIL and value:
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, value):
                    errors.append(f'{field.label} must be a valid email address')
            
            elif field.field_type == FieldType.URL and value:
                import re
                url_pattern = r'^https?://[^\s]+$'
                if not re.match(url_pattern, value):
                    errors.append(f'{field.label} must be a valid URL')
            
            elif field.field_type == FieldType.NUMBER and value:
                try:
                    float(value)
                except ValueError:
                    errors.append(f'{field.label} must be a valid number')
            
            # Custom validation rules
            if field.validation:
                if 'min_length' in field.validation and len(str(value)) < field.validation['min_length']:
                    errors.append(f'{field.label} must be at least {field.validation["min_length"]} characters')
                
                if 'max_length' in field.validation and len(str(value)) > field.validation['max_length']:
                    errors.append(f'{field.label} must be no more than {field.validation["max_length"]} characters')
                
                if 'pattern' in field.validation:
                    import re
                    if not re.match(field.validation['pattern'], str(value)):
                        errors.append(f'{field.label} format is invalid')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    # ========== Configuration and Authentication ==========
    
    def configure(self, credentials: Dict[str, Any], config: Dict[str, Any] = None):
        """Configure the supplier with credentials and optional config"""
        self._credentials = credentials.copy()
        self._config = config.copy() if config else {}
        self._configured = True
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the supplier using configured credentials.
        Returns True if authentication successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the supplier API.
        Returns dict with 'success', 'message', and optional 'details'.
        """
        pass
    
    # ========== API Tracking Helpers ==========
    
    async def _tracked_api_call(self, endpoint_type: str, api_func: Callable, *args, **kwargs):
        """Helper method to track any API call with rate limiting and usage statistics"""
        supplier_name = self.get_supplier_info().name
        rate_service = self._get_rate_limit_service()
        
        if not rate_service:
            # If rate limiting service is not available, just call the function
            return await api_func(*args, **kwargs)
        
        start_time = time.time()
        success = False
        error_message = None
        result = None
        
        try:
            # Check rate limits before making the request
            rate_status = await rate_service.check_rate_limit(supplier_name, endpoint_type)
            if not rate_status.get("allowed", True):
                from .exceptions import SupplierRateLimitError
                raise SupplierRateLimitError(
                    f"Rate limit exceeded for {supplier_name}",
                    supplier_name=supplier_name
                )
            
            # Make the actual API call
            result = await api_func(*args, **kwargs)
            success = True
            return result
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"API call failed for {supplier_name}.{endpoint_type}: {e}")
            raise
        
        finally:
            # Record the request regardless of success/failure
            try:
                response_time_ms = int((time.time() - start_time) * 1000)
                await rate_service.record_request(
                    supplier_name=supplier_name,
                    endpoint_type=endpoint_type,
                    success=success,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    request_metadata={
                        "function": api_func.__name__ if hasattr(api_func, '__name__') else str(api_func),
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                )
            except Exception as tracking_error:
                logger.error(f"Failed to record API usage: {tracking_error}")
                # Don't let tracking errors affect the main functionality
                pass
    
    # ========== Core Functionality ==========
    
    @abstractmethod
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using a text query"""
        pass
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific part"""
        # Default implementation with tracking - subclasses can override for more efficient single-part lookup
        async def _impl():
            results = await self.search_parts(supplier_part_number, limit=1)
            return results[0] if results else None
        
        return await self._tracked_api_call("get_part_details", _impl)
    
    async def bulk_search_parts(self, queries: List[str], limit_per_query: int = 10) -> Dict[str, List[PartSearchResult]]:
        """Search for multiple parts at once (if supported)"""
        # Default implementation with tracking - subclasses can override for more efficient bulk operations
        async def _impl():
            results = {}
            for query in queries:
                try:
                    results[query] = await self.search_parts(query, limit=limit_per_query)
                except Exception as e:
                    results[query] = []
            return results
        
        return await self._tracked_api_call("bulk_search", _impl)
    
    # ========== Optional Advanced Features ==========
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a part (if supported)"""
        async def _impl():
            if SupplierCapability.FETCH_DATASHEET not in self.get_capabilities():
                return None
            # Subclasses should implement this
            return None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a part (if supported)"""
        async def _impl():
            if SupplierCapability.FETCH_IMAGE not in self.get_capabilities():
                return None
            # Subclasses should implement this
            return None
        
        return await self._tracked_api_call("fetch_image", _impl)
    
    async def fetch_pricing(self, supplier_part_number: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch current pricing for a part (if supported)"""
        async def _impl():
            if SupplierCapability.FETCH_PRICING not in self.get_capabilities():
                return None
            # Subclasses should implement this
            return None
        
        return await self._tracked_api_call("fetch_pricing", _impl)
    
    async def fetch_stock(self, supplier_part_number: str) -> Optional[int]:
        """Fetch current stock level for a part (if supported)"""
        async def _impl():
            if SupplierCapability.FETCH_STOCK not in self.get_capabilities():
                return None
            # Subclasses should implement this
            return None
        
        return await self._tracked_api_call("fetch_stock", _impl)
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for a part (if supported)"""
        async def _impl():
            if SupplierCapability.FETCH_SPECIFICATIONS not in self.get_capabilities():
                return None
            # Subclasses should implement this
            return None
        
        return await self._tracked_api_call("fetch_specifications", _impl)
    
    # ========== Order Import Features ==========
    
    async def import_order_file(self, file_content: bytes, file_type: str, filename: str = None) -> ImportResult:
        """Import order file (CSV, XLS, etc.) - usually requires no API key"""
        async def _impl():
            if SupplierCapability.IMPORT_ORDERS not in self.get_capabilities():
                return ImportResult(
                    success=False,
                    error_message=f"{self.get_supplier_info().display_name} does not support order file imports"
                )
            # Subclasses should implement this
            return ImportResult(
                success=False,
                error_message="Import not implemented for this supplier"
            )
        
        return await self._tracked_api_call("import_orders", _impl)
    
    def can_import_file(self, filename: str, file_content: bytes = None) -> bool:
        """Check if this supplier can handle this file"""
        # Default implementation - check if IMPORT_ORDERS capability exists
        # and file type is supported
        if SupplierCapability.IMPORT_ORDERS not in self.get_capabilities():
            return False
        
        # Check file extension
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        supported_types = self.get_supplier_info().supported_file_types
        
        if file_ext and supported_types and file_ext in supported_types:
            return True
        
        # Subclasses should override for content-based detection
        return False
    
    def get_import_file_preview(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Get a preview of what will be imported from a file"""
        # Default implementation - subclasses should override
        return {
            "headers": [],
            "preview_rows": [],
            "total_rows": 0,
            "detected_supplier": self.get_supplier_info().name
        }
    
    # ========== Capability Checking ==========
    
    def is_capability_available(self, capability: SupplierCapability) -> bool:
        """Check if a capability is available with current configuration"""
        if capability not in self.get_capabilities():
            return False
        
        requirements = self.get_capability_requirements().get(capability)
        if not requirements:
            return True  # No requirements means always available
        
        # Check if all required credentials are present
        for cred in requirements.required_credentials:
            if cred not in self._credentials or not self._credentials[cred]:
                return False
        
        return True
    
    def get_missing_credentials_for_capability(self, capability: SupplierCapability) -> List[str]:
        """Get list of missing credentials for a capability"""
        requirements = self.get_capability_requirements().get(capability)
        if not requirements:
            return []
        
        missing = []
        for cred in requirements.required_credentials:
            if cred not in self._credentials or not self._credentials[cred]:
                missing.append(cred)
        
        return missing
    
    # ========== Utility Methods ==========
    
    def is_configured(self) -> bool:
        """Check if supplier has been configured with credentials"""
        return self._configured and bool(self._credentials)
    
    def get_rate_limit_delay(self) -> float:
        """Get the delay (in seconds) to respect rate limits"""
        # Default 1 second delay - subclasses can customize
        return 1.0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session for making API calls"""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self._session and not self._session.closed:
            # Can't await in __del__, so we just close synchronously
            try:
                asyncio.create_task(self.close())
            except:
                pass