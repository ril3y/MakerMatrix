# Enrichment Services Modular Architecture Plan

## Overview

This document outlines the detailed plan for refactoring the monolithic `enrichment_task_handlers.py` (1,843 lines) into 9 focused, single-responsibility services. The plan ensures all existing functionality is preserved while creating a maintainable, testable, and architecturally compliant system.

## Service Architecture Design

### 1. FileSystemService (Foundation Service)
**Location**: `/MakerMatrix/services/system/file_system_service.py`
**Purpose**: Centralized file operations for datasheet and image handling
**Dependencies**: Configuration only

```python
class FileSystemService:
    def __init__(self, config: dict):
        self.config = config
        self.base_datasheet_path = config.get('datasheet_path', 'datasheets')
        self.base_image_path = config.get('image_path', 'images')
    
    def save_file(self, content: bytes, file_path: str, overwrite: bool = False) -> bool
    def get_datasheet_file_path(self, supplier: str, part_number: str) -> str
    def get_image_file_path(self, supplier: str, part_number: str) -> str
    def validate_file_path(self, file_path: str) -> bool
    def ensure_directory_exists(self, file_path: str) -> bool
```

**Migration from monolithic**:
- Extract `_save_datasheet_to_file()` → `save_file()`
- Extract `_get_datasheet_file_path()` → `get_datasheet_file_path()`
- Extract `_save_image_to_file()` → `save_file()`
- Extract `_get_image_file_path()` → `get_image_file_path()`

### 2. EnrichmentDataMapper (Data Transformation)
**Location**: `/MakerMatrix/services/data/enrichment_data_mapper.py`
**Purpose**: Data mapping and transformation between enrichment results and part models
**Dependencies**: SupplierDataMapper

```python
class EnrichmentDataMapper:
    def __init__(self, supplier_data_mapper: SupplierDataMapper):
        self.supplier_data_mapper = supplier_data_mapper
    
    def convert_enrichment_to_part_search_result(self, part: PartModel, enrichment_results: Dict[str, Any], supplier_name: str) -> Optional[PartSearchResult]
    def extract_enrichment_data(self, enrichment_results: Dict[str, Any]) -> Dict[str, Any]
    def validate_enrichment_data(self, data: Dict[str, Any]) -> bool
    def merge_enrichment_results(self, existing_data: Dict, new_data: Dict) -> Dict
```

**Migration from monolithic**:
- Extract `_convert_enrichment_to_part_search_result()` → `convert_enrichment_to_part_search_result()`
- Create new methods for data extraction and validation

### 3. EnrichmentProgressTracker (Progress Monitoring)
**Location**: `/MakerMatrix/services/system/enrichment_progress_tracker.py`
**Purpose**: Progress tracking and reporting for enrichment operations
**Dependencies**: None (Observer pattern)

```python
class EnrichmentProgressTracker:
    def __init__(self):
        self.callbacks = []
        self.current_progress = 0
        self.total_steps = 0
    
    def register_callback(self, callback: callable) -> None
    def update_progress(self, current_step: int, total_steps: int, message: str) -> None
    def report_success(self, message: str) -> None
    def report_error(self, error: Exception, message: str) -> None
    def get_current_progress(self) -> Dict[str, Any]
```

**Migration from monolithic**:
- Extract progress callback logic from all handler methods
- Create centralized progress reporting

### 4. SupplierIntegrationService (External APIs)
**Location**: `/MakerMatrix/services/system/supplier_integration_service.py`
**Purpose**: Supplier API interactions and capability management
**Dependencies**: SupplierConfigService

```python
class SupplierIntegrationService:
    def __init__(self, supplier_config_service: SupplierConfigService):
        self.supplier_config_service = supplier_config_service
    
    def get_supplier_for_part(self, part: PartModel, preferred_supplier: str = None) -> Optional[str]
    def get_available_capabilities(self, supplier: str) -> List[str]
    def validate_supplier_capabilities(self, supplier: str, capabilities: List[str]) -> List[str]
    def execute_supplier_enrichment(self, supplier: str, part: PartModel, capabilities: List[str]) -> Dict[str, Any]
```

**Migration from monolithic**:
- Extract supplier selection logic from `handle_part_enrichment()`
- Extract capability validation logic
- Extract supplier API interaction patterns

### 5. DatasheetHandlerService (File Operations)
**Location**: `/MakerMatrix/services/system/datasheet_handler_service.py`
**Purpose**: Datasheet download, storage, and management
**Dependencies**: DatasheetRepository, FileSystemService, SupplierIntegrationService

```python
class DatasheetHandlerService:
    def __init__(self, datasheet_repository: DatasheetRepository, file_system_service: FileSystemService, supplier_integration_service: SupplierIntegrationService):
        self.datasheet_repository = datasheet_repository
        self.file_system_service = file_system_service
        self.supplier_integration_service = supplier_integration_service
    
    def handle_datasheet_fetch(self, task: TaskModel, progress_tracker: EnrichmentProgressTracker) -> Dict[str, Any]
    def download_and_save_datasheet(self, part: PartModel, datasheet_url: str, supplier: str) -> Dict[str, Any]
    def get_existing_datasheet(self, part_id: str, source_url: str) -> Optional[DatasheetModel]
    def create_datasheet_record(self, part: PartModel, file_info: Dict[str, Any]) -> DatasheetModel
```

**Migration from monolithic**:
- Extract `handle_datasheet_fetch()` → `handle_datasheet_fetch()`
- Integrate with DatasheetRepository for all database operations
- Use FileSystemService for file operations

### 6. ImageHandlerService (Media Operations)
**Location**: `/MakerMatrix/services/system/image_handler_service.py`
**Purpose**: Image download, processing, and storage
**Dependencies**: FileSystemService, SupplierIntegrationService

```python
class ImageHandlerService:
    def __init__(self, file_system_service: FileSystemService, supplier_integration_service: SupplierIntegrationService):
        self.file_system_service = file_system_service
        self.supplier_integration_service = supplier_integration_service
    
    def handle_image_fetch(self, task: TaskModel, progress_tracker: EnrichmentProgressTracker) -> Dict[str, Any]
    def download_and_save_image(self, part: PartModel, image_url: str, supplier: str) -> Dict[str, Any]
    def process_image(self, image_data: bytes, part: PartModel) -> Dict[str, Any]
    def validate_image_format(self, image_data: bytes) -> bool
```

**Migration from monolithic**:
- Extract `handle_image_fetch()` → `handle_image_fetch()`
- Use FileSystemService for file operations
- Add image processing capabilities

### 7. PartEnrichmentService (Core Operations)
**Location**: `/MakerMatrix/services/data/part_enrichment_service.py`
**Purpose**: Core part enrichment operations and data updates
**Dependencies**: PartRepository, CategoryRepository, EnrichmentDataMapper, SupplierIntegrationService

```python
class PartEnrichmentService(BaseService):
    def __init__(self, part_repository: PartRepository, category_repository: CategoryRepository, enrichment_data_mapper: EnrichmentDataMapper, supplier_integration_service: SupplierIntegrationService):
        super().__init__()
        self.part_repository = part_repository
        self.category_repository = category_repository
        self.enrichment_data_mapper = enrichment_data_mapper
        self.supplier_integration_service = supplier_integration_service
    
    def handle_part_enrichment(self, task: TaskModel, progress_tracker: EnrichmentProgressTracker) -> Dict[str, Any]
    def update_part_from_enrichment_results(self, part: PartModel, enrichment_results: Dict[str, Any], supplier: str) -> Dict[str, Any]
    def enrich_single_part(self, part: PartModel, supplier: str, capabilities: List[str]) -> Dict[str, Any]
    def validate_enrichment_results(self, results: Dict[str, Any]) -> bool
```

**Migration from monolithic**:
- Extract `handle_part_enrichment()` → `handle_part_enrichment()`
- Extract `_update_part_from_enrichment_results()` → `update_part_from_enrichment_results()`
- Use repositories for all database operations
- Integrate with BaseService for session management

### 8. BulkEnrichmentService (Batch Processing)
**Location**: `/MakerMatrix/services/data/bulk_enrichment_service.py`
**Purpose**: Batch enrichment operations and pagination
**Dependencies**: PartRepository, PartEnrichmentService, EnrichmentProgressTracker

```python
class BulkEnrichmentService(BaseService):
    def __init__(self, part_repository: PartRepository, part_enrichment_service: PartEnrichmentService):
        super().__init__()
        self.part_repository = part_repository
        self.part_enrichment_service = part_enrichment_service
    
    def handle_bulk_enrichment(self, task: TaskModel, progress_tracker: EnrichmentProgressTracker) -> Dict[str, Any]
    def handle_bulk_enrichment_paginated(self, task: TaskModel, progress_tracker: EnrichmentProgressTracker) -> Dict[str, Any]
    def process_bulk_enrichment_batch(self, parts: List[PartModel], supplier: str, capabilities: List[str]) -> Dict[str, Any]
    def get_parts_for_bulk_enrichment(self, supplier_filter: str, offset: int, limit: int) -> List[PartModel]
```

**Migration from monolithic**:
- Extract `handle_bulk_enrichment()` → `handle_bulk_enrichment()`
- Extract `_handle_bulk_enrichment_paginated()` → `handle_bulk_enrichment_paginated()`
- Extract `_process_bulk_enrichment_batch()` → `process_bulk_enrichment_batch()`
- Use repositories for all database operations

### 9. EnrichmentCoordinatorService (Orchestration)
**Location**: `/MakerMatrix/services/system/enrichment_coordinator_service.py`
**Purpose**: Main coordinator that orchestrates all enrichment services
**Dependencies**: All above services, CSVImportConfigRepository

```python
class EnrichmentCoordinatorService:
    def __init__(self, 
                 part_enrichment_service: PartEnrichmentService,
                 datasheet_handler_service: DatasheetHandlerService,
                 image_handler_service: ImageHandlerService,
                 bulk_enrichment_service: BulkEnrichmentService,
                 csv_import_config_repository: CSVImportConfigRepository):
        self.part_enrichment_service = part_enrichment_service
        self.datasheet_handler_service = datasheet_handler_service
        self.image_handler_service = image_handler_service
        self.bulk_enrichment_service = bulk_enrichment_service
        self.csv_import_config_repository = csv_import_config_repository
    
    def route_enrichment_task(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]
    def get_csv_import_config(self) -> dict
    def create_progress_tracker(self, progress_callback=None) -> EnrichmentProgressTracker
```

**Migration from monolithic**:
- Extract `_get_csv_import_config()` → `get_csv_import_config()`
- Create task routing logic
- Coordinate all services

## Dependency Injection Strategy

### Service Registry
Create a centralized service registry for dependency injection:

```python
# /MakerMatrix/services/system/enrichment_service_registry.py
class EnrichmentServiceRegistry:
    def __init__(self):
        self._services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        # Initialize in dependency order
        self._services['file_system'] = FileSystemService(config)
        self._services['data_mapper'] = EnrichmentDataMapper(supplier_data_mapper)
        self._services['progress_tracker'] = EnrichmentProgressTracker()
        self._services['supplier_integration'] = SupplierIntegrationService(supplier_config_service)
        self._services['datasheet_handler'] = DatasheetHandlerService(...)
        self._services['image_handler'] = ImageHandlerService(...)
        self._services['part_enrichment'] = PartEnrichmentService(...)
        self._services['bulk_enrichment'] = BulkEnrichmentService(...)
        self._services['coordinator'] = EnrichmentCoordinatorService(...)
    
    def get_service(self, service_name: str):
        return self._services.get(service_name)
```

### Integration Points
Update existing integration points to use the new coordinator:

```python
# In task handlers or route handlers
enrichment_registry = EnrichmentServiceRegistry()
coordinator = enrichment_registry.get_service('coordinator')
result = coordinator.route_enrichment_task(task, progress_callback)
```

## Migration Implementation Plan

### Phase 1: Create Foundation Services (Low Risk)
1. **FileSystemService** - No external dependencies
2. **EnrichmentDataMapper** - Only depends on SupplierDataMapper
3. **EnrichmentProgressTracker** - Standalone observer pattern

**Testing**: Unit tests for each service independently
**Validation**: File operations, data transformation, progress tracking

### Phase 2: Create Handler Services (Medium Risk)
1. **SupplierIntegrationService** - Depends on SupplierConfigService
2. **DatasheetHandlerService** - Depends on repositories and file system
3. **ImageHandlerService** - Depends on file system and supplier integration

**Testing**: Integration tests with mock dependencies
**Validation**: Datasheet downloads, image processing, supplier API calls

### Phase 3: Create Core Services (High Risk)
1. **PartEnrichmentService** - Core business logic
2. **BulkEnrichmentService** - Batch processing logic

**Testing**: Comprehensive integration tests
**Validation**: Full enrichment workflows, bulk operations

### Phase 4: Create Coordinator and Integration (Highest Risk)
1. **EnrichmentCoordinatorService** - Orchestrates all services
2. **EnrichmentServiceRegistry** - Dependency injection
3. Update route handlers to use coordinator
4. Remove monolithic file

**Testing**: End-to-end integration tests
**Validation**: All existing functionality preserved

## Testing Strategy

### Unit Testing
Each service will have comprehensive unit tests:
- Mock all external dependencies
- Test all public methods
- Validate error handling
- Test edge cases

### Integration Testing
Test service composition and interaction:
- Test service registry initialization
- Test service communication
- Test shared dependencies
- Test error propagation

### End-to-End Testing
Validate complete workflows:
- Full part enrichment flows
- Bulk enrichment operations
- Datasheet and image processing
- Error scenarios and recovery

### Performance Testing
Ensure no performance degradation:
- Benchmark before/after refactoring
- Monitor memory usage
- Test concurrent operations
- Validate file I/O performance

## Repository Integration

### Database Operations Migration
All database operations will be moved to repositories during refactoring:

```python
# Before (monolithic - repository violation)
session = next(get_session())
try:
    part = session.exec(select(PartModel).where(PartModel.id == part_id)).first()
    session.add(part)
    session.commit()
finally:
    session.close()

# After (modular - repository compliant)
class PartEnrichmentService(BaseService):
    def enrich_part(self, part_id: str):
        with self.get_session() as session:
            part = self.part_repository.get_by_id(session, part_id)
            updated_part = self.part_repository.update(session, part)
            return updated_part
```

### Repository Methods Required
- **DatasheetRepository**: All methods already created in Step 12.6
- **PartRepository**: Enhanced methods already created in Step 12.6
- **CategoryRepository**: Association methods already created in Step 12.6
- **CSVImportConfigRepository**: All methods already created in Step 12.6

## Error Handling Strategy

### Service-Level Error Handling
Each service will have consistent error handling:
- Wrap external API calls in try/catch
- Log errors with context
- Return structured error responses
- Provide fallback mechanisms

### Cross-Service Error Propagation
- Use result objects for service communication
- Implement circuit breaker pattern for external services
- Provide error aggregation in coordinator
- Maintain transaction consistency

## Configuration Management

### Service Configuration
Each service will receive configuration through dependency injection:
- File paths for FileSystemService
- API timeouts for SupplierIntegrationService
- Processing limits for BulkEnrichmentService
- Feature flags for optional functionality

### Environment-Specific Configuration
Support different configurations for different environments:
- Development: Local file paths, debug logging
- Testing: Mock services, in-memory storage
- Production: Production paths, optimized settings

## Rollback Strategy

### Incremental Rollback
If issues are discovered, services can be rolled back incrementally:
1. Revert to coordinator service
2. Revert individual services to monolithic methods
3. Complete rollback to original monolithic file

### Feature Flags
Implement feature flags to switch between old and new implementations:
- `USE_MODULAR_ENRICHMENT`: Enable/disable new services
- `USE_LEGACY_DATASHEET_HANDLER`: Fallback to old datasheet handling
- `USE_LEGACY_BULK_ENRICHMENT`: Fallback to old bulk processing

## Success Metrics

### Code Quality Metrics
- **Lines of Code**: Reduce from 1,843 to ~1,000-1,200 total (distributed across services)
- **Cyclomatic Complexity**: Reduce average complexity by 50%
- **Repository Compliance**: Eliminate all 32 repository violations
- **Test Coverage**: Maintain or increase current test coverage

### Performance Metrics
- **Response Time**: Maintain or improve current response times
- **Memory Usage**: Monitor memory consumption
- **Throughput**: Maintain or improve bulk processing throughput
- **Error Rate**: Maintain or improve current error rates

### Maintainability Metrics
- **Service Size**: Each service 100-350 lines maximum
- **Dependency Count**: Minimize cross-service dependencies
- **Interface Complexity**: Simple, focused service interfaces
- **Documentation**: Comprehensive service documentation

## Timeline and Milestones

### Week 1: Foundation Services
- Create FileSystemService, EnrichmentDataMapper, EnrichmentProgressTracker
- Implement unit tests
- Validate basic functionality

### Week 2: Handler Services
- Create SupplierIntegrationService, DatasheetHandlerService, ImageHandlerService
- Implement integration tests
- Validate file operations and API interactions

### Week 3: Core Services
- Create PartEnrichmentService, BulkEnrichmentService
- Implement comprehensive tests
- Validate core business logic

### Week 4: Coordinator and Integration
- Create EnrichmentCoordinatorService and registry
- Update route handlers
- Remove monolithic file
- Final validation and testing

## Conclusion

This modular architecture plan provides a systematic approach to breaking up the monolithic enrichment_task_handlers.py file into 9 focused services. The plan ensures:

1. **Preservation of Functionality**: All existing functionality is preserved
2. **Architectural Compliance**: All repository violations are resolved
3. **Maintainability**: Code becomes more modular and testable
4. **Extensibility**: New features can be added without modifying existing services
5. **Risk Mitigation**: Incremental implementation with rollback capabilities

The key to success is following the phased implementation approach, comprehensive testing at each stage, and maintaining clear service boundaries with proper dependency injection.