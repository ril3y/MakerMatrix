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
        """
        Update a location's fields. This method can update any combination of name, description, parent_id, and location_type.
        
        Args:
            location_id: The ID of the location to update
            location_data: Dictionary containing the fields to update
            
        Returns:
            LocationModel: The updated location model
            
        Raises:
            ResourceNotFoundError: If the location or parent location is not found
        """
        session = next(get_session())
        try:
            return LocationService.location_repo.update_location(session, location_id, location_data)
        except ResourceNotFoundError as rnfe:
            raise rnfe  # Re-raise the ResourceNotFoundError to be handled by the route
        except Exception as e:
            raise ValueError(f"Failed to update location: {str(e)}")

    @staticmethod
    def get_location_details(location_id: str) -> dict:
        """
        Get detailed information about a location, including its children.

        Args:
            location_id (str): The ID of the location to get details for.

        Returns:
            dict: A dictionary containing the location details and its children in the standard response format.
        """
        try:
            with Session(engine) as session:
                return LocationRepository.get_location_details(session, location_id)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving location details: {str(e)}",
                "data": None
            }

    @staticmethod
    def get_location_path(location_id: str) -> Dict[str, Any]:
        """Get the full path from a location to its root.
        
        Args:
            location_id: The ID of the location to get the path for
            
        Returns:
            A dictionary containing the location path with parent references
            
        Raises:
            ResourceNotFoundError: If the location is not found
        """
        session = next(get_session())
        try:
            path = LocationRepository.get_location_path(session, location_id)
            return {
                "status": "success",
                "message": f"Location path retrieved for location {location_id}",
                "data": path
            }
        except ResourceNotFoundError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error retrieving location path: {str(e)}")

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
                affected_locations_count=len(affected_locations['affected_location_ids']),
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
    def delete_all_locations():
        session = next(get_session())
        return LocationService.location_repo.delete_all_locations(session)

    @staticmethod
    def cleanup_locations() -> dict:
        """
        Clean up locations by removing those with invalid parent IDs and their descendants.
        
        Returns:
            dict: A dictionary containing the cleanup results in the standard response format
        """
        try:
            with Session(engine) as session:
                return LocationRepository.cleanup_locations(session)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during location cleanup: {str(e)}",
                "data": None
            }

    @staticmethod
    def preview_delete(location_id: str) -> dict:
        """
        Preview what will be affected when deleting a location.
        
        Args:
            location_id: The ID of the location to preview deletion for
            
        Returns:
            dict: A dictionary containing the preview information in the standard response format
        """
        try:
            with Session(engine) as session:
                return LocationRepository.preview_delete(session, location_id)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating delete preview: {str(e)}",
                "data": None
            }


