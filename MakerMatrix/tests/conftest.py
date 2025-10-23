"""
Main Test Configuration - Isolated Database Setup

This configuration ensures all tests use isolated test databases
and never contaminate the main application database.
"""

import pytest
import os
import tempfile
from sqlmodel import SQLModel, Session
from fastapi.testclient import TestClient
from typing import Generator

from MakerMatrix.main import app
from MakerMatrix.tests.test_database_config import (
    TestDatabaseConfig,
    create_isolated_test_engine,
    setup_test_database_with_admin,
)


@pytest.fixture(scope="session")
def test_app():
    """Create a test FastAPI application"""
    return app


@pytest.fixture(scope="session")
def test_client(test_app):
    """Create a test client for the application"""
    return TestClient(test_app)


@pytest.fixture(scope="function")
def isolated_test_engine():
    """
    Create an isolated test database engine for each test function.
    This ensures complete test isolation and prevents database contamination.
    """
    # Create isolated test engine
    test_engine = create_isolated_test_engine(use_memory=False)

    # Setup admin user and roles in test database
    setup_test_database_with_admin(test_engine)

    yield test_engine

    # Cleanup
    test_engine.dispose()


@pytest.fixture(scope="function")
def memory_test_engine():
    """
    Create an in-memory test database engine for fast unit tests.
    """
    test_engine = create_isolated_test_engine(use_memory=True)

    # Setup admin user and roles in test database
    setup_test_database_with_admin(test_engine)

    yield test_engine

    # Cleanup
    test_engine.dispose()


@pytest.fixture(scope="function")
def test_session(isolated_test_engine):
    """
    Create a test database session using the isolated test engine.
    """
    with Session(isolated_test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def memory_test_session(memory_test_engine):
    """
    Create a test database session using the in-memory test engine.
    """
    with Session(memory_test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def test_database_config():
    """
    Create a test database configuration for advanced test scenarios.
    """
    config = TestDatabaseConfig()
    config.create_test_engine(use_memory=False)

    # Setup admin user and roles
    setup_test_database_with_admin(config.test_engine)

    yield config

    # Cleanup
    config.cleanup()


@pytest.fixture(scope="function")
def admin_auth_headers(test_client):
    """
    Create authentication headers for admin user in tests.
    Uses the test client to authenticate against the test database.
    """
    login_data = {"username": "admin", "password": "Admin123!"}
    response = test_client.post("/auth/login", json=login_data)

    if response.status_code != 200:
        pytest.fail(f"Authentication failed: {response.json()}")

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def authenticated_test_client(test_client, admin_auth_headers):
    """
    Create an authenticated test client with admin privileges.
    """
    # Attach headers to client for convenience
    test_client.headers.update(admin_auth_headers)
    return test_client


# Validation fixtures to ensure proper test isolation
@pytest.fixture(scope="session", autouse=True)
def validate_test_isolation():
    """
    Validate that tests are using isolated databases and not the main application database.
    """
    # Check that we're not accidentally using main database
    main_db_path = "makermatrix.db"

    # Get initial size of main database (if it exists)
    initial_size = 0
    if os.path.exists(main_db_path):
        initial_size = os.path.getsize(main_db_path)

    yield

    # After all tests, ensure main database size hasn't changed significantly
    if os.path.exists(main_db_path):
        final_size = os.path.getsize(main_db_path)
        size_change = abs(final_size - initial_size)

        # Allow for small changes (metadata, etc.) but not major data changes
        if size_change > 1024:  # 1KB threshold
            pytest.fail(
                f"Main database size changed by {size_change} bytes during tests. "
                f"This indicates potential database contamination."
            )


@pytest.fixture(scope="function", autouse=True)
def prevent_main_database_import():
    """
    Prevent accidental import of main database engine in tests.
    This fixture runs automatically for all tests.
    """
    import sys

    # Check if any test is trying to import the main database engine
    forbidden_imports = [
        "MakerMatrix.models.models.engine",
    ]

    for module_name in sys.modules.keys():
        if any(forbidden in module_name for forbidden in forbidden_imports):
            # Check if it's being imported in a test context
            if "test_" in module_name or "tests" in module_name:
                pytest.fail(
                    f"Test module {module_name} is importing main database engine. "
                    f"Use isolated test fixtures instead."
                )

    yield
