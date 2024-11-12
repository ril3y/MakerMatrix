# add_part_with_categories.py (Updated Test)
import logging
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.schemas.part_create import PartCreate  # Import PartCreate

# Create a TestClient to interact with the app
client = TestClient(app)


def disable_sqlalchemy_logging():
    logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.ERROR)


def enable_sqlalchemy_logging():
    logging.getLogger('sqlalchemy').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    disable_sqlalchemy_logging()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Set up the database (tables creation)
    create_db_and_tables()

    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


def test_add_part():
    # Define the part data to be sent to the API
    part_data = PartCreate(
        part_number="Screw-001",
        part_name="Hex Head Screw",
        quantity=500,
        description="A standard hex head screw",
        location_id=None,
        category_names=["hardware"]
    )

    # Make a POST request to the /add_part endpoint
    response = client.post("/parts/add_part", json=part_data.dict())

    # Check the response status code
    assert response.status_code == 200

    # Parse the response JSON
    response_json = response.json()

    # Check that the part was successfully added
    assert response_json["status"] == "success"
    assert response_json["message"] == "Part added successfully"
    assert response_json["data"]["part_number"] == "Screw-001"
    assert response_json["data"]["part_name"] == "Hex Head Screw"
    assert response_json["data"]["quantity"] == 500
    assert response_json["data"]["description"] == "A standard hex head screw"


def test_add_existing_part():
    part_data = PartCreate(
        part_number="Screw-001",
        part_name="Hex Head Screw",
        quantity=500,
        description="A standard hex head screw",
        location_id=None,
        category_names=["hardware"]
    )

    # Make a POST request to the /add_part endpoint again
    response = client.post("/parts/add_part", json=part_data.dict())

    # Check the response status code
    assert response.status_code == 409

    # Parse the response JSON
    response_json = response.json()

    # Check that the part already exists
    assert response_json["status"] == "conflict"
    assert response_json["message"] == "Part already exists"
    assert "data" in response_json


def test_add_part_with_invalid_data():
    # Define part data with missing required fields
    part_data = {
        "part_number": "Screw-002",
        # Missing 'part_name', 'quantity', and other required fields
    }

    # Make a POST request to the /add_part endpoint
    response = client.post("/parts/add_part", json=part_data)

    # Check the response status code
    assert response.status_code == 422

    # Check that the response follows the custom ResponseSchema format
    response_json = response.json()
    assert response_json["status"] == "error"
    assert response_json["message"] == "Validation failed for the input data."

    # Extract the error details and check the missing fields
    errors = response_json["data"]["errors"]
    assert any("part_name" in error for error in errors)
    assert any("quantity" in error for error in errors)


def test_add_part_with_invalid_category():
    # Define part data with an invalid category (number instead of string)
    part_data = {
        "part_number": "Screw-003",
        "part_name": "Hex Head Screw with Invalid Category",
        "quantity": 100,
        "description": "A hex head screw with an invalid category",
        "location_id": None,
        "category_names": [123]  # Invalid category, should be a string
    }

    # Make a POST request to the /add_part endpoint
    response = client.post("/parts/add_part", json=part_data)

    # Check that the response returns a validation error status code (422 Unprocessable Entity)
    assert response.status_code == 422

    # Parse the response JSON
    response_json = response.json()

    # Check the response structure and validation error
    assert response_json["status"] == "error"
    assert response_json["message"] == "Validation failed for the input data."
    assert "errors" in response_json["data"]

    # Extract errors from the response data
    errors = response_json["data"]["errors"]

    expected_error_message = "Invalid type for field 'body -> category_names -> 0': Expected a valid string but got '123'."
    assert expected_error_message in errors, f"Expected error message '{expected_error_message}' not found in errors: {errors}"


def test_get_part_by_id():
    # First, add a part to the database
    part_data = PartCreate(
        part_number="Screw-002",
        part_name="Round Head Screw",
        quantity=300,
        description="A round head screw",
        location_id=None,
        category_names=["tools"]
    )

    # Make a POST request to add the part to the database
    response = client.post("/parts/add_part", json=part_data.dict())
    assert response.status_code == 200

    # Extract the part ID from the response
    response_json = response.json()
    part_id = response_json["data"]["id"]

    # Make a GET request to retrieve the part by its ID
    get_response = client.get(f"/parts/get_part_by_id/{part_id}")

    # Check the response status code
    assert get_response.status_code == 200

    # Parse the response JSON
    get_response_json = get_response.json()

    # Check that the part data matches
    assert get_response_json["status"] == "found"
    assert get_response_json["message"] == "Part found successfully"
    assert get_response_json["data"]["part_number"] == "Screw-002"
    assert get_response_json["data"]["part_name"] == "Round Head Screw"
    assert get_response_json["data"]["quantity"] == 300
    assert get_response_json["data"]["description"] == "A round head screw"
