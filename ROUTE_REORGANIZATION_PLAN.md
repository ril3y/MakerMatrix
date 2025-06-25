# MakerMatrix Route Reorganization Plan

## Overview
This document outlines the plan to reorganize and consolidate duplicate routes in the MakerMatrix API.

## Major Issues Identified

### 1. Duplicate Endpoints
- User registration: 2 identical endpoints
- Supplier capabilities: 3 different endpoints  
- Supplier testing: 2 endpoints
- Available suppliers: 2 endpoints
- Parts listing: 2 identical endpoints in same router
- Location deletion preview: 2 endpoints (one deprecated)

### 2. Conflicting Route Files
- `printer_routes.py` and `modern_printer_routes.py` both mounted at `/printer`
- Preview functionality split between printer routes and preview routes

### 3. Scattered Functionality
- Enrichment capabilities spread across CSV, Task, and Supplier routes
- Supplier configuration split between supplier_routes and supplier_config_routes
- Import functionality scattered across CSV, Task, and Parts routes

## Proposed Reorganization

### Phase 1: Remove Direct Duplicates
1. **User Registration**
   - DELETE: `/auth/users/register` endpoint from auth_routes.py
   - KEEP: `/users/register` in user_routes.py
   
2. **Parts Listing**
   - DELETE: `/api/parts/all_parts/` endpoint
   - KEEP: `/api/parts/get_all_parts`
   
3. **Location Preview**
   - DELETE: `/locations/preview-delete/{location_id}` (deprecated)
   - KEEP: `/locations/preview-location-delete/{location_id}`
   
4. **Modern Printer Routes**
   - DELETE: `modern_printer_routes.py` file entirely if empty/conflicting

### Phase 2: Consolidate Supplier Management

#### Supplier Routes (`/api/suppliers`)
**Purpose**: Supplier operations and data retrieval
- Discovery endpoints (list available, configured, dropdown)
- Supplier information and schemas
- Part search and data retrieval operations
- OAuth support

#### Supplier Config Routes (`/api/supplier-config`)
**Purpose**: Supplier configuration management only
- CRUD operations for configurations
- Credential management
- Import/Export configurations
- DELETE: Test endpoint (use supplier routes instead)
- DELETE: Capabilities endpoint (use supplier routes instead)

### Phase 3: Consolidate Enrichment System

#### Create New Enrichment Routes (`/api/enrichment`)
**Purpose**: Centralized enrichment management
- Move all enrichment endpoints from CSV routes
- Move enrichment task creation from task routes
- Standardize enrichment queue management
- Unified enrichment capabilities endpoint

### Phase 4: Simplify CSV Import

#### CSV Routes (`/api/import`)
**Purpose**: File import operations only
- Preview CSV/XLS files
- Import with order tracking
- Parser information
- DELETE: Available suppliers endpoint
- DELETE: All enrichment endpoints (moved to enrichment routes)

### Phase 5: Consolidate Preview System

#### Preview Routes (`/api/preview`)
**Purpose**: All preview operations
- Move printer preview endpoints from printer_routes.py
- Consolidate all label preview functionality
- Support multiple preview formats

### Phase 6: Clean Up Task Routes

#### Task Routes (`/api/tasks`)
**Purpose**: Background task management
- Core task CRUD operations
- Task monitoring and statistics
- Worker management
- Quick task creation (simplified)
- DELETE: Enrichment capability endpoints (moved to enrichment routes)

## New Route Structure

```
/api/
├── auth/               # Authentication only
│   ├── login
│   ├── logout
│   └── refresh
├── users/              # User management
├── roles/              # Role management
├── parts/              # Part CRUD operations
├── locations/          # Location management
├── categories/         # Category management
├── suppliers/          # Supplier operations
│   ├── {name}/search
│   ├── {name}/part/{number}
│   └── {name}/test
├── supplier-config/    # Supplier configuration
│   ├── suppliers/
│   └── credentials/
├── import/             # File import (CSV/XLS)
│   ├── preview
│   └── import
├── enrichment/         # Centralized enrichment
│   ├── capabilities/
│   ├── queue/
│   └── tasks/
├── tasks/              # Background tasks
├── printer/            # Printer operations
├── preview/            # All preview operations
├── analytics/          # Analytics and reporting
├── activity/           # Activity logging
├── ai/                 # AI integration
├── rate-limits/        # Rate limiting
├── utility/            # Utility operations
└── ws/                 # WebSocket endpoints
```

## Implementation Steps

### Step 1: Create New Route Files
1. Create `enrichment_routes.py` for centralized enrichment
2. Update imports and dependencies

### Step 2: Move Endpoints
1. Move enrichment endpoints from CSV to enrichment routes
2. Move preview endpoints from printer to preview routes
3. Consolidate supplier capabilities to supplier routes

### Step 3: Update Frontend
1. Update all API calls to use new endpoints
2. Update service files
3. Test all functionality

### Step 4: Remove Deprecated Code
1. Remove duplicate endpoints
2. Remove empty/conflicting route files
3. Clean up unused imports

### Step 5: Update Tests
1. Remove old tests for deleted endpoints
2. Create new tests for reorganized endpoints
3. Ensure all tests pass

## Backward Compatibility

For critical endpoints that are being moved, consider:
1. Adding temporary redirects
2. Deprecation warnings in responses
3. Grace period before removal

## Benefits

1. **Clearer API Structure**: Each route file has a single, clear purpose
2. **Reduced Duplication**: No more multiple endpoints doing the same thing
3. **Better Maintainability**: Easier to find and update functionality
4. **Improved Performance**: Less code to load and maintain
5. **Consistent Naming**: Standardized endpoint patterns

## Testing Strategy

1. Create comprehensive test suite before changes
2. Test each phase independently
3. Run full integration tests after each phase
4. Frontend testing for all API changes
5. Load testing for critical endpoints