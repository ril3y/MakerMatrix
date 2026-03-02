# Contributing to MakerMatrix

We welcome contributions! Whether it's bug reports, feature requests, code contributions, or documentation improvements.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/MakerMatrix.git`
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Set up your development environment (see below)

## Development Setup

### Backend (Python 3.12+)

```bash
python3 -m venv venv_test
source venv_test/bin/activate  # Windows: venv_test\Scripts\activate
pip install -r requirements.txt
pip install -r dev-requirements.txt
```

### Frontend (Node 18+)

```bash
cd MakerMatrix/frontend
npm ci
```

### Running the Development Server

```bash
# Recommended: uses the TUI development manager
python dev_manager.py

# Or manually:
# Terminal 1 - Backend
uvicorn MakerMatrix.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 - Frontend
cd MakerMatrix/frontend && npm run dev
```

## Code Quality Standards

### Backend

- **Formatting**: Black with 120-character line length
- **Type checking**: mypy
- **Linting**: Pylint

```bash
black --check MakerMatrix/
mypy MakerMatrix/
pylint MakerMatrix/
```

### Frontend

- **Zero warnings policy**: ESLint must produce 0 warnings
- **Formatting**: Prettier
- **Type safety**: Strict TypeScript (no `any` types)

```bash
cd MakerMatrix/frontend
npm run quality       # Run all checks
npm run quality:fix   # Auto-fix all issues
```

## Testing

### Backend Tests

```bash
pytest                                    # Unit tests (excludes integration)
pytest tests/test_specific_file.py        # Single file
pytest -m integration                     # Integration tests only
pytest --cov=MakerMatrix tests/           # With coverage
```

### Frontend Tests

```bash
cd MakerMatrix/frontend
npm run test:run       # Unit tests (single run)
npm run test:coverage  # With coverage
npm run test:e2e       # Playwright E2E tests
```

## Architecture

The backend follows a layered architecture:

```
Routes → Services → Repositories → Models → Database
```

- **routers/**: FastAPI route handlers
- **services/data/**: Business logic
- **services/system/**: Infrastructure services
- **repositories/**: Data access layer
- **models/**: SQLModel database models

The frontend uses:
- **Zustand** for state management (`src/store/`)
- **React Query** for server state (`@tanstack/react-query`)
- **Axios** services in `src/services/`
- **Zod** for validation (`src/schemas/`)

## Pull Request Guidelines

1. Keep PRs focused on a single change
2. Add tests for new functionality
3. Ensure all checks pass (`npm run quality` and `pytest`)
4. Update documentation if adding/changing features
5. Write clear commit messages describing the "why"

## Reporting Issues

Use [GitHub Issues](https://github.com/ril3y/MakerMatrix/issues) to report bugs or request features. Include:
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (OS, browser, Python/Node versions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
