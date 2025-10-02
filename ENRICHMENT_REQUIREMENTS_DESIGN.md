# Enrichment Requirements System Design

## Overview
Design a flexible enrichment requirements system that allows suppliers to declare what fields they need for enrichment, and prevents enrichment when requirements aren't met.

## Current Problems
1. **Supplier-specific fields** on base model (`lcsc_part_number`)
2. **No validation** - users can try to enrich without required data
3. **Inconsistent part number usage** - manufacturer vs supplier part numbers
4. **Frontend has no way to check** if enrichment will work
5. **No unified enrichment interface** across import/part/order flows

## Proposed Architecture

### 1. Add Generic `supplier_part_number` Field

```python
# models/part_models.py
class PartModel(SQLModel, table=True):
    # ... existing fields ...

    supplier_part_number: Optional[str] = Field(
        default=None,
        description="Supplier's catalog/part number (e.g., LCSC: C1591, DigiKey: 296-1234-ND)"
    )
```

### 2. Enrichment Requirement Schema

```python
# suppliers/enrichment_requirements.py
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional

class RequirementSource(str, Enum):
    """Where to look for the required value"""
    PART_NUMBER = "part_number"
    SUPPLIER_PART_NUMBER = "supplier_part_number"
    MANUFACTURER_PART_NUMBER = "manufacturer_part_number"
    SUPPLIER_URL = "supplier_url"
    ADDITIONAL_PROPERTIES = "additional_properties"

class EnrichmentRequirement(BaseModel):
    """Single requirement for enrichment"""
    field_name: str  # "supplier_part_number"
    field_label: str  # "LCSC Part Number"
    description: str  # "The LCSC catalog number (starts with 'C')"
    example: str  # "C1591"
    source: RequirementSource
    additional_property_key: Optional[str] = None  # If source is ADDITIONAL_PROPERTIES
    required: bool = True
    validation_pattern: Optional[str] = None  # Regex pattern (e.g., "^C\d+$" for LCSC)

class SupplierEnrichmentRequirements(BaseModel):
    """All requirements for a supplier's enrichment"""
    supplier_name: str
    requirements: List[EnrichmentRequirement]
    any_of: Optional[List[EnrichmentRequirement]] = None  # At least one must be present
```

### 3. Supplier-Specific Requirements

```python
# suppliers/lcsc.py
class LCSCSupplier(BaseSupplier):

    @classmethod
    def get_enrichment_requirements(cls) -> SupplierEnrichmentRequirements:
        """Define what LCSC needs for enrichment"""
        return SupplierEnrichmentRequirements(
            supplier_name="LCSC",
            requirements=[
                EnrichmentRequirement(
                    field_name="supplier_part_number",
                    field_label="LCSC Part Number",
                    description="The LCSC catalog number (starts with 'C' followed by digits)",
                    example="C1591",
                    source=RequirementSource.SUPPLIER_PART_NUMBER,
                    required=True,
                    validation_pattern=r"^C\d+$"
                )
            ],
            any_of=[
                # Could also accept URL
                EnrichmentRequirement(
                    field_name="supplier_url",
                    field_label="LCSC Product URL",
                    description="Full LCSC product page URL",
                    example="https://www.lcsc.com/product-detail/C1591.html",
                    source=RequirementSource.SUPPLIER_URL,
                    required=False,
                    validation_pattern=r"lcsc\.com/product-detail/C\d+"
                )
            ]
        )

# suppliers/digikey.py
class DigiKeySupplier(BaseSupplier):

    @classmethod
    def get_enrichment_requirements(cls) -> SupplierEnrichmentRequirements:
        """DigiKey can use multiple part number types"""
        return SupplierEnrichmentRequirements(
            supplier_name="DigiKey",
            any_of=[
                EnrichmentRequirement(
                    field_name="supplier_part_number",
                    field_label="DigiKey Part Number",
                    description="DigiKey's catalog number",
                    example="296-1234-ND",
                    source=RequirementSource.SUPPLIER_PART_NUMBER,
                    required=False
                ),
                EnrichmentRequirement(
                    field_name="manufacturer_part_number",
                    field_label="Manufacturer Part Number",
                    description="Original manufacturer's part number",
                    example="CL10B104KB8NNNC",
                    source=RequirementSource.MANUFACTURER_PART_NUMBER,
                    required=False
                ),
                EnrichmentRequirement(
                    field_name="supplier_url",
                    field_label="DigiKey Product URL",
                    description="Full DigiKey product page URL",
                    example="https://www.digikey.com/en/products/detail/...",
                    source=RequirementSource.SUPPLIER_URL,
                    required=False
                )
            ]
        )
```

### 4. Requirement Validation Service

```python
# services/system/enrichment_requirement_validator.py
class EnrichmentRequirementValidator:
    """Check if a part meets enrichment requirements"""

    @staticmethod
    def validate_requirements(
        part: PartModel,
        requirements: SupplierEnrichmentRequirements
    ) -> EnrichmentValidationResult:
        """
        Check if part has all required fields for enrichment.

        Returns:
            validation_result: Whether requirements are met
            missing_requirements: List of missing/invalid requirements
            suggestions: How to fix missing data
        """
        missing = []
        suggestions = []

        # Check required fields
        for req in requirements.requirements:
            value = cls._get_field_value(part, req)
            if not value:
                missing.append(req)
                suggestions.append(
                    f"Add {req.field_label}: {req.description} (Example: {req.example})"
                )
            elif req.validation_pattern:
                import re
                if not re.match(req.validation_pattern, value):
                    missing.append(req)
                    suggestions.append(
                        f"{req.field_label} format invalid. Expected pattern: {req.validation_pattern}"
                    )

        # Check any_of requirements
        if requirements.any_of:
            has_any = False
            for req in requirements.any_of:
                value = cls._get_field_value(part, req)
                if value and (not req.validation_pattern or re.match(req.validation_pattern, value)):
                    has_any = True
                    break

            if not has_any:
                missing.extend(requirements.any_of)
                suggestions.append(
                    f"Need at least one of: {', '.join([r.field_label for r in requirements.any_of])}"
                )

        return EnrichmentValidationResult(
            is_valid=len(missing) == 0,
            missing_requirements=missing,
            suggestions=suggestions
        )

    @staticmethod
    def _get_field_value(part: PartModel, requirement: EnrichmentRequirement) -> Optional[str]:
        """Extract field value based on requirement source"""
        if requirement.source == RequirementSource.PART_NUMBER:
            return part.part_number
        elif requirement.source == RequirementSource.SUPPLIER_PART_NUMBER:
            return part.supplier_part_number
        elif requirement.source == RequirementSource.MANUFACTURER_PART_NUMBER:
            return part.manufacturer_part_number
        elif requirement.source == RequirementSource.SUPPLIER_URL:
            return part.supplier_url
        elif requirement.source == RequirementSource.ADDITIONAL_PROPERTIES:
            if part.additional_properties and requirement.additional_property_key:
                return part.additional_properties.get(requirement.additional_property_key)
        return None

class EnrichmentValidationResult(BaseModel):
    is_valid: bool
    missing_requirements: List[EnrichmentRequirement]
    suggestions: List[str]
```

### 5. API Endpoint for Requirements

```python
# routers/parts_routes.py

@router.get("/parts/{part_id}/enrichment-requirements/{supplier}")
async def check_enrichment_requirements(
    part_id: str,
    supplier: str,
    current_user: UserModel = Depends(get_current_user),
    part_service: PartService = Depends(get_part_service)
) -> ResponseSchema[EnrichmentValidationResult]:
    """
    Check if a part meets enrichment requirements for a supplier.

    Used by frontend to enable/disable enrich button and show helpful messages.
    """
    # Get part
    part_response = part_service.get_part_by_id(part_id)
    if not part_response.success:
        raise HTTPException(status_code=404, detail="Part not found")

    part = part_response.data

    # Get supplier requirements
    supplier_config = SupplierRegistry.get_supplier(supplier)
    if not supplier_config:
        raise HTTPException(status_code=404, detail="Supplier not found")

    requirements = supplier_config.get_enrichment_requirements()

    # Validate
    validator = EnrichmentRequirementValidator()
    result = validator.validate_requirements(part, requirements)

    return BaseRouter.build_success_response(
        data=result,
        message="Requirements checked" if result.is_valid else "Missing required fields"
    )
```

### 6. Frontend Integration

```typescript
// services/enrichment.service.ts
interface EnrichmentRequirement {
  field_name: string
  field_label: string
  description: string
  example: string
  required: boolean
  validation_pattern?: string
}

interface ValidationResult {
  is_valid: boolean
  missing_requirements: EnrichmentRequirement[]
  suggestions: string[]
}

async checkEnrichmentRequirements(
  partId: string,
  supplier: string
): Promise<ValidationResult> {
  const response = await apiClient.get(
    `/api/parts/${partId}/enrichment-requirements/${supplier}`
  )
  return response.data
}

// components/parts/PartDetails.tsx
const [enrichmentValid, setEnrichmentValid] = useState(false)
const [enrichmentSuggestions, setEnrichmentSuggestions] = useState<string[]>([])

useEffect(() => {
  if (part.supplier) {
    enrichmentService.checkEnrichmentRequirements(part.id, part.supplier)
      .then(result => {
        setEnrichmentValid(result.is_valid)
        setEnrichmentSuggestions(result.suggestions)
      })
  }
}, [part])

// In render:
<button
  disabled={!enrichmentValid}
  onClick={handleEnrich}
  title={enrichmentValid ? "Enrich part data" : enrichmentSuggestions.join('\n')}
>
  Enrich from {part.supplier}
</button>

{!enrichmentValid && (
  <div className="alert alert-warning">
    <h5>Missing enrichment requirements:</h5>
    <ul>
      {enrichmentSuggestions.map((suggestion, i) => (
        <li key={i}>{suggestion}</li>
      ))}
    </ul>
  </div>
)}
```

## Migration Path

### Phase 1: Add supplier_part_number field
1. Add field to PartModel
2. Update schemas (PartCreate, PartUpdate, PartResponse)
3. Update frontend part forms
4. Run database migration

### Phase 2: Implement requirements system
1. Create EnrichmentRequirement models
2. Add get_enrichment_requirements() to BaseSupplier
3. Implement for LCSC and DigiKey
4. Create validation service

### Phase 3: API integration
1. Add requirements check endpoint
2. Update enrichment service to validate before enriching
3. Return helpful error messages

### Phase 4: Frontend integration
1. Add requirements check on part load
2. Enable/disable enrich button based on validation
3. Show helpful tooltips/alerts
4. Add inline requirement hints in forms

### Phase 5: Unified enrichment interfaces
1. Extract common enrichment logic to base class
2. Unify import enrichment, part enrichment, order enrichment
3. Same requirements system across all flows

## Benefits

1. **No supplier-specific fields** on base model
2. **Self-documenting** - requirements describe what's needed
3. **Better UX** - users know exactly what to provide
4. **Validation before API call** - saves time and errors
5. **Flexible** - easy to add new requirements or suppliers
6. **Maintainable** - requirements live with supplier code

## Example Part Data

```json
{
  "part_name": "Samsung 100nF 0603 Capacitor",
  "part_number": "CL10B104KB8NNNC",  // Manufacturer
  "supplier_part_number": "C1591",    // NEW: LCSC catalog number
  "supplier": "LCSC",
  "manufacturer": "Samsung Electro-Mechanics",
  "manufacturer_part_number": "CL10B104KB8NNNC"
}
```

Now enrichment works because `supplier_part_number` is populated with LCSC's C1591!
