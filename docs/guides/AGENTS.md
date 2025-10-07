# Repository Guidelines

## Project Structure & Module Organization
- `MakerMatrix/` hosts the FastAPI backend: `routers/` publish HTTP endpoints, `services/` hold orchestration logic, and `repositories/` encapsulate SQLModel CRUD while `models/` share schemas.
- `MakerMatrix/main.py` boots the ASGI app, seeds default roles, suppliers, and printers, and wires dependency providers from `dependencies/`.
- Tests live in `MakerMatrix/tests/`, with quick checks in `unit_tests/`, cross-service flows in `integration_tests/`, and fixtures in `conftest.py`.
- The Vite/React frontend sits in `MakerMatrix/frontend/`, keeping UI code in `src/`, static assets in `public/`, and Playwright specs under `tests/`.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` (add `requirements-dev.txt` when you need QA tools) sets up backend dependencies inside a virtualenv.
- `uvicorn MakerMatrix.main:app --reload` runs the API locally with hot reload and bootstrap seeding.
- `pytest` executes the full backend test suite; narrow scope with `pytest -m "not integration"` while iterating.
- `npm install` inside `MakerMatrix/frontend/` pulls UI dependencies; `npm run dev` starts the Vite dev server, `npm run build` compiles production bundles, and `npm run test:run` / `npm run test:e2e` cover unit and Playwright suites.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indents, snake_case functions, PascalCase classes, and explicit type hints on public interfaces.
- Keep FastAPI routers thin—delegate validation and decisions to service and repository layers; share utilities from `utils/` where reuse matters.
- TypeScript modules export PascalCase components, camelCase hooks prefixed with `use`, and colocated Tailwind helpers; run `npm run lint` before pushing.

## Testing Guidelines
- Prefer unit coverage near the code under test; mirror backend updates in `tests/unit_tests/` and broader behaviours in `tests/integration_tests/`.
- Track regressions with `pytest --cov=MakerMatrix`, and refresh MSW handlers when API contracts shift.
- Frontend behavior belongs in `src/__tests__/` (Vitest) and `frontend/tests` (Playwright); align filenames with the component or page under test.

## Commit & Pull Request Guidelines
- Use Conventional Commits, e.g., `feat: add printer queue route`, keeping subjects imperative and under 72 characters.
- PRs should call out scope, linked tickets, schema or data risks, and the verification commands you ran (`pytest`, `npm run test:run`, `npm run test:e2e`).
- Attach screenshots or recordings for visible UI changes, request reviews from the owning area, and wait for green CI before merging.
