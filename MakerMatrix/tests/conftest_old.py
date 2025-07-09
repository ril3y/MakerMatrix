import pytest
import os
import tempfile
from sqlmodel import SQLModel, create_engine
from MakerMatrix.models import user_models, models  # Ensure all models are registered
from MakerMatrix.models.rate_limiting_models import *  # Import rate limiting models
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

@pytest.fixture(scope="session", autouse=True)
def init_db():
    # Create a temporary test database file
    test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(test_db_fd)  # Close the file descriptor, we just need the path
    
    # Create test engine with temporary database
    test_sqlite_url = f"sqlite:///{test_db_path}"
    test_engine = create_engine(test_sqlite_url, echo=False)
    
    # Create tables for all models in test database
    SQLModel.metadata.create_all(test_engine)
    
    # Log tables present after creation
    from sqlalchemy import inspect
    inspector = inspect(test_engine)
    print('Tables after creation:', inspector.get_table_names())
    
    # Setup default roles and admin user in test database
    user_repo = UserRepository()
    # Override the engine in user_repo to use test engine
    user_repo.engine = test_engine
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # Clean up: remove the temporary test database file
    try:
        os.unlink(test_db_path)
    except FileNotFoundError:
        pass

@pytest.fixture
def engine():
    """Create a test engine for individual tests"""
    test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(test_db_fd)
    
    test_sqlite_url = f"sqlite:///{test_db_path}"
    test_engine = create_engine(test_sqlite_url, echo=False)
    
    # Create all tables including rate limiting models
    SQLModel.metadata.create_all(test_engine)
    
    yield test_engine
    
    # Clean up
    try:
        os.unlink(test_db_path)
    except FileNotFoundError:
        pass

@pytest.fixture
def memory_engine():
    """Create an in-memory test engine for fast tests"""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(test_engine)
    return test_engine
