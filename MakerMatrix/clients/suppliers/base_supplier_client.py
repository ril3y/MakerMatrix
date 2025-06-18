"""
Base Supplier Client Abstract Class

Defines the interface that all supplier clients must implement for enrichment operations.
This ensures consistency across all supplier integrations and makes the system extensible.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from MakerMatrix.schemas.enrichment_schemas import (
    DatasheetEnrichmentResponse,
    ImageEnrichmentResponse,
    PricingEnrichmentResponse,
    StockEnrichmentResponse,
    DetailsEnrichmentResponse,
    SpecificationsEnrichmentResponse,
    EnrichmentSource
)

logger = logging.getLogger(__name__)


class BaseSupplierClient(ABC):
    """
    Abstract base class for all supplier API clients.
    
    All supplier clients (LCSC, DigiKey, Mouser, etc.) must inherit from this class
    and implement the required enrichment methods.
    """
    
    def __init__(self, supplier_name: str, **kwargs):
        """
        Initialize the supplier client
        
        Args:
            supplier_name: Name of the supplier (e.g., "LCSC", "DigiKey")
            **kwargs: Additional configuration parameters
        """
        self.supplier_name = supplier_name
        self.logger = logging.getLogger(f"{__name__}.{supplier_name}")
    
    # Required Abstract Methods - All suppliers must implement these
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to the supplier API
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_supplier_part_number(self, part_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the supplier-specific part number from part data
        
        Each supplier has their own way of storing part numbers in additional_properties.
        This method should return the part number that this supplier's API expects.
        
        Args:
            part_data: Dictionary containing part information including additional_properties
            
        Returns:
            Supplier-specific part number, or None if not found
            
        Examples:
            LCSC: Look for 'lcsc_part_number' in additional_properties
            DigiKey: Look for 'digikey_part_number' in additional_properties  
            Mouser: Look for 'mouser_part_number' in additional_properties
        """
        pass
    
    @abstractmethod
    async def enrich_part_datasheet(self, part_number: str) -> DatasheetEnrichmentResponse:
        """
        Enrich part with datasheet information
        
        Args:
            part_number: Supplier-specific part number
            
        Returns:
            DatasheetEnrichmentResponse with validated structure
        """
        pass
    
    @abstractmethod
    async def enrich_part_image(self, part_number: str) -> ImageEnrichmentResponse:
        """
        Enrich part with image information
        
        Args:
            part_number: Supplier-specific part number
            
        Returns:
            ImageEnrichmentResponse with validated structure
        """
        pass
    
    @abstractmethod
    async def enrich_part_details(self, part_number: str) -> DetailsEnrichmentResponse:
        """
        Enrich part with detailed component information
        
        Args:
            part_number: Supplier-specific part number
            
        Returns:
            DetailsEnrichmentResponse with validated structure
        """
        pass
    
    @abstractmethod
    async def enrich_part_pricing(self, part_number: str) -> PricingEnrichmentResponse:
        """
        Enrich part with pricing information
        
        Args:
            part_number: Supplier-specific part number
            
        Returns:
            PricingEnrichmentResponse with validated structure
        """
        pass
    
    # Optional Methods - Suppliers can override these for additional functionality
    
    async def enrich_part_stock(self, part_number: str) -> StockEnrichmentResponse:
        """
        Enrich part with stock/availability information
        
        Default implementation calls enrich_part_pricing() since stock is often included.
        Suppliers can override this for more specific stock information.
        
        Args:
            part_number: Supplier-specific part number
            
        Returns:
            StockEnrichmentResponse with validated structure
        """
        try:
            pricing_result = await self.enrich_part_pricing(part_number)
            if pricing_result.success:
                return StockEnrichmentResponse(
                    success=True,
                    status="success",
                    part_number=part_number,
                    source=pricing_result.source,
                    quantity_available=getattr(pricing_result, 'stock_quantity', None),
                    availability_status="in_stock" if getattr(pricing_result, 'stock_quantity', 0) > 0 else "out_of_stock"
                )
            else:
                return StockEnrichmentResponse(
                    success=False,
                    status="failed",
                    part_number=part_number,
                    source=EnrichmentSource(supplier=self.supplier_name),
                    error_message="Could not retrieve stock information"
                )
        except Exception as e:
            return StockEnrichmentResponse(
                success=False,
                status="failed",
                part_number=part_number,
                source=EnrichmentSource(supplier=self.supplier_name),
                error_message=str(e)
            )
    
    async def enrich_part_specifications(self, part_number: str) -> SpecificationsEnrichmentResponse:
        """
        Enrich part with technical specifications
        
        Default implementation calls enrich_part_details() since specs are often included.
        Suppliers can override this for more specific specification handling.
        
        Args:
            part_number: Supplier-specific part number
            
        Returns:
            SpecificationsEnrichmentResponse with validated structure
        """
        try:
            details_result = await self.enrich_part_details(part_number)
            if details_result.success:
                return SpecificationsEnrichmentResponse(
                    success=True,
                    status="success",
                    part_number=part_number,
                    source=details_result.source,
                    specifications=details_result.specifications
                )
            else:
                return SpecificationsEnrichmentResponse(
                    success=False,
                    status="failed",
                    part_number=part_number,
                    source=EnrichmentSource(supplier=self.supplier_name),
                    error_message="Could not retrieve specifications"
                )
        except Exception as e:
            return SpecificationsEnrichmentResponse(
                success=False,
                status="failed",
                part_number=part_number,
                source=EnrichmentSource(supplier=self.supplier_name),
                error_message=str(e)
            )
    
    # Utility Methods
    
    def get_supported_capabilities(self) -> List[str]:
        """
        Get list of enrichment capabilities supported by this supplier
        
        Returns:
            List of capability names
        """
        return [
            "fetch_datasheet",
            "fetch_image", 
            "fetch_pricing",
            "fetch_stock",
            "fetch_specifications",
            "fetch_details"
        ]
    
    def get_capability_method_mapping(self) -> Dict[str, str]:
        """
        Get mapping of capability names to method names
        
        Returns:
            Dictionary mapping capability to method name
        """
        return {
            "fetch_datasheet": "enrich_part_datasheet",
            "fetch_image": "enrich_part_image",
            "fetch_pricing": "enrich_part_pricing", 
            "fetch_stock": "enrich_part_stock",
            "fetch_specifications": "enrich_part_specifications",
            "fetch_details": "enrich_part_details"
        }
    
    async def execute_enrichment_capability(self, capability: str, part_number: str) -> Dict[str, Any]:
        """
        Execute a specific enrichment capability
        
        Args:
            capability: Name of the capability (e.g., "fetch_datasheet")
            part_number: Part number to enrich
            
        Returns:
            Enrichment result dictionary
        """
        method_mapping = self.get_capability_method_mapping()
        method_name = method_mapping.get(capability)
        
        if not method_name:
            return {
                "success": False,
                "error": f"Capability '{capability}' not supported by {self.supplier_name}",
                "source": self.supplier_name
            }
        
        try:
            method = getattr(self, method_name)
            return await method(part_number)
        except AttributeError:
            return {
                "success": False,
                "error": f"Method '{method_name}' not implemented for {self.supplier_name}",
                "source": self.supplier_name
            }
        except Exception as e:
            self.logger.error(f"Error executing {capability} for {part_number}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": self.supplier_name
            }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create standardized error response
        
        Args:
            error_message: Error description
            
        Returns:
            Standardized error dictionary
        """
        return {
            "success": False,
            "error": error_message,
            "source": self.supplier_name,
            "enriched_at": datetime.now().isoformat()
        }
    
    def _create_success_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create standardized success response
        
        Args:
            data: Success data
            
        Returns:
            Standardized success dictionary
        """
        response = {
            "success": True,
            "source": self.supplier_name,
            "enriched_at": datetime.now().isoformat()
        }
        response.update(data)
        return response