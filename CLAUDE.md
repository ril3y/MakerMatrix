# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

#### Backend API
```bash
python -m MakerMatrix.main
```
Application runs on `http://localhost:8080` with Swagger UI at `/docs`.

#### Frontend Development Server
```bash
cd MakerMatrix/frontend
npm install
npm run dev
```
Frontend development server runs on `http://localhost:5173` by default.

### Development Environment

- The back end and front end auto restart on save.

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
- Use `venv_test` to run python (fresh venv with all dependencies)
- Always use the venv_test for running python
- Includes aiohttp for async HTTP requests and supplier API clients

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
- We never create any test by individual tests in the @MakerMatrix/tests/ dir and use pytest
- Use task-based architecture for long-running operations (enrichment, CSV processing)
- Implement proper progress tracking with WebSocket updates for user feedback
- Follow role-based security patterns for task creation and management
- When changing the API code, always keep @api.md up to date.

### Supplier Implementation Guidelines

#### JSON Response Safety Pattern
**CRITICAL**: All supplier implementations must use defensive null checking when handling JSON API responses to prevent `'NoneType' object has no attribute 'get'` errors.

**Required Pattern:**
```python
# Always use this pattern in all supplier implementations
data = await response.json() or {}  # Handle case where response.json() returns None
nested_data = data.get("SomeKey", {}) or {}  # Handle case where nested keys are None
```

**Background:** API responses can return `{"key": null}` or the `response.json()` call itself can return `None`. This causes runtime errors when calling `.get()` on `None` objects.

**Examples:**
```python
# ✅ CORRECT - Safe pattern used consistently
async def test_connection(self):
    async with session.post(url, json=data) as response:
        if response.status == 200:
            data = await response.json() or {}  # Prevent None
            search_results = data.get("SearchResults", {}) or {}  # Prevent nested None
            count = search_results.get("NumberOfResult", 0)  # Safe to call .get()

# ❌ INCORRECT - Vulnerable to None errors  
async def test_connection(self):
    data = await response.json()  # Could be None
    search_results = data.get("SearchResults")  # Could return None
    count = search_results.get("NumberOfResult", 0)  # CRASH if search_results is None
```

**Architecture Decision:** This pattern is implemented at the individual supplier level rather than in the BaseSupplier abstract class because:
- Each supplier API has different response structures and error conditions
- Supplier-specific handling is more maintainable and debuggable
- The pattern is simple and explicit: `or {}` after any JSON parsing
- Avoids over-abstraction while maintaining safety

**Code Review Checklist:**
- [ ] All `response.json()` calls have `or {}` null safety
- [ ] All `.get()` calls on potentially null nested data have `or {}` safety
- [ ] Test connection methods handle API response edge cases
- [ ] Authentication methods use the same defensive patterns

### Printer Testing Notes
- only use 12mm tape for printer tests

### Dead Code Analysis and Cleanup

#### Overview
The project uses automated dead code detection to identify unused code that can be safely removed to improve maintainability and reduce codebase size.

#### Tools Used
- **Python**: `vulture` - Static analysis tool for finding unused Python code
- **TypeScript/React**: `ts-unused-exports` - Finds unused exports in TypeScript projects

#### Running Dead Code Analysis

##### Automated Analysis (Recommended)
```bash
# Run comprehensive dead code analysis for both Python and TypeScript
python scripts/dead_code_analysis.py
```

This script will:
1. Run vulture analysis on Python code with configured filters
2. Run ts-unused-exports analysis on TypeScript/React code
3. Generate a comprehensive report with findings
4. Provide recommendations for cleanup

##### Manual Analysis Commands

**Python Analysis:**
```bash
# Basic vulture analysis
source venv_test/bin/activate && vulture MakerMatrix/ --config vulture.toml

# With specific confidence level and sorting
source venv_test/bin/activate && vulture MakerMatrix/ --min-confidence 80 --sort-by-size
```

**TypeScript Analysis:**
```bash
# From frontend directory
cd MakerMatrix/frontend
npx ts-unused-exports tsconfig.json --excludePathsFromReport="node_modules;dist;coverage;__tests__;tests"
```

#### Configuration Files

**Python (vulture.toml):**
- Located at project root
- Configures minimum confidence level (80%)
- Excludes virtual environments, cache directories
- Defines ignore patterns for false positives
- Specifies common test fixture patterns to ignore

**TypeScript (.ts-unused-exports.json):**
- Located in MakerMatrix/frontend/
- Excludes test files and directories
- Allows unused enums and types (common in TypeScript)
- Defines specific files/exports to ignore (public APIs, re-exports)

#### False Positives and Considerations

**Common False Positives:**
- Test fixtures used by pytest (setup_*, clean_*, sample_*)
- Code used in decorators or middleware (@app.middleware, @pytest.fixture)
- Dynamic imports or string-based imports
- Public API exports meant for external use
- Code used in configuration files
- Database event handlers (connection_record parameter)

**Before Removing Code:**
1. **Review carefully** - Ensure code isn't used dynamically
2. **Check tests** - Run full test suite after removal
3. **Verify imports** - Check for string-based or dynamic imports
4. **Consider API** - Don't remove public API exports
5. **Check configuration** - Some code may be used in config files

#### Cleanup Process

1. **Generate Report:**
   ```bash
   python scripts/dead_code_analysis.py
   ```

2. **Review Findings:**
   - Check `dead_code_analysis_report.md` for detailed results
   - Identify genuine dead code vs. false positives

3. **Remove Dead Code:**
   - Start with high-confidence items (90%+ confidence)
   - Remove unused imports first (safer)
   - Remove unused functions/classes after careful review

4. **Test After Removal:**
   ```bash
   # Run full test suite
   pytest
   
   # Run frontend tests
   cd MakerMatrix/frontend && npm test
   ```

5. **Update Configuration:**
   - Add new false positives to `vulture.toml` or `.ts-unused-exports.json`
   - Commit configuration updates separately

#### Integration with Development Workflow

**Pre-commit Checks:**
Consider adding dead code analysis to pre-commit hooks for large refactoring PRs.

**Regular Maintenance:**
- Run dead code analysis monthly or before major releases
- Include in CI/CD pipeline for long-running feature branches
- Review findings during code review process

**Documentation Updates:**
- Update this section when new tools or patterns are added
- Document any project-specific false positive patterns
- Keep configuration files in sync with project structure changes