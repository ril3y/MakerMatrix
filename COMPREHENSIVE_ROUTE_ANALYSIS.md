# Comprehensive Route Analysis and Reorganization Plan

## Current Route Structure Issues

### 1. **Supplier Management Chaos**
We have THREE different places handling supplier functionality:

#### `/api/suppliers/` (supplier_routes.py)
- Discovery endpoints (list available, configured, dropdown)
- Info and schema endpoints
- Testing endpoint (with rate limiting)
- OAuth support
- Part search and data retrieval

#### `/api/config/` (supplier_config_routes.py)
- CRUD for supplier configurations
- Testing endpoint (DUPLICATE)
- Capabilities endpoint (DUPLICATE)
- Credential management
- Import/Export

#### `/api/csv/` (csv_routes.py)
- Available suppliers endpoint (DUPLICATE)
- Parser-to-supplier mapping
- Enrichment capabilities (now moved)

### 2. **Enrichment Scattered Everywhere**
Previously spread across:
- CSV routes: Enhanced import, bulk enrich, queue management
- Task routes: Capability discovery, task creation
- Parts routes: Auto-enrichment on add
- Supplier routes: Capability info

### 3. **Task System Confusion**
- Generic task management in task_routes.py
- Enrichment-specific tasks mixed in
- CSV import tasks
- Duplicate quick task creation endpoints

### 4. **Import/Export Mess**
- CSV import in csv_routes.py
- Supplier config import/export in supplier_config_routes.py
- Parts backup/export in utility_routes.py
- No unified approach

## Proposed Clean Architecture

### Core Principles
1. **Single Responsibility**: Each route file handles ONE domain
2. **No Duplicates**: Each functionality exists in exactly ONE place
3. **Clear Naming**: Route prefixes match their purpose
4. **Logical Grouping**: Related functionality stays together

### New Route Structure

```
/api/
├── auth/                    # Authentication ONLY
│   ├── login
│   ├── logout
│   └── refresh
│
├── users/                   # User management
│   ├── register
│   ├── {id}
│   └── profile
│
├── parts/                   # Part CRUD operations
│   ├── search
│   ├── {id}
│   └── bulk-operations
│
├── inventory/               # Inventory-specific operations
│   ├── locations/
│   ├── categories/
│   └── stock-adjustments/
│
├── suppliers/               # Supplier operations & discovery
│   ├── registry/           # Available suppliers
│   │   ├── list
│   │   └── {name}/info
│   ├── operations/         # Supplier API operations
│   │   ├── {name}/search
│   │   ├── {name}/fetch-part
│   │   └── {name}/fetch-pricing
│   └── oauth/              # OAuth flows
│
├── configuration/           # ALL configuration management
│   ├── suppliers/          # Supplier configs
│   │   ├── {name}
│   │   └── credentials/
│   ├── csv-import/         # CSV import configs
│   ├── ai/                 # AI configs
│   └── printer/            # Printer configs
│
├── import/                  # ALL import operations
│   ├── csv/
│   │   ├── preview
│   │   └── import
│   ├── excel/
│   └── backup/
│
├── enrichment/              # Centralized enrichment
│   ├── capabilities/
│   ├── tasks/
│   └── queue/
│
├── tasks/                   # Generic background tasks
│   ├── status/
│   ├── worker/
│   └── history/
│
├── printing/                # All printing operations
│   ├── labels/
│   ├── preview/
│   └── printers/
│
├── analytics/               # Reporting and analytics
│   ├── inventory/
│   ├── spending/
│   └── activity/
│
└── system/                  # System utilities
    ├── backup/
    ├── health/
    └── rate-limits/
```

## Detailed Migration Plan

### Phase 1: Supplier Consolidation
1. **Create new structure**:
   - `/api/suppliers/registry/` - Discovery and info
   - `/api/suppliers/operations/` - API operations
   - `/api/configuration/suppliers/` - Config management

2. **Move endpoints**:
   - Test endpoint → operations (keep only one)
   - Capabilities → registry
   - Credentials → configuration
   - Remove all duplicates

### Phase 2: Import System Unification
1. **Create `/api/import/`**:
   - Move CSV import from csv_routes
   - Move backup import from utility_routes
   - Standardize import response format

2. **Separate parsers from import**:
   - Parser info stays with import
   - Parser-to-supplier mapping → enrichment

### Phase 3: Task System Cleanup
1. **Generic tasks in `/api/tasks/`**:
   - Task CRUD
   - Worker management
   - Statistics

2. **Domain-specific task creation**:
   - Enrichment tasks → `/api/enrichment/tasks/`
   - Import tasks → `/api/import/tasks/`
   - Cleanup tasks → `/api/system/maintenance/`

### Phase 4: Configuration Centralization
1. **Move all configs to `/api/configuration/`**:
   - Supplier configs
   - CSV import settings
   - AI configuration
   - Printer settings

2. **Standardize config operations**:
   - GET /{domain}/
   - PUT /{domain}/
   - POST /{domain}/reset

## Breaking Changes & Frontend Updates

### Critical Frontend Changes
1. **Supplier endpoints**:
   - `/api/suppliers/configured` → `/api/suppliers/registry/configured`
   - `/api/config/suppliers/{name}/test` → `/api/suppliers/operations/{name}/test`
   - `/api/csv/available-suppliers` → `/api/suppliers/registry/list`

2. **Enrichment endpoints**:
   - `/api/tasks/capabilities/suppliers` → `/api/enrichment/capabilities`
   - `/api/csv/bulk-enrich` → `/api/enrichment/tasks/bulk`

3. **Import endpoints**:
   - `/api/csv/import` → `/api/import/csv`
   - `/api/csv/preview` → `/api/import/csv/preview`

### Services to Update
1. `supplier.service.ts`
2. `task.service.ts`
3. `csv-import.service.ts`
4. `enrichment.service.ts` (new)

## Implementation Order

### Step 1: Complete Current Cleanup (In Progress)
- [x] Remove duplicate user registration
- [x] Remove duplicate parts listing
- [x] Remove deprecated location preview
- [x] Delete modern_printer_routes
- [x] Create enrichment_routes
- [ ] Remove enrichment from csv_routes (partial)
- [ ] Remove enrichment from task_routes (partial)

### Step 2: Supplier Reorganization
- [ ] Create new supplier route structure
- [ ] Move test endpoint (remove duplicate)
- [ ] Move capabilities endpoint
- [ ] Update supplier_config_routes prefix
- [ ] Update frontend supplier service

### Step 3: Import System
- [ ] Create import_routes.py
- [ ] Move CSV import endpoints
- [ ] Move backup endpoints
- [ ] Create unified import service

### Step 4: Configuration System
- [ ] Create configuration_routes.py
- [ ] Move all config endpoints
- [ ] Standardize config patterns
- [ ] Update frontend config services

### Step 5: Testing
- [ ] Remove old route tests
- [ ] Create new comprehensive tests
- [ ] Test all frontend integrations
- [ ] Load test critical endpoints

## Benefits of Reorganization

1. **Clarity**: Developers know exactly where to find/add functionality
2. **Maintainability**: No more hunting for duplicate endpoints
3. **Performance**: Less code to load, cleaner imports
4. **Consistency**: Standardized patterns across all routes
5. **Scalability**: Easy to add new domains without confusion

## Risk Mitigation

1. **Gradual Migration**: Move one domain at a time
2. **Backward Compatibility**: Add redirects for critical endpoints
3. **Comprehensive Testing**: Test each phase thoroughly
4. **Documentation**: Update API docs with each change
5. **Feature Flags**: Allow toggling between old/new routes

## Next Immediate Steps

1. Finish removing enrichment endpoints from csv_routes and task_routes
2. Fix broken imports in csv_routes
3. Create supplier registry structure
4. Start moving supplier endpoints
5. Update frontend to use new enrichment routes