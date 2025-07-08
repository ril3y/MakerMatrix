# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Primary Development Tool: Development Manager

**IMPORTANT**: Use the development manager for all development activities:

```bash
# Start the Rich TUI development manager (recommended)
python dev_manager.py
```

The development manager provides:
- **Rich TUI interface** for managing both backend and frontend
- **Auto-restart functionality** with file watching (watchdog)
- **Real-time log monitoring** and health checks
- **HTTPS/HTTP mode switching** 
- **Process management** and port conflict resolution
- **Development server coordination**

### Running the Application

#### Backend API (via dev_manager.py)
```bash
# Primary method - use development manager
python dev_manager.py

# Manual method (if needed)
source venv_test/bin/activate
python -m MakerMatrix.main
```

Application runs on:
- **HTTP**: `http://localhost:8080` 
- **HTTPS**: `https://localhost:8443`
- **Swagger UI**: `/docs` on either protocol

#### Frontend Development Server (via dev_manager.py)
```bash
# Primary method - use development manager
python dev_manager.py

# Manual method (if needed)
cd MakerMatrix/frontend
npm install
npm run dev
```

Frontend development server runs on `http://localhost:5173` by default.

#### HTTPS Setup

**Required for DigiKey OAuth and enhanced security:**

```bash
# Quick setup with self-signed certificate
python scripts/setup_https.py

# Better setup with mkcert (no browser warnings)
python scripts/setup_https.py --method mkcert

# Start with HTTPS
./start_https.sh
```

See `scripts/HTTPS_SETUP.md` for comprehensive HTTPS configuration guide.

### Development Environment

- **Auto-restart**: Both backend and frontend auto-restart on file changes
- **File watching**: Powered by watchdog library with 5-second debounce
- **Process management**: Automatic port conflict resolution
- **Health monitoring**: Real-time service health checks
- **Log aggregation**: Centralized logging in development manager

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

### Advanced Frontend Testing Infrastructure

The project includes comprehensive testing capabilities:

```bash
# Frontend test suite
cd MakerMatrix/frontend

# Unit tests with Jest
npm test

# E2E tests with Playwright
npm run test:e2e

# Visual regression tests
npm run test:visual

# Accessibility tests
npm run test:a11y

# Performance tests with Lighthouse
npm run test:performance

# Bundle size analysis
npm run analyze

# Run all test suites
npm run test:ci
```

**Testing Infrastructure:**
- **Jest** for unit testing with React Testing Library
- **Playwright** for E2E testing with multiple browser configurations
- **Visual regression testing** with screenshot comparisons
- **Accessibility testing** with @axe-core integration
- **Performance testing** with Lighthouse automation
- **MSW (Mock Service Worker)** for API mocking
- **Bundle analysis** with webpack-bundle-analyzer
- **Coverage reporting** with Istanbul

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
POST /api/tasks/quick/file_import_enrichment  # File import enrichment (CSV/XLS)
POST /api/tasks/quick/price_update        # Update part prices
POST /api/tasks/quick/database_backup     # Database backup (admin only)

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

### Virtual Environment

- **Always use `venv_test`** for running Python commands
- **Fresh virtual environment** with all dependencies
- **Includes critical dependencies**:
  - `aiohttp` for async HTTP requests and supplier API clients
  - `rich` for terminal UI components
  - `blessed` for terminal handling
  - `watchdog` for file system monitoring
  - `langchain` ecosystem for AI integration
  - `pandas`, `openpyxl`, `xlrd` for file processing
  - `psutil` for process management
  - `playwright` for E2E testing

### Database Setup

- **Auto-creation**: Database is created automatically on first run
- **Default admin user**: `admin` / `Admin123!`
- **Reset users**: `python MakerMatrix/scripts/setup_admin.py`
- **Session management**: Use `Session(engine)` pattern in tasks
- **Repository pattern**: Always use repositories for database operations

### Database Access Architecture (CRITICAL)

**ONLY REPOSITORIES interact with the database - NEVER services or other layers directly.**

**Repository Pattern for ALL Database Operations:**

```python
# CORRECT: Only repositories handle database sessions
from MakerMatrix.database.database import Session, engine
from MakerMatrix.repository.parts_repository import PartRepository

# In task handlers, services, routes - always use repositories
with Session(engine) as session:
    repository = PartRepository(engine)
    # Repository handles ALL database operations
    # Proper session commit/rollback handled automatically
```

**Services use BaseService for consistency but delegate to repositories:**
```python
# CORRECT: Services use repositories, not direct database access
class PartService(BaseService):
    def get_part(self, part_id: str):
        with self.get_session() as session:
            return self.part_repo.get_by_id(session, part_id)  # Repository handles DB
```

**Architecture Rules:**
- **ONLY repositories** handle database sessions and SQL operations
- **Services** use repositories and provide business logic
- **Routes** use services and handle HTTP concerns  
- **Tasks** use repositories directly (with session management)
- **Never bypass repositories** for database operations

**VIOLATION**: Any code outside `/repositories/` that uses `session.add()`, `session.query()`, `session.commit()`, etc.

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

**Enhanced file import system:**

- **CSV files**: LCSC, DigiKey, and other CSV formats
- **XLS files**: Mouser Electronics order files via file upload
- **Libraries**: `pandas`, `openpyxl`, `xlrd` for Excel file support
- **Primary endpoint**: `POST /api/import/file` (supports CSV/XLS with enrichment)
- **Legacy endpoints**: `/api/csv/import-file` (still supported)
- **Frontend**: Modular import system with supplier-specific components
- **Test files**: `MakerMatrix/tests/mouser_xls_test/` contains test files

**New Import Workflow:**
```bash
# Use the unified import endpoint
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "supplier_name=lcsc" \
  -F "file=@order.csv" \
  -F "enable_enrichment=true" \
  -F "enrichment_capabilities=get_part_details,fetch_datasheet" \
  http://localhost:8080/api/import/file
```

## Current Cleanup Process

**IMPORTANT**: The project is currently undergoing a comprehensive cleanup initiative:

### Active Cleanup Status
- **Phase**: Phase 1 - Analysis and Discovery  
- **Current Step**: Step 5 - Manual Code Review - Frontend Services
- **Progress**: 4/30 steps completed (13.3%)
- **Started**: 2025-01-08
- **Branch**: `before_prd`

### Cleanup Tools and Commands

```bash
# Run comprehensive dead code analysis
python scripts/dead_code_analysis.py

# Manual Python analysis
source venv_test/bin/activate && vulture MakerMatrix/ --config vulture.toml

# Manual TypeScript analysis
cd MakerMatrix/frontend
npx ts-unused-exports tsconfig.json --excludePathsFromReport="node_modules;dist;coverage;__tests__;tests"
```

### Cleanup Configuration Files

- **`vulture.toml`**: Python dead code detection configuration
- **`.ts-unused-exports.json`**: TypeScript unused exports configuration
- **`cleanup.prd`**: Comprehensive cleanup process document

### Major Cleanup Findings

**Backend Issues Identified:**
- Database session management duplicated ~50+ times (400+ lines)
- CRUD patterns duplicated across 6 services (~500 lines)
- Supplier functionality fragmented across 3 files
- PartService too large (879 lines needs splitting)
- Missing base abstractions causing massive duplication

**Expected Impact**: 2,100+ lines reduction (20-30% of backend code)

### Cleanup Best Practices

**Before Removing Code:**
1. **Review carefully** - Ensure code isn't used dynamically
2. **Run tests** - Execute full test suite after removal
3. **Check imports** - Verify no string-based or dynamic imports
4. **Consider API** - Don't remove public API exports
5. **Update configuration** - Add false positives to config files

## CI/CD Pipeline

**GitHub Actions Workflow**: `.github/workflows/frontend-tests.yml`

**Automated Testing:**
- **Unit tests** with Jest and React Testing Library
- **E2E tests** with Playwright across multiple browsers
- **Visual regression testing** with screenshot comparisons
- **Accessibility testing** with axe-core
- **Bundle size analysis** with size limits
- **Performance testing** with Lighthouse
- **Coverage reporting** with threshold enforcement

**Build Configuration:**
- **`pyproject.toml`**: Python project configuration with Hatchling
- **Modern build system** with dependency management
- **Test artifact collection** for debugging

## Configuration Management

### Environment Files
- **`.env`**: Main environment configuration
- **`.env.https`**: HTTPS-specific configuration
- **Configuration loading**: Automatic environment detection

### Configuration Files
- **`mcp_config.json`**: MCP (Message Communication Protocol) configuration
- **`ai_config.json`**: AI integration configuration
- **`digikey_tokens/`**: DigiKey API token management

### AI Integration Configuration

```bash
# AI configuration endpoints
GET /api/ai/config                # Get current AI configuration
PUT /api/ai/config                # Update AI configuration
POST /api/ai/chat                 # Chat with AI assistant
POST /api/ai/test                 # Test AI connection
```

**Supported AI Providers:**
- **Ollama** (default): Local LLM hosting
- **OpenAI**: GPT models
- **Anthropic**: Claude models

## Development Scripts Organization

### Core Scripts (`/scripts/`)
- **`dead_code_analysis.py`**: Comprehensive dead code analysis
- **`setup_https.py`**: HTTPS certificate setup and configuration
- **`check_api_consistency.py`**: API consistency validation
- **`HTTPS_SETUP.md`**: Complete HTTPS setup guide

### Development Scripts (`/MakerMatrix/scripts/dev/`)
- Development utility scripts
- Testing and validation tools
- Legacy file organization in `old_root_files/`

## Coding Guidelines

### Core Principles
- **Always use pytest** for testing - never create individual test files
- **Use task-based architecture** for long-running operations
- **Implement proper progress tracking** with WebSocket updates
- **Follow role-based security patterns** for task creation and management
- **Keep @api.md up to date** when changing API code

### Code Quality Standards
- **No custom task creation** - use predefined quick task endpoints for security
- **Proper error handling** with defensive programming
- **Session management** following established patterns
- **Dead code elimination** as part of regular maintenance

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

## Hardware Integration

### Printer Testing Notes
- **Only use 12mm tape** for printer tests
- **Label printing**: Use `POST /api/printer/print_label` endpoint
- **QR code printing**: Use `POST /api/printer/print_qr` endpoint
- **Configuration**: Use `POST /api/printer/config` for printer setup

## Production Deployment

### Backup System
```bash
# Create comprehensive backup (admin only)
POST /api/tasks/quick/database_backup

# Download backup
GET /api/utility/backup/download/{backup_filename}

# List available backups
GET /api/utility/backup/list
```

**Backup Contents:**
- SQLite database file
- All enrichment datasheet files
- All enrichment image files
- Backup metadata JSON file

### Static File Management
- **Sophisticated file handling** via `services/static/`
- **Datasheet storage** organization
- **Image storage** with proper URL generation
- **Upload system** with size limits and format validation

## Security Considerations

### Task Security
- **No custom task creation** - security risk removed
- **Predefined task types** only via quick endpoints
- **Role-based access control** for task management
- **User permission validation** for all task operations

### API Security
- **JWT authentication** for all endpoints
- **Role-based permissions** with granular access control
- **Input validation** and sanitization
- **Rate limiting** and request validation

## WebSocket Integration

### Real-time Updates
- **Task monitoring**: `WS /ws/tasks` for real-time task updates
- **Admin monitoring**: `WS /ws/admin` for system statistics
- **Progress tracking**: Real-time progress updates during long operations
- **Connection management**: Automatic reconnection and heartbeat

## Troubleshooting

### Common Issues
1. **Port conflicts**: Use development manager for automatic resolution
2. **HTTPS setup**: Use `scripts/setup_https.py` for proper configuration
3. **Database issues**: Check session management patterns
4. **Task failures**: Monitor via WebSocket endpoints
5. **Import failures**: Check file format and supplier configuration

### Debug Commands
```bash
# Check system health
GET /api/utility/get_counts

# Check task worker status
GET /api/tasks/worker/status

# Check backup status
GET /api/utility/backup/status

# Test AI connection
POST /api/ai/test
```

## Documentation References

- **API Documentation**: `api.md` - comprehensive API reference
- **Cleanup Process**: `cleanup.prd` - current cleanup initiative
- **HTTPS Setup**: `scripts/HTTPS_SETUP.md` - complete HTTPS guide
- **Frontend Testing**: GitHub Actions workflow configuration
- **Dead Code Analysis**: `scripts/dead_code_analysis.py` and configuration files

---

**Note**: This documentation reflects the current state of the project during the active cleanup process. Always refer to the latest cleanup.prd for current cleanup status and priorities.