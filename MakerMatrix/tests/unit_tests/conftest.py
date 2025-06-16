# Unit test configuration - no database setup
# This conftest.py prevents the database setup from the main tests/conftest.py
# from affecting our pure unit tests

import pytest

# Override the init_db fixture to prevent database setup in unit tests
@pytest.fixture(scope="session", autouse=True)
def init_db():
    """Empty fixture to override the main conftest.py database setup."""
    pass