"""
Core Models Module

Minimal models.py containing database engine configuration and shared components.
Domain-specific models have been extracted to separate files for better organization.
"""

from sqlalchemy import create_engine
from sqlmodel import SQLModel

# Import all domain models to ensure they're registered with SQLModel metadata
from .part_models import *
from .location_models import *
from .category_models import *
from .system_models import *
from .part_metadata_models import *
from .user_models import *
from .order_models import *
from .task_models import *
from .ai_config_model import *
from .printer_config_model import *
from .supplier_config_models import *
from .rate_limiting_models import *
from .csv_import_config_model import *

# Create an engine for SQLite
sqlite_file_name = "makermatrix.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(
    sqlite_url, 
    echo=False,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600,
    connect_args={"check_same_thread": False}
)


# Create tables if they don't exist
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)