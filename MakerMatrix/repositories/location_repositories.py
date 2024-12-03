from typing import Optional, List, Dict, Any, Sequence
from sqlalchemy import delete, func
from sqlmodel import Session, select
from MakerMatrix.models.models import LocationModel, LocationQueryModel, PartModel
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from sqlalchemy.orm import joinedload, selectinload


class LocationRepository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_all_locations(session: Session) -> Sequence[LocationModel]:
        return session.exec(select(LocationModel)).all()

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
            raise ValueError("Either 'id' or 'name' must be provided")
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
        new_location = LocationModel(**location_data)
        session.add(new_location)
        session.commit()
        session.refresh(new_location)
        return new_location

    @staticmethod
    def get_location_details(session: Session, location_id: str) -> Optional[LocationModel]:
        location = session.exec(
            select(LocationModel)
            .options(joinedload(LocationModel.children))
                .where(LocationModel.id == location_id)
        ).first()
        if location:
            return location
        else:
            raise ResourceNotFoundError(resource="Location", resource_id=location_id)
        

    @staticmethod
    def get_location_path(session: Session, query_location: LocationQueryModel) -> Optional[List[Dict]]:
        path = []
        current_location = LocationRepository.get_location(session, query_location)
        while current_location:
            path.append(current_location)
            if current_location.parent_id:
                current_location = session.exec(select(LocationModel).where(LocationModel.id == current_location.parent_id)).first()
            else:
                current_location = None
        return path[::-1]  # Reverse the path to start from the root
    
    @staticmethod
    def delete_all_locations(session: Session) -> dict:
        try:
            locations = session.exec(select(LocationModel)).all()
            count = len(locations)
            session.exec(delete(LocationModel))
            session.commit()
            return {"status": "success", "message": f"All {count} locations removed successfully", "data": None}
        except Exception as e:
            return {"status": "error", "message": f"Error deleting locations: {str(e)}", "data": None}
        
    @staticmethod
    def update_location(session: Session, location_id: str, location_data: Dict[str, Any]) -> LocationModel:
        location = session.get(LocationModel, location_id)
        if not location:
            raise ResourceNotFoundError(resource="Location", resource_id=location_id)
        
        for key, value in location_data.items():
            setattr(location, key, value)
        
        session.add(location)
        session.commit()
        session.refresh(location)
        return location
