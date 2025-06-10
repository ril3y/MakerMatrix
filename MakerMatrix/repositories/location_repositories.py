from typing import Optional, List, Dict, Any, Sequence
from sqlalchemy import delete, func
from sqlmodel import Session, select
from MakerMatrix.models.models import LocationModel, LocationQueryModel, PartModel
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    LocationAlreadyExistsError,
    InvalidReferenceError
)
from sqlalchemy.orm import joinedload, selectinload


class LocationRepository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_all_locations(session: Session) -> Sequence[LocationModel]:
        return session.exec(
            select(LocationModel).options(selectinload(LocationModel.parent))
        ).all()

    @staticmethod
    def delete_location(session: Session, location: LocationModel):
        session.delete(location)
        session.commit()
        return True

    @staticmethod
    def get_location_hierarchy(session: Session, location_id: str) -> Dict[str, Any]:
        """Get a location and its complete hierarchy of descendants"""
        location = session.exec(
            select(LocationModel)
            .options(selectinload(LocationModel.children))
            .where(LocationModel.id == location_id)
        ).first()

        if not location:
            raise ResourceNotFoundError(resource="Location", resource_id=location_id)

        affected_ids = []

        def build_hierarchy(loc: LocationModel) -> Dict[str, Any]:
            affected_ids.append(loc.id)
            children = session.exec(
                select(LocationModel)
                .options(selectinload(LocationModel.children))
                .where(LocationModel.parent_id == loc.id)
            ).all()

            hierarchy = {
                "id": loc.id,
                "name": loc.name,
                "description": loc.description,
                "children": [build_hierarchy(child) for child in children]
            }
            return hierarchy

        hierarchy = build_hierarchy(location)
        return {
            "hierarchy": hierarchy,
            "affected_location_ids": affected_ids
        }

    @staticmethod
    def get_affected_part_ids(session: Session, location_ids: List[str]) -> List[str]:
        """Get IDs of all parts associated with a list of location IDs"""
        parts = session.exec(
            select(PartModel.id).where(PartModel.location_id.in_(location_ids))
        ).all()

        return parts

    @staticmethod
    def get_location(session: Session, location_query: LocationQueryModel) -> Optional[LocationModel]:
        if location_query.id:
            location = session.exec(select(LocationModel).where(LocationModel.id == location_query.id)).first()
        elif location_query.name:
            location = session.exec(select(LocationModel).where(LocationModel.name == location_query.name)).first()
        else:
            raise InvalidReferenceError(
                status="error",
                message="Either 'id' or 'name' must be provided for location lookup",
                data=None
            )
        if location:
            return location
        else:
            location_id_or_name = location_query.id if location_query.id is not None else location_query.name

            raise ResourceNotFoundError(
                status="error",
                message=f"Location {location_id_or_name} not found",
                data=None)

    @staticmethod
    def add_location(session: Session, location_data: Dict[str, Any]) -> LocationModel:
        # Check for duplicate location name
        existing_location = session.exec(
            select(LocationModel).where(LocationModel.name == location_data.get("name"))
        ).first()
        if existing_location:
            raise LocationAlreadyExistsError(
                status="error",
                message=f"Location with name '{location_data.get('name')}' already exists",
                data={"existing_location_id": existing_location.id}
            )
        
        # Validate parent_id if provided
        if location_data.get("parent_id"):
            parent = session.get(LocationModel, location_data["parent_id"])
            if not parent:
                raise InvalidReferenceError(
                    status="error",
                    message=f"Parent location with ID '{location_data['parent_id']}' does not exist",
                    data={"parent_id": location_data["parent_id"]}
                )
        
        new_location = LocationModel(**location_data)
        session.add(new_location)
        session.commit()
        session.refresh(new_location)
        
        # Load the parent relationship if it exists
        if new_location.parent_id:
            # Refresh with parent loaded
            statement = select(LocationModel).options(selectinload(LocationModel.parent)).where(LocationModel.id == new_location.id)
            new_location = session.exec(statement).first()
        
        return new_location

    @staticmethod
    def get_location_details(session: Session, location_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a location, including its children.

        Args:
            session: The database session
            location_id: The ID of the location to get details for

        Returns:
            dict: A dictionary containing the location details and its children
        """
        location = session.exec(
            select(LocationModel)
            .options(joinedload(LocationModel.children))
            .where(LocationModel.id == location_id)
        ).first()
        
        if not location:
            raise ResourceNotFoundError(
                status="error",
                message=f"Location with ID '{location_id}' not found",
                data=None
            )

        # Convert location to dictionary and include children
        location_data = location.to_dict()
        location_data["children"] = [child.to_dict() for child in location.children]
        
        return location_data

    @staticmethod
    def get_location_path(session: Session, location_id: str) -> Dict[str, Any]:
        """Get the full path from a location to its root, including all parent locations.
        
        Args:
            session: The database session
            location_id: The ID of the location to get the path for
            
        Returns:
            A dictionary containing the location path with parent references
            
        Raises:
            ResourceNotFoundError: If the location is not found
        """
        location = session.get(LocationModel, location_id)
        if not location:
            raise ResourceNotFoundError(f"Location {location_id} not found")
        
        # Build the path from the target location up to the root
        path = []
        current = location
        
        while current:
            path.append({
                "id": current.id,
                "name": current.name,
                "description": current.description,
                "location_type": current.location_type
            })
            if current.parent_id:
                current = session.get(LocationModel, current.parent_id)
            else:
                current = None
        
        # Convert the list into a nested dictionary structure
        if not path:
            return {}
            
        result = path[0].copy()
        current = result
        
        for i in range(1, len(path)):
            current["parent"] = path[i].copy()
            current = current["parent"]
        
        return result
    
    @staticmethod
    def delete_all_locations(session: Session) -> int:
        """
        Delete all locations from the database.
        
        Returns:
            int: Number of locations deleted
        """
        locations = session.exec(select(LocationModel)).all()
        count = len(locations)
        session.exec(delete(LocationModel))
        session.commit()
        return count
        
    @staticmethod
    def update_location(session: Session, location_id: str, location_data: Dict[str, Any]) -> LocationModel:
        """
        Update a location's fields. This method can update any combination of name, description, parent_id, and location_type.
        
        Args:
            session: The database session
            location_id: The ID of the location to update
            location_data: Dictionary containing the fields to update
            
        Returns:
            LocationModel: The updated location model
            
        Raises:
            ResourceNotFoundError: If the location or parent location is not found
        """
        location = session.get(LocationModel, location_id)
        if not location:
            raise ResourceNotFoundError(
                status="error",
                message="Location not found",
                data=None
            )
        
        # If parent_id is being updated, verify the new parent exists
        if "parent_id" in location_data and location_data["parent_id"]:
            parent = session.get(LocationModel, location_data["parent_id"])
            if not parent:
                raise InvalidReferenceError(
                    status="error",
                    message=f"Parent location with ID '{location_data['parent_id']}' does not exist",
                    data={"parent_id": location_data["parent_id"]}
                )
        
        # Update only the provided fields
        for key, value in location_data.items():
            setattr(location, key, value)
        
        session.add(location)
        session.commit()
        session.refresh(location)
        return location

    @staticmethod
    def cleanup_locations(session: Session) -> int:
        """
        Clean up locations by removing those with invalid parent IDs and their descendants.
        
        Args:
            session: The database session
            
        Returns:
            int: Number of invalid locations removed
        """
        # Get all locations
        all_locations = session.exec(select(LocationModel)).all()
        
        # Create a set of all valid location IDs
        valid_ids = {loc.id for loc in all_locations}
        
        # Identify invalid locations (those with parent_id not in valid_ids)
        invalid_locations = [
            loc for loc in all_locations
            if loc.parent_id and loc.parent_id not in valid_ids
        ]
        
        # Delete invalid locations and their descendants
        deleted_count = 0
        for loc in invalid_locations:
            # Get the hierarchy to delete
            hierarchy = LocationRepository.get_location_hierarchy(session, loc.id)
            affected_ids = hierarchy["affected_location_ids"]
            
            # Delete all affected locations
            for loc_id in affected_ids:
                location = session.get(LocationModel, loc_id)
                if location:
                    session.delete(location)
                    deleted_count += 1
        
        session.commit()
        return deleted_count

    @staticmethod
    def preview_delete(session: Session, location_id: str) -> Dict[str, Any]:
        """
        Preview what will be affected when deleting a location.
        
        Args:
            session: The database session
            location_id: The ID of the location to preview deletion for
            
        Returns:
            dict: Dictionary containing preview information
        """
        # Get all affected locations (including children)
        hierarchy = LocationRepository.get_location_hierarchy(session, location_id)
        affected_location_ids = hierarchy["affected_location_ids"]
        
        # Get all affected parts
        affected_parts = LocationRepository.get_affected_part_ids(session, affected_location_ids)
        
        return {
            "affected_parts_count": len(affected_parts),
            "affected_locations_count": len(affected_location_ids),
            "location_hierarchy": hierarchy["hierarchy"]
        }
