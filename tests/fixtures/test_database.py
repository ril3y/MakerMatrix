"""
Test Database Fixtures

Provides pytest fixtures for creating isolated test databases.
These fixtures ensure tests NEVER touch production data.
"""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Generator
import pytest
from sqlalchemy import create_engine, event
from sqlmodel import Session, SQLModel

# Import all models to register them with SQLModel metadata
from MakerMatrix.models.rate_limiting_models import *
from MakerMatrix.models.supplier_config_models import *
from MakerMatrix.models.part_models import *
from MakerMatrix.models.location_models import *
from MakerMatrix.models.category_models import *
from MakerMatrix.models.tool_models import *
from MakerMatrix.models.system_models import *
from MakerMatrix.models.user_models import *
from MakerMatrix.models.order_models import *
from MakerMatrix.models.task_models import *
from MakerMatrix.models.ai_config_model import *
from MakerMatrix.models.printer_config_model import *
from MakerMatrix.models.csv_import_config_model import *
from MakerMatrix.models.label_template_models import *
from MakerMatrix.models.part_metadata_models import *
from MakerMatrix.models.backup_models import *
from MakerMatrix.models.tag_models import *
from MakerMatrix.models.project_models import *
from MakerMatrix.models.part_allocation_models import *
from MakerMatrix.models.api_key_models import *
from MakerMatrix.models.enrichment_requirement_models import *
from MakerMatrix.models.task_security_model import *


# Test database directory (isolated from production)
TEST_DB_DIR = Path("/tmp/makermatrix_test_dbs")


@pytest.fixture(scope="function")
def test_db_path() -> Generator[Path, None, None]:
    """
    Generate a unique test database path for each test.

    Returns:
        Path: Unique database file path in temporary directory

    Cleanup:
        Removes the test database file after test completion
    """
    # Create test database directory if it doesn't exist
    TEST_DB_DIR.mkdir(parents=True, exist_ok=True)

    # Generate unique database filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    db_filename = f"test_backup_{timestamp}_{unique_id}.db"
    db_path = TEST_DB_DIR / db_filename

    yield db_path

    # Cleanup: Remove test database file
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete test database {db_path}: {e}")


@pytest.fixture(scope="function")
def test_engine(test_db_path: Path):
    """
    Create a SQLAlchemy engine for the test database.

    Args:
        test_db_path: Path to the test database file

    Returns:
        Engine: SQLAlchemy engine configured for test database
    """
    sqlite_url = f"sqlite:///{test_db_path}"

    engine = create_engine(
        sqlite_url, echo=False, connect_args={"check_same_thread": False}  # Set to True for SQL debugging
    )

    # Enable foreign key constraints (important for data integrity tests)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """
    Create a database session for the test database.

    Args:
        test_engine: SQLAlchemy engine for test database

    Yields:
        Session: Database session for executing queries
    """
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def test_db_with_schema(test_engine, test_db_path: Path):
    """
    Create a test database with all tables initialized.

    This fixture creates an empty database with the complete schema
    but no data. Use test data generator fixtures to populate it.

    Args:
        test_engine: SQLAlchemy engine for test database
        test_db_path: Path to the test database file

    Returns:
        tuple: (engine, db_path) for use in tests
    """
    # Create all tables from SQLModel metadata
    SQLModel.metadata.create_all(test_engine)

    return test_engine, test_db_path


def cleanup_test_databases(older_than_hours: int = 24):
    """
    Cleanup old test databases from the test directory.

    This function is useful for preventing test database buildup
    in local development environments or CI/CD runners.

    Args:
        older_than_hours: Delete databases older than this many hours
    """
    if not TEST_DB_DIR.exists():
        return

    from datetime import timedelta

    cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

    for db_file in TEST_DB_DIR.glob("test_backup_*.db"):
        try:
            # Check file modification time
            file_mtime = datetime.fromtimestamp(db_file.stat().st_mtime)

            if file_mtime < cutoff_time:
                db_file.unlink()
                print(f"Cleaned up old test database: {db_file.name}")
        except Exception as e:
            print(f"Warning: Could not cleanup {db_file.name}: {e}")


@pytest.fixture(scope="session", autouse=True)
def cleanup_before_tests():
    """
    Automatically cleanup old test databases before test session starts.

    This ensures a clean state before running integration tests.
    """
    cleanup_test_databases(older_than_hours=1)  # Clean up databases older than 1 hour
    yield
    # Optional: Cleanup after all tests (uncomment if desired)
    # cleanup_test_databases(older_than_hours=0)  # Clean up all test databases


@pytest.fixture(scope="function")
def test_static_files_dir(test_db_path: Path) -> Generator[Path, None, None]:
    """
    Create temporary directories for test static files (datasheets, images).

    Args:
        test_db_path: Path to test database (used for unique naming)

    Yields:
        Path: Base directory for static files (contains datasheets/ and images/)

    Cleanup:
        Removes all static file directories after test completion
    """
    # Create base static files directory
    static_base = TEST_DB_DIR / f"static_{test_db_path.stem}"
    static_base.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    datasheets_dir = static_base / "datasheets"
    images_dir = static_base / "images"
    datasheets_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)

    yield static_base

    # Cleanup: Remove all static files and directories
    if static_base.exists():
        try:
            shutil.rmtree(static_base)
        except Exception as e:
            print(f"Warning: Could not delete static files directory {static_base}: {e}")
