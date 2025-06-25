# Route Reorganization Status

## Completed Tasks ✅

### Phase 1: Remove Direct Duplicates
1. **User Registration**
   - ✅ Removed `/auth/users/register` from auth_routes.py
   - ✅ Kept `/users/register` in user_routes.py

2. **Parts Listing**
   - ✅ Removed `/api/parts/all_parts/` endpoint
   - ✅ Kept `/api/parts/get_all_parts`

3. **Location Preview**
   - ✅ Removed deprecated `/locations/preview-delete/{location_id}`
   - ✅ Kept `/locations/preview-location-delete/{location_id}`

4. **Modern Printer Routes**
   - ✅ Deleted `modern_printer_routes.py` file
   - ✅ Updated imports in main.py
   - ✅ Updated __init__.py
   - ✅ Deleted test file

### Phase 2: Enrichment Consolidation
1. **Created Enrichment Routes**
   - ✅ Created `/api/enrichment/` route structure
   - ✅ Moved capability discovery endpoints
   - ✅ Created task creation endpoints
   - ✅ Added queue management endpoints

2. **Removed from Task Routes**
   - ✅ Removed `/capabilities/suppliers`
   - ✅ Removed `/capabilities/suppliers/{supplier_name}`
   - ✅ Removed `/capabilities/find/{capability_type}`

3. **Removed from CSV Routes**
   - ✅ Removed `/available-suppliers`
   - ✅ Removed all enrichment endpoints
   - ✅ Cleaned up broken function bodies

### Phase 3: Supplier Cleanup
1. **Removed Duplicates from Config Routes**
   - ✅ Removed `/suppliers/{supplier_name}/test`
   - ✅ Removed `/suppliers/{supplier_name}/capabilities`

2. **Fixed Imports**
   - ✅ Fixed enrichment_routes.py imports
   - ✅ Fixed routers __init__.py

## Remaining Tasks 📋

### Immediate Tasks
1. **Frontend Updates**
   - Update TasksManagement.tsx to use `/api/enrichment/capabilities`
   - Update supplier services to use correct endpoints
   - Update CSV import service

2. **Remove Old Tests**
   - test_supplier_configuration_api.py (likely has failures)
   - test_task_api_integration.py (enrichment endpoints)
   - test_csv_import.py (enrichment functionality)

3. **Write New Tests**
   - Test enrichment_routes.py endpoints
   - Test consolidated supplier endpoints
   - Test updated CSV import

### Next Phase Tasks
1. **Create Import Routes**
   - Consolidate CSV and file imports
   - Move backup/restore functionality
   - Standardize import responses

2. **Reorganize Supplier Routes**
   - Create registry vs operations separation
   - Move OAuth to dedicated section
   - Standardize response formats

3. **Configuration Centralization**
   - Create configuration_routes.py
   - Move all config endpoints
   - Standardize config patterns

## Current Route Structure

```
/api/
├── auth/               # ✅ Cleaned - removed duplicate registration
├── users/              # ✅ Has registration endpoint
├── parts/              # ✅ Removed duplicate listing
├── locations/          # ✅ Removed deprecated preview
├── categories/         # No changes needed
├── suppliers/          # Has test & capabilities (keeping these)
├── config/             # ✅ Removed duplicate test & capabilities  
├── csv/                # ✅ Removed enrichment & available-suppliers
├── enrichment/         # ✅ NEW - Centralized enrichment
├── tasks/              # ✅ Removed enrichment capabilities
├── printer/            # ✅ Removed modern_printer_routes
└── ... (other routes unchanged)
```

## Frontend Files to Update

1. **High Priority**
   - `src/components/tasks/TasksManagement.tsx`
   - `src/services/supplier.service.ts`
   - `src/services/task.service.ts`
   - `src/services/csv-import.service.ts`

2. **New Services Needed**
   - `src/services/enrichment.service.ts`

## API Endpoint Changes Summary

### Removed Endpoints
- `POST /auth/users/register` → Use `/users/register`
- `GET /api/parts/all_parts/` → Use `/api/parts/get_all_parts`
- `GET /locations/preview-delete/{id}` → Use `/locations/preview-location-delete/{id}`
- `GET /api/csv/available-suppliers` → Use `/api/suppliers/`
- `GET /api/tasks/capabilities/*` → Use `/api/enrichment/capabilities/*`
- `POST /api/config/suppliers/{name}/test` → Use `/api/suppliers/{name}/test`
- `GET /api/config/suppliers/{name}/capabilities` → Use `/api/suppliers/{name}/capabilities`

### New Endpoints
- `GET /api/enrichment/capabilities`
- `GET /api/enrichment/capabilities/{supplier_name}`
- `GET /api/enrichment/capabilities/find/{capability_type}`
- `POST /api/enrichment/tasks/part`
- `POST /api/enrichment/tasks/bulk`
- `GET /api/enrichment/queue/status`
- `POST /api/enrichment/queue/cancel/{task_id}`
- `POST /api/enrichment/queue/cancel-all`

## Next Immediate Action

1. Commit current changes
2. Update frontend to use new enrichment endpoints
3. Remove/update failing tests
4. Test the application end-to-end