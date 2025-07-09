import logging
from typing import Any, Optional, Dict, List, Set
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from MakerMatrix.models.models import LocationModel, LocationQueryModel, engine, PartModel
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.repositories.parts_repositories import PartRepository
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

    def get_all_locations(self) -> ServiceResponse[List[Dict[str, Any]]]:
        """
        Get all locations.
        
        CONSOLIDATED SESSION MANAGEMENT: Eliminates manual session management.
        """
        try:
            self.log_operation("get_all", self.entity_name)
            
            with self.get_session() as session:
                locations = self.location_repo.get_all_locations(session)
                # Convert to dictionaries to avoid DetachedInstanceError
                locations_data = [location.model_dump() for location in locations]
                return self.success_response(
                    f"Retrieved {len(locations)} {self.entity_name.lower()}s",
                    locations_data
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get all {self.entity_name.lower()}s")

    def get_location(self, location_query: LocationQueryModel) -> ServiceResponse[Dict[str, Any]]:
        """
        Get a location by query parameters.
        
        CONSOLIDATED SESSION MANAGEMENT: Eliminates manual session management.
        """
        try:
            self.log_operation("get", self.entity_name)
            
            with self.get_session() as session:
                try:
                    location = self.location_repo.get_location(session, location_query)
                    # Convert to dictionary to avoid DetachedInstanceError
                    location_dict = location.model_dump()
                    return self.success_response(
                        f"{self.entity_name} retrieved successfully",
                        location_dict
                    )
                except ResourceNotFoundError:
                    # Handle specific case where location doesn't exist
                    return self.error_response(f"{self.entity_name} not found")

        except Exception as e:
            return self.handle_exception(e, f"retrieve {self.entity_name}")

    def add_location(self, location_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
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
                # Convert to dictionary to avoid DetachedInstanceError
                location_dict = result.model_dump()
                return self.success_response(
                    f"{self.entity_name} '{location_name}' created successfully",
                    location_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    def update_location(self, location_id: str, location_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
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
                
                # Convert to dictionary to avoid DetachedInstanceError
                result_dict = result.model_dump()
                return self.success_response(
                    f"{self.entity_name} '{result.name}' updated successfully",
                    result_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")

    def get_location_details(self, location_id: str) -> ServiceResponse[Dict[str, Any]]:
        """
        Get detailed information about a location, including its children.

        Args:
            location_id (str): The ID of the location to get details for.

        Returns:
            ServiceResponse[Dict[str, Any]]: Service response containing location details.
        """
        try:
            self.log_operation("get_details", self.entity_name, location_id)
            
            with self.get_session() as session:
                location_data = self.location_repo.get_location_details(session, location_id)
                return self.success_response(
                    "Location details retrieved successfully",
                    location_data
                )
                
        except Exception as e:
            return self.handle_exception(e, f"retrieve {self.entity_name} details")

    def get_location_path(self, location_id: str) -> ServiceResponse[List[Dict[str, Any]]]:
        """Get the full path from a location to its root.
        
        Args:
            location_id: The ID of the location to get the path for
            
        Returns:
            ServiceResponse containing the location path
        """
        try:
            self.log_operation("get_path", self.entity_name, location_id)
            
            with self.get_session() as session:
                path = self.location_repo.get_location_path(session, location_id)
                return self.success_response(
                    f"Location path retrieved for location {location_id}",
                    path
                )
                
        except Exception as e:
            return self.handle_exception(e, f"retrieve {self.entity_name} path")

    def preview_location_delete(self, location_id: str) -> ServiceResponse[Dict[str, Any]]:
        """Preview what will be affected by deleting a location."""
        try:
            self.log_operation("preview_delete", self.entity_name, location_id)
            
            with self.get_session() as session:
                # Get all affected locations (including children) This should always return at LEAST 1, if not the location does not exist
                affected_locations = self.location_repo.get_location_hierarchy(session, location_id)

                if not affected_locations:
                    return self.error_response(f"Location with ID {location_id} not found")

                # Get all affected parts
                affected_parts_count = self.location_repo.get_affected_part_ids(session, affected_locations[
                    'affected_location_ids'])
                    
                location_response = LocationDeleteResponse(
                    location_ids_to_delete=affected_locations['affected_location_ids'],
                    affected_parts_count=len(affected_parts_count),
                    affected_locations_count=len(affected_locations['affected_location_ids']),
                    location_hierarchy=affected_locations['hierarchy']).model_dump()
                    
                return self.success_response(
                    f"Preview data for deleting location {location_id}",
                    location_response
                )

        except Exception as e:
            return self.handle_exception(e, f"preview delete {self.entity_name}")

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

        # Debug: Verify parts with NULL location_id using repository
        orphaned_parts, total_count = PartRepository.get_orphaned_parts(session, page=1, page_size=1000)
        if orphaned_parts:
            logger.info(f"Location deletion resulted in {total_count} orphaned parts")

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

    def get_or_create_unsorted_location(self) -> ServiceResponse[Dict[str, Any]]:
        """
        Get the 'Unsorted' location, creating it if it doesn't exist.
        This is used as a default location for imported parts that don't specify a location.
        
        CONSOLIDATED SESSION MANAGEMENT: Uses BaseService patterns for proper session handling.
        
        Returns:
            ServiceResponse[Dict[str, Any]]: The 'Unsorted' location data
        """
        try:
            self.log_operation("get_or_create_unsorted", self.entity_name)
            
            with self.get_session() as session:
                # First, try to find existing "Unsorted" location
                query = LocationQueryModel(name="Unsorted")
                try:
                    existing_location = self.location_repo.get_location(session, query)
                    if existing_location:
                        logger.debug("Found existing 'Unsorted' location")
                        # Convert to dictionary to avoid DetachedInstanceError
                        location_data = existing_location.model_dump()
                        return self.success_response(
                            "Retrieved existing 'Unsorted' location",
                            location_data
                        )
                except ResourceNotFoundError:
                    # Location doesn't exist, we'll create it below
                    pass
                
                # Create the "Unsorted" location
                location_data = {
                    "name": "Unsorted",
                    "description": "Default location for imported parts that need to be organized",
                    "location_type": "storage",
                    "parent_id": None  # Top-level location
                }
                
                logger.info("Creating 'Unsorted' location for imported parts")
                unsorted_location = self.location_repo.add_location(session, location_data)
                logger.info(f"Successfully created 'Unsorted' location (ID: {unsorted_location.id})")
                
                # Convert to dictionary to avoid DetachedInstanceError
                location_response_data = unsorted_location.model_dump()
                return self.success_response(
                    f"Successfully created 'Unsorted' {self.entity_name.lower()}",
                    location_response_data
                )
                
        except Exception as e:
            logger.error(f"Failed to get or create 'Unsorted' location: {e}")
            return self.error_response(f"Could not create or access 'Unsorted' location: {str(e)}")

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


