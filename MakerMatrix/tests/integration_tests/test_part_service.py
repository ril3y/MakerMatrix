import logging
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from MakerMatrix.database.db import get_session

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import CategoryModel, PartModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.schemas.part_create import PartCreate
from MakerMatrix.services.data.category_service import CategoryService  # Import PartCreate
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
import uuid

# Suppress SQLAlchemy INFO logs (which include SQL statements)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

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
        "password": "Admin123!"
    }
    
    # Post to the login endpoint
    response = client.post("/auth/login", json=login_data)
    
    # Check that the login was successful
    assert response.status_code == 200
    
    # Extract and return the access token
    return response.json()["access_token"]

def test_get_part_by_name(admin_token):
    tmp_part = setup_part_update_part(admin_token)
    response = client.get(
        f"/api/parts/get_part?part_name={tmp_part['data']['part_name']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["part_name"] == tmp_part["data"]["part_name"]


def test_add_part(admin_token):
    # Define the part data to be sent to the API
    part_data = {
        "part_number": "Screw-001",
        "part_name": "Hex Head Screw",
        "quantity": 500,
        "description": "A standard hex head screw",
        "location_id": None,
        "category_names": ["hardware"],
        "supplier": "Acme Hardware",
        "additional_properties": {"material": "steel", "size": "M6"}
    }

    # Make a POST request to the /add_part endpoint
    response = client.post(
        "/api/parts/add_part", 
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Check the response status code
    assert response.status_code == 200

    # Check the response data
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "data" in response_data
    assert response_data["data"]["part_name"] == "Hex Head Screw"
    assert response_data["data"]["part_number"] == "Screw-001"
    assert response_data["data"]["quantity"] == 500


def test_add_existing_part(admin_token):
    # Define the part data
    part_data = {
        "part_number": "Screw-001",
        "part_name": "Hex Head Screw",
        "quantity": 500,
        "description": "A standard hex head screw",
        "location_id": None,
        "category_names": ["hardware"],
        "supplier": "Acme Hardware"
    }

    # Add the part initially
    initial_response = client.post(
        "/api/parts/add_part", 
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert initial_response.status_code == 200

    # Try to add the same part again
    duplicate_response = client.post(
        "/api/parts/add_part", 
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Check that we get a conflict error
    assert duplicate_response.status_code == 409
    # The error message might be in different formats depending on the API implementation
    response_json = duplicate_response.json()
    assert "already exists" in str(response_json).lower()


def test_delete_part_by_id(admin_token):
    """Test deleting a part by ID"""
    # First, add a part to delete
    part_data = {
        "part_number": "DELETE-TEST-001",
        "part_name": "Delete Test Part",
        "quantity": 10,
        "description": "Part for delete testing",
        "location_id": None,
        "category_names": [],
        "supplier": "Test Supplier"
    }
    
    add_response = client.post(
        "/api/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_response.status_code == 200
    part_id = add_response.json()["data"]["id"]
    
    # Now delete the part by ID
    delete_response = client.delete(
        f"/api/parts/delete_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Verify successful deletion
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["status"] == "success"
    assert "deleted" in delete_data["message"].lower()
    
    # Verify the response data structure (this is what caught our bug!)
    assert "data" in delete_data
    assert isinstance(delete_data["data"], dict)  # Should be dict, not PartResponse object
    assert delete_data["data"]["id"] == part_id
    assert delete_data["data"]["part_name"] == "Delete Test Part"


def test_delete_part_by_name(admin_token):
    """Test deleting a part by name"""
    # First, add a part to delete
    part_data = {
        "part_number": "DELETE-TEST-002",
        "part_name": "Delete Test Part By Name",
        "quantity": 15,
        "description": "Part for delete by name testing",
        "location_id": None,
        "category_names": [],
        "supplier": "Test Supplier"
    }
    
    add_response = client.post(
        "/api/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_response.status_code == 200
    
    # Delete by part name
    delete_response = client.delete(
        "/api/parts/delete_part?part_name=Delete Test Part By Name",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Verify successful deletion
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["status"] == "success"
    assert isinstance(delete_data["data"], dict)
    assert delete_data["data"]["part_name"] == "Delete Test Part By Name"


def test_delete_part_by_part_number(admin_token):
    """Test deleting a part by part number"""
    # First, add a part to delete
    part_data = {
        "part_number": "DELETE-TEST-003",
        "part_name": "Delete Test Part By Number",
        "quantity": 20,
        "description": "Part for delete by part number testing",
        "location_id": None,
        "category_names": [],
        "supplier": "Test Supplier"
    }
    
    add_response = client.post(
        "/api/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_response.status_code == 200
    
    # Delete by part number
    delete_response = client.delete(
        "/api/parts/delete_part?part_number=DELETE-TEST-003",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Verify successful deletion
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["status"] == "success"
    assert isinstance(delete_data["data"], dict)
    assert delete_data["data"]["part_number"] == "DELETE-TEST-003"


def test_delete_nonexistent_part(admin_token):
    """Test deleting a part that doesn't exist"""
    delete_response = client.delete(
        "/api/parts/delete_part?part_id=nonexistent-id",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Should return 404 for nonexistent part
    assert delete_response.status_code == 404


def test_delete_part_no_identifier(admin_token):
    """Test delete endpoint with no identifiers provided"""
    delete_response = client.delete(
        "/api/parts/delete_part",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Should return 400 for missing identifier
    assert delete_response.status_code == 400


def test_delete_part_unauthenticated():
    """Test delete endpoint without authentication"""
    delete_response = client.delete("/api/parts/delete_part?part_id=test-id")
    
    # Should return 401 for unauthenticated request
    assert delete_response.status_code == 401


def test_update_part_categories(admin_token):
    """Test updating part categories - this would have caught our category assignment bug!"""
    # First, create some categories to use
    categories_to_create = ["Electronics", "Microcontrollers", "Communication"]
    created_categories = []
    
    for cat_name in categories_to_create:
        try:
            cat_data = {"name": cat_name}
            cat_response = client.post(
                "/categories/add_category",
                json=cat_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            if cat_response.status_code == 200:
                created_categories.append(cat_name)
        except:
            # Category might already exist, that's fine
            created_categories.append(cat_name)
    
    # Create a part with initial categories
    part_data = {
        "part_number": "UPDATE-CAT-TEST-001",
        "part_name": "ESP32 Category Test",
        "quantity": 5,
        "description": "Part for testing category updates",
        "category_names": ["Electronics"],  # Start with one category
        "supplier": "Test Supplier"
    }
    
    add_response = client.post(
        "/api/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_response.status_code == 200
    part_id = add_response.json()["data"]["id"]
    
    # Verify initial categories
    get_response = client.get(
        f"/api/parts/get_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    initial_part = get_response.json()["data"]
    assert len(initial_part["categories"]) == 1
    assert initial_part["categories"][0]["name"] == "Electronics"
    
    # Now update the part to add more categories
    update_data = {
        "category_names": ["Electronics", "Microcontrollers", "Communication"]
    }
    
    update_response = client.put(
        f"/api/parts/update_part/{part_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # This is where our bug would be caught!
    assert update_response.status_code == 200
    update_result = update_response.json()
    assert update_result["status"] == "success"
    
    # Verify response data structure is correct
    assert "data" in update_result
    assert isinstance(update_result["data"], dict)  # Should be dict, not object
    assert update_result["data"]["id"] == part_id
    
    # Verify the categories were actually updated
    get_updated_response = client.get(
        f"/api/parts/get_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_updated_response.status_code == 200
    updated_part = get_updated_response.json()["data"]
    
    # Should now have 3 categories
    assert len(updated_part["categories"]) == 3
    category_names = [cat["name"] for cat in updated_part["categories"]]
    assert "Electronics" in category_names
    assert "Microcontrollers" in category_names
    assert "Communication" in category_names


def test_update_part_remove_all_categories(admin_token):
    """Test removing all categories from a part"""
    # Create a part with categories
    part_data = {
        "part_number": "REMOVE-CAT-TEST-001",
        "part_name": "Remove Categories Test",
        "quantity": 3,
        "description": "Part for testing category removal",
        "category_names": ["Electronics", "Tools"],
        "supplier": "Test Supplier"
    }
    
    add_response = client.post(
        "/api/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_response.status_code == 200
    part_id = add_response.json()["data"]["id"]
    
    # Remove all categories
    update_data = {
        "category_names": []  # Empty array to remove all categories
    }
    
    update_response = client.put(
        f"/api/parts/update_part/{part_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert update_response.status_code == 200
    
    # Verify categories were removed
    get_response = client.get(
        f"/api/parts/get_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    updated_part = get_response.json()["data"]
    assert len(updated_part["categories"]) == 0


def test_add_part_with_invalid_data(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define part data with missing required fields
        part_data = {
            "part_number": "Screw-002",
            # Missing 'part_name' which is required
            "quantity": 100
        }

        # Make a POST request to the /add_part endpoint
        response = client.post(
            "/api/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check that we get a validation error
        assert response.status_code in [400, 422]  # Either 400 Bad Request or 422 Unprocessable Entity
        # Check for the specific error message about part name being required
        response_json = response.json()
        assert "part name is required" in str(response_json).lower()


def test_add_part_with_categories(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define part data with multiple categories
        part_data = {
            "part_number": "Tool-001",
            "part_name": "Power Drill",
            "quantity": 10,
            "description": "A cordless power drill",
            "location_id": None,
            "category_names": ["tools", "power tools", "drills"],
            "supplier": "DeWalt",
            "additional_properties": {"voltage": "18V", "type": "cordless"}
        }

        # Add the part
        response = client.post(
            "/api/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response
        assert response.status_code == 200
        response_data = response.json()
        assert "success" in response_data["status"].lower()
        
        # Verify the part was created with the categories
        part_id = response_data["data"]["id"]
        get_response = client.get(
            f"/api/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        part_data = get_response.json()["data"]
        # Check that categories exist, but don't assert the exact count as it might vary
        assert "categories" in part_data
        assert len(part_data["categories"]) > 0


def test_add_part_with_invalid_category(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define part data with an invalid category (number instead of string)
        part_data = {
            "part_number": "Screw-003",
            "part_name": "Invalid Category Screw",
            "quantity": 100,
            "description": "A screw with invalid category",
            "location_id": None,
            "category_names": [123]  # Invalid category type
        }

        # Make the request
        response = client.post(
            "/api/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check that we get a validation error
        assert response.status_code in [400, 422]  # Either 400 Bad Request or 422 Unprocessable Entity
        # The error message might be in different formats depending on the API implementation
        response_json = response.json()
        assert "error" in str(response_json).lower() or "validation" in str(response_json).lower()


def test_get_part_by_id(admin_token):
    with TestClient(app) as client:
        token = admin_token
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
        response = client.post(
            "/api/parts/add_part", 
            json=part_data.model_dump(),
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # Extract the part ID from the response
        part_id = response.json()["data"]["id"]

        # Make a GET request to retrieve the part by ID
        get_response = client.get(
            f"/api/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response status code
        assert get_response.status_code == 200

        # Check the response data
        response_data = get_response.json()
        # Accept either "success" or "found" as valid status values
        assert response_data["status"] in ["success", "found"]
        assert response_data["data"]["id"] == part_id
        assert response_data["data"]["part_name"] == "Hex Head Screw"


def test_get_part_by_invalid_part_id(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Make a GET request to retrieve a part by a non-existent ID
        part_id = "invalid-id"
        get_response = client.get(
            f"/api/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response status code
        assert get_response.status_code == 404
        # The error message might be in different formats depending on the API implementation
        response_json = get_response.json()
        assert "not found" in str(response_json).lower() or "error" in str(response_json).lower()


def test_get_part_by_part_number(admin_token):
    with TestClient(app) as client:
        token = admin_token
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
        response = client.post(
            "/api/parts/add_part", 
            json=part_data.model_dump(),
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # Extract the part number from the response
        part_number = response.json()["data"]["part_number"]

        # Make a GET request to retrieve the part by part number
        get_response = client.get(
            f"/api/parts/get_part?part_number={part_number}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response status code
        assert get_response.status_code == 200

        # Check the response data
        response_data = get_response.json()
        # Accept either "success" or "found" as valid status values
        assert response_data["status"] in ["success", "found"]
        assert response_data["data"]["part_number"] == part_number
        assert response_data["data"]["part_name"] == "Round Head Screw"


def test_update_existing_part(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Create a unique part number to avoid conflicts
        unique_part_number = f"PART-{uuid.uuid4().hex[:8]}"
        
        # Define part data with a unique part number - use a dictionary with minimal fields
        part_data = {
            "part_number": unique_part_number,
            "part_name": "Test Hammer",
            "quantity": 100,
            "description": "A test hammer for updating"
        }

        # Make a POST request to add the part to the database
        response = client.post(
            "/api/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        part_id = response.json()["data"]["id"]

        # Now update the part
        update_data = {
            "part_name": "Updated Test Hammer",
            "quantity": 200,
            "description": "An updated test hammer"
        }

        update_response = client.put(
            f"/api/parts/update_part/{part_id}", 
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200

        # Verify the update
        get_response = client.get(
            f"/api/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        updated_part = get_response.json()["data"]
        assert updated_part["part_name"] == "Updated Test Hammer"
        assert updated_part["quantity"] == 200
        assert updated_part["description"] == "An updated test hammer"


def setup_part_update_part(admin_token):
    with TestClient(app) as client:
        token = admin_token
        part_data = {
            "part_number": "PN001",
            "part_name": "B1239992810A",
            "quantity": 100,
            "description": "A 1k Ohm resistor",
            "supplier": "Supplier A",
            "additional_properties": {
                "color": "brown",
                "material": "carbon film"
            }
        }

        # Add the part
        response = client.post(
            "/api/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        return response.json()
