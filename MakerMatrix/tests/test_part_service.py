# add_part_with_categories.py (Updated Test)
import logging
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.database.db import get_session

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import CategoryModel, PartModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.schemas.part_create import PartCreate
from MakerMatrix.services.category_service import CategoryService  # Import PartCreate
import logging

# Suppress SQLAlchemy INFO logs (which include SQL statements)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Create a TestClient to interact with the app
client = TestClient(app)


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
def setup_part_update_part():
    # Initial setup: create a part to update later

    part_data = {
        "part_number": "PN001",
        "part_name": "B1239992810A",
        "quantity": 100,
        "description": "A 1k Ohm resistor",
        "supplier": "Supplier A",
        "additional_properties": {"resistance": "1k"},
        "category_names": ["electronics", "passive components"]
    }
    response = client.post("/parts/add_part", json=part_data)
    return response.json()


def test_get_part_by_name(setup_part_update_part):
    tmp_part = setup_part_update_part
    response = client.get(f"/parts/get_part?part_name={tmp_part['data']['part_name']}")
    assert response.status_code == 200
    assert response.json()['data']['part_name'] == tmp_part['data']['part_name']

def test_get_part_by_id(setup_part_update_part):
    tmp_part = setup_part_update_part
    response = client.get(f"/parts/get_part?part_id={tmp_part.id}")
    assert response.status_code == 200
    assert response.json()['data']['id'] == f"{tmp_part.id}"


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
    response = client.post("/parts/add_part", json=part_data.model_dump())

    # Check the response status code
    assert response.status_code == 200

    # Parse the response JSON
    response_json = response.json()

    # Check that the part was successfully added
    assert response_json["status"] == "added"
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

    # Make a POST request to the /add_part endpoint to add the part initially
    initial_response = client.post("/parts/add_part", json=part_data.model_dump())

    # Check the initial response status code to ensure the part was added successfully
    assert initial_response.status_code == 200

    # Make a POST request to the /add_part endpoint again to add the same part
    response = client.post("/parts/add_part", json=part_data.model_dump())

    # Check the response status code
    assert response.status_code == 409

    # Parse the response JSON
    response_json = response.json()

    # Check that the part already exists
    assert response_json["status"] == "conflict"
    assert "already exists" in response_json["message"]
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
    assert response_json["message"] == "Validation error"

    # Extract the error details and check the missing fields
    assert 'quantity' in response_json['data'][0]


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
    assert response_json["message"] == "Validation error"
    assert "Input should be a valid string" in response_json["data"][0]


def test_get_part_by_id():
    # First, add a part to the database with a known part number
    part_data = PartCreate(
        part_number="Screw-001",
        part_name="Hex Head Screw",
        quantity=500,
        description="A standard hex head screw",
        location_id=None,
        category_names=["hardware"]
    )

    # Make a POST request to add the part to the database
    response = client.post("/parts/add_part", json=part_data.model_dump())
    assert response.status_code == 200

    # Extract the part ID from the response
    response_json = response.json()
    part_id = response_json["data"]["id"]

    # Make a GET request to retrieve the part by its ID
    get_response = client.get(f"/parts/get_part?part_id={part_id}")

    # Check the response status code
    assert get_response.status_code == 200

    # Parse the response JSON
    get_response_json = get_response.json()

    # Check that the part data matches
    assert get_response_json["status"] == "found"
    assert "Part with ID" in get_response_json["message"]
    assert get_response_json["data"]["part_number"] == "Screw-001"
    assert get_response_json["data"]["part_name"] == "Hex Head Screw"


def test_get_part_by_invalid_part_id():
    # First, add a part to the database with a known part number
    # part_data = PartCreate(
    #     part_number="Screw-002",
    #     part_name="Round Head Screw",
    #     quantity=300,
    #     description="A round head screw",
    #     location_id=None,
    #     category_names=["tools"]
    # )

    # # Make a POST request to add the part to the database
    # response = client.post("/parts/add_part", json=part_data.model_dump())
    # assert response.status_code == 200

    # # Extract the part number from the response
    part_id = "invalid-id"

    # Make a GET request to retrieve a part by a non-existent ID
    get_response = client.get(f"/parts/get_part?part_id={part_id}")

    # Check the response status code
    assert get_response.status_code == 404

    # Parse the response JSON
    get_response_json = get_response.json()

    # Check that the correct error message is returned
    assert get_response_json["message"] == "Part with ID invalid-id not found"
    assert get_response_json["status"] == "error"
    assert get_response_json["data"] is None


def test_get_part_by_part_number():
    # First, add a part to the database with a known part number
    part_data = PartCreate(
        part_number="Screw-002",
        part_name="Round Head Screw",
        quantity=300,
        description="A round head screw",
        location_id=None,
        category_names=["tools"]
    )

    # Make a POST request to add the part to the database
    response = client.post("/parts/add_part", json=part_data.model_dump())
    assert response.status_code == 200

    # Extract the part number from the response
    part_number = part_data.part_number

    # Make a GET request to retrieve the part by its part number
    get_response = client.get(f"/parts/get_part?part_number={part_number}")

    # Check the response status code
    assert get_response.status_code == 200

    # Parse the response JSON
    get_response_json = get_response.json()

    # Check that the part data matches
    assert get_response_json["status"] == "found"
    assert get_response_json["message"] == f"Part with part number '{part_number}' found."
    assert get_response_json["data"]["part_number"] == part_number
    assert get_response_json["data"]["part_name"] == "Round Head Screw"
    assert get_response_json["data"]["categories"][0]['name'] == "tools"


def test_update_existing_part():
    top_category = CategoryModel(name="tools", description="All Tools")
    CategoryService.add_category(top_category)

    # Create a sub-category with the top-level category as the parent
    sub_category1 = CategoryModel(name="hammers", description="Types of hammers")
    CategoryService.add_category(sub_category1)

    sub_category2 = CategoryModel(name="screwdrivers", description="Types of screwdrivers")
    CategoryService.add_category(sub_category2)

    hardware = client.get("/categories/get_category?name=tools").json()
    # The issue is the category tools does not have the children 

    part_data = PartCreate(
        part_number="323329329dj91",
        part_name="hammer drill",
        quantity=500,
        description="A standard hex head screw",
        location_id=None,
        category_names=["hammers", "screwdrivers"],
        additional_properties={
            "color": "silver",
            "material": "stainless steel"
        }
    )

    # Make a POST request to add the part to the database
    # response = client.post("/parts/add_part", json=part_data.model_dump())

    response = client.post("/parts/add_part", json=part_data.model_dump())

    assert response.status_code == 200

    # Extract the part ID from the response
    response_json = response.json()
    part_id = response_json["data"]["id"]

    # Verify the additional_properties and categories were added correctly
    assert response_json["data"]["additional_properties"]["color"] == "silver"
    assert response_json["data"]["additional_properties"]["material"] == "stainless steel"

    category_names = [category["name"] for category in response_json['data']['categories']]
    assert {"hammers", "screwdrivers"}.issubset(set(category_names))

    # Define updated part data - changing categories and additional_properties
    updated_part_data = {
        "id": part_id,
        "part_number": "Screw-001",
        "part_name": "Updated Hex Head Screw",
        "quantity": 600,
        "description": "An updated description for the hex head screw",
        "location_id": None,
        "category_names": ["tools", "fasteners"],  # Remove "screwdrivers" and add "fasteners"
        "additional_properties": {
            "color": "black",
            "material": "carbon steel",
            "weight": "0.5kg"
        }
    }

    # Make a PUT request to update the part
    update_response = client.put(f"/parts/update_part/{part_id}", json=updated_part_data)

    # Check the response status code
    assert update_response.status_code == 200

    # Parse the response JSON
    update_response_json = update_response.json()

    # Check that the part data has been updated successfully
    assert update_response_json["status"] == "success"
    assert update_response_json["message"] == "Part updated successfully."
    assert update_response_json["data"]["part_name"] == "Updated Hex Head Screw"
    assert update_response_json["data"]["quantity"] == 600
    assert update_response_json["data"]["description"] == "An updated description for the hex head screw"

    # Verify the updated additional_properties
    assert update_response_json["data"]["additional_properties"]["color"] == "black"
    assert update_response_json["data"]["additional_properties"]["material"] == "carbon steel"
    assert update_response_json["data"]["additional_properties"]["weight"] == "0.5kg"

    # Verify the updated categories

    updated_categories = [category["name"] for category in update_response_json['data']['categories']]
    assert {"fasteners", "tools"}.issubset(set(updated_categories))
    assert "hardware" not in updated_categories  # Confirm "hardware" was removed
