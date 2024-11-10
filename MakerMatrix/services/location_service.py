from typing import Optional, Dict, List

from MakerMatrix.models.location_model import LocationModel, LocationQueryModel
from MakerMatrix.repositories.location_repositories import LocationRepository


class LocationService:
    location_repo = LocationRepository()

    @staticmethod
    def get_all_locations():
        return LocationService.location_repo.get_all_locations()

    @staticmethod
    def get_location(location: LocationQueryModel) -> Optional[Dict]:
        return LocationService.location_repo.get_location(location)

    @staticmethod
    def add_location(location: LocationModel) -> Dict:
        return LocationService.location_repo.add_location(location)


    @staticmethod
    def get_location_details(parent_id) -> Optional[Dict]:
        return LocationService.location_repo.get_location_details(parent_id)

    @staticmethod
    def get_location_path(query_location: LocationQueryModel) -> Optional[List[Dict]]:
        """
        Retrieves the path from a specific location to the root in a nested JSON format.

        :param query_location: The ID or name of the specific location.
        :return: A list of dictionaries representing the path from the specified location to the root.
        """

        path = []
        current_location_id = LocationService.location_repo.get_location(query_location)

        while current_location_id:
            # Retrieve the current location using its ID
            location = LocationService.location_repo.get_location(
                LocationQueryModel(id=current_location_id))
            if not location:
                break

            # Build the nested structure
            path = {'location': location, 'parent': path}

            # Move up to the parent
            current_location_id = location.get('parent_id')

        return path if path else None

    @staticmethod
    def update_location(location_id: str, location_data: LocationModel) -> Optional[dict]:
        # Validate the location data if needed (e.g., ensure the name is unique)
        # You may need to validate that the new name is unique and the parent location exists, if applicable.

        # Update the location using the repository
        update_data = location_data.dict(exclude_unset=True)
        updated_location = LocationService.location_repo.update_location(location_id, update_data)
        return updated_location

    @staticmethod
    def get_parts_effected_locations(location_id: str):
        return LocationService.location_repo.get_parts_effected_locations(location_id)

    @staticmethod
    def delete_location(location_id: str) -> Dict:
        # Retrieve all child locations using the repository
        child_locations = LocationService.location_repo.get_location_hierarchy(location_id)

        # Iterate and delete each child location
        for child_location in child_locations:
            LocationService.location_repo.delete_location(child_location['id'])

        # Finally, delete the specified location
        deleted_location = LocationService.location_repo.delete_location(location_id)

        if deleted_location:
            return {
                "status": "success",
                "deleted_children_count": len(child_locations)
            }
        else:
            return {
                "status": "error",
                "message": "Location not found"
            }

    @staticmethod
    def edit_location(location_id: str, name: Optional[str] = None, description: Optional[str] = None,
                      parent_id: Optional[int] = None):
        return LocationService.location_repo.edit_location(location_id, name, description, parent_id)

    @staticmethod
    def delete_all_locations():
        return LocationService.location_repo.delete_all_locations()

    @staticmethod
    def cleanup_locations():
        # Step 1: Get all locations
        all_locations = LocationService.location_repo.get_all_locations()

        # Create a set of all valid location IDs
        valid_ids = {loc.get('id') for loc in all_locations}

        # Step 2: Identify invalid locations
        invalid_locations = [
            loc for loc in all_locations
            if loc.get('parent_id') and loc.get('parent_id') not in valid_ids
        ]

        # Recursive function to delete a location and its descendants
        def delete_location_and_descendants(location_id):
            # Delete all child locations
            for loc in all_locations:
                if loc.get('parent_id') == location_id:
                    delete_location_and_descendants(loc.get('id'))

            # Delete the location itself
            LocationService.location_repo.delete_location(location_id)

        # Step 3: Delete invalid locations and their descendants
        for loc in invalid_locations:
            delete_location_and_descendants(loc.get('id'))

        return len(invalid_locations)


    @staticmethod
    def preview_delete(location_id: str) -> Dict:
        affected_parts = LocationService.get_parts_affected_by_location(location_id)
        affected_parts_count = len(affected_parts)

        affected_children = LocationService.get_child_locations(location_id)
        affected_children_count = len(affected_children)

        return {
            "location_id": location_id,
            "affected_parts_count": affected_parts_count,
            "affected_children_count": affected_children_count
        }