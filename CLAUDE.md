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

### Coding Guidelines
- Always use pytest to test code
- Make sure we update tests if we need to make them simpler, we don't keep creating new files