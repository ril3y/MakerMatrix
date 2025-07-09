"""
Test Database Configuration Module

This module provides isolated database configuration for tests to prevent
contamination of the main application database.
"""

import os
import tempfile
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from typing import Generator

# Import all models to ensure they're registered
import MakerMatrix.models.models


class TestDatabaseConfig:
    """Configuration for test database isolation"""
    
    def __init__(self):
        self.test_db_path = None
        self.test_engine = None
    
    def create_test_engine(self, use_memory: bool = False) -> 'Engine':
        """Create an isolated test database engine"""
        if use_memory:
            test_sqlite_url = "sqlite:///:memory:"
        else:
            test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
            os.close(test_db_fd)  # Close the file descriptor, we just need the path
            test_sqlite_url = f"sqlite:///{self.test_db_path}"
        
        self.test_engine = create_engine(
            test_sqlite_url, 
            echo=False,
            connect_args={"check_same_thread": False}
        )
        
        # Create all tables in the test database
        SQLModel.metadata.create_all(self.test_engine)
        
        return self.test_engine
    
    def cleanup(self):
        """Clean up test database resources"""
        if self.test_engine:
            self.test_engine.dispose()
        
        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except FileNotFoundError:
                pass
    
    def get_test_session(self) -> Generator[Session, None, None]:
        """Get a test database session"""
        if not self.test_engine:
            raise RuntimeError("Test engine not created. Call create_test_engine() first.")
        
        with Session(self.test_engine) as session:
            yield session


def create_isolated_test_engine(use_memory: bool = False) -> 'Engine':
    """
    Create an isolated test database engine.
    
    Args:
        use_memory: If True, use in-memory SQLite database for faster tests
        
    Returns:
        Isolated test database engine
    """
    if use_memory:
        test_sqlite_url = "sqlite:///:memory:"
    else:
        test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(test_db_fd)
        test_sqlite_url = f"sqlite:///{test_db_path}"
    
    test_engine = create_engine(
        test_sqlite_url, 
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables in the test database
    SQLModel.metadata.create_all(test_engine)
    
    return test_engine


def setup_test_database_with_admin(test_engine: 'Engine'):
    """
    Set up test database with default admin user and roles.
    
    Args:
        test_engine: Test database engine
    """
    from MakerMatrix.repositories.user_repository import UserRepository
    from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
    
    # Create user repository with test engine
    user_repo = UserRepository()
    # Override the engine to use test engine
    user_repo.engine = test_engine
    
    # Setup default roles and admin user in test database
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)