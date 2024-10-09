import pytest
from fastapi.testclient import TestClient

from main import app
from models.location_model import LocationModel
from services.location_service import LocationService

client = TestClient(app)


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
        LocationService.add_location(location)
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
        LocationService.location_repo.add_location(child_location)
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
        LocationService.location_repo.add_location(nested_location)
        added_locations.append(nested_location)

    return added_locations


@pytest.fixture
def setup_test_location_details():
    # Clear existing locations first
    client.delete("/locations/delete_all_locations")

    # Create a parent location
    office = LocationModel(name="Office", description="Main office space")
    office_response = client.post("/locations/add_location", json=office.dict())

    # Extract the ID of the created parent location
    office_id = office_response.json()["data"]["id"]

    # Create child locations under the parent location
    desk = LocationModel(name="Desk", description="Office desk", parent_id=office_id, id="12345")
    chair = LocationModel(name="Chair", description="Office chair", parent_id=office_id)

    bottom_drawer = LocationModel(name="Bottom Drawer", description="Bottom Drawer in Desk",
                                  id="2211224", parent_id=desk.id)
    pencil_box = LocationModel(name="Pencil Box", description="Pencil Box in Bottom Drawer in Desk",
                               parent_id=bottom_drawer.id)

    client.post("/locations/add_location", json=desk.dict())
    client.post("/locations/add_location", json=chair.dict())
    client.post("/locations/add_location", json=bottom_drawer.dict())
    client.post("/locations/add_location", json=pencil_box.dict())

    return {
        "office_id": office_id,
    }


def test_get_location_details(setup_test_location_details):
    # Extract the parent ID from the fixture
    office_id = setup_test_location_details["office_id"]

    # Make a request to get the location details for the parent location
    response = client.get(f"/locations/get_location_details/{office_id}")
    assert response.status_code == 200

    # Get the location details from the response
    location_details = response.json()

    # Assert the parent location information
    assert location_details["id"] == office_id
    assert location_details["name"] == "Office"
    assert location_details["description"] == "Main office space"

    # Assert that the children locations are present
    children = location_details.get("children", [])
    assert len(children) == 2

    # Check that each child has the correct parent_id and is one of the expected children
    expected_children = {"Desk", "Chair"}
    for child in children:
        assert child["parent_id"] == office_id
        assert child["name"] in expected_children
        expected_children.remove(child["name"])


def test_get_location_by_id(setup_test_locations):
    # Get the ID of a known location, e.g., "Office"
    office_location = next((loc for loc in setup_test_locations if loc.name == "Office"), None)
    assert office_location is not None

    response = client.get("/locations/get_location", params={"id": office_location.id})
    assert response.status_code == 200
    res = response.json()
    assert res["data"]["name"] == "Office"


# def test_get_location_path(setup_test_locations_get_path):
#     # Use the drawer ID for testing
#     drawer_id = setup_test_locations_get_path["drawer_id"]
#
#     # Make a GET request to get the path for the drawer
#     response = client.get(f"/locations/get_location_path/{drawer_id}")
#
#     # Check the status code
#     assert response.status_code == 200
#
#     # Check the content of the response
#     path_data = response.json()["path"]
#
#     # Validate that the path is correct (Drawer -> Desk -> Office)
#     assert path_data["location"]["name"] == "Drawer"
#     assert path_data["parent"]["location"]["name"] == "Desk"
#     assert path_data["parent"]["parent"]["location"]["name"] == "Office"
#     assert path_data["parent"]["parent"]["parent"] is None  # Root level


def test_update_location(setup_test_locations):
    # Get a location from the setup
    location_to_update = setup_test_locations[1]
    location_id = location_to_update.id

    # Prepare the update data
    update_data = {
        "name": "Updated Office",
        "description": "Updated description for office location"
    }
    # Make the PUT request
    response = client.put(f"/locations/update_location/{location_id}", json=update_data)

    # Assert the status code and response
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Location updated"
    assert data["location"]["name"] == "Updated Office"
    assert data["location"]["description"] == "Updated description for office location"


def fail_test_update_location():
    # Get a location from the setup
    location_id = "1234"

    # Prepare the update data
    update_data = {
        "name": "Missing ID Test Office",
        "description": "Updated description for office location"
    }
    # Make the PUT request
    response = client.put(f"/locations/update_location/{location_id}", json=update_data)

    # Assert the status code and response
    assert response.status_code == 404
    assert response.json()["detail"] == "Location not found"


@pytest.fixture
def setup_test_delete_locations():
    # Setup test data with parent and child locations
    client.delete("/locations/delete_all_locations")
    parent_location = {"name": "Warehouse", "description": "Main warehouse"}
    response = client.post("/locations/add_location/", json=parent_location)
    parent_location_id = response.json()["data"]['id']

    # Add child locations
    child_locations = [
        {"name": "Aisle 1", "id": "54321", "parent_id": parent_location_id},
        {"name": "Aisle 2", "id": "12345", "parent_id": parent_location_id},
    ]

    for loc in child_locations:
        client.post("/locations/add_location/", json=loc)

    return parent_location_id, child_locations


def test_delete_location(setup_test_delete_locations):
    parent_location_id, child_locations = setup_test_delete_locations

    # Call delete_location route
    response = client.delete(f"/locations/delete_location/{parent_location_id}")
    assert response.status_code == 200

    # Check the response data
    data = response.json()
    assert data["message"] == "Location and its children deleted successfully"
    assert data["deleted_location"] == parent_location_id
    assert data["deleted_children_count"] == len(child_locations)

    # Verify that the location and its children are removed
    for child in child_locations:
        response = client.get(f"/locations/get_location?id={child['id']}")
        assert response.status_code == 404

    # Verify that the parent location is removed
    response = client.get(f"/locations/get_location?id={parent_location_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Location not found"


@pytest.fixture
def setup_test_locations_cleanup():
    # Clear all locations before starting the test
    client.delete("/locations/delete_all_locations")

    # Add top-level locations
    loc1 = {"name": "Office", "id": "2333322"}
    loc2 = {"name": "Warehouse", "id": "2333323"}
    response1 = client.post("/locations/add_location", json=loc1)
    response2 = client.post("/locations/add_location", json=loc2)
    office_id = response1.json()["data"]["id"]
    warehouse_id = response2.json()["data"]["id"]

    # Add child locations
    loc3 = {"name": "Desk", "parent_id": office_id, "id": "2333324"}
    loc4 = {"name": "Top Drawer", "parent_id": loc3["id"], "id": "2333325"}
    loc5 = {"name": "Shelf", "parent_id": "invalid_parent_id", "id": "2234352"}  # Invalid parent_id
    client.post("/locations/add_location", json=loc3)
    client.post("/locations/add_location", json=loc4)
    client.post("/locations/add_location", json=loc5)

    return [office_id, warehouse_id, loc3["id"], loc4["id"], loc5["id"]]


def test_cleanup_locations(setup_test_locations_cleanup):
    # Call the cleanup endpoint
    response = client.delete("/locations/cleanup-locations")
    assert response.status_code == 200

    res = response.json()
    assert res["message"] == "Cleanup completed"
    assert res["deleted_locations_count"] == 1  # Expecting one invalid location to be deleted

    # Verify that the invalid location is deleted
    invalid_location_id = setup_test_locations_cleanup[-1]
    get_response = client.get(f"/locations/get_location/{invalid_location_id}")
    assert get_response.status_code == 404
