# Gemini Project Configuration

This file provides configuration and context for the Gemini AI assistant to understand and effectively assist with this project.

## Project Overview

- **Name:** MakerMatrix
- **Description:** A part inventory management system with label printing capabilities.
- **Tech Stack:**
    - **Backend:** Python with FastAPI
    - **Frontend:** Vite-based (likely React or Vue)
    - **Database:** SQLAlchemy-compatible (e.g., PostgreSQL, MySQL, SQLite)

## Key Directories

- `MakerMatrix/`: The main Python package containing all backend source code.
- `MakerMatrix/routers/`: FastAPI routers for different API endpoints.
- `MakerMatrix/services/`: Business logic and services.
- `MakerMatrix/models/`: Pydantic and SQLAlchemy models.
- `MakerMatrix/repositories/`: Data access layer.
- `MakerMatrix/frontend/`: Contains the frontend application source code.
- `tests/`: Backend tests.

## Commands

### Running the Application

- **Backend:**
  ```bash
  python -m MakerMatrix.main
  ```
- **Frontend (from `MakerMatrix/frontend` directory):**
  ```bash
  npm install
  npm run dev
  ```

### Testing

- **Backend:**
  ```bash
  pytest
  ```
- **Frontend (from `MakerMatrix/frontend` directory):**
  ```bash
  npm test
  ```

### Linting and Formatting

- **Backend (assumed):**
  ```bash
  black .
  isort .
  ```
- **Frontend (from `MakerMatrix/frontend` directory):**
  ```bash
  npm run lint
  ```

## Project Conventions

- **API:** The API is RESTful and uses JWT for authentication. Role-based access control is in place.
- **Code Style:** Follow standard Python (PEP 8) and TypeScript/JavaScript best practices. Use the existing code as a style guide.
- **Commits:** Use conventional commit messages (e.g., `feat:`, `fix:`, `refactor:`).
