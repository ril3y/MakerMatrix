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
