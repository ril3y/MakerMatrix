"""
Supplier Integration Service.
Handles supplier API interactions and capability management for enrichment operations.
"""

import logging
from typing import Dict, List, Any, Optional
import asyncio

from MakerMatrix.models.models import PartModel
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.suppliers.base import BaseSupplier, SupplierCapability, EnrichmentResult
from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers
from MakerMatrix.suppliers.exceptions import (
    SupplierError,
    SupplierConfigurationError,
    SupplierAuthenticationError,
    SupplierConnectionError,
    SupplierRateLimitError,
)

logger = logging.getLogger(__name__)


class SupplierIntegrationService:
    """Supplier API interactions and capability management"""

    def __init__(self, supplier_config_service: SupplierConfigService):
        """
        Initialize SupplierIntegrationService.

        Args:
            supplier_config_service: Service for managing supplier configurations
        """
        self.supplier_config_service = supplier_config_service
        self._supplier_cache: Dict[str, BaseSupplier] = {}

    def get_supplier_for_part(self, part: PartModel, preferred_supplier: str = None) -> Optional[str]:
        """
        Determine the best supplier for enriching a part.

        Args:
            part: The part to enrich
            preferred_supplier: Preferred supplier name

        Returns:
            Supplier name or None if no suitable supplier found
        """
        try:
            # If a preferred supplier is specified and available, use it
            if preferred_supplier:
                if self._is_supplier_available(preferred_supplier):
                    logger.debug(f"Using preferred supplier: {preferred_supplier}")
                    return preferred_supplier
                else:
                    logger.warning(f"Preferred supplier {preferred_supplier} not available")

            # Try to determine supplier from part data
            if part.supplier:
                supplier_name = self._normalize_supplier_name(part.supplier)
                if self._is_supplier_available(supplier_name):
                    logger.debug(f"Using part's supplier: {supplier_name}")
                    return supplier_name

            # Try to determine from part number pattern
            if part.part_number:
                detected_supplier = self._detect_supplier_from_part_number(part.part_number)
                if detected_supplier and self._is_supplier_available(detected_supplier):
                    logger.debug(f"Detected supplier from part number: {detected_supplier}")
                    return detected_supplier

            # Fall back to the first available supplier with GET_PART_DETAILS capability
            available_suppliers = get_available_suppliers()
            for supplier_name in available_suppliers:
                if self._is_supplier_available(supplier_name):
                    supplier = self._get_supplier_instance(supplier_name)
                    if supplier and SupplierCapability.GET_PART_DETAILS in supplier.get_capabilities():
                        logger.debug(f"Using fallback supplier: {supplier_name}")
                        return supplier_name

            logger.warning("No suitable supplier found for part enrichment")
            return None

        except Exception as e:
            logger.error(f"Error determining supplier for part {part.id}: {e}")
            return None

    def get_available_capabilities(self, supplier_name: str) -> List[SupplierCapability]:
        """
        Get available capabilities for a supplier.

        Args:
            supplier_name: Name of the supplier

        Returns:
            List of available capabilities
        """
        try:
            supplier = self._get_supplier_instance(supplier_name)
            if not supplier:
                return []

            all_capabilities = supplier.get_capabilities()
            available_capabilities = []

            for capability in all_capabilities:
                if supplier.is_capability_available(capability):
                    available_capabilities.append(capability)
                else:
                    missing_creds = supplier.get_missing_credentials_for_capability(capability)
                    logger.debug(
                        f"Capability {capability.value} not available for {supplier_name}: missing {missing_creds}"
                    )

            return available_capabilities

        except Exception as e:
            logger.error(f"Error getting capabilities for supplier {supplier_name}: {e}")
            return []

    def validate_supplier_capabilities(
        self, supplier_name: str, capabilities: List[SupplierCapability]
    ) -> List[SupplierCapability]:
        """
        Validate and filter capabilities against what's available for a supplier.

        Args:
            supplier_name: Name of the supplier
            capabilities: Requested capabilities

        Returns:
            List of valid, available capabilities
        """
        try:
            available_capabilities = self.get_available_capabilities(supplier_name)
            valid_capabilities = []

            for capability in capabilities:
                if capability in available_capabilities:
                    valid_capabilities.append(capability)
                else:
                    logger.warning(f"Capability {capability.value} not available for {supplier_name}")

            return valid_capabilities

        except Exception as e:
            logger.error(f"Error validating capabilities for supplier {supplier_name}: {e}")
            return []

    async def execute_supplier_enrichment(
        self, supplier_name: str, part: PartModel, capabilities: List[SupplierCapability]
    ) -> Dict[str, Any]:
        """
        Execute enrichment using a specific supplier.

        Args:
            supplier_name: Name of the supplier to use
            part: Part to enrich
            capabilities: Capabilities to use for enrichment

        Returns:
            Dict with enrichment results
        """
        try:
            supplier = self._get_supplier_instance(supplier_name)
            if not supplier:
                return {"success": False, "error": f"Supplier {supplier_name} not available", "supplier": supplier_name}

            # Configure supplier if needed
            await self._configure_supplier(supplier, supplier_name)

            # Validate capabilities
            valid_capabilities = self.validate_supplier_capabilities(supplier_name, capabilities)
            if not valid_capabilities:
                return {
                    "success": False,
                    "error": f"No valid capabilities available for {supplier_name}",
                    "supplier": supplier_name,
                    "requested_capabilities": [cap.value for cap in capabilities],
                }

            # Use the part number for enrichment - try different part number fields
            part_number = self._get_best_part_number(part)
            if not part_number:
                return {
                    "success": False,
                    "error": "No suitable part number found for enrichment",
                    "supplier": supplier_name,
                }

            # Execute enrichment using supplier's built-in enrich_part method
            logger.info(
                f"Enriching part {part.id} with supplier {supplier_name}, capabilities: {[cap.value for cap in valid_capabilities]}"
            )
            enrichment_result = await supplier.enrich_part(part_number, valid_capabilities)

            # Convert EnrichmentResult to our expected format
            return self._convert_enrichment_result(enrichment_result, supplier_name)

        except SupplierRateLimitError as e:
            logger.warning(f"Rate limit exceeded for {supplier_name}: {e}")
            return {
                "success": False,
                "error": f"Rate limit exceeded for {supplier_name}",
                "error_type": "rate_limit",
                "supplier": supplier_name,
            }
        except SupplierAuthenticationError as e:
            logger.error(f"Authentication failed for {supplier_name}: {e}")
            return {
                "success": False,
                "error": f"Authentication failed for {supplier_name}",
                "error_type": "authentication",
                "supplier": supplier_name,
            }
        except SupplierConnectionError as e:
            logger.error(f"Connection error for {supplier_name}: {e}")
            return {
                "success": False,
                "error": f"Connection error for {supplier_name}",
                "error_type": "connection",
                "supplier": supplier_name,
            }
        except Exception as e:
            logger.error(f"Error executing enrichment with {supplier_name}: {e}")
            return {"success": False, "error": str(e), "error_type": "general", "supplier": supplier_name}

    def get_supplier_info(self, supplier_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a supplier.

        Args:
            supplier_name: Name of the supplier

        Returns:
            Dict with supplier information or None
        """
        try:
            supplier = self._get_supplier_instance(supplier_name)
            if not supplier:
                return None

            info = supplier.get_supplier_info()
            capabilities = supplier.get_capabilities()
            available_capabilities = self.get_available_capabilities(supplier_name)

            return {
                "name": info.name,
                "display_name": info.display_name,
                "description": info.description,
                "website_url": info.website_url,
                "api_documentation_url": info.api_documentation_url,
                "supports_oauth": info.supports_oauth,
                "rate_limit_info": info.rate_limit_info,
                "supported_file_types": info.supported_file_types,
                "all_capabilities": [cap.value for cap in capabilities],
                "available_capabilities": [cap.value for cap in available_capabilities],
                "is_configured": supplier.is_configured(),
            }

        except Exception as e:
            logger.error(f"Error getting supplier info for {supplier_name}: {e}")
            return None

    def _get_supplier_instance(self, supplier_name: str) -> Optional[BaseSupplier]:
        """Get supplier instance with caching"""
        try:
            normalized_name = self._normalize_supplier_name(supplier_name)

            if normalized_name not in self._supplier_cache:
                supplier = get_supplier(normalized_name)
                if supplier:
                    self._supplier_cache[normalized_name] = supplier
                else:
                    logger.warning(f"Supplier {normalized_name} not found in registry")
                    return None

            return self._supplier_cache[normalized_name]

        except Exception as e:
            logger.error(f"Error getting supplier instance for {supplier_name}: {e}")
            return None

    async def _configure_supplier(self, supplier: BaseSupplier, supplier_name: str):
        """Configure supplier with credentials and settings"""
        try:
            if supplier.is_configured():
                return  # Already configured

            # Get configuration from supplier config service
            try:
                config_data = self.supplier_config_service.get_supplier_by_name(supplier_name)
                if config_data:
                    # Extract credentials and configuration
                    credentials = config_data.get("credentials", {})
                    config = config_data.get("config", {})

                    # Configure the supplier
                    supplier.configure(credentials, config)

                    # Test authentication if credentials are provided
                    if credentials:
                        await supplier.authenticate()

                    logger.debug(f"Configured supplier {supplier_name}")
                else:
                    logger.debug(f"No configuration found for {supplier_name}, using defaults")
                    # Configure with empty credentials (for suppliers that don't need auth)
                    supplier.configure({}, {})

            except Exception as config_error:
                logger.warning(f"Error loading configuration for {supplier_name}: {config_error}")
                # Try to configure with defaults anyway
                supplier.configure({}, {})

        except Exception as e:
            logger.error(f"Error configuring supplier {supplier_name}: {e}")
            raise SupplierConfigurationError(f"Failed to configure supplier {supplier_name}: {e}")

    def _is_supplier_available(self, supplier_name: str) -> bool:
        """Check if supplier is available and can be instantiated"""
        try:
            normalized_name = self._normalize_supplier_name(supplier_name)
            available_suppliers = get_available_suppliers()
            return normalized_name in available_suppliers
        except Exception:
            return False

    def _normalize_supplier_name(self, supplier_name: str) -> str:
        """Normalize supplier name for consistency"""
        if not supplier_name:
            return ""
        return supplier_name.lower().strip()

    def _detect_supplier_from_part_number(self, part_number: str) -> Optional[str]:
        """Detect supplier from part number pattern"""
        if not part_number:
            return None

        part_number = part_number.upper().strip()

        # LCSC parts typically start with 'C' followed by numbers
        if part_number.startswith("C") and part_number[1:].isdigit():
            return "lcsc"

        # DigiKey parts often have specific patterns
        if "-ND" in part_number or part_number.endswith("-DKR"):
            return "digikey"

        # Mouser parts often have specific patterns
        if part_number.count("-") >= 2 and len(part_number) > 8:
            return "mouser"

        return None

    def _get_best_part_number(self, part: PartModel) -> Optional[str]:
        """Get the best part number for enrichment from part data"""
        # Priority order: part_number, manufacturer_part_number, part_name
        if part.part_number:
            return part.part_number
        if hasattr(part, "manufacturer_part_number") and part.manufacturer_part_number:
            return part.manufacturer_part_number
        if part.part_name:
            return part.part_name
        return None

    def _convert_enrichment_result(self, enrichment_result: EnrichmentResult, supplier_name: str) -> Dict[str, Any]:
        """Convert supplier's EnrichmentResult to our expected format"""
        result = {
            "success": enrichment_result.success,
            "supplier": supplier_name,
            "enriched_fields": enrichment_result.enriched_fields,
            "failed_fields": enrichment_result.failed_fields,
            "errors": enrichment_result.errors,
            "warnings": enrichment_result.warnings,
            "duration_ms": enrichment_result.duration_ms,
        }

        # Convert part data if available
        if enrichment_result.data:
            part_data = enrichment_result.data
            result["part_data"] = {
                "success": True,
                "supplier_part_number": part_data.supplier_part_number,
                "manufacturer": part_data.manufacturer,
                "manufacturer_part_number": part_data.manufacturer_part_number,
                "description": part_data.description,
                "category": part_data.category,
                "datasheet_url": part_data.datasheet_url,
                "image_url": part_data.image_url,
                "pricing": part_data.pricing,
                "stock_quantity": part_data.stock_quantity,
                "specifications": part_data.specifications or {},
                "additional_data": part_data.additional_data or {},
            }

        # Also add individual capability results for backward compatibility
        if enrichment_result.data:
            part_data = enrichment_result.data

            if (
                "part_details" in enrichment_result.enriched_fields
                or "get_part_details" in enrichment_result.enriched_fields
            ):
                result["get_part_details"] = {
                    "success": True,
                    "manufacturer": part_data.manufacturer,
                    "manufacturer_part_number": part_data.manufacturer_part_number,
                    "description": part_data.description,
                    "category": part_data.category,
                    "image_url": part_data.image_url,
                    "specifications": part_data.specifications or {},
                }

            if "datasheet_url" in enrichment_result.enriched_fields:
                result["fetch_datasheet"] = {"success": True, "datasheet_url": part_data.datasheet_url}

            if "pricing" in enrichment_result.enriched_fields or "stock_quantity" in enrichment_result.enriched_fields:
                result["fetch_pricing_stock"] = {
                    "success": True,
                    "pricing": part_data.pricing,
                    "stock_quantity": part_data.stock_quantity,
                }

        return result
