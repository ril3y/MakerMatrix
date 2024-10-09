import uuid
from random import randint

import pytest
from fastapi.testclient import TestClient

from main import app  # Import your FastAPI app
from models.location_model import LocationModel
from models.part_model import PartModel

client = TestClient(app)


@pytest.fixture
def setup_decrement_part_quantity_test_data():
    cleanup()

    part = {
        "part_number": "PN001",
        "quantity": 50,
        "part_id": "71479ea9-061a-4813-97d4-0374d851a588",
        "part_name": "Test Part",
        "categories": [
            "electronics",  # Simple category as a string
            {"name": "components", "description": "Basic electronic components"}  # Detailed category
        ]
    }

    response = client.post("/parts/add_part?overwrite=true", json=part)
    return response.json()


@pytest.fixture
def setup_test_data_search_parts():
    # Clear the database before adding new parts
    response = client.delete("/parts/clear_parts")
    assert response.status_code == 200

    # Generate unique parts with random UUIDs for each part name
    parts = [
        {"part_number": f"PN{str(uuid.uuid4())[:8]}",
         "additional_properties": {"resistance": "1k", "resistor": True},
         "quantity": 100, "part_name": f"Resistor {uuid.uuid4()}"},
        {"part_number": f"PN{str(uuid.uuid4())[:8]}", "quantity": 200, "description": "100nF capacitor",
         "part_name": f"Capacitor {uuid.uuid4()}"},
        {"part_number": f"PN{str(uuid.uuid4())[:8]}", "quantity": 200, "description": "10uH capacitor",
         "part_name": f"Capacitor {uuid.uuid4()}"},
        {"part_number": f"PN{str(uuid.uuid4())[:8]}", "quantity": 300, "part_name": f"Inductor {uuid.uuid4()}"},
        {"part_number": f"PN{str(uuid.uuid4())[:8]}", "quantity": 400, "part_name": f"Diode {uuid.uuid4()}"},
        {"part_number": f"PN{str(uuid.uuid4())[:8]}", "quantity": 500, "part_name": f"Transistor {uuid.uuid4()}"},
        {"part_number": f"PN{str(uuid.uuid4())[:8]}", "quantity": 500, "description": "current sense resistor",
         "part_name": f"testing part {uuid.uuid4()}"},
    ]

    # Add each part to the database and store the response to fetch IDs
    added_parts = []
    for part in parts:
        response = client.post("/parts/add_part?overwrite=true", json=part)
        added_parts.append(response.json()["data"])

    # Return the added parts so tests can access them
    return added_parts


@pytest.fixture
def setup_test_delete_data():
    # Setup test data: populate the database with a test part

    part = {
        "part_number": "PN006",
        "quantity": 50,
        "part_id": "6",
        "part_name": "Test Part",
        "categories": [
            "electronics",  # Simple category as a string
            {"name": "components", "description": "Basic electronic components"}  # Detailed category
        ]
    }

    client.post("/parts/add_part?overwrite=true", json=part)
    return part


@pytest.fixture
def setup_part_update_part():
    cleanup()
    # Initial setup: create a part to update later
    part_data = {
        "part_number": "PN001",
        "part_name": "Resistor",
        "quantity": 100,
        "description": "A 1k Ohm resistor",
        "supplier": "Supplier A",
        "additional_properties": {"resistance": "1k"},
        "categories": ["electronics", "passive components"]
    }
    response = client.post("/parts/add_part", json=part_data)
    return response.json()["data"]


@pytest.fixture
def setup_test_data():
    # Setup test data: populate the database with test parts
    # This fixture runs before each test that uses it
    response = client.delete("/parts/clear_parts")
    assert response.status_code == 200

    parts = [
        {"part_number": "PN001", "quantity": 100, "part_id": "1", "part_name": "Resistor"},
        {"part_number": "PN002", "quantity": 200, "part_id": "2", "part_name": "Capacitor"},
        {"part_number": "PN003", "quantity": 300, "part_id": "3", "part_name": "Inductor"},
        {"part_number": "PN004", "quantity": 400, "part_id": "4", "part_name": "Diode"},
        {"part_number": "PN005", "quantity": 500, "part_id": "5", "part_name": "Transistor"},
    ]
    for part in parts:
        client.post("/parts/add_part", json=part)


def test_get_parts_empty_page(setup_test_data):
    # Test requesting a page that should be empty (page 3 with page size of 2)
    response = client.get("/parts/get_parts/", params={"page": 3, "page_size": 2})
    assert response.status_code == 200

    data = response.json()
    assert "parts" in data
    assert len(data["parts"]) == 1  # Only one part left on page 3
    assert data["page"] == 3
    assert data["page_size"] == 2
    assert data["total"] == 5  # Total remains the same


def test_get_parts_invalid_page_size(setup_test_data):
    # Test with an invalid page size (0)
    response = client.get("/parts/get_parts/", params={"page": 1, "page_size": 0})
    assert response.status_code == 422  # Should return validation error


def test_get_parts_paginated(setup_test_data):
    # Test retrieving the first page with a page size of 2
    response = client.get("/parts/get_parts/", params={"page": 1, "page_size": 2})
    assert response.status_code == 200

    data = response.json()
    assert "parts" in data
    assert len(data["parts"]) == 2  # Check that we got 2 parts
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] == 5  # We added 5 parts in total


def test_delete_part(setup_test_delete_data):
    # Use the part_id from the setup_test_data fixture
    part_id = setup_test_delete_data["part_id"]

    # Delete the part
    response = client.delete(f"/parts/delete_part/{part_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Part deleted successfully", "deleted_part_id": part_id}

    # Verify the part is deleted by attempting to get it
    response = client.get(f"/parts/get_part_by_id/{part_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": f"Part ID {part_id} not found"}


def test_decrement_part_quantity_with_part_id(setup_decrement_part_quantity_test_data):
    # Test updating a part's quantity using part_id

    part_id = "71479ea9-061a-4813-97d4-0374d851a588"

    request_data = {
        "part_id": part_id,
    }
    response = client.put("/parts/decrement_count/", json=request_data)
    assert response.status_code == 200
    res = response.json()
    assert "message" in res
    assert res["previous_quantity"] == res["new_quantity"] + 1


def test_get_part_by_details_with_part_id():
    # Assuming you have a part with part_id '71479ea9-061a-4813-97d4-0374d851a588' in your test setup
    part_id = '71479ea9-061a-4813-97d4-0374d851a588'
    response = client.get(f"/parts/get_part_by_id/{part_id}")
    assert response.status_code == 200
    res = response.json()
    assert "part_id" in res
    assert res["part_number"] == 'PN001'


def test_update_part_quantity_with_part_id(setup_decrement_part_quantity_test_data):
    # Test updating a part's quantity using part_id
    part_id = "71479ea9-061a-4813-97d4-0374d851a588"
    new_quantity = randint(1, 10000)
    update_request = {
        "part_id": part_id,
        "new_quantity": new_quantity
    }
    response = client.put("/parts/update_quantity/", json=update_request)
    assert response.status_code == 200
    res = response.json()
    assert "message" in res
    assert res["message"] == f"Quantity updated to {new_quantity}"

    # Verify the quantity was updated
    response_get = client.get(f"/parts/get_part_by_id/{part_id}")
    assert response_get.status_code == 200
    part = response_get.json()
    assert part["quantity"] == new_quantity


def test_get_all_parts():
    response = client.get("/parts/all_parts")
    assert response.status_code == 200
    parts = response.json()
    assert isinstance(parts, list)


def test_get_part_by_details_with_part_number(setup_test_data_search_parts):
    part_number = setup_test_data_search_parts[0]["part_number"]

    response = client.get("/parts/get_part_by_part_number/", params={"part_number": part_number})
    assert response.status_code == 200
    res = response.json()
    assert "part_number" in res
    assert res["part_number"] == part_number


def test_search_by_part_name(setup_test_data_search_parts):
    # Search using a part name
    response = client.get("/parts/search-parts/", params={"term": "Resistor"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) == 2


def test_search_by_description(setup_test_data_search_parts):
    # Search using a term found in the description
    response = client.get("/parts/search-parts/", params={"term": "capacitor"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"][0]['matched_fields']) > 0
    assert any(
        field["field"] == "description" and "capacitor".lower() in str(part["part"].get("description", "")).lower()
        for part in data["data"]
        for field in part["matched_fields"]
    )


def test_search_by_additional_property(setup_test_data_search_parts):
    # Search using a term found in the additional properties
    search_term = "1k"
    response = client.get("/parts/search-parts/", params={"term": search_term})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) > 0
    assert data['data'][0]['matched_fields'][0]['key'] == 'resistance'
    assert data['data'][0]['matched_fields'][0]['field'] == 'additional_properties'
    assert data['data'][0]['part']['additional_properties']['resistance'] == search_term


def test_search_parts_min_length(setup_test_data_search_parts):
    # Test with a search term that is too short
    short_search_term = "a"  # Less than the minimum length (e.g., 3)
    response = client.get("/parts/search-parts/", params={"term": short_search_term})

    # Assert that the status code is 400 (Bad Request)
    assert response.status_code == 400

    # Assert the response message matches the expected error
    assert response.json() == {"detail": "Search term must be at least 2 characters long."}


def test_search_parts_valid_length():
    # Test with a valid search term
    valid_search_term = "resistor"  # More than the minimum length (e.g., 3)
    response = client.get("/parts/search-parts/", params={"term": valid_search_term})

    # Assert that the status code is 200 (OK)
    assert response.status_code == 200

    # Assert that "results" key is in the response
    assert "data" in response.json()


def test_get_part_by_details_with_id(setup_test_data_search_parts):
    # Get the part_id from the setup data
    test_part = setup_test_data_search_parts[0]
    part_id = test_part["part_id"]

    # Create the part model
    part_data = {"part_id": part_id}

    # Test by part_id
    response = client.get("/parts/get_part_by_details/", params={"part_id": part_id})
    assert response.status_code == 200
    res = response.json()
    assert res["part_id"] == part_id


def test_get_part_by_details_not_found(setup_test_data_search_parts):
    # Test with a non-existent part
    part_number = "NonExistentPart123"

    response = client.get("/parts/get_part_by_details/", params={"part_number": part_number})
    assert response.status_code == 404
    assert response.json() == {"detail": f"Part Details with part_number '{part_number}' not found"}


def test_get_part_by_details_with_part_name(setup_test_data_search_parts):
    # Get the part_name from the setup data
    test_part = setup_test_data_search_parts[2]
    part_name = test_part["part_name"]

    # Test by part_name using query parameters
    response = client.get("/parts/get_part_by_details/", params={"part_name": part_name})
    assert response.status_code == 200
    res = response.json()
    assert res["part_name"] == part_name


def test_update_part(setup_part_update_part):
    # Get the part_id from the setup
    part_id = setup_part_update_part["part_id"]

    # Prepare update data
    updated_data = {
        "part_id": part_id,
        "quantity": 200,
        "description": "A 2k Ohm resistor",
        "additional_properties": {
            "resistance": "2k",
            "tolerance": "5%"
        }
    }

    # Make the PUT request to update the part
    response = client.put("/parts/update_part", json=updated_data)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["data"]["quantity"] == 200
    assert response_data["data"]["additional_properties"]["resistance"] == "2k"
    assert response_data["data"]["additional_properties"]["tolerance"] == "5%"


def cleanup():
    # remove all parts
    response = client.delete("/parts/clear_parts")
    assert response.status_code == 200


@pytest.fixture
def setup_test_locations_and_parts():
    # Clear existing locations and parts first
    client.delete("/locations/delete_all_locations")
    client.delete("/parts/clear_parts")

    # Create top-level location (Office)
    office_location = LocationModel(name="Office", description="Main office space")
    office_response = client.post("/locations/add_location", json=office_location.dict())
    office_id = office_response.json()["data"]["id"]

    # Create a child location (Toolbox) under the office
    toolbox_location = LocationModel(name="Toolbox", description="Tool storage", parent_id=office_id)
    toolbox_response = client.post("/locations/add_location", json=toolbox_location.dict())
    toolbox_id = toolbox_response.json()["data"]["id"]

    # Add a part to the office location
    part_office = PartModel(
        part_number=f"PN{uuid.uuid4().hex[:6]}",
        part_name="Office Chair",
        quantity=5,
        description="An office chair",
        location={"id": office_id}
    )
    office_part_response = client.post("/parts/add_part", json=part_office.dict())
    office_part_id = office_part_response.json()["data"]["part_id"]

    # Add a part to the toolbox location
    part_toolbox = PartModel(
        part_number=f"PN{uuid.uuid4().hex[:6]}",
        part_name="Hammer",
        quantity=10,
        description="A hammer from the toolbox",
        location={"id": toolbox_id}
    )
    screwdriver = PartModel(
        part_number=f"PN{uuid.uuid4().hex[:6]}",
        part_name="Phillips Screwdriver",
        quantity=1,
        description="A screwdriver 5mm",
        location={"id": toolbox_id}
    )

    toolbox_part_response = client.post("/parts/add_part", json=part_toolbox.dict())
    toolbox_part_id = toolbox_part_response.json()["data"]["part_id"]

    screwdriver_part_response = client.post("/parts/add_part", json=screwdriver.dict())
    screwdriver_part_id = screwdriver_part_response.json()["data"]["part_id"]

    return {
        "office_id": office_id,
        "toolbox_id": toolbox_id,
        "office_part_id": office_part_id,
        "toolbox_part_id": toolbox_part_id,
        "screwdriver_part_id": screwdriver_part_id,
    }


def test_get_parts_by_location_id(setup_test_locations_and_parts):
    # Retrieve the setup data
    setup_data = setup_test_locations_and_parts
    office_id = setup_data["office_id"]
    toolbox_id = setup_data["toolbox_id"]

    # Get parts directly associated with the office location (non-recursive)
    response = client.get(f"/parts/get_parts_by_location/{office_id}", params={"recursive": False})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1  # Only one part directly tied to 'office'

    # Get all parts associated with the office location and its children (recursive)
    response_recursive = client.get(
        f"/parts/get_parts_by_location/{office_id}",
        params={"recursive": "true"}
    )
    assert response_recursive.status_code == 200
    assert len(response_recursive.json()["data"]) == 3  # Includes the part from the 'Toolbox' location

    # Test getting parts directly associated with the toolbox location (non-recursive)
    response_toolbox = client.get(f"/parts/get_parts_by_location/{toolbox_id}?recursive=false")
    assert response_toolbox.status_code == 200
    assert len(response_toolbox.json()["data"]) == 2  # Only one part tied to 'Toolbox'
