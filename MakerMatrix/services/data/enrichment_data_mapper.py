"""
Enrichment Data Mapper Service.
Handles data mapping and transformation between enrichment results and part models.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from MakerMatrix.models.models import PartModel
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
from MakerMatrix.suppliers.base import PartSearchResult

logger = logging.getLogger(__name__)


class EnrichmentDataMapper:
    """Data mapping and transformation for enrichment operations"""

    def __init__(self, supplier_data_mapper: SupplierDataMapper):
        """
        Initialize EnrichmentDataMapper.

        Args:
            supplier_data_mapper: Supplier data mapper for standardized data mapping
        """
        self.supplier_data_mapper = supplier_data_mapper

    def convert_enrichment_to_part_search_result(
        self, part: PartModel, enrichment_results: Dict[str, Any], supplier_name: str
    ) -> Optional[PartSearchResult]:
        """
        Convert enrichment results to PartSearchResult for standardized data mapping.
        This allows us to use the SupplierDataMapper with enrichment data.

        Args:
            part: The part being enriched
            enrichment_results: Results from enrichment operations
            supplier_name: Name of the supplier used for enrichment

        Returns:
            PartSearchResult or None if conversion fails
        """
        try:
            # Extract data from enrichment results
            extracted_data = self.extract_enrichment_data(enrichment_results)

            # Create PartSearchResult from enrichment data (prefer enriched data over existing part data)
            return PartSearchResult(
                supplier_part_number=part.part_number or part.manufacturer_part_number or part.part_name,
                manufacturer=extracted_data.get("manufacturer") or part.manufacturer,
                manufacturer_part_number=extracted_data.get("manufacturer_part_number")
                or part.manufacturer_part_number,
                description=extracted_data.get("description") or part.description,
                category=extracted_data.get("category"),
                datasheet_url=extracted_data.get("datasheet_url"),
                image_url=extracted_data.get("image_url"),
                pricing=extracted_data.get("pricing"),
                stock_quantity=extracted_data.get("stock_quantity"),
                specifications={},  # No longer using nested specifications - all data goes to additional_data
                additional_data={
                    **extracted_data.get("additional_data", {}),
                    # Flatten any specifications directly into additional_data
                    **self._flatten_specifications(extracted_data.get("specifications", {})),
                    "enrichment_source": supplier_name,
                    "enrichment_timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.warning(f"Failed to convert enrichment results to PartSearchResult: {e}")
            return None

    def extract_enrichment_data(self, enrichment_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from enrichment results.

        Args:
            enrichment_results: Raw enrichment results from supplier

        Returns:
            Dict with extracted and normalized data
        """
        extracted_data = {
            "datasheet_url": None,
            "image_url": None,
            "pricing": None,
            "stock_quantity": None,
            "specifications": {},
            "additional_data": {},
            "manufacturer": None,
            "manufacturer_part_number": None,
            "description": None,
            "category": None,
        }

        try:
            # Check if we have the consolidated part_data format
            if "part_data" in enrichment_results:
                part_data_result = enrichment_results["part_data"]
                if isinstance(part_data_result, dict) and part_data_result.get("success"):
                    # Extract data directly from the unified part data
                    extracted_data.update(
                        {
                            "datasheet_url": part_data_result.get("datasheet_url"),
                            "image_url": part_data_result.get("image_url"),
                            "pricing": part_data_result.get("pricing"),
                            "stock_quantity": part_data_result.get("stock_quantity"),
                            "specifications": part_data_result.get("specifications") or {},
                            "additional_data": part_data_result.get("additional_data") or {},
                            "manufacturer": part_data_result.get("manufacturer"),
                            "manufacturer_part_number": part_data_result.get("manufacturer_part_number"),
                            "description": part_data_result.get("description"),
                            "category": part_data_result.get("category"),
                        }
                    )

                    # Also store core fields in additional_data for backward compatibility
                    extracted_data["additional_data"].update(
                        {
                            "manufacturer": extracted_data["manufacturer"],
                            "manufacturer_part_number": extracted_data["manufacturer_part_number"],
                            "description": extracted_data["description"],
                            "category": extracted_data["category"],
                        }
                    )
            else:
                # Process each enrichment result (legacy format)
                for capability, result_data in enrichment_results.items():
                    if not isinstance(result_data, dict) or not result_data.get("success"):
                        continue

                    self._process_capability_result(capability, result_data, extracted_data)

        except Exception as e:
            logger.error(f"Error extracting enrichment data: {e}")

        return extracted_data

    def _process_capability_result(self, capability: str, result_data: Dict[str, Any], extracted_data: Dict[str, Any]):
        """
        Process individual capability result and update extracted data.

        Args:
            capability: Capability name
            result_data: Result data for this capability
            extracted_data: Extracted data dict to update
        """
        try:
            if capability == "fetch_datasheet" and result_data.get("datasheet_url"):
                extracted_data["datasheet_url"] = result_data["datasheet_url"]

            elif capability == "get_part_details":
                if result_data.get("image_url"):
                    extracted_data["image_url"] = result_data["image_url"]

                if result_data.get("specifications"):
                    extracted_data["specifications"].update(result_data["specifications"])

                # Extract core fields from part details
                for field in ["manufacturer", "manufacturer_part_number", "description", "category"]:
                    if result_data.get(field):
                        extracted_data[field] = result_data[field]

            elif capability == "fetch_pricing_stock":
                if result_data.get("pricing"):
                    extracted_data["pricing"] = result_data["pricing"]

                if result_data.get("stock_quantity") is not None:
                    extracted_data["stock_quantity"] = result_data["stock_quantity"]

            elif capability == "fetch_details":
                # Add any additional details to additional_data
                for key, value in result_data.items():
                    if key not in ["success"]:
                        extracted_data["additional_data"][key] = value

        except Exception as e:
            logger.warning(f"Error processing capability {capability}: {e}")

    def validate_enrichment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate enrichment data for completeness and quality.

        Args:
            data: Enrichment data to validate

        Returns:
            Dict with validation results
        """
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "completeness_score": 0.0,
            "quality_score": 0.0,
        }

        try:
            # Check for required fields
            required_fields = ["manufacturer", "manufacturer_part_number", "description"]
            present_required = sum(1 for field in required_fields if data.get(field))

            # Check for optional but valuable fields
            optional_fields = ["datasheet_url", "image_url", "pricing", "stock_quantity", "specifications", "category"]
            present_optional = sum(1 for field in optional_fields if data.get(field))

            # Calculate completeness score
            total_fields = len(required_fields) + len(optional_fields)
            validation_result["completeness_score"] = (present_required + present_optional) / total_fields

            # Check data quality
            quality_checks = []

            # URL validation
            if data.get("datasheet_url"):
                if self._is_valid_url(data["datasheet_url"]):
                    quality_checks.append(True)
                else:
                    validation_result["warnings"].append("Invalid datasheet URL format")
                    quality_checks.append(False)

            if data.get("image_url"):
                if self._is_valid_url(data["image_url"]):
                    quality_checks.append(True)
                else:
                    validation_result["warnings"].append("Invalid image URL format")
                    quality_checks.append(False)

            # Pricing validation
            if data.get("pricing"):
                if self._is_valid_pricing(data["pricing"]):
                    quality_checks.append(True)
                else:
                    validation_result["warnings"].append("Invalid pricing format")
                    quality_checks.append(False)

            # Stock quantity validation
            if data.get("stock_quantity") is not None:
                if isinstance(data["stock_quantity"], (int, float)) and data["stock_quantity"] >= 0:
                    quality_checks.append(True)
                else:
                    validation_result["warnings"].append("Invalid stock quantity")
                    quality_checks.append(False)

            # Calculate quality score
            if quality_checks:
                validation_result["quality_score"] = sum(quality_checks) / len(quality_checks)
            else:
                validation_result["quality_score"] = 1.0  # No quality checks to fail

            # Check for critical errors
            if present_required < len(required_fields):
                missing_required = [field for field in required_fields if not data.get(field)]
                validation_result["errors"].append(f"Missing required fields: {missing_required}")
                validation_result["valid"] = False

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")

        return validation_result

    def merge_enrichment_results(self, existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge new enrichment data with existing data.

        Args:
            existing_data: Existing enrichment data
            new_data: New enrichment data to merge

        Returns:
            Merged enrichment data
        """
        merged_data = existing_data.copy()

        try:
            # Merge simple fields (new data takes precedence if not None/empty)
            simple_fields = [
                "datasheet_url",
                "image_url",
                "pricing",
                "stock_quantity",
                "manufacturer",
                "manufacturer_part_number",
                "description",
                "category",
            ]

            for field in simple_fields:
                if new_data.get(field):
                    merged_data[field] = new_data[field]

            # Merge specifications (combine both)
            if new_data.get("specifications"):
                merged_data.setdefault("specifications", {})
                merged_data["specifications"].update(new_data["specifications"])

            # Merge additional_data (combine both)
            if new_data.get("additional_data"):
                merged_data.setdefault("additional_data", {})
                merged_data["additional_data"].update(new_data["additional_data"])

            # Add merge metadata
            merged_data["merge_timestamp"] = datetime.utcnow().isoformat()

        except Exception as e:
            logger.error(f"Error merging enrichment data: {e}")

        return merged_data

    def normalize_part_data(self, part_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize part data for consistent formatting.

        Args:
            part_data: Raw part data to normalize

        Returns:
            Normalized part data
        """
        normalized = {}

        try:
            # Normalize text fields
            text_fields = ["manufacturer", "manufacturer_part_number", "description", "category"]
            for field in text_fields:
                if part_data.get(field):
                    normalized[field] = str(part_data[field]).strip()

            # Normalize URLs
            url_fields = ["datasheet_url", "image_url"]
            for field in url_fields:
                if part_data.get(field):
                    normalized[field] = str(part_data[field]).strip()

            # Normalize pricing
            if part_data.get("pricing"):
                normalized["pricing"] = self._normalize_pricing(part_data["pricing"])

            # Normalize stock quantity
            if part_data.get("stock_quantity") is not None:
                try:
                    normalized["stock_quantity"] = int(part_data["stock_quantity"])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid stock quantity: {part_data['stock_quantity']}")

            # Normalize specifications
            if part_data.get("specifications"):
                normalized["specifications"] = self._normalize_specifications(part_data["specifications"])

            # Copy additional_data as-is
            if part_data.get("additional_data"):
                normalized["additional_data"] = part_data["additional_data"]

        except Exception as e:
            logger.error(f"Error normalizing part data: {e}")
            normalized = part_data  # Return original if normalization fails

        return normalized

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid format"""
        try:
            return url.startswith(("http://", "https://")) and len(url) > 10
        except:
            return False

    def _is_valid_pricing(self, pricing: Any) -> bool:
        """Check if pricing data is valid"""
        try:
            if isinstance(pricing, dict):
                return any(isinstance(v, (int, float)) and v >= 0 for v in pricing.values())
            elif isinstance(pricing, (int, float)):
                return pricing >= 0
            else:
                return False
        except:
            return False

    def _normalize_pricing(self, pricing: Any) -> Dict[str, float]:
        """Normalize pricing data to consistent format"""
        normalized = {}

        try:
            if isinstance(pricing, dict):
                for key, value in pricing.items():
                    try:
                        normalized[str(key)] = float(value)
                    except (ValueError, TypeError):
                        pass
            elif isinstance(pricing, (int, float)):
                normalized["unit_price"] = float(pricing)

        except Exception as e:
            logger.warning(f"Error normalizing pricing: {e}")

        return normalized

    def _normalize_specifications(self, specifications: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize specifications data"""
        normalized = {}

        try:
            for key, value in specifications.items():
                # Convert key to string and normalize
                normalized_key = str(key).strip().lower().replace(" ", "_")

                # Convert value to string and normalize
                if value is not None:
                    normalized[normalized_key] = str(value).strip()

        except Exception as e:
            logger.warning(f"Error normalizing specifications: {e}")
            normalized = specifications  # Return original if normalization fails

        return normalized

    def _flatten_specifications(self, specifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested specifications into simple key-value pairs.
        Specifications should not be nested - flatten them directly into additional_data.
        """
        if not isinstance(specifications, dict):
            return {}

        flattened = {}
        try:
            for key, value in specifications.items():
                if isinstance(value, dict):
                    # Flatten nested dictionaries
                    for nested_key, nested_value in value.items():
                        clean_key = str(nested_key).lower().replace(" ", "_").replace("-", "_")
                        flattened[clean_key] = str(nested_value) if nested_value is not None else ""
                else:
                    # Keep simple key-value pairs
                    clean_key = str(key).lower().replace(" ", "_").replace("-", "_")
                    flattened[clean_key] = str(value) if value is not None else ""
        except Exception as e:
            logger.warning(f"Error flattening specifications: {e}")

        return flattened
