# PRP: Fix Critical LCSC CSV Import Description Mapping

## Project Requirements Plan

**PRP ID**: lcsc-csv-import-fix  
**Priority**: CRITICAL  
**Estimated Effort**: 2-3 hours  
**Confidence Score**: 9/10  

---

## Problem Statement

The LCSC supplier implementation has a critical bug where CSV imports provide meaningless part data instead of rich descriptions from CSV files. Currently, the LCSC supplier hardcodes generic values instead of parsing CSV columns, making imported parts unusable without manual data entry.

**Current Broken Behavior** (lines 481-488 in `/MakerMatrix/suppliers/lcsc.py`):
```python
# ❌ BROKEN - No column mapping logic
parts.append({
    'part_number': lcsc_part,
    'part_name': lcsc_part,  # Should be description from CSV
    'quantity': quantity,
    'supplier': 'LCSC',
    'description': f'Imported from {filename or "LCSC CSV"}'  # Should be description from CSV
})
```

**Expected Behavior**: Extract rich descriptions from CSV and use as both `part_name` and `description` fields.

---

## Technical Context

### Working Reference Implementation (Mouser Supplier)
The Mouser supplier (lines 704-721 in `/MakerMatrix/suppliers/mouser.py`) demonstrates the correct pattern:

```python
# ✅ CORRECT - Proper column mapping
column_mappings = {
    'part_number': ['mouser #:', 'mouser part #', 'mouser part number', 'part number', 'mouser p/n'],
    'manufacturer': ['manufacturer', 'mfr', 'mfg'],
    'manufacturer_part_number': ['mfr. #:', 'manufacturer part number', 'mfr part #', 'mfg part #', 'customer #'],
    'description': ['desc.:', 'description', 'product description'],
    'quantity': ['order qty.', 'quantity', 'qty', 'order qty'],
}

# Dynamic column detection
mapped_columns = {}
for field, possible_names in column_mappings.items():
    for possible_name in possible_names:
        matching_cols = [col for col in df.columns if possible_name.lower() in col.lower()]
        if matching_cols:
            mapped_columns[field] = matching_cols[0]
            break

# Proper data mapping with fallbacks
part = {
    'part_name': str(row.get(mapped_columns.get('description', ''), 
                           row.get(mapped_columns.get('manufacturer_part_number', ''), ''))).strip(),
    'description': str(row.get(mapped_columns.get('description', ''), '')).strip(),
    'manufacturer': str(row.get(mapped_columns.get('manufacturer', ''), '')).strip(),
}
```

### Architecture Context
- **BaseSupplier Interface**: Defines `ImportResult` return type with `parts` list
- **Registry Pattern**: Uses `@register_supplier("lcsc")` decorator
- **Unified Architecture**: LCSC uses `SupplierHTTPClient` and `DataExtractor` patterns
- **Defensive Patterns**: Extensive null safety with `or {}` patterns throughout

### Real LCSC CSV Format
Based on `/MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv`:
```csv
LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\Mult Order Qty.,Unit Price($),Order Price($)
C7442639,VEJ101M1VTT-0607L,Lelon,,"SMD,D6.3xL7.7mm","100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS",YES,50,5\5,0.0874,4.37
```

---

## External Research & Best Practices

### CSV Parsing Best Practices
**Source**: [Python CSV Error Handling Best Practices](https://labex.io/tutorials/python-how-to-implement-robust-error-handling-in-python-csv-processing-398214)

Key defensive patterns:
1. **Encoding Handling**: Use `utf-8-sig` to handle BOM, fallback to `utf-8` with `errors='ignore'`
2. **Malformed Data**: Wrap parsing in try-catch blocks for each row
3. **Missing Columns**: Implement graceful fallbacks when expected columns are missing
4. **Empty Values**: Handle empty strings and None values defensively

### Pandas Column Mapping
**Source**: [Pandas CSV Column Mapping](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)

Best practices for flexible header matching:
```python
def map_columns(headers: List[str], mappings: Dict[str, List[str]]) -> Dict[str, str]:
    """Map CSV headers to standardized field names using flexible matching."""
    mapped = {}
    headers_lower = [h.lower().strip() for h in headers]
    
    for field, variations in mappings.items():
        for variation in variations:
            for i, header in enumerate(headers_lower):
                if variation.lower() in header:
                    mapped[field] = headers[i]  # Use original case
                    break
            if field in mapped:
                break
    
    return mapped
```

---

## Implementation Blueprint

### Step 1: Column Mapping Algorithm
```python
def _map_csv_columns(self, headers: List[str]) -> Dict[str, str]:
    """Map CSV headers to standardized fields with flexible matching."""
    column_mappings = {
        'part_number': ['lcsc part number', 'lcsc part #', 'part number', 'lcsc #'],
        'description': ['description', 'desc', 'part description', 'product description'],
        'quantity': ['quantity', 'qty', 'order qty'],
        'manufacturer': ['manufacturer', 'mfr', 'mfg', 'manufacture part number'],
        'manufacturer_part_number': ['manufacturer part number', 'mfr part number', 'mpn', 'mfr part #', 'manufacture part number'],
        'package': ['package', 'pkg'],
        'value': ['value', 'val']
    }
    
    mapped_columns = {}
    headers_lower = [h.lower().strip() for h in headers]
    
    for field, variations in column_mappings.items():
        for variation in variations:
            for i, header in enumerate(headers_lower):
                if variation.lower() in header:
                    mapped_columns[field] = headers[i]  # Use original case
                    break
            if field in mapped_columns:
                break
    
    return mapped_columns
```

### Step 2: Data Transformation
```python
def _transform_csv_row(self, row: Dict[str, str], mapped_columns: Dict[str, str], filename: str) -> Dict[str, Any]:
    """Transform CSV row data using column mappings into standardized part data."""
    # Extract core fields with defensive access
    description = row.get(mapped_columns.get('description', ''), '').strip()
    manufacturer_part = row.get(mapped_columns.get('manufacturer_part_number', ''), '').strip()
    part_number = row.get(mapped_columns.get('part_number', ''), '').strip()
    manufacturer = row.get(mapped_columns.get('manufacturer', ''), '').strip()
    
    # Determine best part_name (preference: description > mfr_part > part_number)
    part_name = description or manufacturer_part or part_number
    
    # Build additional properties from extracted data
    additional_properties = {}
    if mapped_columns.get('package'):
        package = row.get(mapped_columns['package'], '').strip()
        if package:
            additional_properties['package'] = package
    
    if mapped_columns.get('value'):
        value = row.get(mapped_columns['value'], '').strip()
        if value:
            additional_properties['value'] = value
    
    return {
        'part_number': part_number,
        'part_name': part_name,
        'supplier_part_number': part_number,  # LCSC uses same value
        'description': description,
        'manufacturer': manufacturer,
        'manufacturer_part_number': manufacturer_part,
        'supplier': 'LCSC',
        'additional_properties': additional_properties if additional_properties else {}
    }
```

### Step 3: Error Handling Strategy
```python
# Encoding handling with fallbacks
try:
    csv_text = file_content.decode('utf-8-sig')  # Handle BOM
except UnicodeDecodeError:
    csv_text = file_content.decode('utf-8', errors='ignore')

# Row-level error handling
for i, line in enumerate(lines[1:], 1):
    try:
        cols = [col.strip().strip('"') for col in line.split(',')]
        # Process row...
    except Exception as e:
        failed_items.append({
            'line_number': i,
            'error': str(e),
            'data': line
        })
```

---

## Implementation Tasks

### Task 1: Implement Column Mapping Logic
**File**: `/MakerMatrix/suppliers/lcsc.py`  
**Location**: Replace `import_order_file` method (lines 419-511)  
**Duration**: 45 minutes

1. Add `_map_csv_columns` method with LCSC-specific column mappings
2. Add `_transform_csv_row` method for data transformation
3. Update CSV parsing logic to use column mapping

### Task 2: Replace Hardcoded Values with Dynamic Mapping
**File**: `/MakerMatrix/suppliers/lcsc.py`  
**Location**: Lines 481-488  
**Duration**: 15 minutes

1. Replace hardcoded `part_name = lcsc_part` with description mapping
2. Replace hardcoded `description = f'Imported from {filename}'` with CSV description
3. Add manufacturer and additional properties extraction

### Task 3: Enhance Error Handling
**File**: `/MakerMatrix/suppliers/lcsc.py`  
**Location**: Throughout `import_order_file` method  
**Duration**: 30 minutes

1. Implement defensive encoding handling (UTF-8 with BOM fallback)
2. Add row-level error handling with detailed error tracking
3. Handle missing or empty column values gracefully

### Task 4: Comprehensive Testing
**File**: `/MakerMatrix/tests/test_lcsc_csv_import_fix.py`  
**Duration**: 45 minutes

1. Update existing test assertions to match new behavior
2. Test real LCSC CSV files with rich descriptions
3. Test edge cases: missing columns, empty values, encoding issues
4. Verify backward compatibility

### Task 5: Integration Testing
**Duration**: 15 minutes

1. Test with development manager using real CSV files
2. Verify parts are created with meaningful descriptions
3. Ensure no regression in other supplier imports

---

## Validation Gates

### Syntax and Style Validation
```bash
# Navigate to project root
cd /home/ril3y/MakerMatrix

# Check Python syntax and style
source venv_test/bin/activate
python -m py_compile MakerMatrix/suppliers/lcsc.py

# Optional: Run linting if available
# ruff check MakerMatrix/suppliers/lcsc.py --fix
```

### Unit Tests
```bash
# Run LCSC-specific tests
source venv_test/bin/activate
python -m pytest MakerMatrix/tests/test_lcsc_csv_import_fix.py -v

# Run all supplier tests to ensure no regression
python -m pytest MakerMatrix/tests/unit_tests/test_supplier_*.py -v
```

### Integration Tests
```bash
# Test with real CSV file
source venv_test/bin/activate
python -c "
import asyncio
from MakerMatrix.suppliers.lcsc import LCSCSupplier

async def test_real_csv():
    supplier = LCSCSupplier()
    supplier.configure(credentials={}, config={'rate_limit_requests_per_minute': 20})
    
    with open('MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv', 'rb') as f:
        result = await supplier.import_order_file(f.read(), 'csv', 'test.csv')
    
    print(f'Success: {result.success}')
    print(f'Imported: {result.imported_count}')
    for part in result.parts[:2]:  # Show first 2 parts
        print(f'Part: {part[\"part_number\"]} -> \"{part[\"description\"]}\"')
        
asyncio.run(test_real_csv())
"
```

### Manual Validation
```bash
# Start development manager for manual testing
python dev_manager.py

# Use frontend import feature with LCSC CSV files
# Verify parts have meaningful descriptions instead of generic text
```

---

## Risk Mitigation

### Backward Compatibility
- All existing LCSC data remains unaffected (import only)
- Other supplier implementations unchanged
- ImportResult interface remains consistent

### Error Handling
- Graceful fallbacks for missing columns
- Detailed error reporting for malformed data
- Row-level error tracking prevents total import failure

### Testing Coverage
- Unit tests for all CSV format variations
- Integration tests with real LCSC data
- Edge case testing for encoding and malformed data

---

## Success Criteria

### Primary Goals
- [ ] LCSC CSV imports create parts with meaningful descriptions (not generic text)
- [ ] All existing supplier imports continue working without changes
- [ ] Test suite passes with >90% coverage of import scenarios
- [ ] Fix is backward compatible with existing data

### Quality Metrics
- [ ] Real LCSC CSV files import with rich part descriptions
- [ ] Column mapping handles various header formats
- [ ] Error handling gracefully manages malformed data
- [ ] Performance impact minimal (<10% slower than current)

---

## Code References

### Primary Files
- **Implementation**: `/MakerMatrix/suppliers/lcsc.py` (lines 419-511)
- **Reference Pattern**: `/MakerMatrix/suppliers/mouser.py` (lines 704-721)
- **Test Suite**: `/MakerMatrix/tests/test_lcsc_csv_import_fix.py`
- **Sample Data**: `/MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv`

### Supporting Architecture
- **Base Interface**: `/MakerMatrix/suppliers/base.py` (ImportResult class)
- **Registry System**: `/MakerMatrix/suppliers/registry.py`
- **Development Tools**: `dev_manager.py`, `CLAUDE.md`

---

## Implementation Notes

### Key Patterns to Follow
1. **Defensive Programming**: Use `or {}` patterns extensively like existing LCSC code
2. **Column Mapping**: Follow Mouser's flexible matching algorithm exactly
3. **Error Handling**: Implement row-level error tracking with detailed messages
4. **Testing**: Use existing test structure and patterns from test_lcsc_csv_import_fix.py

### Common Pitfalls to Avoid
1. **Breaking Existing Code**: Ensure other suppliers remain unaffected
2. **Missing Fallbacks**: Always provide fallback values for missing data
3. **Encoding Issues**: Handle UTF-8 BOM and various encodings
4. **Performance**: Avoid loading entire CSV into pandas for simple parsing

**Confidence Score: 9/10** - High confidence due to clear problem definition, working reference implementation, comprehensive test coverage, and detailed implementation plan.