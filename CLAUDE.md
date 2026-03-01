# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MakerMatrix is an electronic parts inventory management system with a FastAPI backend and React/TypeScript frontend. It manages parts, tools, storage locations, supplier integrations, and label printing.

## Build & Development Commands

### Backend (Python 3.12+)
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r dev-requirements.txt  # For development tools

# Start development server (recommended - includes TUI)
python dev_manager.py

# Or manually with uvicorn
uvicorn MakerMatrix.main:app --reload --host 127.0.0.1 --port 8000

# Run tests (excludes integration tests by default)
pytest
pytest tests/test_specific_file.py  # Single test file
pytest -m integration               # Run integration tests
pytest --cov=MakerMatrix tests/     # With coverage

# Code quality
black --check MakerMatrix/          # Formatting check (120 char line length)
mypy MakerMatrix/                   # Type checking
pylint MakerMatrix/                 # Linting
```

### Frontend (Node 18+)
```bash
cd MakerMatrix/frontend

npm ci                    # Install dependencies
npm run dev               # Start Vite dev server (http://localhost:5173)
npm run build             # Production build

# Testing
npm run test:run          # Run tests once (Vitest)
npm run test:e2e          # Playwright E2E tests
npm run test:coverage     # With coverage

# Code quality
npm run lint              # ESLint (0 warnings policy)
npm run lint:fix          # Auto-fix
npm run type-check        # TypeScript check
npm run quality           # All checks (format + lint + type-check)
npm run quality:fix       # Auto-fix all
```

### Docker
```bash
docker build -t makermatrix:latest .
docker-compose up -d      # Access at http://localhost:8080
```

## Architecture

### Layered Backend Structure
```
Routes → Services → Repositories → Models → Database
```

- **routers/**: FastAPI route handlers (parts_routes.py, locations_routes.py, etc.)
- **services/data/**: Business logic (part_service.py, location_service.py)
- **services/system/**: Infrastructure services (enrichment_engine.py, task_service.py)
- **services/printer/**: Label printing (printer_manager_service.py, label_service.py)
- **repositories/**: Data access layer
- **models/**: SQLModel database models (ORM + Pydantic validation combined). Domain models are split across separate files (part_models.py, location_models.py, etc.) but all re-exported via `models/models.py`.

### Database Engine
The SQLAlchemy engine is created in `models/models.py` (not `database/db.py`). The `database/db.py` module imports the engine and provides the `get_session()` dependency and `create_db_and_tables()` setup. SQLite with foreign keys enabled via PRAGMA.

### Dependency Injection
`dependencies.py` provides service factory functions (`get_part_service()`, etc.) that use `get_engine()` which can be overridden in tests. Routes use `Depends()` for services and auth guards.

### Auth System
- `auth/guards.py` - `require_permission()`, `require_admin()`, `secure_all_routes()`
- `auth/dependencies.py` - `get_current_user` JWT dependency
- All routes are secured via `secure_all_routes()` applied in `main.py`
- Default credentials: admin / Admin123!

### Supplier Integration Pattern
Suppliers follow a plugin architecture in `suppliers/`:
- `base.py` - `BaseSupplier` abstract class defining capabilities (`SupplierCapability` enum), credential schemas (`FieldDefinition`), and data types (`PartSearchResult`, `EnrichmentResult`)
- Each supplier implements `BaseSupplier` and uses the `@register_supplier("name")` decorator from `registry.py` for auto-registration
- `registry.py` - `SupplierRegistry` class with factory pattern (`get_supplier()`, `get_available_suppliers()`)
- `enrichment_engine.py` - Supplier-agnostic enrichment orchestrator that works with any registered supplier's capabilities
- Web scraping fallback uses Playwright (`scrapers/web_scraper.py`) for suppliers without APIs
- Current suppliers: digikey, mouser, lcsc, adafruit, seeed_studio, mcmaster_carr, bolt_depot

### Frontend Architecture
- **State**: Zustand stores in `src/store/` (authStore, partsStore, locationsStore, categoriesStore, dashboardStore)
- **API**: Axios services in `src/services/` with React Query (`@tanstack/react-query`). `baseCrud.service.ts` provides a reusable CRUD base class extended by entity-specific services.
- **Components**: Feature-based organization in `src/components/`
- **Validation**: Zod schemas in `src/schemas/`
- **Path alias**: `@/*` maps to `./src/*` (configured in tsconfig.json)

### Background Tasks
- APScheduler for job scheduling
- `tasks/base_task.py` defines the base task pattern; concrete tasks in `tasks/` (enrichment, backup, pricing updates, datasheet download, etc.)
- Progress tracking via WebSocket (`services/system/websocket_service.py`)

## Test Organization

Backend tests are in these locations (per pytest.ini):
- `MakerMatrix/tests/` - Mixed tests (supplier, enrichment, general)
- `MakerMatrix/tests/unit_tests/` - Unit tests (repositories, services, models)
- `MakerMatrix/tests/integration_tests/` - Integration tests (API routes, cross-service, live server)

There is also a top-level `tests/` directory with additional tests (security, supplier, tags, enrichment). These are **not** in the pytest.ini `testpaths` so must be run explicitly: `pytest tests/test_specific.py`.

Test marker: `integration` (opt-in, excluded by default via `addopts = -m "not integration"`)

Frontend tests:
- Unit tests: `MakerMatrix/frontend/src/__tests__/` (Vitest)
- E2E tests: `MakerMatrix/frontend/tests/` (Playwright)

## Code Quality Standards

- **Backend**: Black formatting (120 char line length), mypy, Pylint
- **Frontend**: ESLint with 0 warnings policy, Prettier formatting
- Pre-commit hooks enforce formatting via Husky + lint-staged

## Key Files

- `MakerMatrix/main.py` - FastAPI entry point with lifespan manager (DB setup, auth init, rate limiting, task scheduler)
- `MakerMatrix/models/models.py` - Database engine creation and all model re-exports
- `MakerMatrix/database/db.py` - Session dependency and table creation
- `MakerMatrix/dependencies.py` - Service factory dependency injection
- `MakerMatrix/auth/guards.py` - Route protection (permission-based and admin-only)
- `MakerMatrix/suppliers/base.py` - Supplier plugin interface
- `MakerMatrix/suppliers/registry.py` - Supplier discovery and factory
- `MakerMatrix/services/system/enrichment_engine.py` - Unified enrichment orchestrator
- `dev_manager.py` - Development server manager with TUI

## Environment Variables

Key variables (see `.env.example`):
- `JWT_SECRET_KEY` - Required for production
- `DATABASE_URL` - Default: SQLite (`sqlite:///makermatrix.db`)
- `DIGIKEY_CLIENT_ID/SECRET`, `MOUSER_API_KEY` - Supplier APIs (optional)
- `HTTPS_ENABLED` - Set to `true` for HTTPS mode (requires cert setup via `scripts/setup_https.py`)
