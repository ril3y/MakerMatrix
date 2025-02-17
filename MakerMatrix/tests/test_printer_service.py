import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from MakerMatrix.lib.print_config import PrintJobConfig
from MakerMatrix.main import app
from MakerMatrix.models.label_model import LabelData
from MakerMatrix.models.models import PartModel, engine, create_db_and_tables
from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.services.printer_service import PrinterService

client = TestClient(app)


# config = PrinterConfig(
#     model="QL-800",
#     backend="network",
#     printer_identifier="tcp://192.168.1.71",
#     dpi=300,
#     scaling_factor=1.1
# )


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Set up the database (tables creation)
    create_db_and_tables()

    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def printer_repo() -> PrinterRepository:
    """Create and configure a printer repository for tests."""
    return PrinterRepository(config_path="printer_config.json")


@pytest.fixture
def printer_service(printer_repo: PrinterRepository) -> PrinterService:
    """Construct a PrinterService that uses the same repository fixture."""
    return PrinterService(printer_repo)


def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def setup_part_update_part():
    # Initial setup: create a part to update later

    part_data = {
        "part_number": "PN001",
        "part_name": "Resistor",
        "quantity": 100,
        "description": "A 1k Ohm resistor",
        "supplier": "Supplier A",
        "additional_properties": {"resistance": "1k"},
        "category_names": ["electronics", "passive components"]
    }
    response = client.post("/parts/add_part", json=part_data)
    return response.json()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_code_with_name(printer_service, setup_part_update_part):
    tmp_part = setup_part_update_part

    # Create an example part object (if needed for your test):
    part_office = PartModel(
        part_number=f"PN{uuid.uuid4().hex[:6]}",
        part_name="Office Chair",
        quantity=5,
        description="An office chair"
    )

    # Create test label data
    label_data = LabelData(
        part=part_office,
        label_size=12,
        part_name=part_office.part_name,

    )

    # Call the new combined print function
    result = await printer_service.print_qr_code_with_name(label_data)

    # Validate the result
    assert result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_part_name(printer_service, setup_part_update_part):
    # Load and configure printer
    printer_service.load_printer_config()
    tmp_part = setup_part_update_part["data"]

    # Convert JSON dictionary to PartModel instance
    new_part = PartModel.from_json(tmp_part)

    pconf = PrintJobConfig()
    # Test the new part name print function
    result = await printer_service.print_part_name(new_part, print_config=pconf)
    assert result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_and_text_combined(printer_service):
    # Set up printer config

    part_data = {
        "part_number": "Screw-003",
        "part_name": "PB129skz89",
        "quantity": 100,
        "description": "A hex head screw with an invalid category",
        "location_id": None,
        "category_names": ["hardware", "screws"]  # Invalid category, should be a string
    }

    # Make a POST request to the /add_part endpoint
    response = client.post("/parts/add_part", json=part_data)

    # Extract JSON response
    part_json = response.json()["data"]  # Get only the part data

    # Convert JSON dictionary to PartModel instance
    part = PartModel.from_json(part_json)

    # qr_image = await printer_service.generate_qr_code(response.json()['data'])
    pconf = PrintJobConfig()
    # Test the combined print function
    result = await printer_service.print_qr_and_text(part, pconf, text=part.part_name)
    assert result
