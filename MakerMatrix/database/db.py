from typing import Generator

from sqlmodel import Session, SQLModel
from MakerMatrix.models.models import engine
from sqlalchemy import inspect, event
from sqlalchemy import event


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
