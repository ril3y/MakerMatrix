from sqlmodel import Session, SQLModel
from MakerMatrix.models.models import engine
from sqlalchemy import inspect



# Dependency that will provide a session to FastAPI routes
def get_session() -> Session:
    with Session(engine) as session:

        yield session


# Function to create tables in the SQLite database
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

from sqlalchemy import event

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
