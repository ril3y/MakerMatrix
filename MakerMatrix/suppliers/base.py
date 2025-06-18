"""
Base Supplier Interface

Defines the abstract interface that all supplier implementations must follow.
This ensures consistency and makes it easy to add new suppliers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import aiohttp
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
class SupplierInfo:
    """Information about a supplier"""
    name: str
    display_name: str
    description: str
    website_url: Optional[str] = None
    api_documentation_url: Optional[str] = None
    supports_oauth: bool = False
    rate_limit_info: Optional[str] = None

class BaseSupplier(ABC):
    """
    Abstract base class for all supplier implementations.
    
    Each supplier must implement these methods to provide a consistent interface
    for discovering capabilities, configuring credentials, and fetching data.
    """
    
    def __init__(self):
        self._configured = False
        self._credentials: Dict[str, Any] = {}
        self._config: Dict[str, Any] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    # ========== Supplier Information ==========
    
    @abstractmethod
    def get_supplier_info(self) -> SupplierInfo:
        """Get basic information about this supplier"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[SupplierCapability]:
        """Get list of capabilities this supplier supports"""
        pass
    
    # ========== Schema Definitions ==========
    
    @abstractmethod
    def get_credential_schema(self) -> List[FieldDefinition]:
        """Get the schema for credentials this supplier requires"""
        pass
    
    @abstractmethod 
    def get_configuration_schema(self) -> List[FieldDefinition]:
        """Get the schema for configuration fields this supplier needs"""
        pass
    
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
    
    # ========== Core Functionality ==========
    
    @abstractmethod
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using a text query"""
        pass
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific part"""
        # Default implementation - subclasses can override for more efficient single-part lookup
        results = await self.search_parts(supplier_part_number, limit=1)
        return results[0] if results else None
    
    async def bulk_search_parts(self, queries: List[str], limit_per_query: int = 10) -> Dict[str, List[PartSearchResult]]:
        """Search for multiple parts at once (if supported)"""
        # Default implementation - subclasses can override for more efficient bulk operations
        results = {}
        for query in queries:
            try:
                results[query] = await self.search_parts(query, limit=limit_per_query)
            except Exception as e:
                results[query] = []
        return results
    
    # ========== Optional Advanced Features ==========
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a part (if supported)"""
        if SupplierCapability.FETCH_DATASHEET not in self.get_capabilities():
            return None
        # Subclasses should implement this
        return None
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a part (if supported)"""
        if SupplierCapability.FETCH_IMAGE not in self.get_capabilities():
            return None
        # Subclasses should implement this
        return None
    
    async def fetch_pricing(self, supplier_part_number: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch current pricing for a part (if supported)"""
        if SupplierCapability.FETCH_PRICING not in self.get_capabilities():
            return None
        # Subclasses should implement this
        return None
    
    async def fetch_stock(self, supplier_part_number: str) -> Optional[int]:
        """Fetch current stock level for a part (if supported)"""
        if SupplierCapability.FETCH_STOCK not in self.get_capabilities():
            return None
        # Subclasses should implement this
        return None
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for a part (if supported)"""
        if SupplierCapability.FETCH_SPECIFICATIONS not in self.get_capabilities():
            return None
        # Subclasses should implement this
        return None
    
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