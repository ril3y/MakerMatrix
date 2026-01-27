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
npm run test:run          # Run tests once
npm run test:e2e          # Playwright E2E tests
npm run test:coverage     # With coverage

# Code quality
npm run lint              # ESLint (0 warnings policy)
npm run lint:fix          # Auto-fix
npm run type-check        # TypeScript strict check
npm run quality           # All checks
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
- **models/**: SQLModel database models (ORM + Pydantic validation combined)

### Supplier Integration Pattern
Suppliers follow a plugin architecture in `suppliers/`:
- `base.py` - Abstract interface defining capabilities and credential fields
- Each supplier (digikey.py, mouser.py, lcsc.py, etc.) implements the interface
- `registry.py` - Supplier registration
- Web scraping uses Playwright (`scrapers/web_scraper.py`)

### Frontend Architecture
- **State**: Zustand stores in `src/store/`
- **API**: Axios services in `src/services/` with React Query
- **Components**: Feature-based organization in `src/components/`
- **Validation**: Zod schemas in `src/schemas/`

### Background Tasks
- APScheduler for job scheduling
- Task implementations in `tasks/` (enrichment, backup, pricing updates)
- Progress tracking via WebSocket (`services/system/websocket_service.py`)

### Key Patterns
- **Dependency Injection**: FastAPI `Depends()` for database sessions and auth guards
- **Real-time Updates**: WebSocket-based synchronization
- **Enrichment Engine**: Orchestrates supplier data fetching and standardization

## Test Organization

Backend tests are in three locations (per pytest.ini):
- `MakerMatrix/tests/`
- `MakerMatrix/integration_tests/`
- `MakerMatrix/unit_tests/`

Test markers: `integration` (opt-in), `critical` (security tests)

Frontend tests:
- Unit tests: `MakerMatrix/frontend/src/__tests__/`
- E2E tests: `MakerMatrix/frontend/tests/`

## Code Quality Standards

This codebase maintains 100% type safety:
- **Backend**: Black formatting (120 chars), mypy strict, Pylint
- **Frontend**: ESLint with 0 warnings policy, TypeScript strict mode, Prettier

Pre-commit hooks enforce formatting via Husky + lint-staged.

## Key Files

- `MakerMatrix/main.py` - FastAPI entry point with lifespan manager
- `MakerMatrix/dependencies.py` - Dependency injection setup
- `MakerMatrix/database/db.py` - SQLAlchemy/SQLModel setup
- `MakerMatrix/auth/guards.py` - Route protection
- `dev_manager.py` - Development server manager with TUI

## Environment Variables

Key variables (see `.env.example`):
- `JWT_SECRET_KEY` - Required for production
- `DATABASE_URL` - Default: SQLite
- `DIGIKEY_CLIENT_ID/SECRET`, `MOUSER_API_KEY` - Supplier APIs (optional)
- `HTTPS_ENABLED` - Set to `true` for HTTPS mode
