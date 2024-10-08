import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.fixture
def setup_test_data():
    category_id = 'd6c5963b-3ab3-436f-9042-d5f233898a45'
    category_data = {"name": "Test Category", "id": category_id}
    response = client.post("/categories/add_category/", json=category_data)
    return response.json()


def test_remove_category(setup_test_data):
    # Add a category to ensure it exists before attempting to remove it
    category_id = setup_test_data["data"]["id"]

    # Now attempt to remove the category using the ID
    response = client.delete("/categories/remove_category", params={"id": category_id})
    assert response.status_code == 200
    assert response.json() == {"message": f"Category with id '{category_id}' removed successfully"}


def test_remove_non_existent_category_by_id():
    # Attempt to remove a category with a non-existent ID
    response = client.delete("/categories/remove_category", params={"id": "non-existent-id"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Category with id 'non-existent-id' not found"}


def test_remove_non_existent_category_by_name():
    # Attempt to remove a category with a non-existent name
    response = client.delete("/categories/remove_category", params={"name": "Non-Existent Category"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Category with name 'Non-Existent Category' not found"}


def test_remove_category_without_id_or_name():
    # Attempt to remove a category without providing either ID or name
    response = client.delete("/categories/remove_category")
    assert response.status_code == 400
    assert response.json() == {"detail": "Either category ID or name must be provided"}


def test_remove_all_categories():
    # Add a few categories
    client.post("/categories/add_category/", json={"name": "Category 1"})
    client.post("/categories/add_category/", json={"name": "Category 2"})

    # Attempt to delete all categories
    response = client.delete("/categories/remove_all_categories")
    assert response.status_code == 200
    assert response.json()['message'] == "All categories removed successfully"
    # Verify that no categories remain
    get_response = client.get("/categories/all_categories")
    assert get_response.status_code == 200
    assert len(get_response.json()['categories']) == 0


@pytest.fixture
def setup_test_data_category_update():
    # Add a category to set up the initial data for testing
    response = client.delete("/categories/remove_category", params={"name": "Test Category Update"})

    category_data = {"name": "Test Category Update", "description": "Initial description"}
    add_response = client.post("/categories/add_category/", json=category_data)
    assert add_response.status_code == 200
    return add_response.json()


def test_update_category_name(setup_test_data_category_update):
    # Retrieve the category ID from the setup
    category_id = setup_test_data_category_update["data"]["id"]

    # Prepare new data for updating the category
    update_data = {
        "name": "Updated Category Name",
        "description": "Updated description"
    }

    # Send a PUT request to update the category
    response = client.put(f"/categories/update_category/{category_id}", json=update_data)
    assert response.status_code == 200

    # Check that the response message is correct
    assert response.json()["message"] == f"Category with ID '{category_id}' updated successfully"

    # Optional: Verify that the update is correctly reflected in the database
    get_response = client.get("/categories/get_category", params={"category_id": category_id})
    assert get_response.status_code == 200
    assert get_response.json()["data"]["name"] == update_data["name"]
    assert get_response.json()["data"]["description"] == update_data["description"]


@pytest.fixture
def setup_categories_for_get_categories():
    # Add some unique categories for testing
    categories = [
        {"name": "Electronics", "description": "Devices and components related to electronics"},
        {"name": "Mechanical Parts", "description": "Gears, screws, and other mechanical components"},
        {"name": "Software Tools", "description": "Tools and software utilities for development"},
    ]

    added_categories = []
    for category_data in categories:
        response = client.post("/categories/add_category/", json=category_data)
        added_categories.append(response.json()["data"])

    return added_categories


def test_get_category_by_id(setup_categories_for_get_categories):
    # Use the first category added in the fixture
    category_id = setup_categories_for_get_categories[0]["id"]

    # Now attempt to get the category using the ID
    get_response = client.get("/categories/get_category", params={"category_id": category_id})
    assert get_response.status_code == 200
    data = get_response.json()

    # Validate the response data
    assert data["status"] == "success"
    assert data["data"]["id"] == category_id
    assert data["data"]["name"] == "Electronics"


def test_get_category_by_name(setup_categories_for_get_categories):
    # Use the name of the second category added in the fixture
    category_name = setup_categories_for_get_categories[1]["name"]

    # Now attempt to get the category using the name
    get_response = client.get("/categories/get_category", params={"name": category_name})
    assert get_response.status_code == 200
    data = get_response.json()

    # Validate the response data
    assert data["status"] == "success"
    assert data["data"]["name"] == category_name
    assert data["data"]["description"] == "Gears, screws, and other mechanical components"
