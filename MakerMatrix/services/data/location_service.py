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


def apply_slot_naming_pattern(
    pattern: str,
    slot_number: int,
    slot_metadata: Optional[Dict] = None
) -> str:
    """
    Apply naming pattern with variable substitution.

    Supported variables:
    - {n} - Slot number (always available)
    - {row} - Row number (from slot_metadata)
    - {col} - Column number (from slot_metadata)
    - {side} - Side name (Phase 2+, from slot_metadata)

    Args:
        pattern: Naming pattern string (e.g., "Slot {n}" or "R{row}-C{col}")
        slot_number: Linear slot number (1, 2, 3, ...)
        slot_metadata: Optional dict with row, column, side, etc.

    Returns:
        Formatted slot name with variables substituted
    """
    # Start with the pattern
    result = pattern

    # Always substitute {n} with slot number
    result = result.replace("{n}", str(slot_number))

    # Substitute spatial variables if metadata is provided
    if slot_metadata:
        if "row" in slot_metadata:
            result = result.replace("{row}", str(slot_metadata["row"]))
        if "column" in slot_metadata:
            result = result.replace("{col}", str(slot_metadata["column"]))
        # Phase 2+ support for side
        if "side" in slot_metadata:
            result = result.replace("{side}", str(slot_metadata["side"]))

    return result


class LocationService(BaseService):
    """
    Location service with consolidated session management using BaseService.

    This migration eliminates 8+ instances of duplicated session management code.
    """

    def __init__(self, engine_override=None):
        super().__init__(engine_override)
        self.location_repo = LocationRepository(self.engine)
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
        from MakerMatrix.models.part_allocation_models import PartLocationAllocation
        from MakerMatrix.repositories.part_allocation_repository import PartAllocationRepository
        from sqlalchemy import select
        from datetime import datetime

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

        # Handle allocations before deletion
        # Find all allocations at this location
        allocations_query = select(PartLocationAllocation).where(
            PartLocationAllocation.location_id == location_id
        )
        allocations = session.exec(allocations_query).all()

        returned_count = 0
        deleted_count = 0

        if allocations:
            logger.info(f"Found {len(allocations)} allocation(s) at location '{location_name}'")

            for allocation in allocations:
                part_id = allocation.part_id
                quantity = allocation.quantity_at_location
                is_primary = allocation.is_primary_storage

                logger.info(f"Processing allocation: Part {part_id}, Quantity: {quantity}, Primary: {is_primary}")

                if is_primary:
                    # If this is the primary storage, just delete the allocation
                    # The CASCADE will handle it, but we log it explicitly
                    logger.warning(
                        f"Deleting primary storage allocation for part {part_id} at location '{location_name}'. "
                        f"Part will have no primary storage location."
                    )
                    deleted_count += 1
                else:
                    # For non-primary allocations, return quantity to primary storage
                    try:
                        # Find the primary allocation for this part
                        primary_alloc = PartAllocationRepository.get_primary_allocation(
                            session, part_id
                        )

                        if not primary_alloc:
                            # No primary allocation exists - find any allocation and promote it
                            other_allocations_query = select(PartLocationAllocation).where(
                                PartLocationAllocation.part_id == part_id,
                                PartLocationAllocation.location_id != location_id
                            )
                            other_allocations = session.exec(other_allocations_query).all()

                            if other_allocations:
                                # Promote first allocation to primary
                                primary_alloc = other_allocations[0]
                                primary_alloc.is_primary_storage = True
                                logger.info(f"Promoted allocation at {primary_alloc.location.name} to primary storage for part {part_id}")
                            else:
                                logger.warning(f"No other allocations found for part {part_id}. Quantity {quantity} will be lost.")
                                deleted_count += 1
                                continue

                        # Add quantity back to primary storage
                        primary_alloc.quantity_at_location += quantity
                        primary_alloc.last_updated = datetime.utcnow()
                        session.add(primary_alloc)

                        logger.info(
                            f"Returned {quantity} units of part {part_id} from '{location_name}' "
                            f"to primary storage at '{primary_alloc.location.name}'"
                        )
                        returned_count += 1

                    except Exception as e:
                        logger.error(f"Error returning quantity to primary storage for part {part_id}: {e}")
                        deleted_count += 1

            # Commit the quantity returns before deleting the location
            session.commit()
            logger.info(f"Returned {returned_count} allocation(s) to primary storage, deleted {deleted_count} allocation(s)")

        # Delete location and its children (CASCADE will handle remaining allocations)
        LocationRepository.delete_location(session, location)

        # Debug: Verify parts with NULL location_id using repository
        orphaned_parts, total_count = PartRepository.get_orphaned_parts(session, page=1, page_size=1000)
        if orphaned_parts:
            logger.info(f"Location deletion resulted in {total_count} orphaned parts")

        logger.info(f"Successfully deleted location: '{location_name}' (ID: {location_id})")
        return {
            "status": "success",
            "message": f"Deleted location '{location_name}' and returned {returned_count} allocation(s) to primary storage",
            "data": {
                "deleted_location_name": location.name,
                "deleted_location_id": location_id,
                "allocations_returned": returned_count,
                "allocations_deleted": deleted_count
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

    def create_container_with_slots(
        self,
        container_data: Dict[str, Any]
    ) -> ServiceResponse:
        """
        Create a container location with auto-generated child slot locations.

        Supports:
        - Simple layout: Linear numbering (1, 2, 3, ...)
        - Grid layout: Rows × columns with spatial metadata
        - Phase 2: Custom layouts via slot_layout JSON

        Args:
            container_data: Container location data including:
                - name, description, parent_id, etc. (standard location fields)
                - slot_count: Number of slots to create
                - slot_naming_pattern: Pattern for slot names (default: "Slot {n}")
                - slot_layout_type: "simple" | "grid" | "custom"
                - grid_rows: For grid layout
                - grid_columns: For grid layout

        Returns:
            ServiceResponse with container data and slots_created count
        """
        try:
            # Extract slot configuration
            slot_count = container_data.get("slot_count")
            slot_naming_pattern = container_data.get("slot_naming_pattern", "Slot {n}")
            slot_layout_type = container_data.get("slot_layout_type", "simple")
            grid_rows = container_data.get("grid_rows")
            grid_columns = container_data.get("grid_columns")

            # Validate slot configuration if provided
            if slot_count is not None:
                # Validate slot_count
                if slot_count < 1:
                    return self.error_response("slot_count must be at least 1")

                # Validate based on layout type
                if slot_layout_type == "simple":
                    # Simple layout only needs slot_count
                    pass

                elif slot_layout_type == "grid":
                    # Grid layout requires rows and columns
                    if grid_rows is None or grid_columns is None:
                        return self.error_response(
                            "grid_rows and grid_columns are required for grid layout"
                        )

                    if grid_rows < 1 or grid_columns < 1:
                        return self.error_response(
                            "grid_rows and grid_columns must be at least 1"
                        )

                    # Calculate expected slot count
                    expected_slot_count = grid_rows * grid_columns

                    # If slot_count is provided, verify it matches
                    if slot_count != expected_slot_count:
                        return self.error_response(
                            f"slot_count ({slot_count}) must equal grid_rows × grid_columns ({expected_slot_count})"
                        )

                    # Use grid-appropriate default naming pattern if not provided
                    if container_data.get("slot_naming_pattern") is None:
                        slot_naming_pattern = "R{row}-C{col}"

                elif slot_layout_type == "custom":
                    # Phase 2: Custom layouts - not implemented yet
                    return self.error_response(
                        "Custom slot layouts are not yet implemented (Phase 2+)"
                    )

                else:
                    return self.error_response(
                        f"Invalid slot_layout_type: {slot_layout_type}. Must be 'simple', 'grid', or 'custom'"
                    )

            # Log operation
            container_name = container_data.get("name", "Unknown")
            self.log_operation("create_container_with_slots", self.entity_name, container_name)

            with self.get_session() as session:
                # Create the parent container location
                container = self.location_repo.add_location(session, container_data)
                self.logger.info(
                    f"Created container '{container.name}' (ID: {container.id})"
                )

                # Generate child slots if slot_count is specified
                slots_created = 0
                if slot_count is not None and slot_count > 0:
                    if slot_layout_type == "simple":
                        slots = self._generate_simple_slots(
                            session, container, slot_count, slot_naming_pattern
                        )
                        slots_created = len(slots)
                        self.logger.info(
                            f"Generated {slots_created} simple slots for container '{container.name}'"
                        )

                    elif slot_layout_type == "grid":
                        slots = self._generate_grid_slots(
                            session, container, grid_rows, grid_columns, slot_naming_pattern
                        )
                        slots_created = len(slots)
                        self.logger.info(
                            f"Generated {slots_created} grid slots ({grid_rows}×{grid_columns}) for container '{container.name}'"
                        )

                # Convert to dictionary to avoid DetachedInstanceError
                container_dict = container.model_dump()

                # Add slots_created count to response
                response_data = {
                    "container": container_dict,
                    "slots_created": slots_created
                }

                return self.success_response(
                    f"Container '{container.name}' created successfully with {slots_created} slots",
                    response_data
                )

        except Exception as e:
            return self.handle_exception(e, f"create container with slots")

    def _generate_simple_slots(
        self,
        session: Session,
        container: LocationModel,
        slot_count: int,
        naming_pattern: str
    ) -> List[LocationModel]:
        """
        Generate simple linear slots (1, 2, 3, ...).

        Args:
            session: Database session
            container: Parent container location
            slot_count: Number of slots to create
            naming_pattern: Naming pattern (e.g., "Slot {n}")

        Returns:
            List of created slot LocationModel instances
        """
        slots = []

        for i in range(1, slot_count + 1):
            # Apply naming pattern with slot number
            slot_name = apply_slot_naming_pattern(naming_pattern, i, None)

            # Create slot location data
            slot_data = {
                "name": slot_name,
                "parent_id": container.id,
                "location_type": "slot",
                "is_auto_generated_slot": True,
                "slot_number": i,
                "slot_metadata": None  # No spatial data in simple mode
            }

            # Create the slot location
            slot = self.location_repo.add_location(session, slot_data)
            slots.append(slot)
            self.logger.debug(f"Created simple slot: {slot_name} (#{i})")

        return slots

    def _generate_grid_slots(
        self,
        session: Session,
        container: LocationModel,
        rows: int,
        columns: int,
        naming_pattern: str
    ) -> List[LocationModel]:
        """
        Generate grid-based slots with row/column metadata.

        Slot numbering: Top-left is slot 1, incrementing left-to-right, top-to-bottom.
        Example 4×3 grid:
          C1  C2  C3
        R1 1   2   3
        R2 4   5   6
        R3 7   8   9
        R4 10  11  12

        Args:
            session: Database session
            container: Parent container location
            rows: Number of rows
            columns: Number of columns
            naming_pattern: Naming pattern (e.g., "R{row}-C{col}")

        Returns:
            List of created slot LocationModel instances
        """
        slots = []
        slot_number = 1

        for row in range(1, rows + 1):
            for col in range(1, columns + 1):
                # Build slot metadata with spatial information
                slot_metadata = {
                    "row": row,
                    "column": col
                }

                # Apply naming pattern with all variables
                slot_name = apply_slot_naming_pattern(
                    naming_pattern, slot_number, slot_metadata
                )

                # Create slot location data
                slot_data = {
                    "name": slot_name,
                    "parent_id": container.id,
                    "location_type": "slot",
                    "is_auto_generated_slot": True,
                    "slot_number": slot_number,
                    "slot_metadata": slot_metadata
                }

                # Create the slot location
                slot = self.location_repo.add_location(session, slot_data)
                slots.append(slot)
                self.logger.debug(
                    f"Created grid slot: {slot_name} (#{slot_number}, R{row}C{col})"
                )

                slot_number += 1

        return slots

    def get_container_slots(
        self,
        container_id: str,
        include_occupancy: bool = True
    ) -> ServiceResponse[List[Dict[str, Any]]]:
        """
        Get all slots for a container with optional occupancy information.

        This method is used by the hierarchical location picker to show slots
        when a container is selected, along with which slots are occupied.

        Args:
            container_id: ID of the parent container location
            include_occupancy: Whether to include part allocation/occupancy data

        Returns:
            ServiceResponse containing list of slots with occupancy data
        """
        try:
            self.log_operation("get_container_slots", self.entity_name, container_id)

            with self.get_session() as session:
                from MakerMatrix.models.part_allocation_models import PartLocationAllocation

                # Query slots for this container
                query = select(LocationModel).where(
                    LocationModel.parent_id == container_id,
                    LocationModel.is_auto_generated_slot == True
                ).order_by(LocationModel.slot_number)

                slots = session.exec(query).all()

                if not slots:
                    self.logger.debug(f"No slots found for container {container_id}")
                    return self.success_response(
                        f"No slots found for container",
                        []
                    )

                # Convert slots to dictionaries
                slots_data = []
                for slot in slots:
                    slot_dict = slot.model_dump()

                    # Add occupancy information if requested
                    if include_occupancy:
                        # Query allocations for this slot with part details
                        alloc_query = select(PartLocationAllocation).where(
                            PartLocationAllocation.location_id == slot.id
                        ).options(selectinload(PartLocationAllocation.part))
                        allocations = session.exec(alloc_query).all()

                        # Calculate occupancy
                        total_parts = len(allocations)
                        total_quantity = sum(alloc.quantity_at_location for alloc in allocations)

                        slot_dict['occupancy'] = {
                            'is_occupied': total_parts > 0,
                            'part_count': total_parts,
                            'total_quantity': total_quantity,
                            'parts': [
                                {
                                    'part_id': alloc.part_id,
                                    'part_name': alloc.part.name if alloc.part else 'Unknown',
                                    'part_number': alloc.part.part_number if alloc.part else None,
                                    'quantity': alloc.quantity_at_location,
                                    'is_primary': alloc.is_primary_storage,
                                    'description': alloc.part.description if alloc.part else None,
                                    'image_url': alloc.part.image_url if alloc.part else None,
                                    'category': alloc.part.categories[0].name if alloc.part and alloc.part.categories else None
                                }
                                for alloc in allocations
                            ] if total_parts > 0 else []
                        }
                    else:
                        slot_dict['occupancy'] = None

                    slots_data.append(slot_dict)

                self.logger.info(
                    f"Retrieved {len(slots_data)} slots for container {container_id}"
                )

                return self.success_response(
                    f"Retrieved {len(slots_data)} slots",
                    slots_data
                )

        except Exception as e:
            return self.handle_exception(e, f"retrieve container slots")

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


