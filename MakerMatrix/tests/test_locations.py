import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.schemas.part_create import PartCreate
from MakerMatrix.models.models import LocationModel
from MakerMatrix.services.location_service import LocationService


client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()
    yield  # Let the tests run
    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)



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
def setup_test_location_details():
    # Clear existing locations first
    client.delete("/locations/delete_all_locations")
    # Create a parent location
    office = LocationModel(name="Office", description="Main office space")
    office_response = client.post("/locations/add_location", json=office.model_dump())
    # Extract the ID of the created parent location
    office_id = office_response.json()["data"]["id"]
    # Create child locations under the parent location
    desk = LocationModel(name="Desk", description="Office desk", parent_id=office_id)
    chair = LocationModel(name="Chair", description="Office chair", parent_id=office_id)
    bottom_drawer = LocationModel(name="Bottom Drawer", description="Bottom Drawer in Desk",
                                  id="2211224", parent_id=desk.id)
    pencil_box = LocationModel(name="Pencil Box", description="Pencil Box in Bottom Drawer in Desk",
                               parent_id=bottom_drawer.id)
    r1 = client.post("/locations/add_location", json=desk.model_dump())
    r2 = client.post("/locations/add_location", json=chair.model_dump())
    r3 = client.post("/locations/add_location", json=bottom_drawer.model_dump())
    r4 = client.post("/locations/add_location", json=pencil_box.model_dump())
    office_with_children = client.get(f"/locations/get_location_details/{office_id}")

    return {
        "office_id": office_id,
    }


def test_add_location():
    """Test to add a location via the API."""
    location_data = {
        "name": "Warehouse",
        "description": "Main warehouse storage",
        "location_type": "storage"
    }

    # Add the location using the API
    response = client.post("/locations/add_location", json=location_data)
    assert response.status_code == 200

    # Verify the response data
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["message"] == "Location added successfully"
    assert response_data["data"]["id"] is not None
    assert response_data["data"]["name"] == location_data["name"]
    assert response_data["data"]["description"] == location_data["description"]
    assert response_data["data"]["location_type"] == location_data["location_type"]

    # Verify that the location can be retrieved from the database
    location_id = response_data["data"]["id"]
    retrieved_response = client.get(f"/locations/get_location_details/{location_id}")
    assert retrieved_response.status_code == 200
    retrieved_data = retrieved_response.json()
    assert retrieved_data["data"]["id"] == location_id
    assert retrieved_data["data"]["name"] == location_data["name"]
    assert retrieved_data["data"]["description"] == location_data["description"]
    assert retrieved_data["data"]["location_type"] == location_data["location_type"]


def test_get_location_details(setup_test_location_details):
    # Extract the parent ID from the fixture
    office_id = setup_test_location_details["office_id"]
    # Make a request to get the location details for the parent location
    response = client.get(f"/locations/get_location_details/{office_id}")
    assert response.status_code == 200
    # Get the location details from the response
    location_details = response.json()
    # Assert the parent location information
    assert location_details["data"]["id"] == office_id
    assert location_details["data"]["name"] == "Office"
    assert location_details["data"]["description"] == "Main office space"
    # Assert that the children locations are present
    children = location_details["data"]["children"]
    assert len(children) == 2
    # Check that each child has the correct parent_id and is one of the expected children
    expected_children = {"Desk", "Chair"}
    for child in children:
        assert child["parent_id"] == office_id
        assert child["name"] in expected_children


def test_get_location_by_id(setup_test_locations):
    # Get the ID of a known location, e.g., "Office"
    office_location = next((loc for loc in setup_test_locations if loc.name == "Office"), None)
    assert office_location is not None

    response = client.get("/locations/get_location", params={"location_id": office_location.id})
    assert response.status_code == 200
    res = response.json()
    assert res["data"]["name"] == "Office"


@pytest.fixture
def setup_test_locations_get_path():
    # Clear existing locations
    client.delete("/locations/delete_all_locations")
    
    # Create a hierarchy: Office -> Desk -> Drawer
    office = {"name": "Office", "description": "Main office"}
    office_response = client.post("/locations/add_location", json=office)
    office_id = office_response.json()["data"]["id"]
    
    desk = {"name": "Desk", "description": "Office desk", "parent_id": office_id}
    desk_response = client.post("/locations/add_location", json=desk)
    desk_id = desk_response.json()["data"]["id"]
    
    drawer = {"name": "Drawer", "description": "Desk drawer", "parent_id": desk_id}
    drawer_response = client.post("/locations/add_location", json=drawer)
    drawer_id = drawer_response.json()["data"]["id"]
    
    return {"drawer_id": drawer_id}


def test_get_location_path(setup_test_locations_get_path):
    # Use the drawer ID for testing
    drawer_id = setup_test_locations_get_path["drawer_id"]
    
    # Make a GET request to get the path for the drawer
    response = client.get(f"/locations/get_location_path/{drawer_id}")
    
    # Check the status code
    assert response.status_code == 200
    
    # Check the content of the response
    response_data = response.json()
    
    # Debug: Print error message if status is error
    if response_data["status"] == "error":
        print(f"Error message: {response_data['message']}")
    
    # Check the response structure matches our standard format
    assert response_data["status"] == "success"  # Keep consistent with other location endpoints
    assert "Location path retrieved" in response_data["message"]
    
    # Get the path data
    path_data = response_data["data"]
    
    # Validate that the path is correct (Drawer -> Desk -> Office)
    assert path_data["location"]["name"] == "Drawer"
    assert path_data["parent"]["location"]["name"] == "Desk"
    assert path_data["parent"]["parent"]["location"]["name"] == "Office"
    assert path_data["parent"]["parent"]["parent"] is None  # Root level


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
    assert data["data"]["name"] == "Updated Office"
    assert data["data"]["description"] == "Updated description for office location"


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
    delete_response = client.delete("/locations/delete_all_locations")
    parent_location = {"name": "Warehouse", "description": "Main warehouse"}
    response = client.post("/locations/add_location/", json=parent_location)
    parent_location_id = response.json()["data"]['id']

    # Add child locations
    child_locations = [
        {"name": "Aisle 1", "parent_id": parent_location_id},
        {"name": "Aisle 2", "parent_id": parent_location_id},
    ]

    locs = []
    parts = []

    for loc in child_locations:
        response = client.post("/locations/add_location/", json=loc)
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
    response = client.post("/parts/add_part", json=part_data.dict())
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
    response = client.post("/parts/add_part", json=part_data2.dict())
    parts.append(response.json())

    return parent_location_id, child_locations, parts


def test_delete_location(setup_test_delete_locations):
    parent_location_id, child_locations, parts = setup_test_delete_locations

    # check preview delete
    response = client.get(f"/locations/preview-location-delete/{parent_location_id}")
    assert response.status_code == 200
    preview_json = response.json()
    assert preview_json['data']['affected_parts_count'] == 2
    assert len(preview_json['data']['location_ids_to_delete']) == 3
    assert preview_json['data']['location_hierarchy']['name'] == "Warehouse"

    # Call delete_location route
    response = client.delete(f"/locations/delete_location/{parent_location_id}")
    assert response.status_code == 200

    # Check the response data
    res_json = response.json()
    assert f"Deleted location_id: {parent_location_id}" in res_json["message"]
    assert res_json['data']["deleted_location_id"] == parent_location_id
    assert res_json['data']["deleted_location_name"] == "Warehouse"

    # Verify that the location and its children are removed
    for child in child_locations:
        response = client.get(f"/locations/get_location?location_id={child['id']}")
        assert response.status_code == 404

    # Verify that the parent location is removed
    response = client.get(f"/locations/get_location?location_id={parent_location_id}")
    assert response.status_code == 404
    assert response.json()["message"] == f"Location {parent_location_id} not found"

    for part in parts:
        res = client.get(f"/parts/get_part?part_id={part['data']['id']}")
        assert res.status_code == 200
        assert res.json()['data']['location_id'] is None


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
    """
    Test the cleanup_locations endpoint that removes locations with invalid parent IDs.
    """
    # Get the list of location IDs from the fixture
    location_ids = setup_test_locations_cleanup
    
    # Make a request to cleanup locations
    response = client.delete("/locations/cleanup-locations")
    
    # Check the status code
    assert response.status_code == 200
    
    # Check the response structure
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "Cleanup completed" in response_data["message"]
    assert "deleted_count" in response_data["data"]
    
    # Verify that the invalid location (with invalid parent_id) is deleted
    invalid_location_response = client.get(f"/locations/get_location?location_id={location_ids[4]}")
    assert invalid_location_response.status_code == 404
    
    # Verify that valid locations still exist
    for valid_id in location_ids[:4]:  # First 4 locations are valid
        valid_location_response = client.get(f"/locations/get_location?location_id={valid_id}")
        assert valid_location_response.status_code == 200
        assert valid_location_response.json()["status"] == "success"


def test_edit_location():
    """Test editing a location's fields."""
    # First create a location to edit
    location_data = {
        "name": "Test Location",
        "description": "Test Description",
        "parent_id": None
    }
    response = client.post("/locations/add_location", json=location_data)
    assert response.status_code == 200
    location_id = response.json()["data"]["id"]
    
    # Edit the location
    edit_data = {
        "name": "Updated Location",
        "description": "Updated Description"
    }
    response = client.put(f"/locations/edit_location/{location_id}", params=edit_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["name"] == "Updated Location"
    assert data["data"]["description"] == "Updated Description"
    
    # Verify the changes persist using the correct endpoint
    response = client.get("/locations/get_location", params={"location_id": location_id})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "Updated Location"
    assert data["data"]["description"] == "Updated Description"
