# Developer Technical Insights

This document contains verified technical nuggets about how the MakerMatrix system works internally. All details are verified against the actual codebase.

## Task System Architecture

### Task Registration Process
**Auto-Discovery Pattern:** Tasks are automatically discovered and registered at startup through file-based scanning.

**Verified Implementation:**
- File pattern: Any `*_task.py` file in `/MakerMatrix/tasks/` directory
- Discovery happens in `MakerMatrix/tasks/__init__.py:61` when module is imported
- Each task class must inherit from `BaseTask` and define a `task_type` property
- Registration creates a global `TASK_REGISTRY` dictionary mapping task types to classes
- TaskService then instantiates handlers in `_register_modular_handlers()`

**Code Pattern:**
```python
class MyNewTask(BaseTask):
    @property
    def task_type(self) -> str:
        return "my_new_task"  # This becomes the registry key
```

**Startup Log Pattern:**
```
Registered task: part_enrichment -> PartEnrichmentTask      # From __init__.py discovery
Registered task handler: part_enrichment -> PartEnrichmentTask  # From TaskService registration
```

**To Add New Task:** Simply create `my_new_task.py` in tasks directory - it will auto-register on restart.

## WebSocket Service Architecture

### Dynamic Host Resolution
**Environment-Aware Connection:** WebSocket service intelligently determines connection host based on environment and configuration.

**Verified Implementation in `websocket.service.ts:46-74`:**
1. **VITE_API_URL Override:** If `VITE_API_URL` environment variable is set, parse and use that host/protocol
2. **Development Port Detection:** If on ports 5173, 5174, or 3000, fallback to backend on port 8080 with WS protocol
3. **Protocol Mapping:** HTTPS → WSS, HTTP → WS

**Connection Resolution Order:**
```typescript
if (envApiUrl) {
  // Use parsed VITE_API_URL
} else if (developmentPort) {
  // Force ws://localhost:8080 for dev
} else {
  // Use current page host/protocol
}
```

## Authentication Architecture

### JWT Token Flow
**Stateless Authentication:** System uses JWT tokens with refresh token pattern stored in HTTP-only cookies.

**Verified Endpoints:**
- `POST /api/auth/login` - Form-based login (web UI)
- `POST /api/auth/mobile-login` - JSON login (APIs/mobile)
- `POST /api/auth/refresh` - Refresh expired tokens using cookie
- `GET /api/users/me` - Get current user info with JWT

**Token Storage Pattern:**
- **Access Token:** Stored in localStorage as 'auth_token'
- **Refresh Token:** HTTP-only cookie for security
- **WebSocket Auth:** Token passed as query parameter `?token={jwt}`

## Database Session Management

### Repository Pattern Enforcement
**Critical Architecture Rule:** ONLY repositories interact with database sessions - never services or routes directly.

**Verified Pattern in codebase:**
```python
# CORRECT: Repository handles session
with Session(engine) as session:
    repository = PartRepository(engine)
    return repository.get_by_id(session, part_id)

# VIOLATION: Service/route direct DB access
session.add(model)  # Never do this outside repositories
```

**Session Lifecycle:**
- Repositories receive `Session` object as parameter
- Services use `with Session(engine)` pattern
- Tasks create their own sessions for background work
- Routes delegate all DB operations to services

## Development Environment

### dev_manager.py TUI
**Primary Development Tool:** Rich TUI interface manages both backend and frontend servers with integrated monitoring.

**Verified Features:**
- **Auto-restart:** File watching with 5-second debounce
- **Process Management:** Port conflict resolution and health checks
- **Log Aggregation:** Real-time logs from both servers
- **HTTPS/HTTP Toggle:** Dynamic protocol switching

**Usage Pattern:**
```bash
python dev_manager.py  # Start TUI
# Use keyboard shortcuts in TUI to control services
```

**Log File:** `/home/ril3y/MakerMatrix/dev_manager.log` contains startup and service logs

### Virtual Environment
**Standard Environment:** All Python operations use `venv_test` virtual environment.

**Verified Setup:**
```bash
source venv_test/bin/activate  # Required for all Python commands
python -m MakerMatrix.main     # Backend server
```

## API Response Architecture

### Standardized Response Schema
**Consistent API Responses:** All endpoints return standardized ResponseSchema format.

**Verified Schema in `schemas/response.py`:**
```json
{
  "status": "success|error|warning",
  "message": "Human readable message",
  "data": "Response data (any type)",
  "page": "Page number (pagination)",
  "page_size": "Items per page (pagination)",
  "total_parts": "Total count (pagination)"
}
```

**BaseRouter Pattern:** Routes use `BaseRouter.build_success_response()` and `BaseRouter.build_error_response()` for consistency.

## File Upload System

### Image Upload Workflow
**Two-Step Process:** Images uploaded separately then referenced by URL.

**Verified Workflow:**
1. `POST /utility/upload_image` → Returns `{image_id: "uuid"}`
2. Use URL format: `/utility/get_image/{image_id}.{extension}`
3. Reference in part/location: `"image_url": "/utility/get_image/uuid.png"`

**Security:** JWT authentication required for both upload and retrieval.

## Issues Identified

### Printer/Preview Functionality Problems
**Frontend-Backend API Mismatch:** Frontend calls `/api/printer/preview/*` but preview endpoints moved to `/api/preview/*`.

**Critical Pydantic Schema Error:** Backend crashes with OpenAPI generation:
```
PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema
```

**Verified Issues:**
- `settings.service.ts:40` calls `/api/printer/preview/text` (moved to `/api/preview/text`)
- `settings.service.ts:88` calls `/api/printer/preview/advanced` (moved to `/api/preview/advanced`)
- Backend returns 500 errors on OpenAPI endpoint causing timeouts
- Printer endpoints hanging due to schema generation errors

**Solution Status:** ✅ Fixed - Frontend endpoints updated and missing `/api/preview/advanced` endpoint added

### Add Part Modal Missing Description Field
**Issue:** Description field was missing from the Add Part form despite being supported by the API.

**Verified Problem:**
- `CreatePartRequest` interface includes `description?: string` field
- AddPartModal form state missing `description` property
- No description input field in the UI

**✅ Fixed:**
- Added `description: ''` to form state initialization
- Added description field to form reset function
- Added textarea input field for description after Part Number field
- Used full-width layout with proper styling and placeholder text

---

*This document is maintained as a living reference. All entries are verified against actual codebase implementation.*