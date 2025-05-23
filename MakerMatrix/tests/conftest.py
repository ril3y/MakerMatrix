import pytest
from sqlmodel import SQLModel
from MakerMatrix.models import user_models  # Ensure all models are registered
from MakerMatrix.models.models import engine
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

@pytest.fixture(scope="session", autouse=True)
def init_db():
    # Drop existing tables
    SQLModel.metadata.drop_all(engine)
    # Create tables for all models
    create_db_and_tables()
    # Log tables present after creation
    from sqlalchemy import inspect
    inspector = inspect(engine)
    print('Tables after creation:', inspector.get_table_names())
    # Setup default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    yield
    # Clean up tables after session
    SQLModel.metadata.drop_all(engine)
