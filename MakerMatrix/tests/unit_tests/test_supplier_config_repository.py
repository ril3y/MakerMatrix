"""Unit tests for SupplierConfigRepository case-insensitive lookups."""

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from MakerMatrix.models.supplier_config_models import SupplierConfigModel
from MakerMatrix.repositories.supplier_config_repository import SupplierConfigRepository


def setup_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def test_get_by_supplier_name_case_insensitive():
    """Repository lookups should ignore supplier name casing."""
    engine = setup_database()
    repo = SupplierConfigRepository()

    with Session(engine) as session:
        config = SupplierConfigModel(
            supplier_name="DIGIKEY",
            display_name="DigiKey",
            base_url="https://example.com",
        )
        session.add(config)
        session.commit()

    with Session(engine) as session:
        retrieved = repo.get_by_supplier_name(session, "digikey")

    assert retrieved is not None
    assert retrieved.supplier_name == "DIGIKEY"

