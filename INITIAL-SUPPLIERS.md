## FEATURE:

Standardize and fix the MakerMatrix supplier framework to ensure consistent data handling across all suppliers and eliminate inconsistencies between import and enrichment workflows. Currently suppliers have inconsistent data mapping patterns, the LCSC supplier has broken CSV import, and the import/enrichment integration produces inconsistent additional_properties structures.

This is a framework-wide standardization initiative that leverages existing infrastructure (SupplierDataMapper, EnrichmentDataMapper, StandardizedAdditionalProperties schemas) to create unified data transformation pipelines for both file import and API enrichment operations.

Core framework requirements:
- Standardize file import column mapping across all suppliers (LCSC, Mouser, DigiKey) 
- Ensure consistent additional_properties structure whether data comes from import or enrichment
- Fix critical LCSC CSV import that hardcodes generic values instead of parsing descriptions
- Implement unified data transformation pipeline using existing SupplierDataMapper infrastructure
- Standardize file type support and detection across suppliers
- Integrate import→enrichment workflow to produce consistent part data structures
- Create framework-wide validation and testing for data consistency

The supplier architecture has good foundations (BaseSupplier, registry pattern, capability system, standardization schemas) but needs enforcement of existing standards and elimination of inconsistent implementations.

## EXAMPLES:

- MakerMatrix/suppliers/lcsc.py - Broken CSV import (lines 481-488) hardcodes generic values
- MakerMatrix/suppliers/mouser.py - Working column mapping reference (lines 704-721)  
- MakerMatrix/suppliers/digikey.py - Additional file format support patterns
- MakerMatrix/services/data/supplier_data_mapper.py - Existing standardization infrastructure
- MakerMatrix/services/data/enrichment_data_mapper.py - Import/enrichment coordination
- MakerMatrix/services/enhanced_import_service.py - Integration workflow implementation
- MakerMatrix/schemas/part_data_standards.py - StandardizedAdditionalProperties schema
- MakerMatrix/tasks/file_import_enrichment_task.py - Task-based enrichment system
- MakerMatrix/routers/import_routes.py - File upload and processing workflow
- MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv - Real LCSC CSV format examples
- MakerMatrix/tests/mouser_xls_test/ - Mouser Excel test files
- MakerMatrix/tests/test_lcsc_csv_import_fix.py - Existing test structure for validation

## DOCUMENTATION:

**Existing Standardization Infrastructure:**
- SupplierDataMapper with supplier-specific mapping methods for standardized data transformation
- EnrichmentDataMapper coordinates import/enrichment integration workflows  
- StandardizedAdditionalProperties schema defines consistent structure for all part data
- BaseSupplier abstract class with capability system and registry pattern (@register_supplier)
- Task-based enrichment system with file_import_enrichment_task integration

**Current File Type Support by Supplier:**
- LCSC: CSV only (lcsc.py) - BROKEN: hardcodes values instead of parsing
- Mouser: XLS/XLSX only (mouser.py) - WORKING: proper column mapping lines 704-721
- DigiKey: CSV, XLS, XLSX (digikey.py) - supports multiple formats

**Import→Enrichment Integration Workflow:**
```
File Upload → Supplier Detection → File Parsing → Part Creation → Optional Enrichment Task
     ↓              ↓                   ↓              ↓                    ↓
import_routes → get_supplier() → import_order_file() → PartService → file_import_enrichment_task
```

**Standardized Data Transformation Pattern:**
```python
# SupplierDataMapper handles consistent additional_properties structure
supplier_mapper = SupplierDataMapper()
standardized_data = supplier_mapper.map_supplier_result_to_part_data(
    supplier_result, supplier_name, enrichment_capabilities
)
# Result follows StandardizedAdditionalProperties schema
```

**Working Column Mapping Reference (Mouser lines 704-721):**
```python
column_mappings = {
    'part_number': ['mouser #:', 'mouser part #', 'part number'],
    'manufacturer': ['manufacturer', 'mfr', 'mfg'],
    'manufacturer_part_number': ['mfr. #:', 'manufacturer part number'], 
    'description': ['desc.:', 'description', 'product description'],
    'quantity': ['order qty.', 'quantity', 'qty']
}
```

**API Endpoints for Import and Enrichment:**
- POST /api/import/file - Unified import with optional enrichment (import_routes.py)
- POST /api/tasks/quick/file_import_enrichment - Task-based enrichment for imported parts
- WebSocket /ws/tasks - Real-time progress tracking for import and enrichment operations

**Part Data Model Architecture:**
- Universal fields: part_name, part_number, supplier_part_number, description, manufacturer
- additional_properties JSON field with StandardizedAdditionalProperties schema
- Consistent structure whether populated via import or enrichment

## OTHER CONSIDERATIONS:

- Framework changes must be backward compatible with all existing part data and imports
- Leverage existing infrastructure (SupplierDataMapper, EnrichmentDataMapper, schemas) rather than rebuilding
- Ensure all suppliers use SupplierDataMapper for consistent additional_properties structure
- Suppliers handle their own file-specific column mappings, SupplierDataMapper handles standardization
- Write comprehensive pytest test suite covering:
  - Framework-wide supplier data consistency validation
  - Import→enrichment integration produces identical additional_properties structures  
  - LCSC CSV import fix with real CSV files containing rich descriptions
  - All file formats across all suppliers (CSV, XLS, XLSX)
  - Column mapping flexibility with various header formats
  - Edge cases: missing columns, empty values, malformed data, encoding issues
  - Integration tests for import_routes.py workflow with enrichment
  - Task system integration for file_import_enrichment_task
- Test with real supplier files: LCSC CSV exports, Mouser XLS orders, DigiKey formats
- Use development manager (python dev_manager.py) for integrated testing
- Run validation commands after implementation to ensure no regressions
- Create framework-wide validation tools to catch supplier data inconsistencies
- Document supplier implementation requirements and StandardizedAdditionalProperties usage
- Create supplier compliance testing to ensure future suppliers follow standards
- Consider supplier-specific additional_properties population during import (packages, values, specs)
- Implement proper defensive error handling across all suppliers following existing patterns