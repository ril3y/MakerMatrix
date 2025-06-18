# QR Code Part Creation with Enrichment

This document describes how to use the enhanced `add_part` endpoint with automatic enrichment for QR code scanning in mobile apps.

## Overview

The enhanced `add_part` endpoint now supports automatic part enrichment during creation. This is particularly useful for mobile QR code scanning where you want to:

1. Create a part from QR code data
2. Automatically enrich it with additional information from suppliers
3. Return the fully enriched part data in one API call

## API Usage

### Basic QR Part Creation (No Enrichment)

```json
POST /parts/add_part
{
  "part_number": "C136648",
  "part_name": "LMR16030SDDAR",
  "description": "DC-DC Buck Converter IC",
  "quantity": 5,
  "supplier": "LCSC"
}
```

### QR Part Creation with Automatic Enrichment

```json
POST /parts/add_part
{
  "part_number": "C136648",
  "part_name": "LMR16030SDDAR", 
  "description": "DC-DC Buck Converter IC",
  "quantity": 5,
  "supplier": "LCSC",
  
  "auto_enrich": true,
  "enrichment_supplier": "LCSC",
  "enrichment_capabilities": ["fetch_datasheet", "fetch_image", "fetch_pricing"]
}
```

## New Schema Fields

### PartCreate Schema Extensions

- `auto_enrich: bool = False` - Enable automatic enrichment
- `enrichment_supplier: str = None` - Supplier to use for enrichment
- `enrichment_capabilities: List[str] = []` - Specific capabilities to use

### Available Enrichment Capabilities

**Core Capabilities:**
- `fetch_datasheet` - Download and attach datasheet
- `fetch_image` - Download part images
- `fetch_pricing` - Get current pricing information
- `fetch_stock` - Check availability and stock levels
- `fetch_specifications` - Get detailed technical specifications

**Advanced Capabilities:**
- `fetch_alternatives` - Find alternative/substitute parts
- `fetch_lifecycle_status` - Get part lifecycle and availability status
- `validate_part_number` - Validate part numbers and existence
- `fetch_details` - Basic part information enrichment (auto-included)

## Response Messages

The API returns enhanced status messages indicating enrichment status:

### Success Cases
- ✅ `"Part created successfully. Part successfully enriched from LCSC."`
- ✅ `"Part created successfully. Enrichment task created (ID: abc123)."`

### Warning Cases  
- ⚠️ `"Part created successfully. Warning: Supplier 'LCSC' not configured on backend."`
- ⚠️ `"Part created successfully. Warning: Supplier 'LCSC' not properly configured."`
- ⚠️ `"Part created successfully. Enrichment task started but did not complete within timeout."`

### Error Cases
- ❌ `"Part created successfully. Warning: Enrichment failed - [error details]"`

## QR Code Data Mapping

Based on the QR format: `{pbn:PICK2311010075,on:GB2311011210,pc:C136648,pm:LMR16030SDDAR,qty:5,mc:10,cc:1,pdi:95387529,hp:0,wc:ZH}`

| QR Field | API Field | Description |
|----------|-----------|-------------|
| `pc` | `part_number` | Part/Component code |
| `pm` | `part_name` | Part model/name |
| `qty` | `quantity` | Quantity |
| `pbn` | *(metadata)* | Pick bin number |
| `on` | *(metadata)* | Order number |

The mobile app determines the supplier context (LCSC, DigiKey, etc.) and sets:
- `supplier` - The supplier name
- `enrichment_supplier` - Same as supplier for auto-enrichment

## Mobile App Integration

### TypeScript/JavaScript Example

```typescript
interface QRPartData {
  part_number: string;
  part_name: string;
  quantity: number;
  description?: string;
  supplier: string;
  auto_enrich: boolean;
  enrichment_supplier: string;
  enrichment_capabilities: string[];
}

async function createPartFromQR(qrData: any, supplier: string): Promise<any> {
  const partData: QRPartData = {
    part_number: qrData.pc,
    part_name: qrData.pm,
    quantity: parseInt(qrData.qty),
    supplier: supplier,
    
    // Enable enrichment
    auto_enrich: true,
    enrichment_supplier: supplier,
    enrichment_capabilities: ['fetch_datasheet', 'fetch_image', 'fetch_pricing']
  };
  
  const response = await fetch('/parts/add_part', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(partData)
  });
  
  return response.json();
}
```

### Error Handling

```typescript
const result = await createPartFromQR(qrData, 'LCSC');

if (result.status === 'success') {
  if (result.message.includes('successfully enriched')) {
    console.log('✅ Part created and enriched!', result.data);
  } else if (result.message.includes('Warning')) {
    console.warn('⚠️ Part created but enrichment had issues:', result.message);
  } else {
    console.log('✅ Part created (no enrichment requested)');
  }
} else {
  console.error('❌ Part creation failed:', result.message);
}
```

## Backend Requirements

### Supplier Configuration

For enrichment to work, suppliers must be:

1. **Available** - Listed in `get_available_suppliers()`
2. **Configured** - Have proper configuration in `SupplierConfigService`
3. **Capable** - Support the requested enrichment capabilities

Check available suppliers:
```bash
GET /tasks/capabilities/suppliers
```

### Task System

The enrichment uses the existing task system:
- Creates `TaskType.PART_ENRICHMENT` tasks
- Uses `TaskPriority.HIGH` for QR-triggered enrichment
- Includes progress tracking and WebSocket updates
- Supports timeout and retry mechanisms

## Testing

Run the pytest suite to validate functionality:

```bash
# Run all QR enrichment tests
./venv_test/bin/python -m pytest MakerMatrix/tests/integration_tests/test_qr_enrichment.py -v

# Run schema validation tests only  
./venv_test/bin/python -m pytest MakerMatrix/tests/integration_tests/test_qr_enrichment.py -k "schema or validation" -v

# Run integration tests (requires running backend)
./venv_test/bin/python -m pytest MakerMatrix/tests/integration_tests/test_qr_enrichment.py -m integration -v
```

### Import Fix Applied ✅

The import issue has been resolved by changing:
```python
# Before (incorrect)
from MakerMatrix.services.task_service import get_task_service

# After (correct)  
from MakerMatrix.services.task_service import task_service
```

### Modular Supplier System Enhancement ✅

**Issue:** Enrichment UI was only showing client-supported capabilities instead of user-configured capabilities.

**Root Cause:** API endpoints were returning `client.get_supported_capabilities()` instead of `supplier_config.get_capabilities()`.

**Solution:** Modified API endpoints to return configured capabilities:
- `/api/tasks/capabilities/suppliers` - Returns user-configured capabilities for all suppliers
- `/api/tasks/capabilities/suppliers/{supplier_name}` - Returns user-configured capabilities for specific supplier
- Added `client_capabilities` field for debugging/validation purposes

**Enhanced Capabilities:** Added 3 new configurable capabilities:
- Alternative Parts (`fetch_alternatives`)
- Lifecycle Status (`fetch_lifecycle_status`)  
- Part Validation (`validate_part_number`)

**Frontend Updates:**
- Fixed missing `fetch_stock` capability in enrichment UI
- Added all new capabilities to supplier configuration form
- Enhanced capability mapping for proper database field names

**Database Migration:** Added new capability columns to `supplier_configs` table automatically.

## Performance Considerations

- **Timeout**: Enrichment waits max 30 seconds before returning
- **Async**: Uses task system to avoid blocking part creation
- **Fallback**: Part is created even if enrichment fails
- **Caching**: Supplier validation results are cached

## Backward Compatibility

The enhancement is fully backward compatible:
- Existing `add_part` calls work unchanged
- New fields are optional with sensible defaults
- No breaking changes to existing functionality