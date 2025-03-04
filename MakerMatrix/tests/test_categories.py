import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.schemas.part_create import PartCreate  # Import PartCreate
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.main import app

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


def test_remove_category():
    category_data = {"name": "Test Category", "description": "This is a test category"}
    response = client.post("/categories/add_category/", json=category_data)
    response_json = response.json()
    # Add a category to ensure it exists before attempting to remove it
    category_id = response_json["data"]["id"]

    # Now attempt to remove the category using the ID
    rm_response = client.delete("/categories/remove_category", params={"id": category_id})
    rm_response_json = rm_response.json()
    assert response.status_code == 200
    assert rm_response_json['message'] == "Category with name 'Test Category' removed"


def test_remove_non_existent_category_by_id():
    # Attempt to remove a category with a non-existent ID
    response = client.delete("/categories/remove_category", params={"id": "non-existent-id"})
    assert response.status_code == 404
    response_json = response.json()
    assert response_json["status"] == "error"
    assert response_json["message"] == 'Category with ID non-existent-id not found'
    assert response_json["data"] is None


def test_remove_non_existent_category_by_name():
    # Attempt to remove a category with a non-existent name
    response = client.delete("/categories/remove_category", params={"name": "Non-Existent Category"})
    assert response.status_code == 404
    response_json = response.json()
    assert response_json["status"] == "error"
    assert response_json["message"] == 'Category with name Non-Existent Category not found'
    assert response_json["data"] is None


def test_remove_category_without_id_or_name():
    # Attempt to remove a category without providing either ID or name
    response = client.delete("/categories/remove_category")
    assert response.status_code == 400
    assert response.json() == {"detail": "Either category ID or name must be provided"}


def test_delete_all_categories():
    # Add a few categories
    client.post("/categories/add_category/", json={"name": "Category 1"})
    client.post("/categories/add_category/", json={"name": "Category 2"})

    # Attempt to delete all categories
    response = client.delete("/categories/delete_all_categories")
    response.status_code == 200

    # Verify that no categories remain
    get_response = client.get("/categories/get_all_categories")
    assert get_response.status_code == 200
    assert "All categories retrieved successfully" in get_response.json()["message"]
    assert len(get_response.json()['data']) == 0


@pytest.fixture
def setup_test_data_category_update():
    # Add a category to set up the initial data for testing
    category_data = {"name": "Test Category", "description": "Initial description"}
    add_response = client.post("/categories/add_category/", json=category_data)
    assert add_response.status_code == 200
    return add_response.json()


def test_update_category():
    """Test to update a category via the API."""
    # First, add a category
    category_data = {
        "name": "Electronics",
        "description": "Electronic components"
    }
    response = client.post("/categories/add_category", json=category_data)
    assert response.status_code == 200
    category_id = response.json()["data"]["id"]

    # Prepare update data to move the child category to a new parent
    new_parent_data = {
        "name": "Loose Parts",
        "description": "Miscellaneous parts"
    }
    new_parent_response = client.post("/categories/add_category", json=new_parent_data)
    assert new_parent_response.status_code == 200
    new_parent_id = new_parent_response.json()["data"]["id"]

    update_data = {
        "description": "Misc parts"
    }

    # Update the new parent category to include the child category
    response = client.put(f"/categories/update_category/{new_parent_id}", json=update_data)
    assert response.status_code == 200

    # Verify the response data
    response_data = response.json()
    assert response_data["status"] == "success"
    assert f"Category with ID '{new_parent_id}' updated." == response_data["message"]
    assert response_data["data"]["id"] == new_parent_id


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
    response_json = response.json()
    assert response_json["message"] == f"Category with ID '{category_id}' updated."

    # Optional: Verify that the update is correctly reflected in the database
    get_response = client.get("/categories/get_category", params={"category_id": category_id})
    assert get_response.status_code == 200
    get_response_json = get_response.json()
    assert get_response_json["message"] == (f"Category with name '{get_response_json['data']['name']}' retrieved "
                                            f"successfully")
    assert get_response_json["data"]["name"] == update_data["name"]
    assert get_response_json["data"]["description"] == update_data["description"]


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
