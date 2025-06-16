# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

#### Backend API
```bash
python -m MakerMatrix.main
```
Application runs on `http://localhost:57891` with Swagger UI at `/docs`.

#### Frontend Development Server
```bash
cd MakerMatrix/frontend
npm install
npm run dev
```
Frontend development server runs on `http://localhost:5173` by default.

### Testing
```bash
# Run all tests (excludes integration tests by default)
pytest

# Run specific test categories
pytest -m integration          # Integration tests only
pytest -m "not integration"    # Unit tests only

# Run with coverage
pytest --cov=MakerMatrix

# Run repository tests specifically
python run_repository_tests.py

# Test individual modules
pytest MakerMatrix/tests/integration_tests/test_auth.py
pytest MakerMatrix/unit_tests/test_parts_repository.py
```

### Virtual Environment
- Use `venv_test` to run python
- Always use the venv_test for running python

### Database Setup
- Database is created automatically on first run
- Default admin user: `admin` / `Admin123!`
- Run `python MakerMatrix/scripts/setup_admin.py` to recreate default users

### Task-Based Enrichment System Testing
```bash
# Test task-based enrichment functionality
pytest MakerMatrix/tests/integration_tests/test_part_enrichment_task.py -v
pytest MakerMatrix/tests/integration_tests/test_task_api_integration.py -v

# Test specific task functionality
pytest MakerMatrix/tests/integration_tests/test_part_enrichment_task.py::test_part_enrichment_task_with_real_part -v
pytest MakerMatrix/tests/integration_tests/test_task_api_integration.py::test_part_enrichment_api_endpoint -v

# Test all task-related functionality
pytest MakerMatrix/tests/integration_tests/ -k "task" -v
```

### Task Management API Endpoints for Development
```bash
# Quick task creation endpoints
POST /api/tasks/quick/part_enrichment     # Enrich individual part
POST /api/tasks/quick/datasheet_fetch     # Fetch part datasheet  
POST /api/tasks/quick/image_fetch         # Fetch part images
POST /api/tasks/quick/bulk_enrichment     # Bulk enrich multiple parts
POST /api/tasks/quick/csv_enrichment      # Enrich CSV imported parts
POST /api/tasks/quick/price_update        # Update part prices

# Task monitoring and management
GET /api/tasks/                           # List tasks with filtering
GET /api/tasks/{task_id}                  # Get specific task details
POST /api/tasks/{task_id}/cancel          # Cancel running task
GET /api/tasks/stats/summary              # Get task system statistics
GET /api/tasks/worker/status              # Get task worker status

# Task capabilities system
GET /api/tasks/capabilities/suppliers     # Get all supplier capabilities
GET /api/tasks/capabilities/suppliers/{supplier_name}  # Get specific supplier capabilities
GET /api/tasks/capabilities/find/{capability_type}     # Find suppliers with capability
```

### Database Session Management for Tasks
- Tasks use proper `Session(engine)` management for database operations
- Always use `with Session(engine) as session:` pattern in task handlers
- Repository classes require `engine` parameter: `PartRepository(engine)`
- Avoid direct engine usage in tasks - use repositories for database operations
- Ensure proper session commit/rollback in task error handling

### Enhanced Parser Integration Patterns
```python
# Task handlers should use enhanced parsers for supplier-specific operations
from MakerMatrix.parsers.enhanced_parsers import get_enhanced_parser
from MakerMatrix.parsers.capabilities import CapabilityType

# Get enhanced parser for supplier
parser = get_enhanced_parser(supplier)
if parser and parser.supports_capability(CapabilityType.FETCH_PRICING):
    pricing_result = await parser.fetch_pricing(part)
```

### Order File Import Support
- **CSV files**: LCSC, DigiKey, and other CSV formats via text-based endpoints
- **XLS files**: Mouser Electronics order files via file upload endpoints  
- **Libraries**: pandas, openpyxl, xlrd for Excel file support
- **API endpoints**: `/api/csv/preview-file` and `/api/csv/import-file` for file uploads
- **Frontend**: Modular import system with supplier-specific components
- **Test files**: `@MakerMatrix/tests/mouser_xls_test/` contains Mouser XLS test file

### Coding Guidelines
- Always use pytest to test code
- Make sure we update tests if we need to make them simpler, we don't keep creating new files
- Use task-based architecture for long-running operations (enrichment, CSV processing)
- Implement proper progress tracking with WebSocket updates for user feedback
- Follow role-based security patterns for task creation and management
- When changing the API code, always keep @api.md up to date.

### Printer Testing Notes
- only use 12mm tape for printer tests