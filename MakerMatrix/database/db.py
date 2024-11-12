from sqlmodel import Session, SQLModel
from MakerMatrix.models.models import engine


# Dependency that will provide a session to FastAPI routes
def get_session() -> Session:
    return Session(engine)


# Function to create tables in the SQLite database
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
