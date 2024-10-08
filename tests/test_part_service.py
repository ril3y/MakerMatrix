import pytest
from fastapi.testclient import TestClient
from main import app  # Import your FastAPI app
from random import randint

client = TestClient(app)


@pytest.fixture
def setup_decrement_part_quantity_test_data():
    response = client.post("/parts/add_part?overwrite=true", json={
        "part_number": "PN001",
        "quantity": 50,
        "part_id": "71479ea9-061a-4813-97d4-0374d851a588",
        "part_name": "Test Part Decrement",
        "categories": [
            "electronics",  # Simple category as a string
            {"name": "components", "description": "Basic electronic components"}  # Detailed category
        ]
                           })
    assert response.status_code == 200

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
    assert data["total"] == 5 # Total remains the same


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


def test_update_part_quantity_with_part_id():
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


def test_get_part_by_details_with_part_number():
    part_number = "PN001"

    response = client.get("/parts/get_part_by_part_number/", params={"part_number": part_number})
    assert response.status_code == 200
    res = response.json()
    assert "part_number" in res
    assert res["part_number"] == part_number



# def test_get_part_by_details_not_found():
#     # Test with details that don't match any part
#     response = client.get("/get_part_by_details", params={"part_id": "nonexistent"})
#     assert response.status_code == 404
#     assert response.json() == {"error": "Part not found with the provided details"}


# def test_get_part_by_details_no_params():
#     # Test with no parameters provided
#     response = client.get("/get_part_by_details")
#     assert response.status_code == 400
#     assert "At least one of part_id, part_name, or part_number must be provided." in response.json()["detail"]
