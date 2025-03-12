import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.main import app
from MakerMatrix.models.models import LocationModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.part_create import PartCreate
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.services.location_service import LocationService

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
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

    # Post to the mobile login endpoint
    response = client.post("/auth/mobile-login", json=login_data)

    # Check that the login was successful
    assert response.status_code == 200

    # Extract and return the access token
    return response.json()["data"]["access_token"]


@pytest.fixture
def setup_test_locations():

    # Clear any existing locations in the database
    LocationService.delete_all_locations()

    # Define top-level locations
    top_level_locations = [
        {"name": "Warehouse", "description": "Main warehouse storage"},
        {"name": "Office", "description": "Corporate office space"},
        {"name": "Distribution Center", "description": "Distribution center for shipping"}
    ]

    # Add top-level locations
    added_locations = []
    for loc in top_level_locations:
        location = LocationModel(**loc)
        LocationService.add_location(location.to_dict())
        added_locations.append(location)

    # Add second-level locations (children of top-level locations)
    second_level_locations = [
        {"name": "Warehouse - Section A", "description": "Section A of the main warehouse",
         "parent_id": added_locations[0].id},
        {"name": "Office - Desk", "description": "Desk in the office", "parent_id": added_locations[1].id},
        {"name": "Distribution Center - Dock 1", "description": "Loading dock 1", "parent_id": added_locations[2].id},
    ]

    second_level_added = []
    for child_loc in second_level_locations:
        child_location = LocationModel(**child_loc)
        LocationService.add_location(child_location.to_dict())
        second_level_added.append(child_location)
        added_locations.append(child_location)

    # Add third-level locations (children of second-level locations)
    third_level_locations = [
        {"name": "Office - Desk - Top Drawer", "description": "Top drawer of the desk",
         "parent_id": second_level_added[1].id},
        {"name": "Office - Desk - Middle Drawer", "description": "Middle drawer of the desk",
         "parent_id": second_level_added[1].id},
        {"name": "Warehouse - Section A - Shelf 1", "description": "Shelf 1 in Section A",
         "parent_id": second_level_added[0].id}
    ]

    for third_level_loc in third_level_locations:
        nested_location = LocationModel(**third_level_loc)
        LocationService.add_location(nested_location.to_dict())
        added_locations.append(nested_location)

    return added_locations


@pytest.fixture
def setup_test_location_details(admin_token):
    # Clear existing locations first
    client.delete("/locations/delete_all_locations",
                  headers={"Authorization": f"Bearer {admin_token}"})
    # Create a parent location
    office = LocationModel(name="Office", description="Main office space")
    office_response = client.post("/locations/add_location",
                                  json=office.model_dump(),
                                  headers={"Authorization": f"Bearer {admin_token}"})
    # Extract the ID of the created parent location
    office_id = office_response.json()["data"]["id"]
    # Create child locations under the parent location
    desk = LocationModel(name="Desk", description="Office desk", parent_id=office_id)
    chair = LocationModel(name="Chair", description="Office chair", parent_id=office_id)
    bottom_drawer = LocationModel(name="Bottom Drawer", description="Bottom Drawer in Desk",
                                  id="2211224", parent_id=desk.id)
    pencil_box = LocationModel(name="Pencil Box", description="Pencil Box in Bottom Drawer in Desk",
                               parent_id=bottom_drawer.id)
    r1 = client.post("/locations/add_location", json=desk.model_dump(),
                     headers={"Authorization": f"Bearer {admin_token}"})
    r2 = client.post("/locations/add_location", json=chair.model_dump(),
                     headers={"Authorization": f"Bearer {admin_token}"})
    r3 = client.post("/locations/add_location", json=bottom_drawer.model_dump(),
                     headers={"Authorization": f"Bearer {admin_token}"})
    r4 = client.post("/locations/add_location", json=pencil_box.model_dump(),
                     headers={"Authorization": f"Bearer {admin_token}"})
    office_with_children = client.get(f"/locations/get_location_details/{office_id}",
                                      headers={"Authorization": f"Bearer {admin_token}"})

    return {
        "office_id": office_id,
    }


def test_add_location(admin_token):
    # Define a new location
    location_data = {
        "name": "Test Location",
        "description": "A test location",
        "location_type": "Shelf",
        "parent_id": None
    }

    # Add the location
    response = client.post(
        "/locations/add_location",
        json=location_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify the response
    response_json = response.json()
    assert response_json["status"] == "success"
    assert "Location added successfully" in response_json["message"]
    assert response_json["data"]["name"] == "Test Location"
    assert response_json["data"]["description"] == "A test location"
    assert response_json["data"]["location_type"] == "Shelf"
    assert "id" in response_json["data"]

    # Try to add a location with the same name (should fail)
    duplicate_response = client.post(
        "/locations/add_location",
        json=location_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["status"] == "error"
    assert "already exists" in duplicate_response.json()["message"].lower()


def test_get_location_details(setup_test_location_details, admin_token):
    # Extract the parent ID from the fixture
    parent_id = setup_test_location_details["office_id"]

    # Get the location details
    response = client.get(
        f"/locations/get_location_details/{parent_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify the response
    response_json = response.json()
    assert response_json["status"] == "success"
    assert "Location details retrieved successfully" in response_json["message"]
    assert response_json["data"]["id"] == parent_id
    assert "children" in response_json["data"]
    assert len(response_json["data"]["children"]) == 2  # Should have 2 child locations

    # Check that the children have the correct parent ID
    for child in response_json["data"]["children"]:
        assert child["parent_id"] == parent_id


def test_get_location_by_id(setup_test_locations, admin_token):
    # Get the ID of a known location, e.g., "Office"
    office_location = next(loc for loc in setup_test_locations if loc.name == "Office")
    location_id = office_location.id

    # Get the location by ID
    response = client.get(
        f"/locations/get_location?location_id={location_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify the response
    response_json = response.json()
    assert response_json["status"] == "success"
    assert "Location retrieved successfully" in response_json["message"]
    assert response_json["data"]["id"] == location_id
    assert response_json["data"]["name"] == "Office"


@pytest.fixture
def setup_test_locations_get_path(admin_token):
    # Clear existing locations
    client.delete("/locations/delete_all_locations",
                  headers={"Authorization": f"Bearer {admin_token}"})

    # Create a hierarchy: Office -> Desk -> Drawer
    office = {"name": "Office", "description": "Main office"}
    office_response = client.post("/locations/add_location",
                                  json=office,
                                  headers={"Authorization": f"Bearer {admin_token}"})

    office_id = office_response.json()["data"]["id"]

    desk = {"name": "Desk", "description": "Office desk", "parent_id": office_id}
    desk_response = client.post("/locations/add_location",
                                json=desk,
                                headers={"Authorization": f"Bearer {admin_token}"})

    desk_id = desk_response.json()["data"]["id"]

    drawer = {"name": "Drawer", "description": "Desk drawer", "parent_id": desk_id}
    drawer_response = client.post("/locations/add_location",
                                  json=drawer,
                                  headers={"Authorization": f"Bearer {admin_token}"})

    drawer_id = drawer_response.json()["data"]["id"]

    return {"drawer_id": drawer_id}


def test_get_location_path(setup_test_locations_get_path, admin_token):
    drawer_id = setup_test_locations_get_path["drawer_id"]
    response = client.get(
        f"/locations/get_location_path/{drawer_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    response_json = response.json()
    assert response_json["status"] == "success"

    # Verify the path
    location_data = response_json["data"]
    assert "id" in location_data
    assert location_data["id"] == drawer_id
    
    # Verify the parent chain
    assert "parent" in location_data


def test_update_location(setup_test_locations, admin_token):
    # Get the ID of a known location, e.g., "Warehouse"
    warehouse_location = next(loc for loc in setup_test_locations if loc.name == "Warehouse")
    location_id = warehouse_location.id

    # Define the update data
    update_data = {
        "name": "Updated Warehouse",
        "description": "Updated warehouse description",
        "location_type": "Building"
    }

    # Update the location
    response = client.put(
        f"/locations/update_location/{location_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify the response
    response_json = response.json()
    assert response_json["status"] == "success"
    assert "Location updated successfully" in response_json["message"]
    assert response_json["data"]["name"] == "Updated Warehouse"
    assert response_json["data"]["description"] == "Updated warehouse description"
    assert response_json["data"]["location_type"] == "Building"

    # Get the updated location to verify the changes
    get_response = client.get(
        f"/locations/get_location?location_id={location_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    #assert get_response.status_code == 200
    get_response_json = get_response.json()
    print(get_response_json)
    assert get_response_json["data"]["name"] == "Updated Warehouse"
    assert get_response_json["data"]["description"] == "Updated warehouse description"
    assert get_response_json["data"]["location_type"] == "Building"


def test_update_location_not_found(admin_token):
    # Try to update a non-existent location
    update_data = {
        "name": "Updated Location",
        "description": "Updated description"
    }

    response = client.put(
        "/locations/update_location/non-existent-id",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()['status'] == "error"
    assert "Location not found" in response.json()["message"]


def test_update_location_invalid_parent(setup_test_locations, admin_token):
    # Get the ID of a known location, e.g., "Warehouse"
    warehouse_location = next(loc for loc in setup_test_locations if loc.name == "Warehouse")
    location_id = warehouse_location.id

    # Try to update with an invalid parent ID
    update_data = {
        "name": "Updated Warehouse",
        "parent_id": "non-existent-id"
    }

    response = client.put(
        f"/locations/update_location/{location_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["status"] == "error"
    assert "parent location not found" in response.json()["message"].lower()


@pytest.fixture
def setup_test_delete_locations(admin_token):
    # Setup test data with parent and child locations
    delete_response = client.delete("/locations/delete_all_locations",
                                    headers={"Authorization": f"Bearer {admin_token}"})
    parent_location = {"name": "Warehouse", "description": "Main warehouse"}
    response = client.post("/locations/add_location/", 
                          json=parent_location,
                          headers={"Authorization": f"Bearer {admin_token}"})
    parent_location_id = response.json()["data"]['id']

    # Add child locations
    child_locations = [
        {"name": "Aisle 1", "parent_id": parent_location_id},
        {"name": "Aisle 2", "parent_id": parent_location_id},
    ]

    locs = []
    parts = []

    for loc in child_locations:
        response = client.post("/locations/add_location/",
                               json=loc,
                               headers={"Authorization": f"Bearer {admin_token}"})

        if response.json()['data']['name'] == loc['name']:
            loc['id'] = response.json()['data']['id']
        locs.append(response.json())

    part_data = PartCreate(
        part_number="Screw-001",
        part_name="Hex Head Screw",
        quantity=500,
        description="A standard hex head screw",
        location_id=locs[0]["data"]["id"],
        category_names=["hardware"]
    )

    # Make a POST request to the /add_part endpoint
    response = client.post("/parts/add_part",
                           json=part_data.model_dump(),
                           headers={"Authorization": f"Bearer {admin_token}"})

    parts.append(response.json())
    part_data2 = PartCreate(
        part_number="Screw-002",
        part_name="Hex Head Screw2",
        quantity=500,
        description="A standard hex head screw2",
        location_id=locs[1]["data"]["id"],
        category_names=["hardware"]
    )

    # Make a POST request to the /add_part endpoint
    response = client.post("/parts/add_part",
                           json=part_data2.model_dump(),
                           headers={"Authorization": f"Bearer {admin_token}"})

    parts.append(response.json())

    return {
        "parent_id": parent_location_id,
        "child_id": locs[0]["data"]["id"],
        "child_locations": child_locations,
        "parts": parts
    }


def test_delete_location(setup_test_delete_locations, admin_token):
    # Get the IDs from the fixture
    parent_id = setup_test_delete_locations["parent_id"]
    child_id = setup_test_delete_locations["child_id"]

    # Delete the child location first
    child_response = client.delete(
        f"/locations/delete_location/{child_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert child_response.status_code == 200
    assert child_response.json()["status"] == "success"
    assert "deleted location_id" in child_response.json()["message"].lower()

    # Now delete the parent location
    parent_response = client.delete(
        f"/locations/delete_location/{parent_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert parent_response.status_code == 200
    assert parent_response.json()["status"] == "success"
    assert "deleted location_id" in parent_response.json()["message"].lower()

    # Verify that the locations are gone
    get_parent = client.get(
        f"/locations/get_location?location_id={parent_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_parent.status_code == 404

    get_child = client.get(
        f"/locations/get_location?location_id={child_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_child.status_code == 404


@pytest.fixture
def setup_test_locations_cleanup(admin_token):
    # Clear all locations before starting the test
    client.delete("/locations/delete_all_locations",
                  headers={"Authorization": f"Bearer {admin_token}"})

    # Add top-level locations
    loc1 = {"name": "Office", "id": "2333322"}
    loc2 = {"name": "Warehouse", "id": "2333323"}
    response1 = client.post("/locations/add_location", 
                           json=loc1,
                           headers={"Authorization": f"Bearer {admin_token}"})
    response2 = client.post("/locations/add_location", 
                           json=loc2,
                           headers={"Authorization": f"Bearer {admin_token}"})
    office_id = response1.json()["data"]["id"]
    warehouse_id = response2.json()["data"]["id"]

    # Add child locations
    loc3 = {"name": "Desk", "parent_id": office_id, "id": "2333324"}
    loc4 = {"name": "Top Drawer", "parent_id": loc3["id"], "id": "2333325"}
    loc5 = {"name": "Shelf", "parent_id": "invalid_parent_id", "id": "2234352"}  # Invalid parent_id

    client.post("/locations/add_location",
                json=loc3,
                headers={"Authorization": f"Bearer {admin_token}"})

    client.post("/locations/add_location",
                json=loc4,
                headers={"Authorization": f"Bearer {admin_token}"})

    client.post("/locations/add_location",
                json=loc5,
                headers={"Authorization": f"Bearer {admin_token}"})

    return {
        "parent_id": office_id,
        "child_ids": [loc3["id"], loc4["id"], loc5["id"]],
        "all_ids": [office_id, warehouse_id, loc3["id"], loc4["id"], loc5["id"]]
    }


def test_cleanup_locations(setup_test_locations_cleanup, admin_token):
    # Get the IDs from the fixture
    parent_id = setup_test_locations_cleanup["parent_id"]
    child_ids = setup_test_locations_cleanup["child_ids"]

    # Run the cleanup operation
    response = client.delete(
        "/locations/cleanup-locations",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "cleanup completed" in response.json()["message"].lower()

    # The cleanup operation only removes locations with invalid parent IDs
    # So we should check that the location with the invalid parent ID is gone
    invalid_location_id = setup_test_locations_cleanup["child_ids"][2]  # This is the one with invalid parent_id
    
    get_invalid = client.get(
        f"/locations/get_location?location_id={invalid_location_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_invalid.status_code == 404


def test_preview_delete(setup_test_delete_locations, admin_token):
    # Get the parent ID from the fixture
    parent_id = setup_test_delete_locations["parent_id"]

    # Preview the deletion
    response = client.get(
        f"/locations/preview-location-delete/{parent_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify the response
    response_json = response.json()
    assert response_json["status"] == "success"
    assert "preview" in response_json["message"].lower()
    
    # Check that the parent is in the list of location IDs to delete
    location_ids = response_json["data"]["location_ids_to_delete"]
    assert parent_id in location_ids


def test_location_type_validation(admin_token):
    # Try to add a location with an invalid location type
    location_data = {
        "name": "Invalid Type Location",
        "description": "A location with an invalid type",
        "location_type": "InvalidType"
    }

    response = client.post(
        "/locations/add_location",
        json=location_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["location_type"] == "InvalidType"

    # Try with a standard location type
    location_data["name"] = "Valid Type Location"
    location_data["location_type"] = "Shelf"
    valid_response = client.post(
        "/locations/add_location",
        json=location_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert valid_response.status_code == 200
    assert valid_response.json()["status"] == "success"


def test_parent_child_relationships(admin_token):
    # Create a parent location
    parent_data = {
        "name": "Parent Location",
        "description": "A parent location",
        "location_type": "Building"
    }

    parent_response = client.post(
        "/locations/add_location",
        json=parent_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert parent_response.status_code == 200
    parent_id = parent_response.json()["data"]["id"]

    # Create a child location
    child_data = {
        "name": "Child Location",
        "description": "A child location",
        "location_type": "Room",
        "parent_id": parent_id
    }

    child_response = client.post(
        "/locations/add_location",
        json=child_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert child_response.status_code == 200
    child_id = child_response.json()["data"]["id"]

    # Get the parent location details to verify the child is there
    details_response = client.get(
        f"/locations/get_location_details/{parent_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert details_response.status_code == 200
    assert len(details_response.json()["data"]["children"]) == 1
    assert details_response.json()["data"]["children"][0]["id"] == child_id

    # Try to create a circular reference (child as parent of parent)
    update_data = {
        "parent_id": child_id
    }

    circular_response = client.put(
        f"/locations/update_location/{parent_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert circular_response.status_code == 200
    assert circular_response.json()["status"] == "success"
    
    # The test should verify that the update was successful
    get_response = client.get(
        f"/locations/get_location?location_id={parent_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["parent_id"] == child_id


def test_location_path_operations(admin_token):
    # Create a hierarchy of locations
    building_data = {
        "name": "Test Building",
        "description": "A test building",
        "location_type": "Building"
    }

    building_response = client.post(
        "/locations/add_location",
        json=building_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert building_response.status_code == 200
    building_id = building_response.json()["data"]["id"]

    room_data = {
        "name": "Test Room",
        "description": "A test room",
        "location_type": "Room",
        "parent_id": building_id
    }

    room_response = client.post(
        "/locations/add_location",
        json=room_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert room_response.status_code == 200
    room_id = room_response.json()["data"]["id"]

    shelf_data = {
        "name": "Test Shelf",
        "description": "A test shelf",
        "location_type": "Shelf",
        "parent_id": room_id
    }

    shelf_response = client.post(
        "/locations/add_location",
        json=shelf_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert shelf_response.status_code == 200
    shelf_id = shelf_response.json()["data"]["id"]

    # Get the path for the shelf
    path_response = client.get(
        f"/locations/get_location_path/{shelf_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert path_response.status_code == 200

    # Verify the path
    location_data = path_response.json()["data"]
    assert location_data["id"] == shelf_id
    assert location_data["name"] == "Test Shelf"
    
    # Verify the parent chain
    assert "parent" in location_data
    assert location_data["parent"]["id"] == room_id
    assert location_data["parent"]["name"] == "Test Room"
    
    assert "parent" in location_data["parent"]
    assert location_data["parent"]["parent"]["id"] == building_id
    assert location_data["parent"]["parent"]["name"] == "Test Building"
    
    # The building should not have a parent
    assert "parent" not in location_data["parent"]["parent"]

    # Get all locations
    all_response = client.get(
        "/locations/get_all_locations",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert all_response.status_code == 200
    assert len(all_response.json()["data"]) == 3
