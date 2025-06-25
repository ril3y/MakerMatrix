# CSV and Task Route Consolidation Plan

## Current Problems

### 1. **CSV Routes Do Too Much**
- Parse CSV files
- Import data
- Create enrichment tasks
- Track progress
- Handle both sync and async operations

### 2. **Multiple Ways to Create Same Tasks**
- CSV import auto-creates enrichment tasks
- Task routes have "quick" endpoints for task creation
- Enrichment routes also create tasks
- No single source of truth

### 3. **Confusing Separation**
- `/csv/import` - Does import + optional task creation
- `/csv/import/with-progress` - Same but with progress
- `/tasks/quick/csv_enrichment` - Just creates task, no import
- Users don't know which to use

## Proposed Clean Architecture

### Import System (`/api/import/`)
**Purpose**: Handle ALL file imports (CSV, Excel, JSON, etc.)

```
/api/import/
├── csv/
│   ├── preview          # Preview CSV content
│   ├── parse            # Parse without importing
│   └── execute          # Import data (sync operation)
├── excel/
│   ├── preview
│   └── execute
└── status/{import_id}   # Check import status
```

**Key Points**:
- Import routes ONLY handle data import
- Return imported part IDs
- NO task creation
- Synchronous operations only

### Task System (`/api/tasks/`)
**Purpose**: Manage ALL background tasks

```
/api/tasks/
├── create               # Generic task creation
├── {task_id}           # Task CRUD
├── templates/          # Task templates
│   ├── enrichment      # Template for enrichment
│   ├── cleanup         # Template for cleanup
│   └── audit           # Template for audit
└── bulk/               # Bulk operations
    └── create          # Create multiple tasks
```

**Key Points**:
- Single endpoint for task creation
- Use templates for common patterns
- Clear async operations

### Enrichment System (`/api/enrichment/`)
**Already created, but refine**:

```
/api/enrichment/
├── capabilities/        # What can be enriched
├── create/             # Create enrichment jobs
│   ├── parts           # Enrich specific parts
│   ├── import          # Enrich an import batch
│   └── supplier        # Enrich by supplier
└── queue/              # Monitor enrichment
```

## Migration Strategy

### Phase 1: Separate Import from Task Creation

1. **Modify CSV Import Endpoints**:
   ```python
   # OLD: /csv/import
   result = import_csv(data)
   if enable_enrichment:
       task = create_enrichment_task(result.part_ids)
   return {**result, "task_id": task.id}
   
   # NEW: /import/csv/execute
   result = import_csv(data)
   return {"import_id": id, "part_ids": result.part_ids}
   ```

2. **Client Handles Orchestration**:
   ```typescript
   // Import CSV
   const importResult = await importService.importCSV(data);
   
   // If enrichment desired, create task
   if (enableEnrichment) {
     const task = await enrichmentService.createImportEnrichment({
       import_id: importResult.import_id,
       part_ids: importResult.part_ids
     });
   }
   ```

### Phase 2: Remove Quick Task Endpoints

1. **Replace Quick Tasks with Templates**:
   ```python
   # OLD: POST /tasks/quick/csv_enrichment
   # OLD: POST /tasks/quick/part_enrichment
   # OLD: POST /tasks/quick/bulk_enrichment
   
   # NEW: POST /tasks/create
   {
     "template": "enrichment",
     "params": {
       "source": "csv_import",
       "part_ids": [...],
       "supplier": "LCSC"
     }
   }
   ```

### Phase 3: Consolidate Progress Tracking

1. **Unified Progress System**:
   - Import progress: `/api/import/status/{import_id}`
   - Task progress: `/api/tasks/{task_id}/progress`
   - WebSocket updates for both

## Endpoint Mapping

### Current → New

**CSV/Import Operations**:
- `POST /csv/import` → `POST /import/csv/execute`
- `POST /csv/import-file` → `POST /import/file/execute`
- `POST /csv/preview` → `POST /import/csv/preview`
- `POST /csv/preview-file` → `POST /import/file/preview`
- `GET /csv/import/progress` → `GET /import/status/{import_id}`

**Task Operations**:
- `POST /tasks/quick/*` → `POST /tasks/create` (with template)
- `POST /csv/import` (enrichment part) → `POST /enrichment/create/import`

**Remove Completely**:
- `/csv/import/with-progress` (use `/import/csv/execute` + status endpoint)
- All `/tasks/quick/*` endpoints
- Task creation logic from CSV routes

## Benefits

1. **Clear Separation of Concerns**:
   - Import: Handles data import only
   - Tasks: Manages background jobs only
   - Enrichment: Handles enrichment logic only

2. **Single Responsibility**:
   - Each route does ONE thing well
   - No more mixed sync/async operations

3. **Better Client Control**:
   - Clients orchestrate workflows
   - More flexibility in how operations are combined

4. **Easier Testing**:
   - Test import without tasks
   - Test tasks without import
   - Mock individual services

5. **Scalability**:
   - Import service can be scaled separately
   - Task workers can be scaled separately
   - Clear boundaries for microservices

## Implementation Steps

### Step 1: Create Import Routes (New File)
```python
# /api/import/
- Create import_routes.py
- Move CSV preview/parse logic
- Remove task creation code
- Return only import results
```

### Step 2: Update Task Routes
```python
# /api/tasks/
- Add template system
- Remove quick endpoints
- Standardize task creation
```

### Step 3: Update Frontend
```typescript
// New flow
1. Import CSV → Get part IDs
2. Create enrichment task with part IDs
3. Monitor both operations separately
```

### Step 4: Deprecate Old Endpoints
- Add deprecation warnings
- Provide migration guide
- Remove after transition period

## Example New Flow

```mermaid
graph LR
    A[Upload CSV] --> B[Preview/Parse]
    B --> C[Import Data]
    C --> D[Return Part IDs]
    D --> E{Enrich?}
    E -->|Yes| F[Create Enrichment Task]
    E -->|No| G[Complete]
    F --> H[Monitor Task Progress]
    H --> G
```

## Summary

This consolidation will:
1. Eliminate ALL duplicate task creation endpoints
2. Separate sync (import) from async (enrichment) operations
3. Create clear, single-purpose route systems
4. Make the API more predictable and maintainable
5. Reduce code duplication significantly