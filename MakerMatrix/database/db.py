import os
from typing import Generator

from sqlmodel import Session, SQLModel
from MakerMatrix.models.models import engine
# Import all model modules to register them with SQLModel metadata
from MakerMatrix.models.rate_limiting_models import *
from MakerMatrix.models.supplier_config_models import *
from MakerMatrix.models.part_models import *
from MakerMatrix.models.location_models import *
from MakerMatrix.models.category_models import *
from MakerMatrix.models.system_models import *
from MakerMatrix.models.user_models import *
from MakerMatrix.models.order_models import *
from MakerMatrix.models.task_models import *
from MakerMatrix.models.ai_config_model import *
from MakerMatrix.models.printer_config_model import *
from MakerMatrix.models.csv_import_config_model import *
from MakerMatrix.models.label_template_models import *
from MakerMatrix.models.part_metadata_models import *
from sqlalchemy import inspect, event

# Database URL for backup and utility operations
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///makermatrix.db")


# Dependency that will provide a session to FastAPI routes
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# Function to create tables in the SQLite database
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)




@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
