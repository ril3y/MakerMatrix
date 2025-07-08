import logging
from typing import Any, Optional, Dict, List, Set
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from MakerMatrix.models.models import LocationModel, LocationQueryModel, engine, PartModel
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    LocationAlreadyExistsError,
    InvalidReferenceError
)
from MakerMatrix.schemas.location_delete_response import LocationDeleteResponse
from MakerMatrix.services.base_service import BaseService, ServiceResponse

# Configure logging
logger = logging.getLogger(__name__)


class LocationService(BaseService):
    """
    Location service with consolidated session management using BaseService.
    
    This migration eliminates 8+ instances of duplicated session management code.
    """
    
    def __init__(self):
        super().__init__()
        self.location_repo = LocationRepository(engine)
        self.entity_name = "Location"

    def get_all_locations(self) -> ServiceResponse[List[LocationModel]]:
        """
        Get all locations.
        
        CONSOLIDATED SESSION MANAGEMENT: Eliminates manual session management.
        """
        try:
            self.log_operation("get_all", self.entity_name)
            
            with self.get_session() as session:
                locations = self.location_repo.get_all_locations(session)
                return self.success_response(
                    f"Retrieved {len(locations)} {self.entity_name.lower()}s",
                    locations
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get all {self.entity_name.lower()}s")

    def get_location(self, location_query: LocationQueryModel) -> ServiceResponse[LocationModel]:
        """
        Get a location by query parameters.
        
        CONSOLIDATED SESSION MANAGEMENT: Eliminates manual session management.
        """
        try:
            self.log_operation("get", self.entity_name)
            
            with self.get_session() as session:
                location = self.location_repo.get_location(session, location_query)
                if location:
                    return self.success_response(
                        f"{self.entity_name} retrieved successfully",
                        location
                    )
                else:
                    return self.error_response(f"{self.entity_name} not found")

        except Exception as e:
            return self.handle_exception(e, f"retrieve {self.entity_name}")

    def add_location(self, location_data: Dict[str, Any]) -> ServiceResponse[LocationModel]:
        """
        Add a new location.
        
        CONSOLIDATED SESSION MANAGEMENT: This method previously had 15+ lines
        of manual session and error handling. Now uses BaseService patterns.
        """
        try:
            # Validate required fields
            self.validate_required_fields(location_data, ["name"])
            
            location_name = location_data.get("name", "Unknown")
            parent_id = location_data.get("parent_id")
            location_type = location_data.get("location_type", "standard")
            
            self.log_operation("create", self.entity_name, location_name)
            if parent_id:
                self.logger.debug(f"Creating location '{location_name}' with parent ID: {parent_id}")
            
            with self.get_session() as session:
                result = self.location_repo.add_location(session, location_data)
                return self.success_response(
                    f"{self.entity_name} '{location_name}' created successfully",
                    result
                )
                
        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    def update_location(self, location_id: str, location_data: Dict[str, Any]) -> ServiceResponse[LocationModel]:
        """
        Update a location's fields. This method can update any combination of name, description, parent_id, and location_type.
        
        CONSOLIDATED SESSION MANAGEMENT: This method previously had 20+ lines
        of manual session and error handling. Now uses BaseService patterns.
        """
        try:
            self.log_operation("update", self.entity_name, location_id)
            
            with self.get_session() as session:
                # Get the current location to show before/after changes
                query_model = LocationQueryModel(id=location_id)
                current_location = self.location_repo.get_location(session, query_model)
                
                if not current_location:
                    return self.error_response(f"{self.entity_name} with ID '{location_id}' not found")
                
                # Log current state and planned changes
                self.logger.debug(f"Current location state: '{current_location.name}' (ID: {location_id})")
                updated_fields = []
                
                for field, new_value in location_data.items():
                    if hasattr(current_location, field):
                        old_value = getattr(current_location, field)
                        if old_value != new_value:
                            if field == "name":
                                self.logger.info(f"Updating location name (ID: {location_id}): '{old_value}' → '{new_value}'")
                                updated_fields.append(f"name: '{old_value}' → '{new_value}'")
                            elif field == "description":
                                self.logger.info(f"Updating location description for '{current_location.name}' (ID: {location_id})")
                                updated_fields.append(f"description updated")
                            elif field == "parent_id":
                                self.logger.info(f"Updating parent for location '{current_location.name}' (ID: {location_id}): {old_value} → {new_value}")
                                updated_fields.append(f"parent: {old_value} → {new_value}")
                            elif field == "location_type":
                                self.logger.info(f"Updating type for location '{current_location.name}' (ID: {location_id}): '{old_value}' → '{new_value}'")
                                updated_fields.append(f"type: '{old_value}' → '{new_value}'")
                            else:
                                self.logger.info(f"Updating {field} for location '{current_location.name}' (ID: {location_id}): {old_value} → {new_value}")
                                updated_fields.append(f"{field}: {old_value} → {new_value}")
                
                result = self.location_repo.update_location(session, location_id, location_data)
                
                if updated_fields:
                    changes_message = f"Changes: {', '.join(updated_fields)}"
                    self.logger.info(f"Successfully updated location '{result.name}' (ID: {location_id}). {changes_message}")
                else:
                    self.logger.info(f"No changes made to location '{result.name}' (ID: {location_id})")
                
                return self.success_response(
                    f"{self.entity_name} '{result.name}' updated successfully",
                    result
                )
                
        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")

    @staticmethod
    def get_location_details(location_id: str) -> dict:
        """
        Get detailed information about a location, including its children.

        Args:
            location_id (str): The ID of the location to get details for.

        Returns:
            dict: A dictionary containing the location details and its children in the standard response format.
        """
        with Session(engine) as session:
            location_data = LocationRepository.get_location_details(session, location_id)
            return {
                "status": "success",
                "message": "Location details retrieved successfully",
                "data": location_data
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

        logger.info(f"Attempting to delete location: {location_id}")
        
        query_model = LocationQueryModel(id=location_id)
        location = LocationRepository.get_location(session, location_query=query_model)

        if not location:
            logger.error(f"Location deletion failed: Location with ID '{location_id}' not found")
            return {
                "status": "error",
                "message": f"Location {location_id} not found",
                "data": None
            }

        # Log location details before deletion
        location_name = location.name
        location_type = getattr(location, 'location_type', 'Unknown')
        logger.info(f"Deleting location: '{location_name}' (ID: {location_id}, type: {location_type})")

        # Delete location and its children
        LocationRepository.delete_location(session, location)

        # Debug: Verify parts with NULL location_id
        orphaned_parts = session.query(PartModel).filter(PartModel.location_id == None).all()
        if orphaned_parts:
            logger.info(f"Location deletion resulted in {len(orphaned_parts)} orphaned parts")

        logger.info(f"Successfully deleted location: '{location_name}' (ID: {location_id})")
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
    def get_or_create_unsorted_location() -> LocationModel:
        """
        Get the 'Unsorted' location, creating it if it doesn't exist.
        This is used as a default location for imported parts that don't specify a location.
        
        Returns:
            LocationModel: The 'Unsorted' location
        """
        session = next(get_session())
        try:
            # First, try to find existing "Unsorted" location
            query = LocationQueryModel(name="Unsorted")
            existing_location = LocationService.location_repo.get_location(session, query)
            if existing_location:
                logger.debug("Found existing 'Unsorted' location")
                return existing_location
                
        except ResourceNotFoundError:
            # Location doesn't exist, we'll create it below
            pass
        except Exception as e:
            logger.warning(f"Error checking for existing 'Unsorted' location: {e}")
            # Continue to creation attempt
        
        # Create the "Unsorted" location
        try:
            location_data = {
                "name": "Unsorted",
                "description": "Default location for imported parts that need to be organized",
                "location_type": "storage",
                "parent_id": None  # Top-level location
            }
            
            logger.info("Creating 'Unsorted' location for imported parts")
            unsorted_location = LocationService.location_repo.add_location(session, location_data)
            logger.info(f"Successfully created 'Unsorted' location (ID: {unsorted_location.id})")
            return unsorted_location
            
        except Exception as e:
            logger.error(f"Failed to create 'Unsorted' location: {e}")
            # If we can't create it, return None and let the import continue without a location
            # This prevents import failures due to location creation issues
            raise ValueError(f"Could not create or access 'Unsorted' location: {str(e)}")

    @staticmethod
    def cleanup_locations() -> dict:
        """
        Clean up locations by removing those with invalid parent IDs and their descendants.
        
        Returns:
            dict: A dictionary containing the cleanup results in the standard response format
        """
        with Session(engine) as session:
            deleted_count = LocationRepository.cleanup_locations(session)
            return {
                "status": "success",
                "message": f"Cleanup completed. Removed {deleted_count} invalid locations.",
                "data": {"deleted_count": deleted_count}
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
        with Session(engine) as session:
            preview_data = LocationRepository.preview_delete(session, location_id)
            return {
                "status": "success",
                "message": "Delete preview generated successfully",
                "data": preview_data
            }


