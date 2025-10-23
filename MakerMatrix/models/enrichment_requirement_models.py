"""
Enrichment Requirement Models

Defines models and schemas for validating that parts have the necessary data
before attempting enrichment from suppliers. This helps provide better UX by
showing users what's missing before they try to enrich.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class RequirementSeverity(str, Enum):
    """Severity level of a requirement"""

    REQUIRED = "required"  # Must have this field for enrichment to work
    RECOMMENDED = "recommended"  # Enrichment may work but results will be limited
    OPTIONAL = "optional"  # Nice to have but not necessary


class FieldRequirement(BaseModel):
    """Defines a requirement for a specific field"""

    field_name: str = Field(description="Name of the required field (e.g., 'supplier_part_number')")
    display_name: str = Field(description="Human-readable field name (e.g., 'Supplier Part Number')")
    severity: RequirementSeverity = Field(description="How critical this field is")
    description: str = Field(description="Why this field is needed and what it enables")
    example: Optional[str] = Field(default=None, description="Example value for this field")
    validation_pattern: Optional[str] = Field(default=None, description="Regex pattern for validation")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "supplier_part_number",
                "display_name": "LCSC Part Number",
                "severity": "required",
                "description": "The LCSC part number (e.g., C25804) is required to look up part details",
                "example": "C25804",
                "validation_pattern": "^C\\d+$",
            }
        }


class EnrichmentRequirements(BaseModel):
    """Complete set of requirements for a supplier's enrichment"""

    supplier_name: str = Field(description="Name of the supplier")
    display_name: str = Field(description="Human-readable supplier name")
    required_fields: List[FieldRequirement] = Field(
        default_factory=list, description="Fields that MUST be present for enrichment"
    )
    recommended_fields: List[FieldRequirement] = Field(
        default_factory=list, description="Fields that improve enrichment quality"
    )
    optional_fields: List[FieldRequirement] = Field(default_factory=list, description="Fields that are nice to have")
    description: str = Field(default="", description="Overall description of what this supplier can enrich")

    def get_all_requirements(self) -> List[FieldRequirement]:
        """Get all requirements regardless of severity"""
        return self.required_fields + self.recommended_fields + self.optional_fields

    def get_required_field_names(self) -> List[str]:
        """Get list of required field names"""
        return [req.field_name for req in self.required_fields]

    def get_recommended_field_names(self) -> List[str]:
        """Get list of recommended field names"""
        return [req.field_name for req in self.recommended_fields]

    class Config:
        json_schema_extra = {
            "example": {
                "supplier_name": "lcsc",
                "display_name": "LCSC Electronics",
                "description": "LCSC can enrich parts with detailed specifications, images, pricing, and datasheets",
                "required_fields": [
                    {
                        "field_name": "supplier_part_number",
                        "display_name": "LCSC Part Number",
                        "severity": "required",
                        "description": "Required to look up part details from LCSC",
                        "example": "C25804",
                    }
                ],
                "recommended_fields": [],
            }
        }


@dataclass
class FieldCheck:
    """Result of checking a single field requirement"""

    field_name: str
    display_name: str
    severity: RequirementSeverity
    is_present: bool
    current_value: Optional[Any] = None
    validation_passed: bool = True
    validation_message: Optional[str] = None

    def is_satisfied(self) -> bool:
        """Check if this requirement is satisfied"""
        return self.is_present and self.validation_passed


@dataclass
class EnrichmentRequirementCheck:
    """Result of checking all requirements for a part"""

    supplier_name: str
    part_id: str
    can_enrich: bool  # Overall: can enrichment proceed?
    required_checks: List[FieldCheck] = field(default_factory=list)
    recommended_checks: List[FieldCheck] = field(default_factory=list)
    optional_checks: List[FieldCheck] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    missing_recommended: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "supplier_name": self.supplier_name,
            "part_id": self.part_id,
            "can_enrich": self.can_enrich,
            "required_checks": [
                {
                    "field_name": check.field_name,
                    "display_name": check.display_name,
                    "is_present": check.is_present,
                    "current_value": check.current_value,
                    "validation_passed": check.validation_passed,
                    "validation_message": check.validation_message,
                }
                for check in self.required_checks
            ],
            "recommended_checks": [
                {
                    "field_name": check.field_name,
                    "display_name": check.display_name,
                    "is_present": check.is_present,
                    "current_value": check.current_value,
                }
                for check in self.recommended_checks
            ],
            "missing_required": self.missing_required,
            "missing_recommended": self.missing_recommended,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


class EnrichmentRequirementCheckResponse(BaseModel):
    """API response schema for enrichment requirement checks"""

    supplier_name: str
    part_id: str
    can_enrich: bool
    required_checks: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_checks: List[Dict[str, Any]] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    missing_recommended: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "supplier_name": "lcsc",
                "part_id": "123e4567-e89b-12d3-a456-426614174000",
                "can_enrich": False,
                "required_checks": [
                    {
                        "field_name": "supplier_part_number",
                        "display_name": "LCSC Part Number",
                        "is_present": False,
                        "current_value": None,
                        "validation_passed": False,
                        "validation_message": "Supplier part number is required",
                    }
                ],
                "missing_required": ["supplier_part_number"],
                "missing_recommended": [],
                "warnings": [],
                "suggestions": [
                    "Add the LCSC part number (e.g., C25804) to enable enrichment",
                    "The part number can be found on the LCSC product page",
                ],
            }
        }
