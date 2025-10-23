"""
Test Fixtures Package

Provides reusable pytest fixtures for integration testing.
"""

from .test_database import (
    test_db_path,
    test_engine,
    test_session,
    test_db_with_schema,
    test_static_files_dir,
    cleanup_test_databases,
)

from .test_data_generators import (
    create_test_roles,
    create_test_users,
    create_test_api_keys,
    create_test_categories,
    create_test_locations,
    create_test_parts,
    create_test_allocations,
    create_test_datasheet_files,
    create_test_image_files,
    populate_test_database,
)

__all__ = [
    # Database fixtures
    "test_db_path",
    "test_engine",
    "test_session",
    "test_db_with_schema",
    "test_static_files_dir",
    "cleanup_test_databases",
    # Data generators
    "create_test_roles",
    "create_test_users",
    "create_test_api_keys",
    "create_test_categories",
    "create_test_locations",
    "create_test_parts",
    "create_test_allocations",
    "create_test_datasheet_files",
    "create_test_image_files",
    "populate_test_database",
]
