"""
Enhanced Parser class with supplier capabilities and task system integration.
This extends the basic Parser with enrichment capabilities tied to the task system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import json
import logging
from datetime import datetime

from MakerMatrix.parsers.parser import Parser
from MakerMatrix.parsers.supplier_capabilities import (
    SupplierCapabilities, CapabilityType, get_supplier_capabilities
)


logger = logging.getLogger(__name__)


class EnrichmentResult:
    """Result of an enrichment operation"""
    
    def __init__(self, capability: CapabilityType, success: bool = True, 
                 data: Any = None, error: Optional[str] = None):
        self.capability = capability
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability.value,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class EnhancedParser(Parser):
    """
    Enhanced parser that supports supplier capabilities and task-based enrichment.
    This class extends the basic Parser with modern enrichment capabilities.
    """
    
    def __init__(self, pattern, supplier_name: str):
        super().__init__(pattern)
        self.supplier_name = supplier_name
        self.capabilities = get_supplier_capabilities(supplier_name)
        self.enrichment_results: Dict[str, EnrichmentResult] = {}
        
        if not self.capabilities:
            logger.warning(f"No capabilities defined for supplier: {supplier_name}")
    
    def supports_capability(self, capability: CapabilityType) -> bool:
        """Check if this parser supports a specific capability"""
        if not self.capabilities:
            return False
        return self.capabilities.supports_capability(capability)
    
    def get_supported_capabilities(self) -> List[CapabilityType]:
        """Get list of all supported capabilities"""
        if not self.capabilities:
            return []
        return self.capabilities.get_supported_capabilities()
    
    def get_capabilities_summary(self) -> Dict[str, Any]:
        """Get capabilities summary for API responses"""
        if not self.capabilities:
            return {"supplier": self.supplier_name, "supported_capabilities": [], "capabilities_detail": {}}
        return self.capabilities.get_capabilities_summary()
    
    # Abstract methods for capability-based enrichment
    # Subclasses should implement these based on their specific APIs
    
    async def fetch_datasheet(self, part_number: str) -> EnrichmentResult:
        """Fetch datasheet URL for a part"""
        if not self.supports_capability(CapabilityType.FETCH_DATASHEET):
            return EnrichmentResult(
                CapabilityType.FETCH_DATASHEET, 
                success=False, 
                error="Datasheet fetching not supported by this supplier"
            )
        return await self._fetch_datasheet_impl(part_number)
    
    async def fetch_image(self, part_number: str) -> EnrichmentResult:
        """Fetch image URL for a part"""
        if not self.supports_capability(CapabilityType.FETCH_IMAGE):
            return EnrichmentResult(
                CapabilityType.FETCH_IMAGE, 
                success=False, 
                error="Image fetching not supported by this supplier"
            )
        return await self._fetch_image_impl(part_number)
    
    async def fetch_pricing(self, part_number: str) -> EnrichmentResult:
        """Fetch pricing information for a part"""
        if not self.supports_capability(CapabilityType.FETCH_PRICING):
            return EnrichmentResult(
                CapabilityType.FETCH_PRICING, 
                success=False, 
                error="Pricing fetching not supported by this supplier"
            )
        return await self._fetch_pricing_impl(part_number)
    
    async def fetch_stock(self, part_number: str) -> EnrichmentResult:
        """Fetch stock information for a part"""
        if not self.supports_capability(CapabilityType.FETCH_STOCK):
            return EnrichmentResult(
                CapabilityType.FETCH_STOCK, 
                success=False, 
                error="Stock fetching not supported by this supplier"
            )
        return await self._fetch_stock_impl(part_number)
    
    async def fetch_specifications(self, part_number: str) -> EnrichmentResult:
        """Fetch detailed specifications for a part"""
        if not self.supports_capability(CapabilityType.FETCH_SPECIFICATIONS):
            return EnrichmentResult(
                CapabilityType.FETCH_SPECIFICATIONS, 
                success=False, 
                error="Specifications fetching not supported by this supplier"
            )
        return await self._fetch_specifications_impl(part_number)
    
    async def validate_part_number(self, part_number: str) -> EnrichmentResult:
        """Validate if a part number exists"""
        if not self.supports_capability(CapabilityType.VALIDATE_PART_NUMBER):
            return EnrichmentResult(
                CapabilityType.VALIDATE_PART_NUMBER, 
                success=False, 
                error="Part number validation not supported by this supplier"
            )
        return await self._validate_part_number_impl(part_number)
    
    async def enrich_basic_info(self, part_number: str) -> EnrichmentResult:
        """Perform basic enrichment (name, description, manufacturer, etc.)"""
        if not self.supports_capability(CapabilityType.ENRICH_BASIC_INFO):
            return EnrichmentResult(
                CapabilityType.ENRICH_BASIC_INFO, 
                success=False, 
                error="Basic enrichment not supported by this supplier"
            )
        return await self._enrich_basic_info_impl(part_number)
    
    # Implementation methods - to be overridden by subclasses
    
    async def _fetch_datasheet_impl(self, part_number: str) -> EnrichmentResult:
        """Implementation of datasheet fetching - override in subclasses"""
        return EnrichmentResult(
            CapabilityType.FETCH_DATASHEET, 
            success=False, 
            error="Not implemented"
        )
    
    async def _fetch_image_impl(self, part_number: str) -> EnrichmentResult:
        """Implementation of image fetching - override in subclasses"""
        return EnrichmentResult(
            CapabilityType.FETCH_IMAGE, 
            success=False, 
            error="Not implemented"
        )
    
    async def _fetch_pricing_impl(self, part_number: str) -> EnrichmentResult:
        """Implementation of pricing fetching - override in subclasses"""
        return EnrichmentResult(
            CapabilityType.FETCH_PRICING, 
            success=False, 
            error="Not implemented"
        )
    
    async def _fetch_stock_impl(self, part_number: str) -> EnrichmentResult:
        """Implementation of stock fetching - override in subclasses"""
        return EnrichmentResult(
            CapabilityType.FETCH_STOCK, 
            success=False, 
            error="Not implemented"
        )
    
    async def _fetch_specifications_impl(self, part_number: str) -> EnrichmentResult:
        """Implementation of specifications fetching - override in subclasses"""
        return EnrichmentResult(
            CapabilityType.FETCH_SPECIFICATIONS, 
            success=False, 
            error="Not implemented"
        )
    
    async def _validate_part_number_impl(self, part_number: str) -> EnrichmentResult:
        """Implementation of part number validation - override in subclasses"""
        return EnrichmentResult(
            CapabilityType.VALIDATE_PART_NUMBER, 
            success=False, 
            error="Not implemented"
        )
    
    async def _enrich_basic_info_impl(self, part_number: str) -> EnrichmentResult:
        """Implementation of basic enrichment - override in subclasses"""
        return EnrichmentResult(
            CapabilityType.ENRICH_BASIC_INFO, 
            success=False, 
            error="Not implemented"
        )
    
    # Task-based enrichment methods
    
    async def perform_enrichment_task(self, capabilities: List[CapabilityType], 
                                     part_number: str, progress_callback=None) -> Dict[str, EnrichmentResult]:
        """
        Perform multiple enrichment operations as a task.
        This method is designed to be called from the task system.
        """
        results = {}
        total_capabilities = len(capabilities)
        
        for i, capability in enumerate(capabilities):
            if progress_callback:
                progress_percentage = int((i / total_capabilities) * 100)
                await progress_callback(progress_percentage, f"Processing {capability.value}")
            
            try:
                if capability == CapabilityType.FETCH_DATASHEET:
                    result = await self.fetch_datasheet(part_number)
                elif capability == CapabilityType.FETCH_IMAGE:
                    result = await self.fetch_image(part_number)
                elif capability == CapabilityType.FETCH_PRICING:
                    result = await self.fetch_pricing(part_number)
                elif capability == CapabilityType.FETCH_STOCK:
                    result = await self.fetch_stock(part_number)
                elif capability == CapabilityType.FETCH_SPECIFICATIONS:
                    result = await self.fetch_specifications(part_number)
                elif capability == CapabilityType.VALIDATE_PART_NUMBER:
                    result = await self.validate_part_number(part_number)
                elif capability == CapabilityType.ENRICH_BASIC_INFO:
                    result = await self.enrich_basic_info(part_number)
                else:
                    result = EnrichmentResult(
                        capability, 
                        success=False, 
                        error=f"Unknown capability: {capability.value}"
                    )
                
                results[capability.value] = result
                self.enrichment_results[capability.value] = result
                
                logger.info(f"Enrichment {capability.value} for {part_number}: {'success' if result.success else 'failed'}")
                
            except Exception as e:
                error_msg = f"Error during {capability.value} enrichment: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                result = EnrichmentResult(capability, success=False, error=error_msg)
                results[capability.value] = result
                self.enrichment_results[capability.value] = result
        
        if progress_callback:
            await progress_callback(100, "Enrichment completed")
        
        return results
    
    def get_enrichment_summary(self) -> Dict[str, Any]:
        """Get summary of all enrichment results"""
        return {
            "supplier": self.supplier_name,
            "total_enrichments": len(self.enrichment_results),
            "successful_enrichments": sum(1 for r in self.enrichment_results.values() if r.success),
            "failed_enrichments": sum(1 for r in self.enrichment_results.values() if not r.success),
            "results": {k: v.to_dict() for k, v in self.enrichment_results.items()}
        }
    
    # Backward compatibility with existing enrich method
    def enrich(self):
        """
        Legacy enrich method for backward compatibility.
        New implementations should use the async capability-based methods.
        """
        logger.warning(f"Using legacy enrich() method for {self.supplier_name}. "
                      "Consider implementing async capability-based enrichment.")
        pass
    
    # Task creation helpers
    
    def create_enrichment_task_data(self, part_id: str, capabilities: List[str]) -> Dict[str, Any]:
        """Create task data for enrichment operations"""
        return {
            "part_id": part_id,
            "supplier": self.supplier_name,
            "capabilities": capabilities,
            "parser_class": self.__class__.__name__
        }
    
    def get_recommended_enrichment_capabilities(self) -> List[CapabilityType]:
        """Get recommended capabilities for basic enrichment"""
        recommended = []
        
        # Always try basic info first
        if self.supports_capability(CapabilityType.ENRICH_BASIC_INFO):
            recommended.append(CapabilityType.ENRICH_BASIC_INFO)
        
        # Add datasheet if supported (very useful for electronic components)
        if self.supports_capability(CapabilityType.FETCH_DATASHEET):
            recommended.append(CapabilityType.FETCH_DATASHEET)
        
        # Add image if supported (useful for visual identification)
        if self.supports_capability(CapabilityType.FETCH_IMAGE):
            recommended.append(CapabilityType.FETCH_IMAGE)
        
        # Add pricing if supported (always useful)
        if self.supports_capability(CapabilityType.FETCH_PRICING):
            recommended.append(CapabilityType.FETCH_PRICING)
        
        # Add specifications if supported
        if self.supports_capability(CapabilityType.FETCH_SPECIFICATIONS):
            recommended.append(CapabilityType.FETCH_SPECIFICATIONS)
        
        return recommended


class ParserRegistry:
    """Registry for managing enhanced parsers"""
    
    def __init__(self):
        self._parsers: Dict[str, EnhancedParser] = {}
    
    def register_parser(self, supplier_name: str, parser_class: type):
        """Register a parser for a supplier"""
        self._parsers[supplier_name] = parser_class
    
    def get_parser(self, supplier_name: str) -> Optional[EnhancedParser]:
        """Get parser instance for a supplier"""
        parser_class = self._parsers.get(supplier_name)
        if parser_class:
            return parser_class()
        return None
    
    def get_available_suppliers(self) -> List[str]:
        """Get list of available suppliers"""
        return list(self._parsers.keys())
    
    def get_suppliers_with_capability(self, capability: CapabilityType) -> List[str]:
        """Get suppliers that support a specific capability"""
        suppliers = []
        for supplier_name, parser_class in self._parsers.items():
            parser = parser_class()
            if parser.supports_capability(capability):
                suppliers.append(supplier_name)
        return suppliers


# Global parser registry
parser_registry = ParserRegistry()


def get_enhanced_parser(supplier_name: str) -> Optional[EnhancedParser]:
    """
    Get an enhanced parser instance for a supplier.
    
    Args:
        supplier_name: Name of the supplier (e.g., 'LCSC', 'Mouser', 'DigiKey')
    
    Returns:
        Enhanced parser instance or None if not found
    """
    # For testing and compatibility, create a mock parser if none exists
    if supplier_name and supplier_name not in parser_registry._parsers:
        # Create a mock parser for testing
        class MockParser(EnhancedParser):
            def __init__(self):
                super().__init__("", supplier_name)
            
            async def perform_enrichment_task(self, capabilities, part, progress_callback=None):
                # Mock enrichment results for testing
                results = {}
                for capability in capabilities:
                    if isinstance(capability, str):
                        capability_name = capability
                    else:
                        capability_name = capability.value if hasattr(capability, 'value') else str(capability)
                    
                    results[capability_name] = {
                        "success": True,
                        "data": {
                            "mock_data": f"Mock {capability_name} data for {part.name if hasattr(part, 'name') else 'unknown part'}",
                            "supplier": supplier_name
                        }
                    }
                
                # Simulate progress updates
                if progress_callback:
                    await progress_callback(progress=50, step=f"Processing {len(capabilities)} capabilities")
                    await progress_callback(progress=100, step="Enrichment completed")
                
                return results
            
            async def fetch_datasheet(self, part, progress_callback=None):
                if progress_callback:
                    await progress_callback(progress=50, step="Fetching datasheet")
                    await progress_callback(progress=100, step="Datasheet retrieved")
                
                return {
                    "success": True,
                    "datasheet_url": f"https://example.com/{supplier_name}/datasheet_{part.name if hasattr(part, 'name') else 'unknown'}.pdf",
                    "file_path": f"/static/datasheets/{supplier_name}_datasheet.pdf"
                }
            
            async def fetch_image(self, part, progress_callback=None):
                if progress_callback:
                    await progress_callback(progress=50, step="Fetching image")
                    await progress_callback(progress=100, step="Image retrieved")
                
                import uuid
                mock_uuid = str(uuid.uuid4())
                return {
                    "success": True,
                    "image_url": f"/utility/get_image/{mock_uuid}",
                    "file_path": f"/uploaded_images/{mock_uuid}.jpg"
                }
            
            async def fetch_pricing(self, part, progress_callback=None):
                if progress_callback:
                    await progress_callback(progress=50, step="Fetching pricing")
                    await progress_callback(progress=100, step="Pricing retrieved")
                
                return {
                    "success": True,
                    "pricing_data": {
                        "unit_price": 0.25,
                        "currency": "USD",
                        "quantity_breaks": [
                            {"qty": 1, "price": 0.25},
                            {"qty": 10, "price": 0.20},
                            {"qty": 100, "price": 0.15}
                        ]
                    }
                }
            
            async def fetch_specifications(self, part, progress_callback=None):
                if progress_callback:
                    await progress_callback(progress=50, step="Fetching specifications")
                    await progress_callback(progress=100, step="Specifications retrieved")
                
                return {
                    "success": True,
                    "specifications": {
                        "manufacturer": f"Mock {supplier_name} Manufacturer",
                        "package": "SOT-23",
                        "category": "Electronic Components"
                    }
                }
        
        # Don't return mock parsers for real operations - return None instead
        return None
    
    return parser_registry.get_parser(supplier_name)