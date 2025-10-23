"""
Unified Enrichment Engine

This service provides a single, unified code path for all part enrichment operations,
eliminating duplication between instant enrichment (URL pasting) and background
enrichment (Enrich button). It is completely supplier-agnostic and makes enrichment
decisions based on supplier capabilities rather than hardcoded supplier names.

Architecture:
- Instant Enrichment: URL pasting in AddPartModal -> immediate enrichment with progress feedback
- Background Enrichment: Enrich button in PartDetailsPage -> task-based enrichment with WebSocket updates

Both paths use this SAME engine with the SAME logic for maximum code reuse.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from MakerMatrix.suppliers.base import PartSearchResult, EnrichmentResult, SupplierCapability
from MakerMatrix.suppliers.registry import get_supplier
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper


logger = logging.getLogger(__name__)


class EnrichmentEngine:
    """
    Unified enrichment engine for all part enrichment operations.

    This engine provides a single code path for both instant and background enrichment,
    ensuring maximum code reuse and consistency.
    """

    def __init__(self):
        self.mapper = SupplierDataMapper()

    async def enrich_part(
        self,
        supplier_name: str,
        part_identifier: str,
        force_refresh: bool = False,
        enrichment_capabilities: Optional[List[SupplierCapability]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich a part using supplier data.

        This method handles all enrichment logic in a supplier-agnostic way:
        1. Gets supplier instance from registry
        2. Checks if supplier has credentials
        3. Checks if supplier supports scraping
        4. Decides between API enrichment vs scraping based on capabilities
        5. Maps result to standardized format
        6. Returns enrichment data ready for database storage

        Args:
            supplier_name: Name of the supplier
            part_identifier: Part number, URL, or other identifier
            force_refresh: Whether to force refresh cached data
            enrichment_capabilities: Optional list of specific capabilities to use

        Returns:
            Dictionary with enrichment results and standardized part data

        Raises:
            ValueError: If supplier not found or invalid parameters
            Exception: If enrichment fails
        """
        try:
            # Get supplier instance from registry
            supplier = get_supplier(supplier_name)
            if not supplier:
                raise ValueError(f"Supplier '{supplier_name}' not found in registry")

            supplier_info = supplier.get_supplier_info()
            logger.info(f"Starting enrichment for {supplier_info.display_name} part: {part_identifier}")

            # Configure supplier with credentials from database
            try:
                from MakerMatrix.services.system.supplier_config_service import SupplierConfigService

                config_service = SupplierConfigService()

                # Get supplier config and credentials
                supplier_config = config_service.get_supplier_config(supplier_name)
                credentials = config_service.get_supplier_credentials(supplier_name)

                # Build config dict
                config_dict = {
                    "base_url": supplier_config.get("base_url", ""),
                    "request_timeout": supplier_config.get("timeout_seconds", 30),
                    "max_retries": supplier_config.get("max_retries", 3),
                    "rate_limit_per_minute": supplier_config.get("rate_limit_per_minute", 60),
                }

                # Add custom parameters if available
                custom_params = supplier_config.get("custom_parameters", {})
                if custom_params:
                    config_dict.update(custom_params)

                # Configure the supplier
                supplier.configure(credentials or {}, config_dict)
                logger.info(f"Configured {supplier_name} supplier with credentials from database")

            except Exception as e:
                logger.warning(f"Could not load credentials for {supplier_name}: {e}")
                # Continue anyway - some suppliers may work without credentials via scraping

            # Check supplier capabilities and credentials
            supports_scraping = supplier.supports_scraping()
            has_credentials = supplier.is_configured()

            logger.debug(f"Supplier capabilities: scraping={supports_scraping}, credentials={has_credentials}")

            # SUPPLIER-AGNOSTIC DECISION LOGIC
            # This is the core logic that determines API vs scraping
            # No hardcoded supplier names - purely based on capabilities

            enriched_data = None

            if supports_scraping and not has_credentials:
                # Use scraping when supplier supports it and has no credentials
                logger.info(f"Using web scraping for {supplier_info.display_name} (no API credentials)")
                enriched_data = await self._enrich_via_scraping(
                    supplier=supplier, part_identifier=part_identifier, force_refresh=force_refresh
                )

            elif has_credentials:
                # Use API when credentials are available
                logger.info(f"Using API enrichment for {supplier_info.display_name}")
                enriched_data = await self._enrich_via_api(
                    supplier=supplier,
                    part_identifier=part_identifier,
                    enrichment_capabilities=enrichment_capabilities,
                    force_refresh=force_refresh,
                )

            elif supports_scraping:
                # Fallback to scraping if available (even with credentials if API fails)
                logger.info(f"Falling back to web scraping for {supplier_info.display_name}")
                enriched_data = await self._enrich_via_scraping(
                    supplier=supplier, part_identifier=part_identifier, force_refresh=force_refresh
                )

            else:
                # No enrichment method available
                raise ValueError(
                    f"Supplier '{supplier_info.display_name}' has no credentials and does not support scraping. "
                    f"Please configure API credentials or use a supplier that supports web scraping."
                )

            if not enriched_data:
                raise Exception(f"Enrichment returned no data for part {part_identifier}")

            # Map the enriched data to standardized format
            standardized_data = self._map_to_standard_format(
                enriched_data=enriched_data,
                supplier_name=supplier_name,
                enrichment_capabilities=enrichment_capabilities,
            )

            logger.info(f"Successfully enriched part {part_identifier} from {supplier_info.display_name}")

            return {
                "success": True,
                "supplier": supplier_name,
                "part_identifier": part_identifier,
                "enrichment_method": enriched_data.get("enrichment_method", "unknown"),
                "data": standardized_data,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Enrichment failed for {supplier_name} part {part_identifier}: {e}")
            return {
                "success": False,
                "supplier": supplier_name,
                "part_identifier": part_identifier,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _enrich_via_scraping(
        self, supplier, part_identifier: str, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich part data via web scraping.

        Args:
            supplier: Supplier instance
            part_identifier: Part number or URL
            force_refresh: Whether to force refresh cached data

        Returns:
            Dictionary with scraped data and enrichment metadata
        """
        try:
            # Call supplier's scrape_part_details method
            result = await supplier.scrape_part_details(url_or_part_number=part_identifier, force_refresh=force_refresh)

            if not result:
                logger.warning(f"Scraping returned no data for {part_identifier}")
                return None

            return {"enrichment_method": "scraping", "result": result, "success": True}

        except Exception as e:
            logger.error(f"Scraping failed for {part_identifier}: {e}")
            raise

    async def _enrich_via_api(
        self,
        supplier,
        part_identifier: str,
        enrichment_capabilities: Optional[List[SupplierCapability]] = None,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich part data via supplier API.

        Args:
            supplier: Supplier instance
            part_identifier: Part number
            enrichment_capabilities: Optional list of specific capabilities to use
            force_refresh: Whether to force refresh cached data

        Returns:
            Dictionary with API data and enrichment metadata
        """
        try:
            # Call supplier's enrich_part method
            result = await supplier.enrich_part(
                supplier_part_number=part_identifier, capabilities=enrichment_capabilities
            )

            if not result or not result.success:
                error_msg = result.errors if result else "Unknown error"
                logger.warning(f"API enrichment failed for {part_identifier}: {error_msg}")
                return None

            return {"enrichment_method": "api", "result": result, "success": True}

        except Exception as e:
            logger.error(f"API enrichment failed for {part_identifier}: {e}")
            raise

    def _map_to_standard_format(
        self,
        enriched_data: Dict[str, Any],
        supplier_name: str,
        enrichment_capabilities: Optional[List[SupplierCapability]] = None,
    ) -> Dict[str, Any]:
        """
        Map enriched data to standardized database format.

        Args:
            enriched_data: Raw enrichment data (from scraping or API)
            supplier_name: Name of the supplier
            enrichment_capabilities: Capabilities used for enrichment

        Returns:
            Dictionary with standardized part data ready for database storage
        """
        # Extract the result based on enrichment method
        result = enriched_data.get("result")

        if not result:
            logger.warning("No result data to map")
            return {}

        # Handle different result types
        if isinstance(result, PartSearchResult):
            # Scraping returns PartSearchResult directly
            part_search_result = result

        elif isinstance(result, EnrichmentResult):
            # API returns EnrichmentResult which contains PartSearchResult
            if result.data:
                part_search_result = result.data
            else:
                logger.warning("EnrichmentResult contains no data")
                return {}

        else:
            logger.error(f"Unknown result type: {type(result)}")
            return {}

        # Use SupplierDataMapper to map to standardized format
        # This delegates to the supplier's map_to_standard_format() method
        standardized_data = self.mapper.map_supplier_result_to_part_data(
            supplier_result=part_search_result,
            supplier_name=supplier_name,
            enrichment_capabilities=[cap.value for cap in enrichment_capabilities] if enrichment_capabilities else None,
        )

        return standardized_data


# Singleton instance for use throughout the application
enrichment_engine = EnrichmentEngine()
