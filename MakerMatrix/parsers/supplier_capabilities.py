"""
Supplier capabilities interface for defining what operations each parser/supplier supports.
This allows the system to know which enrichment operations are available for each supplier.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class CapabilityType(Enum):
    """Types of capabilities a supplier can support"""
    FETCH_DATASHEET = "fetch_datasheet"
    FETCH_IMAGE = "fetch_image"  
    FETCH_PRICING = "fetch_pricing"
    FETCH_STOCK = "fetch_stock"
    FETCH_SPECIFICATIONS = "fetch_specifications"
    FETCH_ALTERNATIVES = "fetch_alternatives"
    VALIDATE_PART_NUMBER = "validate_part_number"
    FETCH_LIFECYCLE_STATUS = "fetch_lifecycle_status"
    ENRICH_BASIC_INFO = "enrich_basic_info"
    FETCH_3D_MODEL = "fetch_3d_model"
    FETCH_FOOTPRINT = "fetch_footprint"
    FETCH_SYMBOL = "fetch_symbol"


@dataclass
class CapabilityMetadata:
    """Metadata for a specific capability"""
    supported: bool = False
    requires_api_key: bool = False
    rate_limited: bool = False
    cost_per_request: Optional[float] = None
    max_requests_per_minute: Optional[int] = None
    description: str = ""
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class SupplierCapabilities(ABC):
    """
    Abstract base class for defining supplier capabilities.
    Each parser should implement this to declare what operations it supports.
    """
    
    def __init__(self, supplier_name: str):
        self.supplier_name = supplier_name
        self._capabilities: Dict[CapabilityType, CapabilityMetadata] = {}
        self._initialize_capabilities()
    
    @abstractmethod
    def _initialize_capabilities(self):
        """Initialize the capabilities this supplier supports"""
        pass
    
    def supports_capability(self, capability: CapabilityType) -> bool:
        """Check if this supplier supports a specific capability"""
        return (
            capability in self._capabilities and 
            self._capabilities[capability].supported
        )
    
    def get_capability_metadata(self, capability: CapabilityType) -> Optional[CapabilityMetadata]:
        """Get metadata for a specific capability"""
        return self._capabilities.get(capability)
    
    def get_supported_capabilities(self) -> List[CapabilityType]:
        """Get list of all supported capabilities"""
        return [
            cap for cap, metadata in self._capabilities.items() 
            if metadata.supported
        ]
    
    def get_capabilities_summary(self) -> Dict[str, Any]:
        """Get a summary of all capabilities for API responses"""
        return {
            "supplier": self.supplier_name,
            "supported_capabilities": [cap.value for cap in self.get_supported_capabilities()],
            "capabilities_detail": {
                cap.value: {
                    "supported": metadata.supported,
                    "requires_api_key": metadata.requires_api_key,
                    "rate_limited": metadata.rate_limited,
                    "description": metadata.description
                }
                for cap, metadata in self._capabilities.items()
            }
        }
    
    def add_capability(self, capability: CapabilityType, metadata: CapabilityMetadata):
        """Add or update a capability"""
        self._capabilities[capability] = metadata


class LCSCCapabilities(SupplierCapabilities):
    """Capabilities for LCSC supplier"""
    
    def __init__(self):
        super().__init__("LCSC")
    
    def _initialize_capabilities(self):
        self._capabilities = {
            CapabilityType.FETCH_DATASHEET: CapabilityMetadata(
                supported=True,
                description="Fetch datasheet URL from LCSC/EasyEDA API",
                examples=["C1525", "C17414"]
            ),
            CapabilityType.FETCH_IMAGE: CapabilityMetadata(
                supported=False,  # LCSC doesn't provide component images via API
                description="LCSC does not provide component images via API"
            ),
            CapabilityType.FETCH_PRICING: CapabilityMetadata(
                supported=True,
                description="Fetch pricing tiers from LCSC API",
                examples=["C1525", "C17414"]
            ),
            CapabilityType.FETCH_STOCK: CapabilityMetadata(
                supported=True,
                description="Fetch stock levels from LCSC API"
            ),
            CapabilityType.FETCH_SPECIFICATIONS: CapabilityMetadata(
                supported=True,
                description="Fetch component specifications (value, package, manufacturer, etc.)"
            ),
            CapabilityType.VALIDATE_PART_NUMBER: CapabilityMetadata(
                supported=True,
                description="Validate LCSC part numbers via API lookup"
            ),
            CapabilityType.ENRICH_BASIC_INFO: CapabilityMetadata(
                supported=True,
                description="Enrich basic part information from LCSC/EasyEDA API"
            ),
            CapabilityType.FETCH_3D_MODEL: CapabilityMetadata(
                supported=True,
                description="Fetch 3D models from EasyEDA when available"
            ),
            CapabilityType.FETCH_FOOTPRINT: CapabilityMetadata(
                supported=True,
                description="Fetch PCB footprints from EasyEDA"
            ),
            CapabilityType.FETCH_SYMBOL: CapabilityMetadata(
                supported=True,
                description="Fetch schematic symbols from EasyEDA"
            )
        }


class MouserCapabilities(SupplierCapabilities):
    """Capabilities for Mouser supplier"""
    
    def __init__(self):
        super().__init__("Mouser")
    
    def _initialize_capabilities(self):
        self._capabilities = {
            CapabilityType.FETCH_DATASHEET: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                rate_limited=True,
                max_requests_per_minute=1000,
                description="Fetch datasheet URLs from Mouser API",
                examples=["STM32F103C8T6", "LM358N"]
            ),
            CapabilityType.FETCH_IMAGE: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Fetch high-quality component images from Mouser"
            ),
            CapabilityType.FETCH_PRICING: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                rate_limited=True,
                description="Fetch real-time pricing with quantity breaks"
            ),
            CapabilityType.FETCH_STOCK: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Fetch current stock levels"
            ),
            CapabilityType.FETCH_SPECIFICATIONS: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Fetch detailed component specifications and parameters"
            ),
            CapabilityType.FETCH_ALTERNATIVES: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Fetch alternative/substitute parts"
            ),
            CapabilityType.VALIDATE_PART_NUMBER: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Validate manufacturer part numbers"
            ),
            CapabilityType.FETCH_LIFECYCLE_STATUS: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Fetch product lifecycle status (active, obsolete, etc.)"
            ),
            CapabilityType.ENRICH_BASIC_INFO: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Comprehensive part information enrichment"
            )
        }


class BoltDepotCapabilities(SupplierCapabilities):
    """Capabilities for Bolt Depot supplier (hardware fasteners)"""
    
    def __init__(self):
        super().__init__("Bolt Depot")
    
    def _initialize_capabilities(self):
        self._capabilities = {
            CapabilityType.FETCH_DATASHEET: CapabilityMetadata(
                supported=False,
                description="Hardware fasteners typically don't have datasheets"
            ),
            CapabilityType.FETCH_IMAGE: CapabilityMetadata(
                supported=True,
                description="Fetch product images from Bolt Depot website",
                examples=["1234", "5678"]
            ),
            CapabilityType.FETCH_PRICING: CapabilityMetadata(
                supported=True,
                rate_limited=True,  # Web scraping is rate limited
                description="Scrape pricing from product pages"
            ),
            CapabilityType.FETCH_STOCK: CapabilityMetadata(
                supported=True,
                description="Check availability on product pages"
            ),
            CapabilityType.FETCH_SPECIFICATIONS: CapabilityMetadata(
                supported=True,
                description="Scrape product specifications (material, size, finish, etc.)"
            ),
            CapabilityType.VALIDATE_PART_NUMBER: CapabilityMetadata(
                supported=True,
                description="Validate part numbers by checking if product page exists"
            ),
            CapabilityType.ENRICH_BASIC_INFO: CapabilityMetadata(
                supported=True,
                description="Enrich hardware part information from product pages"
            )
        }


class DigiKeyCapabilities(SupplierCapabilities):
    """Capabilities for DigiKey supplier (future implementation)"""
    
    def __init__(self):
        super().__init__("DigiKey")
    
    def _initialize_capabilities(self):
        self._capabilities = {
            CapabilityType.FETCH_DATASHEET: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                rate_limited=True,
                description="Fetch datasheet URLs from DigiKey API"
            ),
            CapabilityType.FETCH_IMAGE: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Fetch high-quality component images"
            ),
            CapabilityType.FETCH_PRICING: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Fetch pricing with quantity breaks"
            ),
            CapabilityType.FETCH_STOCK: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Real-time stock information"
            ),
            CapabilityType.FETCH_SPECIFICATIONS: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Comprehensive parametric data"
            ),
            CapabilityType.FETCH_ALTERNATIVES: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Alternative and substitute parts"
            ),
            CapabilityType.VALIDATE_PART_NUMBER: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Validate part numbers via API"
            ),
            CapabilityType.FETCH_LIFECYCLE_STATUS: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Product lifecycle information"
            ),
            CapabilityType.ENRICH_BASIC_INFO: CapabilityMetadata(
                supported=True,
                requires_api_key=True,
                description="Complete part information enrichment"
            )
        }


# Dynamic registry using supplier registry system
def _build_dynamic_capabilities_registry() -> Dict[str, SupplierCapabilities]:
    """Build capabilities registry dynamically using supplier registry"""
    registry = {}
    
    try:
        from MakerMatrix.clients.suppliers.supplier_registry import get_available_suppliers, get_supplier_capabilities
        
        # Get all available suppliers from the dynamic registry
        for supplier_name in get_available_suppliers():
            capabilities_list = get_supplier_capabilities(supplier_name)
            
            if capabilities_list:
                # Create a dynamic SupplierCapabilities instance
                capabilities = SupplierCapabilities(
                    name=supplier_name,
                    supported_operations={
                        cap: True for cap in capabilities_list
                    }
                )
                registry[supplier_name] = capabilities
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to build dynamic capabilities registry: {e}")
        
        # Fallback to legacy hardcoded registry
        registry = {
            "LCSC": LCSCCapabilities(),
            "Mouser": MouserCapabilities(),
            "Bolt Depot": BoltDepotCapabilities(),
            "DigiKey": DigiKeyCapabilities(),
        }
    
    return registry


# Dynamic registry - rebuilt on each access to pick up new suppliers
def get_supplier_capabilities(supplier_name: str) -> Optional[SupplierCapabilities]:
    """Get capabilities for a specific supplier using dynamic registry"""
    registry = _build_dynamic_capabilities_registry()
    return registry.get(supplier_name)


def get_all_supplier_capabilities() -> Dict[str, SupplierCapabilities]:
    """Get capabilities for all suppliers using dynamic registry"""
    return _build_dynamic_capabilities_registry()


def find_suppliers_with_capability(capability: CapabilityType) -> List[str]:
    """Find all suppliers that support a specific capability"""
    return [
        supplier_name for supplier_name, capabilities in SUPPLIER_CAPABILITIES_REGISTRY.items()
        if capabilities.supports_capability(capability)
    ]