from typing import Any, Optional, Dict, List, Set
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from MakerMatrix.models.models import LocationModel, LocationQueryModel, engine, PartModel
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.location_delete_response import LocationDeleteResponse


class LocationService:
    location_repo = LocationRepository(engine)

    @staticmethod
    def get_all_locations() -> List[LocationModel]:
        session = next(get_session())
        try:
            return LocationService.location_repo.get_all_locations(session)
        except Exception as e:
            raise ValueError(f"Failed to retrieve all locations: {str(e)}")

    @staticmethod
    def get_location(location_query: LocationQueryModel) -> Optional[LocationModel]:
        session = next(get_session())
        try:
            location = LocationService.location_repo.get_location(session, location_query)
            if location:
                return location

        except ResourceNotFoundError as rnfe:
            raise rnfe
        except Exception as e:
            raise ValueError(f"Failed to retrieve location: {str(e)}")

    @staticmethod
    def add_location(location_data: Dict[str, Any]) -> LocationModel:
        session = next(get_session())
        try:
            return LocationService.location_repo.add_location(session, location_data)
        except Exception as e:
            raise ValueError(f"Failed to add location: {str(e)}")

    @staticmethod
    def update_location(location_id: str, location_data: Dict[str, Any]) -> LocationModel:
        session = next(get_session())
        try:
            return LocationService.location_repo.update_location(session, location_id, location_data)

        except ResourceNotFoundError as rnfe:
            raise ResourceNotFoundError(
                status="error",
                message=f"Location with ID '{location_id}' not found.",
                data=None
            )
        except Exception as e:
            raise ValueError(f"Failed to update location: {str(e)}")

    @staticmethod
    def get_location_details(location_id: str) -> Optional[LocationModel]:
        session = next(get_session())
        try:
            location = LocationRepository.get_location_details(session, location_id)
            if not location:
                raise ResourceNotFoundError(resource="Location", resource_id=location_id)
            return location
        except ResourceNotFoundError as rnfe:
            raise ResourceNotFoundError(
                status="error",
                message=f"Location with ID '{location_id}' not found.",
                data=None
            )

        except Exception as e:
            raise ValueError(f"Failed to retrieve location details: {str(e)}")

    @staticmethod
    def get_location_path(query_location: LocationQueryModel) -> Optional[List[Dict]]:
        session = next(get_session())
        try:
            return LocationService.location_repo.get_location_path(session, query_location)
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except Exception as e:
            raise ValueError(f"Failed to retrieve location path: {str(e)}")

    # @staticmethod
    # def update_location(location_id: str, location_data: LocationModel) -> Optional[dict]:
    #     # Validate the location data if needed (e.g., ensure the name is unique)
    #     # You may need to validate that the new name is unique and the parent location exists, if applicable.
    #
    #     # Update the location using the repository
    #     update_data = location_data.dict(exclude_unset=True)
    #     updated_location = LocationService.location_repo.update_location(location_id, update_data)
    #     return updated_location

    @staticmethod
    def preview_location_delete(location_id: str) -> dict[str, Any]:
        session = next(get_session())
        try:
            # Get all affected locations (including children) This should always return at LEAST 1, if not the location does not exist
            affected_locations = LocationService.location_repo.get_location_hierarchy(session, location_id)

            if not affected_locations:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Location with ID {location_id} not found",
                    data=None)

            # Get all affected parts
            affected_parts_count = LocationService.location_repo.get_affected_part_ids(session, affected_locations[
                'affected_location_ids'])
            location_response = LocationDeleteResponse(
                location_ids_to_delete=affected_locations['affected_location_ids'],
                affected_parts_count=len(affected_parts_count),
                location_hierarchy=affected_locations['hierarchy']).model_dump()
            return location_response

        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_parts_effected_locations(location_id: str):
        return LocationService.location_repo.get_parts_effected_locations(location_id)

    @staticmethod
    def delete_location(location_id: str) -> Dict:
        session = next(get_session())

        query_model = LocationQueryModel(id=location_id)
        location = LocationRepository.get_location(session, location_query=query_model)

        if not location:
            return {
                "status": "error",
                "message": f"Location {location_id} not found",
                "data": None
            }

        # Delete location and its children
        LocationRepository.delete_location(session, location)

        # Debug: Verify parts with NULL location_id
        orphaned_parts = session.query(PartModel).filter(PartModel.location_id == None).all()
        print(f"Orphaned Parts: {orphaned_parts}")

        return {
            "status": "success",
            "message": f"Deleted location_id: {location_id} and its children",
            "data": {
                "deleted_location_name": location.name,
                "deleted_location_id": location_id,
            }
        }

    @staticmethod
    def edit_location(location_id: str, name: Optional[str] = None, description: Optional[str] = None,
                      parent_id: Optional[int] = None):
        return LocationService.location_repo.edit_location(location_id, name, description, parent_id)

    @staticmethod
    def delete_all_locations():
        session = next(get_session())
        return LocationService.location_repo.delete_all_locations(session)

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
