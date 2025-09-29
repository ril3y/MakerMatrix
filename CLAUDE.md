# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Primary Development Tool: Development Manager

**IMPORTANT**: Use the development manager for all development activities:

MakerMatrix Development Manager API Summary

  The dev_manager.py exposes a REST API on port 8765 for programmatic control of both backend and frontend services.

  Base URL

  http://localhost:8765

  Key Endpoints

  Service Control

  # Start/Stop Services
  POST /backend/start     # Start FastAPI backend
  POST /backend/stop      # Stop FastAPI backend  
  POST /backend/restart   # Restart backend (async)
  POST /frontend/start    # Start Vite dev server
  POST /frontend/stop     # Stop Vite dev server
  POST /frontend/restart  # Restart frontend (async)
  POST /frontend/build    # Run production build
  POST /all/stop          # Stop both services

  Monitoring

  # Get Status
  GET /status             # Current service status, PIDs, URLs
  GET /logs?service=all&limit=100  # Get recent logs
  POST /backend/health    # Health check backend

  # Log Management  
  POST /logs/clear        # Clear log buffers

  Configuration

  # Mode Switching
  POST /mode              # Body: {"https": true/false}

  # Auto-restart Control
  POST /auto-restart      # Body: {"backend": true, "frontend": false}

  Documentation

  GET /docs               # Full API documentation
  GET /                   # API summary + current status

  Example Usage

  # Check if services are running
  curl http://localhost:8765/status

  # Restart backend after code changes
  curl -X POST http://localhost:8765/backend/restart

  # Get recent error logs
  curl "http://localhost:8765/logs?service=errors&limit=50"

  # Switch to HTTP mode
  curl -X POST http://localhost:8765/mode -H "Content-Type: application/json" -d '{"https": false}'

  # Enable frontend auto-restart
  curl -X POST http://localhost:8765/auto-restart -H "Content-Type: application/json" -d '{"frontend": true}'

  Configuration via Environment Variables

  DEV_MANAGER_API_ENABLED=true     # Enable/disable API (default: true)
  DEV_MANAGER_API_HOST=0.0.0.0     # API host (default: 0.0.0.0)  
  DEV_MANAGER_API_PORT=8765        # API port (default: 8765)
  DEV_MANAGER_API_LOG_REQUESTS=true # Log API requests (default: true)

  The API is designed for automation, CI/CD integration, and programmatic control of the development environment.

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
- never try to start the server directly use dev_manager.py to do this
- @dev_manager.py has an api to use to get logs and status stop and start the backend we should always use this.
- when writing tests always write them in the test dir and use pytest this way we have them in the future.