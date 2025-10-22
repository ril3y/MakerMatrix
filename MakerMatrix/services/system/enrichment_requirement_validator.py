"""
Enrichment Requirement Validator Service

Service for validating that parts have the necessary data before attempting
enrichment from suppliers. Provides detailed feedback about what's missing
and what can be improved.
"""

import re
import logging
from typing import Optional
from sqlalchemy import Engine

from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.enrichment_requirement_models import (
    EnrichmentRequirements, FieldRequirement, RequirementSeverity,
    FieldCheck, EnrichmentRequirementCheck
)
from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers


logger = logging.getLogger(__name__)


class EnrichmentRequirementValidator:
    """
    Service for validating part data against supplier enrichment requirements.

    This service checks if a part has the necessary fields to be enriched by a
    specific supplier and provides helpful feedback about what's missing.
    """

    def __init__(self, engine: Optional[Engine] = None):
        """
        Initialize the validator.

        Args:
            engine: Database engine (optional, not currently used but follows pattern)
        """
        self.engine = engine
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_supplier_requirements(self, supplier_name: str) -> Optional[EnrichmentRequirements]:
        """
        Get enrichment requirements for a specific supplier.

        Args:
            supplier_name: Name of the supplier (e.g., 'lcsc', 'digikey')

        Returns:
            EnrichmentRequirements if supplier supports it, None otherwise
        """
        try:
            supplier = get_supplier(supplier_name)
            if not supplier:
                self.logger.warning(f"Supplier '{supplier_name}' not found")
                return None

            # Check if supplier implements get_enrichment_requirements
            if not hasattr(supplier, 'get_enrichment_requirements'):
                self.logger.warning(f"Supplier '{supplier_name}' does not implement enrichment requirements")
                return None

            return supplier.get_enrichment_requirements()

        except Exception as e:
            self.logger.error(f"Error getting requirements for supplier '{supplier_name}': {e}")
            return None

    def validate_part_for_enrichment(
        self,
        part,
        supplier_name: str
    ) -> EnrichmentRequirementCheck:
        """
        Validate that a part has the necessary data for enrichment.

        Args:
            part: The part to validate (can be PartModel object or dict)
            supplier_name: Name of the supplier to validate against

        Returns:
            EnrichmentRequirementCheck with validation results
        """
        # Get part ID (handle both dict and object)
        part_id = part.get('id') if isinstance(part, dict) else part.id

        # Get supplier requirements
        requirements = self.get_supplier_requirements(supplier_name)

        if not requirements:
            # Check if supplier supports scraping (like McMaster-Carr)
            try:
                supplier = get_supplier(supplier_name)
                if supplier and hasattr(supplier, 'supports_scraping') and supplier.supports_scraping():
                    # For scraping suppliers, check if we have a URL or part number
                    has_url = False
                    has_part_number = False

                    if isinstance(part, dict):
                        has_url = bool(part.get('product_url') or part.get('supplier_url'))
                        has_part_number = bool(part.get('supplier_part_number'))
                    else:
                        has_url = bool(getattr(part, 'product_url', None) or getattr(part, 'supplier_url', None))
                        has_part_number = bool(getattr(part, 'supplier_part_number', None))

                    can_enrich_via_scraping = has_url or has_part_number

                    warnings = []
                    suggestions = []

                    if not can_enrich_via_scraping:
                        warnings.append(f"Supplier '{supplier_name}' requires a product URL or part number for enrichment")
                        suggestions.append(f"Add a product URL from {supplier_name} website")
                        suggestions.append(f"Or add the {supplier_name} part number")

                    return EnrichmentRequirementCheck(
                        supplier_name=supplier_name,
                        part_id=part_id,
                        can_enrich=can_enrich_via_scraping,
                        warnings=warnings,
                        suggestions=suggestions
                    )
            except Exception as e:
                self.logger.error(f"Error checking scraping support for '{supplier_name}': {e}")

            # If supplier doesn't have requirements and doesn't support scraping, assume it can't enrich
            return EnrichmentRequirementCheck(
                supplier_name=supplier_name,
                part_id=part_id,
                can_enrich=False,
                warnings=[f"Supplier '{supplier_name}' does not support enrichment or requirements not defined"]
            )

        # Validate required fields
        required_checks = []
        missing_required = []

        for field_req in requirements.required_fields:
            check = self._check_field(part, field_req)
            required_checks.append(check)

            if not check.is_satisfied():
                missing_required.append(field_req.field_name)

        # Validate recommended fields
        recommended_checks = []
        missing_recommended = []

        for field_req in requirements.recommended_fields:
            check = self._check_field(part, field_req)
            recommended_checks.append(check)

            if not check.is_present:
                missing_recommended.append(field_req.field_name)

        # Validate optional fields (just for completeness)
        optional_checks = []

        for field_req in requirements.optional_fields:
            check = self._check_field(part, field_req)
            optional_checks.append(check)

        # Determine if enrichment can proceed
        can_enrich = len(missing_required) == 0

        # Build warnings and suggestions
        warnings = []
        suggestions = []

        if not can_enrich:
            warnings.append(f"Missing required fields: {', '.join(missing_required)}")

            # Add specific suggestions for each missing field
            for field_req in requirements.required_fields:
                if field_req.field_name in missing_required:
                    suggestion = f"Add {field_req.display_name}"
                    if field_req.example:
                        suggestion += f" (e.g., {field_req.example})"
                    suggestion += f": {field_req.description}"
                    suggestions.append(suggestion)

        if missing_recommended:
            warnings.append(f"Missing recommended fields: {', '.join(missing_recommended)}. Enrichment may work but results will be limited.")

            for field_req in requirements.recommended_fields:
                if field_req.field_name in missing_recommended:
                    suggestion = f"Consider adding {field_req.display_name}"
                    if field_req.example:
                        suggestion += f" (e.g., {field_req.example})"
                    suggestion += f": {field_req.description}"
                    suggestions.append(suggestion)

        return EnrichmentRequirementCheck(
            supplier_name=supplier_name,
            part_id=part_id,
            can_enrich=can_enrich,
            required_checks=required_checks,
            recommended_checks=recommended_checks,
            optional_checks=optional_checks,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            warnings=warnings,
            suggestions=suggestions
        )

    def _check_field(self, part, field_req: FieldRequirement) -> FieldCheck:
        """
        Check a single field requirement against a part.

        Args:
            part: The part to check (can be PartModel object or dict)
            field_req: The field requirement to validate

        Returns:
            FieldCheck with validation results
        """
        # Get the field value from the part (handle both dict and object)
        if isinstance(part, dict):
            field_value = part.get(field_req.field_name)
        else:
            field_value = getattr(part, field_req.field_name, None)

        # Check if field is present (not None and not empty string)
        is_present = field_value is not None and (
            not isinstance(field_value, str) or field_value.strip() != ""
        )

        # Validate the field if present and validation pattern is defined
        validation_passed = True
        validation_message = None

        if is_present and field_req.validation_pattern:
            try:
                # Convert field value to string for regex validation
                str_value = str(field_value)

                if not re.match(field_req.validation_pattern, str_value):
                    validation_passed = False
                    validation_message = f"{field_req.display_name} does not match expected pattern"

                    if field_req.example:
                        validation_message += f". Example: {field_req.example}"
            except Exception as e:
                self.logger.error(f"Error validating field '{field_req.field_name}': {e}")
                validation_passed = False
                validation_message = f"Validation error: {str(e)}"

        # Generate validation message for missing fields
        if not is_present:
            validation_message = f"{field_req.display_name} is required" if field_req.severity == RequirementSeverity.REQUIRED else f"{field_req.display_name} is recommended"

        return FieldCheck(
            field_name=field_req.field_name,
            display_name=field_req.display_name,
            severity=field_req.severity,
            is_present=is_present,
            current_value=field_value if is_present else None,
            validation_passed=validation_passed,
            validation_message=validation_message
        )

    def can_part_be_enriched(self, part, supplier_name: str) -> bool:
        """
        Quick check if a part can be enriched by a supplier.

        Args:
            part: The part to check (can be PartModel object or dict)
            supplier_name: Name of the supplier

        Returns:
            True if part has required fields, False otherwise
        """
        check = self.validate_part_for_enrichment(part, supplier_name)
        return check.can_enrich

    def get_all_supplier_requirements(self) -> dict:
        """
        Get enrichment requirements for all configured suppliers.

        Returns:
            Dictionary mapping supplier names to their EnrichmentRequirements
        """
        requirements = {}

        for supplier_name in get_available_suppliers():
            supplier_reqs = self.get_supplier_requirements(supplier_name)
            if supplier_reqs:
                requirements[supplier_name] = supplier_reqs

        return requirements
