import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from MakerMatrix.models.models import PartModel, CategoryModel, LocationModel, AdvancedPartSearch
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="test_data")
def test_data_fixture(session: Session):
    # Create test categories
    categories = [CategoryModel(name="Electronics"), CategoryModel(name="Mechanical"), CategoryModel(name="Tools")]
    for category in categories:
        session.add(category)
    session.commit()

    # Create test locations
    locations = [LocationModel(name="Workshop A"), LocationModel(name="Storage B"), LocationModel(name="Lab C")]
    for location in locations:
        session.add(location)
    session.commit()

    # Create test parts
    parts = [
        PartModel(
            part_name="Arduino Uno",
            part_number="A001",
            description="Microcontroller board",
            quantity=10,
            supplier="Arduino",
            location_id=locations[0].id,
            categories=[categories[0]],
        ),
        PartModel(
            part_name="Stepper Motor",
            part_number="SM001",
            description="NEMA 17 stepper motor",
            quantity=5,
            supplier="Adafruit",
            location_id=locations[1].id,
            categories=[categories[0], categories[1]],
        ),
        PartModel(
            part_name="Screwdriver Set",
            part_number="SD001",
            description="Professional screwdriver set",
            quantity=3,
            supplier="ToolCo",
            location_id=locations[2].id,
            categories=[categories[2]],
        ),
    ]
    for part in parts:
        session.add(part)
    session.commit()

    return {"categories": categories, "locations": locations, "parts": parts}


def test_search_by_term(session: Session, test_data):
    search_params = AdvancedPartSearch(search_term="Arduino")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].part_name == "Arduino Uno"


def test_search_by_category(session: Session, test_data):
    search_params = AdvancedPartSearch(category_names=["Electronics"])
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 2
    assert len(results) == 2
    assert all("Electronics" in [cat.name for cat in part.categories] for part in results)


def test_search_by_location(session: Session, test_data):
    search_params = AdvancedPartSearch(location_id=test_data["locations"][0].id)
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].location_id == test_data["locations"][0].id


def test_search_by_quantity_range(session: Session, test_data):
    search_params = AdvancedPartSearch(min_quantity=5, max_quantity=10)
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 2
    assert len(results) == 2
    assert all(5 <= part.quantity <= 10 for part in results)


def test_search_by_supplier(session: Session, test_data):
    search_params = AdvancedPartSearch(supplier="Arduino")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].supplier == "Arduino"


def test_search_with_sorting(session: Session, test_data):
    search_params = AdvancedPartSearch(sort_by="quantity", sort_order="desc")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 3
    assert len(results) == 3
    assert results[0].quantity == 10  # Should be highest quantity


def test_search_with_pagination(session: Session, test_data):
    search_params = AdvancedPartSearch(page=1, page_size=2)
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 3
    assert len(results) == 2  # Should only return 2 items per page


def test_search_with_multiple_filters(session: Session, test_data):
    search_params = AdvancedPartSearch(
        search_term="motor", category_names=["Electronics"], min_quantity=1, max_quantity=10
    )
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].part_name == "Stepper Motor"


def test_search_with_no_results(session: Session, test_data):
    search_params = AdvancedPartSearch(search_term="NonexistentPart")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 0
    assert len(results) == 0


def test_search_with_empty_params(session: Session, test_data):
    search_params = AdvancedPartSearch()
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 3  # Should return all parts
    assert len(results) == 3
