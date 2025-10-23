"""
Supplier Data Mapping Service

Maps supplier data (PartSearchResult) to standardized database format,
ensuring consistent storage regardless of supplier source.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from MakerMatrix.suppliers.base import PartSearchResult, SupplierCapability
from MakerMatrix.suppliers.registry import get_supplier
from MakerMatrix.schemas.part_data_standards import (
    ComponentType,
    MountingType,
    RoHSStatus,
    LifecycleStatus,
    StandardizedAdditionalProperties,
    StandardizedSupplierData,
    StandardizedMetadata,
    StandardizedSpecifications,
    determine_component_type,
    determine_mounting_type,
)
from MakerMatrix.services.system.file_download_service import file_download_service

logger = logging.getLogger(__name__)


class SupplierDataMapper:
    """
    Maps supplier-specific data to standardized database format.

    This service is now completely supplier-agnostic. All supplier-specific
    mapping logic is delegated to the suppliers themselves via their
    map_to_standard_format() method.
    """

    def __init__(self):
        # No more hardcoded supplier mappings!
        # Each supplier handles its own mapping via map_to_standard_format()
        pass

    def map_supplier_result_to_part_data(
        self, supplier_result: PartSearchResult, supplier_name: str, enrichment_capabilities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Map PartSearchResult to standardized part data format.

        This method is now completely supplier-agnostic. It delegates supplier-specific
        mapping to the supplier's own map_to_standard_format() method.

        Args:
            supplier_result: Result from supplier API
            supplier_name: Name of the supplier
            enrichment_capabilities: List of capabilities used for enrichment

        Returns:
            Dictionary with standardized part data for database storage
        """

        # Start with core field mapping (supplier-agnostic)
        core_data = self._map_core_fields(supplier_result, supplier_name)

        # Create standardized additional_properties (supplier-agnostic)
        additional_props = self._map_additional_properties(supplier_result, supplier_name, enrichment_capabilities)

        # Get supplier-specific mapping from the supplier itself
        supplier_specific_data = self._get_supplier_specific_mapping(supplier_result, supplier_name)

        if supplier_specific_data:
            # Merge supplier-specific core fields
            core_data.update(supplier_specific_data.get("core_fields", {}))

            # Merge supplier-specific custom fields into additional_properties
            additional_props.custom_fields.update(supplier_specific_data.get("custom_fields", {}))

        # Build FLAT additional_properties (simple key-value pairs only)
        # Extract only the meaningful custom_fields for clean display
        flat_additional_properties = {}

        # Add the clean custom fields we extracted
        flat_additional_properties.update(additional_props.custom_fields)

        # Add enrichment metadata as flat keys
        flat_additional_properties["last_enrichment_date"] = datetime.utcnow().isoformat()
        flat_additional_properties["enrichment_source"] = supplier_name

        # Combine everything
        result = {
            **core_data,
            "additional_properties": flat_additional_properties,
            "last_enrichment_date": datetime.utcnow(),
            "enrichment_source": supplier_name,
        }

        # Add pricing tiers for PartPricingHistory creation (if available)
        if supplier_result.pricing:
            pricing_data = self._normalize_pricing_data(supplier_result.pricing)
            result["pricing_tiers_for_history"] = {
                "supplier": supplier_name,
                "tiers": pricing_data.get("price_tiers", []),
                "currency": pricing_data.get("currency", "USD"),
                "source": "enrichment",
            }

        # Calculate data quality score
        result["data_quality_score"] = self._calculate_quality_score(result)

        logger.info(f"Mapped {supplier_name} data for part {supplier_result.supplier_part_number}")
        return result

    def _get_supplier_specific_mapping(
        self, supplier_result: PartSearchResult, supplier_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get supplier-specific mapping by calling the supplier's map_to_standard_format() method.

        This is the ONLY place where we interact with supplier instances for mapping,
        and we do it generically without any hardcoded supplier names.

        Args:
            supplier_result: Result from supplier API
            supplier_name: Name of the supplier

        Returns:
            Dictionary with 'core_fields' and 'custom_fields', or None if supplier not found
        """
        try:
            # Get the supplier instance from the registry
            supplier = get_supplier(supplier_name)

            if not supplier:
                logger.warning(f"Supplier '{supplier_name}' not found in registry for mapping")
                return None

            # Call the supplier's map_to_standard_format() method
            mapped_data = supplier.map_to_standard_format(supplier_result)

            if not mapped_data:
                return None

            # The supplier returns a flat dict - we need to separate core fields from custom fields
            core_field_names = {
                "supplier_part_number",
                "part_name",
                "manufacturer",
                "manufacturer_part_number",
                "description",
                "component_type",
                "rohs_status",
                "lifecycle_status",
                "unit_price",
                "currency",
                "stock_quantity",
                "image_url",
                "datasheet_url",
                "category",
                "quantity",
                "price",
            }

            core_fields = {}
            custom_fields = {}

            for key, value in mapped_data.items():
                if key in core_field_names:
                    core_fields[key] = value
                else:
                    custom_fields[key] = value

            return {"core_fields": core_fields, "custom_fields": custom_fields}

        except Exception as e:
            logger.error(f"Error getting supplier-specific mapping for '{supplier_name}': {e}")
            return None

    def _map_core_fields(self, result: PartSearchResult, supplier_name: str) -> Dict[str, Any]:
        """Map PartSearchResult to core database fields"""

        # Use component type from additional_data if available (e.g., from DigiKey API extraction)
        # Otherwise fall back to automatic determination
        component_type = None
        if result.additional_data and "component_type" in result.additional_data:
            component_type = result.additional_data["component_type"]
        else:
            component_type = determine_component_type(
                result.supplier_part_number or "", result.description or "", result.specifications or {}
            )

        # Use RoHS status from additional_data if available (e.g., from DigiKey Classifications)
        rohs_status = None
        if result.additional_data and "rohs_status" in result.additional_data:
            rohs_status = result.additional_data["rohs_status"]
        else:
            rohs_status = self._map_rohs_status(result.additional_data or {})

        # Use lifecycle status from additional_data if available (e.g., from DigiKey product status)
        lifecycle_status = None
        if result.additional_data and "lifecycle_status" in result.additional_data:
            lifecycle_status = result.additional_data["lifecycle_status"]
        else:
            lifecycle_status = self._map_lifecycle_status(result.additional_data or {})

        core_data = {
            "part_name": result.manufacturer_part_number or result.supplier_part_number or f"{supplier_name}_part",
            "part_number": result.supplier_part_number,
            "supplier_part_number": result.supplier_part_number,  # Store supplier's part number for API calls
            "manufacturer": result.manufacturer,
            "manufacturer_part_number": result.manufacturer_part_number,
            "description": result.description,
            "component_type": component_type,
            "rohs_status": rohs_status,
            "lifecycle_status": lifecycle_status,
            "supplier": supplier_name.upper(),
        }

        # Add pricing data if available - only unit_price and currency for PartModel
        # The full pricing tiers will be returned separately for PartPricingHistory creation
        if result.pricing:
            pricing_data = self._normalize_pricing_data(result.pricing)
            core_data.update(
                {
                    "unit_price": pricing_data.get("unit_price"),
                    "currency": pricing_data.get("currency", "USD"),
                }
            )

        # Add stock data if available
        if result.stock_quantity is not None:
            core_data.update({"stock_quantity": result.stock_quantity, "last_stock_update": datetime.utcnow()})

        # Download and store image locally if available
        if result.image_url:
            try:
                # Download the image and store it locally
                image_info = file_download_service.download_image(
                    url=result.image_url,
                    part_number=result.supplier_part_number or result.manufacturer_part_number or "unknown",
                    supplier=supplier_name,
                )

                if image_info:
                    # Use the local image URL instead of the remote one
                    # The frontend will access this via /api/utility/get_image/{uuid}
                    local_image_url = f"/api/utility/get_image/{image_info['image_uuid']}"
                    core_data["image_url"] = local_image_url
                    logger.info(f"Downloaded and stored image locally: {image_info['filename']}")
                else:
                    # If download failed, still store the remote URL as fallback
                    core_data["image_url"] = result.image_url
                    logger.warning(f"Failed to download image, using remote URL: {result.image_url}")
            except Exception as e:
                logger.error(f"Error downloading image: {e}")
                # On error, store the remote URL as fallback
                core_data["image_url"] = result.image_url

        return {k: v for k, v in core_data.items() if v is not None}

    def _map_additional_properties(
        self, result: PartSearchResult, supplier_name: str, enrichment_capabilities: List[str] = None
    ) -> StandardizedAdditionalProperties:
        """Map PartSearchResult to standardized additional_properties structure"""

        props = StandardizedAdditionalProperties()

        # NO LONGER mapping specifications - we want flat key-value pairs instead
        # All specification data should go directly into additional_data as flat keys
        # This prevents nested {"specifications": {...}} structure

        # Map supplier data (keep nested structure for supplier_data)
        supplier_data = StandardizedSupplierData(
            supplier_name=supplier_name,
            supplier_part_number=result.supplier_part_number or "",
            product_url=result.additional_data.get("product_detail_url") if result.additional_data else None,
            datasheet_url=result.datasheet_url,
            supplier_category=result.category,
        )

        # Add supplier-specific fields to supplier_data
        if result.additional_data:
            for key, value in result.additional_data.items():
                if key not in ["product_detail_url"]:
                    setattr(supplier_data, key, value)

        props.add_supplier_data(supplier_name, supplier_data)

        # Extract meaningful fields as flat key-value pairs in custom_fields
        # This creates the readable additional_properties that users see

        # IMPORTANT: Add datasheet_url directly to custom_fields so frontend can find it
        # Check multiple possible sources for datasheet URL
        datasheet_url = result.datasheet_url
        if not datasheet_url and result.additional_data:
            # Check alternative keys that suppliers might use
            datasheet_keys = ["datasheet_url", "lcsc_datasheet_url", "DataSheetUrl", "datasheet_link"]
            for key in datasheet_keys:
                if key in result.additional_data and result.additional_data[key]:
                    datasheet_url = result.additional_data[key]
                    break

        if datasheet_url:
            props.custom_fields["datasheet_url"] = datasheet_url

        if result.additional_data:
            # Extract specific technical specifications that users care about
            interesting_fields = {
                "package": "Package",
                "value": "Value",
                "mounting_type": "Mounting Type",
                "voltage_rating": "Voltage Rating",
                "capacitance": "Capacitance",
                "tolerance": "Tolerance",
                "temperature_coefficient": "Temperature Coefficient",
                "rohs_compliant": "RoHS Compliant",
                "part_type": "Component Type",
                "manufacturer": "Manufacturer",
                "manufacturer_part_number": "Manufacturer Part Number",
                "key_attributes": "Key Attributes",
                "lcsc_price": "LCSC Price",
                "lcsc_inventory_level": "Stock Level",
                "product_url": "Product URL",
            }

            for data_key, display_name in interesting_fields.items():
                if data_key in result.additional_data and result.additional_data[data_key]:
                    value = result.additional_data[data_key]
                    # Format the value nicely for display
                    if isinstance(value, bool):
                        props.custom_fields[display_name.lower().replace(" ", "_")] = "Yes" if value else "No"
                    elif isinstance(value, (int, float)) and data_key == "lcsc_price":
                        props.custom_fields["price"] = f"${value:.4f}"
                    elif isinstance(value, (int, float)) and data_key == "lcsc_inventory_level":
                        props.custom_fields["stock_level"] = f"{value:,} units"
                    else:
                        props.custom_fields[display_name.lower().replace(" ", "_")] = str(value)

        # Map metadata
        props.metadata = StandardizedMetadata(
            last_enrichment=datetime.utcnow(),
            enrichment_supplier=supplier_name,
            enrichment_capabilities=enrichment_capabilities or [],
            has_datasheet=bool(result.datasheet_url),
            has_image=bool(result.image_url),
            needs_enrichment=False,  # Just enriched
        )

        return props

    def _map_specifications(self, specifications: Dict[str, Any]) -> StandardizedSpecifications:
        """Map supplier specifications to standardized format"""

        specs = StandardizedSpecifications()

        # Common specification field mappings
        field_mappings = {
            "value": ["value", "resistance", "capacitance", "inductance", "part_value"],
            "tolerance": ["tolerance", "tol"],
            "voltage_rating": ["voltage", "voltage_rating", "max_voltage", "rated_voltage"],
            "current_rating": ["current", "current_rating", "max_current"],
            "power_rating": ["power", "power_rating", "max_power", "wattage"],
            "temperature_rating": ["temperature", "temp_range", "operating_temperature"],
            "package": ["package", "footprint", "case", "mounting"],
            "material": ["material", "composition"],
            "frequency_rating": ["frequency", "freq", "clock_speed"],
        }

        # Map known fields
        for spec_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                for orig_key, value in specifications.items():
                    if key.lower() in orig_key.lower():
                        setattr(specs, spec_field, str(value))
                        break
                if getattr(specs, spec_field):
                    break

        # Determine mounting type if package is available
        if specs.package:
            mounting_type = determine_mounting_type(specs.package, specifications)
            specs.mounting_type = mounting_type

        # Store unmapped specifications as additional_specs
        mapped_values = {getattr(specs, field) for field in field_mappings.keys()}
        mapped_values.discard(None)

        additional_specs = {}
        for key, value in specifications.items():
            if str(value) not in mapped_values:
                additional_specs[key] = str(value)

        if additional_specs:
            specs.additional_specs = additional_specs

        return specs

    def _map_rohs_status(self, additional_data: Dict[str, Any]) -> Optional[RoHSStatus]:
        """Map RoHS status from additional data"""

        rohs_fields = ["rohs", "rohs_status", "rohs_compliant", "rohs_compliance"]

        for field in rohs_fields:
            if field in additional_data:
                value = str(additional_data[field]).lower()
                if value in ["yes", "compliant", "true", "1", "rohs compliant"]:
                    return RoHSStatus.COMPLIANT
                elif value in ["no", "non-compliant", "false", "0", "non compliant"]:
                    return RoHSStatus.NON_COMPLIANT
                elif value in ["exempt", "exempted"]:
                    return RoHSStatus.EXEMPT

        return None

    def _map_lifecycle_status(self, additional_data: Dict[str, Any]) -> Optional[LifecycleStatus]:
        """Map lifecycle status from additional data"""

        lifecycle_fields = ["lifecycle", "lifecycle_status", "status", "availability"]

        for field in lifecycle_fields:
            if field in additional_data:
                value = str(additional_data[field]).lower()
                if value in ["active", "production", "available"]:
                    return LifecycleStatus.ACTIVE
                elif value in ["obsolete", "discontinued", "end of life"]:
                    return LifecycleStatus.OBSOLETE
                elif value in ["nrnd", "not recommended", "not recommended for new designs"]:
                    return LifecycleStatus.NRND
                elif value in ["preview", "engineering sample", "pre-production"]:
                    return LifecycleStatus.PREVIEW

        return None

    def _normalize_pricing_data(self, pricing) -> Dict[str, Any]:
        """Normalize pricing data to standard format - handles multiple input formats"""

        if not pricing:
            return {}

        # Handle different pricing formats
        price_tiers = []
        unit_price = None
        currency = "USD"
        source = None

        if isinstance(pricing, dict):
            # Format 1: LCSC-style dict with quantity_breaks
            if "quantity_breaks" in pricing:
                price_tiers = pricing.get("quantity_breaks", [])
                unit_price = pricing.get("unit_price")
                currency = pricing.get("currency", "USD")
                source = pricing.get("source")

                # Ensure each tier has currency if not present
                for tier in price_tiers:
                    if "currency" not in tier:
                        tier["currency"] = currency

            # Format 2: Single price tier dict
            elif "price" in pricing:
                price_tiers = [pricing]
                unit_price = pricing.get("price")
                currency = pricing.get("currency", "USD")

        elif isinstance(pricing, list):
            # Format 3: List of price tier dicts (traditional format)
            price_tiers = pricing

        else:
            # Invalid format
            return {}

        # Sort by quantity
        if price_tiers:
            sorted_pricing = sorted(price_tiers, key=lambda x: x.get("quantity", 0))

            # Get unit price from lowest quantity tier if not already set
            if unit_price is None and sorted_pricing:
                first_tier = sorted_pricing[0]
                unit_price = first_tier.get("price")
                currency = first_tier.get("currency", currency)
        else:
            sorted_pricing = []

        result = {
            "unit_price": unit_price,
            "currency": currency,
            "price_tiers": sorted_pricing,
            "tier_count": len(sorted_pricing),
        }

        # Add source if available
        if source:
            result["source"] = source

        return result

    def _calculate_quality_score(self, part_data: Dict[str, Any]) -> float:
        """Calculate data quality score (0.0-1.0) based on field completeness"""

        # Define important fields and their weights
        weighted_fields = {
            "manufacturer": 0.2,
            "manufacturer_part_number": 0.15,
            "description": 0.1,
            "component_type": 0.15,
            "package": 0.1,
            "image_url": 0.1,
            "unit_price": 0.1,
            "stock_quantity": 0.05,
            "rohs_status": 0.05,
        }

        score = 0.0
        for field, weight in weighted_fields.items():
            if part_data.get(field) is not None:
                score += weight

        # Bonus for specifications
        additional_props = part_data.get("additional_properties", {})
        specs = additional_props.get("specifications", {})
        if specs and len(specs) > 2:  # Has some specifications
            score += 0.1

        return min(score, 1.0)


# Utility functions for enrichment integration


def map_enrichment_result_to_part_updates(
    part_id: str, enrichment_results: Dict[str, Any], supplier_name: str
) -> Dict[str, Any]:
    """
    Map enrichment results to part update data

    Args:
        part_id: ID of part being enriched
        enrichment_results: Results from enrichment capabilities
        supplier_name: Name of supplier that provided enrichment

    Returns:
        Dictionary of fields to update in part record
    """

    mapper = SupplierDataMapper()
    updates = {}

    # Process each enrichment result
    for capability, result in enrichment_results.items():
        if capability == "fetch_datasheet" and result:
            # Handle datasheet - might create separate DatasheetModel record
            updates["has_datasheet"] = True

        elif capability == "fetch_image" and result:
            updates["image_url"] = result

        elif capability == "fetch_pricing" and result:
            pricing_data = mapper._normalize_pricing_data(result)
            updates.update(
                {
                    "unit_price": pricing_data.get("unit_price"),
                    "currency": pricing_data.get("currency", "USD"),
                }
            )
            # Return pricing tiers for PartPricingHistory creation
            updates["pricing_tiers_for_history"] = {
                "supplier": supplier_name,
                "tiers": pricing_data.get("price_tiers", []),
                "currency": pricing_data.get("currency", "USD"),
                "source": "enrichment",
            }

        elif capability == "fetch_stock" and result is not None:
            updates.update({"stock_quantity": result, "last_stock_update": datetime.utcnow()})

        elif capability == "fetch_specifications" and result:
            # Update specifications in additional_properties
            # This would need to merge with existing specs
            pass

    # Update enrichment tracking
    updates.update({"last_enrichment_date": datetime.utcnow(), "enrichment_source": supplier_name})

    return updates
