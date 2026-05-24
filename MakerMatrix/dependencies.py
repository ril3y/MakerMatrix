"""
FastAPI dependency functions for service injection.

This module provides dependency functions that create service instances
at request time, enabling proper dependency injection and testability.
"""

from typing import Generator
from sqlalchemy import Engine

from MakerMatrix.models.models import engine as global_engine
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.services.data.tag_service import TagService
from MakerMatrix.services.data.tool_service import ToolService
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService


def get_engine() -> Engine:
    """
    Get the database engine for the current request.

    This can be overridden in tests to provide a test engine.

    Returns:
        Engine: The SQLAlchemy engine instance
    """
    return global_engine


def get_part_service() -> Generator[PartService, None, None]:
    """
    Get a PartService instance for the current request.

    Uses get_engine() which can be overridden in tests.

    Yields:
        PartService: A new PartService instance
    """
    engine = get_engine()
    yield PartService(engine_override=engine)


def get_location_service() -> Generator[LocationService, None, None]:
    """
    Get a LocationService instance for the current request.

    Uses get_engine() which can be overridden in tests.

    Yields:
        LocationService: A new LocationService instance
    """
    engine = get_engine()
    yield LocationService(engine_override=engine)


def get_category_service() -> Generator[CategoryService, None, None]:
    """
    Get a CategoryService instance for the current request.

    Uses get_engine() which can be overridden in tests.

    Yields:
        CategoryService: A new CategoryService instance
    """
    engine = get_engine()
    yield CategoryService(engine_override=engine)


def get_tag_service() -> Generator[TagService, None, None]:
    """
    Get a TagService instance for the current request.

    Yields:
        TagService: A new TagService instance
    """
    engine = get_engine()
    yield TagService(engine_override=engine)


def get_tool_service() -> Generator[ToolService, None, None]:
    """
    Get a ToolService instance for the current request.

    Yields:
        ToolService: A new ToolService instance
    """
    engine = get_engine()
    yield ToolService(engine_override=engine)


def get_supplier_config_service() -> Generator[SupplierConfigService, None, None]:
    """
    Get a SupplierConfigService instance for the current request.

    SupplierConfigService does not accept an engine override (uses repository
    pattern with module-level engine), but this provider lets routes use the
    Depends() pattern uniformly and allows tests to substitute a mock.

    Yields:
        SupplierConfigService: A new SupplierConfigService instance
    """
    yield SupplierConfigService()


def get_backup_repository():
    """
    Get a BackupRepository instance bound to the current engine.

    Yields:
        BackupRepository: A new BackupRepository instance
    """
    from MakerMatrix.repositories.backup_repository import BackupRepository
    engine = get_engine()
    yield BackupRepository(engine)


def get_task_service():
    """
    Get the singleton TaskService instance.

    TaskService is a module-level singleton (it owns the worker loop and
    in-memory task registry). This provider returns that singleton so routes
    can use the standard Depends() pattern and tests can override it.

    Yields:
        TaskService: The module-level task_service singleton
    """
    from MakerMatrix.services.system.task_service import task_service
    yield task_service
