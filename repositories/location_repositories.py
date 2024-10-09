import uuid
from typing import Dict, Optional, List

from models.location_model import LocationModel, LocationQueryModel
from repositories.base_repository import BaseRepository
from repositories.parts_repositories import PartRepository
from services.part_service import PartService


class LocationRepository(BaseRepository):
    def __init__(self):
        super().__init__('locations')

    def get_all_locations(self):
        return self.table.all()

    def delete_all_locations(self) -> dict:
        try:
            self.table.truncate()
            return {"status": "success", "message": "All locations removed successfully"}

        except Exception as e:
            return {"status": "error", "message": f"Error truncating locations table: {str(e)}"}

    def update_location(self, location_id: str, update_data: dict) -> Optional[dict]:
        # Find the location by id
        location = self.table.get(self.query().id == location_id)
        if not location:
            return None

        # Remove 'id' from update_data to prevent overwriting the existing ID
        if 'id' in update_data:
            del update_data['id']

        # Update the location while keeping the existing ID
        self.table.update(update_data, self.query().id == location_id)

        # Retrieve the updated location to return it
        updated_location = self.table.get(self.query().id == location_id)
        return updated_location

    def get_location(self, location: LocationQueryModel) -> Optional[Dict]:
        # If location ID is provided, search by ID
        if location.id:
            return self.table.get(self.query().id == location.id)
        # If location name is provided, search by name
        elif location.name:
            return self.table.get(self.query().name == location.name)
        else:
            return None

    def add_location(self, location: LocationModel) -> Dict:
        # Check if a location with the same name already exists
        existing_location = self.table.get(self.query().name == location.name)
        if existing_location:
            return {"status": "exists", "message": f"Location '{location.name}' already exists.",
                    "data": existing_location}

        # Assign a unique ID if not already set
        if not location.id:
            location.id = str(uuid.uuid4())

        # Convert the LocationModel instance to a dictionary
        location_data = location.dict()

        # Insert the location data into the database
        self.table.insert(location_data)

        return {"status": "success", "message": "Location added successfully.", "data": location_data}

    def delete_location(self, location_id: str) -> bool:
        """
        Deletes a location by ID.
        """
        result = self.table.remove(self.query().id == location_id)
        return len(result) > 0

    def get_location_details(self, parent_id):
        """
        Recursively retrieves the parent location and all child locations for a given parent location.

        :param parent_id: The ID of the parent location.
        :return: A nested JSON structure of the parent location with its children.
        """

        def fetch_children(location_id):
            # Retrieve all children of the current location
            children = self.table.search(self.query().parent_id == location_id)

            # For each child, recursively find its children
            for child in children:
                child['children'] = fetch_children(child['id'])
            return children

        # Fetch the parent location details
        parent = self.table.get(self.query().id == parent_id)
        if parent is None:
            return None  # If no parent is found, return None

        # Attach all children to the parent location
        parent['children'] = fetch_children(parent_id)
        return parent



    def get_child_locations(self, location_id: str) -> List[Dict]:
        """
        Retrieve all child locations for the given location ID.
        """

        def fetch_children(loc_id):
            children = self.table.search(self.query().parent_id == loc_id)
            result = []
            for child in children:
                result.append(child)
                result.extend(fetch_children(child['id']))
            return result

        return fetch_children(location_id)