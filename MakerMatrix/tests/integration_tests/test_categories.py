import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.schemas.part_create import PartCreate  # Import PartCreate
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.main import app
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Set up the database (tables creation)
    create_db_and_tables()
    
    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    # Login data for the admin user
    login_data = {
        "username": "admin",
        "password": "Admin123!"  # Updated to match the default password in setup_admin.py
    }
    
    # Post to the login endpoint
    response = client.post("/auth/login", json=login_data)
    
    # Check that the login was successful
    assert response.status_code == 200
    
    # Extract and return the access token
    assert "access_token" in response.json()
    return response.json()["access_token"]


def test_add_category(admin_token):
    """Test adding a new category via the API."""
    category_data = {"name": "Test Category", "description": "This is a test category"}
    response = client.post(
        "/categories/add_category/", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print(f"Response body: {response.json()}")  # Debug log
    assert response.status_code == 200
    
    response_json = response.json()
    assert response_json["status"] == "success"
    assert "Category with name 'Test Category' created successfully" in response_json["message"]
    assert response_json["data"]["name"] == "Test Category"
    assert response_json["data"]["description"] == "This is a test category"
    assert "id" in response_json["data"]


def test_remove_category(admin_token):
    category_data = {"name": "Test Category", "description": "This is a test category"}
    response = client.post(
        "/categories/add_category/", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    response_json = response.json()
    # Add a category to ensure it exists before attempting to remove it
    category_id = response_json["data"]["id"]

    # Now attempt to remove the category
    remove_response = client.delete(
        "/categories/remove_category", 
        params={"cat_id": category_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["status"] == "success"


def test_remove_non_existent_category_by_id(admin_token):
    # Attempt to remove a category with a non-existent ID
    response = client.delete(
        "/categories/remove_category", 
        params={"cat_id": "non-existent-id"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_remove_non_existent_category_by_name(admin_token):
    # Attempt to remove a category with a non-existent name
    response = client.delete(
        "/categories/remove_category", 
        params={"name": "Non-Existent Category"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_remove_category_without_id_or_name(admin_token):
    # Attempt to remove a category without providing either ID or name
    response = client.delete(
        "/categories/remove_category",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_delete_all_categories(admin_token):
    # Add a few categories
    client.post(
        "/categories/add_category/", 
        json={"name": "Category 1"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    client.post(
        "/categories/add_category/", 
        json={"name": "Category 2"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Attempt to delete all categories
    response = client.delete(
        "/categories/delete_all_categories",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify that no categories remain
    get_response = client.get(
        "/categories/get_all_categories",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    assert len(get_response.json()["data"]["categories"]) == 0


@pytest.fixture
def setup_test_data_category_update(admin_token):
    # Add a category to set up the initial data for testing
    category_data = {"name": "Test Category", "description": "Initial description"}
    add_response = client.post(
        "/categories/add_category/", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_response.status_code == 200
    return add_response.json()["data"]


def test_update_category(admin_token):
    """Test to update a category via the API."""
    # First, add a category
    category_data = {
        "name": "Electronics",
        "description": "Electronic components"
    }
    response = client.post(
        "/categories/add_category", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    category_id = response.json()["data"]["id"]

    # Now update the category
    update_data = {
        "name": "Electronics",
        "description": "Updated description for electronic components"
    }
    update_response = client.put(
        f"/categories/update_category/{category_id}", 
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_response.status_code == 200
    
    # Verify the update
    get_response = client.get(
        f"/categories/get_category?category_id={category_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    updated_category = get_response.json()["data"]
    assert updated_category["description"] == "Updated description for electronic components"


def test_update_category_name(setup_test_data_category_update, admin_token):
    # Retrieve the category ID from the setup
    category_id = setup_test_data_category_update["id"]
    
    # Update the category name
    update_data = {
        "name": "Updated Category Name",
        "description": "Initial description"
    }
    update_response = client.put(
        f"/categories/update_category/{category_id}", 
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_response.status_code == 200
    
    # Verify the update
    get_response = client.get(
        f"/categories/get_category?category_id={category_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    updated_category = get_response.json()["data"]
    assert updated_category["name"] == "Updated Category Name"


@pytest.fixture
def setup_categories_for_get_categories(admin_token):
    # Add some unique categories for testing
    categories = [
        {"name": "Electronics", "description": "Devices and components related to electronics"},
        {"name": "Mechanical Parts", "description": "Gears, screws, and other mechanical components"},
        {"name": "Software Tools", "description": "Tools and software utilities for development"},
    ]

    added_categories = []
    for category_data in categories:
        response = client.post(
            "/categories/add_category/", 
            json=category_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        added_categories.append(response.json()["data"])
    
    return added_categories


def test_get_category_by_id(setup_categories_for_get_categories, admin_token):
    # Use the first category added in the fixture
    category_id = setup_categories_for_get_categories[0]["id"]
    
    # Get the category by ID
    response = client.get(
        f"/categories/get_category?category_id={category_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify the response
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["data"]["id"] == category_id
    assert response_data["data"]["name"] == "Electronics"


def test_get_category_by_name(setup_categories_for_get_categories, admin_token):
    # Use the name of the second category added in the fixture
    category_name = setup_categories_for_get_categories[1]["name"]
    
    # Get the category by name
    response = client.get(
        f"/categories/get_category?name={category_name}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify the response
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["data"]["name"] == category_name
    assert response_data["data"]["description"] == "Gears, screws, and other mechanical components"


def test_get_all_categories(admin_token):
    # First test with no categories
    response = client.get(
        "/categories/get_all_categories/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["categories"]) == 0
    
    # Add some categories
    categories = [
        {"name": "Category 1", "description": "Description 1"},
        {"name": "Category 2", "description": "Description 2"},
        {"name": "Category 3", "description": "Description 3"},
    ]
    
    for category_data in categories:
        client.post(
            "/categories/add_category/", 
            json=category_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    # Get all categories
    response = client.get(
        "/categories/get_all_categories/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify the response
    response_data = response.json()
    assert response_data["status"] == "success"
    assert len(response_data["data"]["categories"]) == 3
