"""
Part Allocation Repository

Handles database operations for PartLocationAllocation model.
Provides CRUD operations and specialized queries for multi-location inventory.
"""

from typing import Optional, List, Sequence
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from MakerMatrix.models.part_allocation_models import PartLocationAllocation, AllocationCreate, AllocationUpdate
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError, InvalidReferenceError


class PartAllocationRepository:
    """Repository for managing part-location allocations"""

    @staticmethod
    def get_all_allocations_for_part(
        session: Session, part_id: str, include_details: bool = True
    ) -> Sequence[PartLocationAllocation]:
        """
        Get all location allocations for a specific part.

        Args:
            session: Database session
            part_id: Part UUID
            include_details: Whether to eagerly load location and part details

        Returns:
            List of PartLocationAllocation records
        """
        query = select(PartLocationAllocation).where(PartLocationAllocation.part_id == part_id)

        if include_details:
            query = query.options(
                selectinload(PartLocationAllocation.location), selectinload(PartLocationAllocation.part)
            )

        return session.exec(query).all()

    @staticmethod
    def get_allocation_by_id(session: Session, allocation_id: str) -> Optional[PartLocationAllocation]:
        """Get a specific allocation by ID with details loaded"""
        allocation = session.exec(
            select(PartLocationAllocation)
            .options(selectinload(PartLocationAllocation.location), selectinload(PartLocationAllocation.part))
            .where(PartLocationAllocation.id == allocation_id)
        ).first()

        if not allocation:
            raise ResourceNotFoundError(resource="Allocation", resource_id=allocation_id)

        return allocation

    @staticmethod
    def get_allocation_by_part_and_location(
        session: Session, part_id: str, location_id: str
    ) -> Optional[PartLocationAllocation]:
        """Get allocation for specific part-location pair"""
        return session.exec(
            select(PartLocationAllocation)
            .options(selectinload(PartLocationAllocation.location), selectinload(PartLocationAllocation.part))
            .where(PartLocationAllocation.part_id == part_id, PartLocationAllocation.location_id == location_id)
        ).first()

    @staticmethod
    def get_allocations_at_location(session: Session, location_id: str) -> Sequence[PartLocationAllocation]:
        """Get all part allocations at a specific location"""
        return session.exec(
            select(PartLocationAllocation)
            .options(selectinload(PartLocationAllocation.part), selectinload(PartLocationAllocation.location))
            .where(PartLocationAllocation.location_id == location_id)
        ).all()

    @staticmethod
    def create_allocation(
        session: Session,
        part_id: str,
        location_id: str,
        quantity: int,
        is_primary: bool = False,
        notes: Optional[str] = None,
    ) -> PartLocationAllocation:
        """
        Create a new part-location allocation.

        Args:
            session: Database session
            part_id: Part UUID
            location_id: Location UUID
            quantity: Quantity to allocate
            is_primary: Whether this is primary storage
            notes: Optional allocation notes

        Returns:
            Created PartLocationAllocation

        Raises:
            ResourceNotFoundError: If part or location doesn't exist
            InvalidReferenceError: If allocation already exists
        """
        # Verify part exists
        part = session.get(PartModel, part_id)
        if not part:
            raise ResourceNotFoundError(resource="Part", resource_id=part_id)

        # Verify location exists
        location = session.get(LocationModel, location_id)
        if not location:
            raise ResourceNotFoundError(resource="Location", resource_id=location_id)

        # Check if allocation already exists
        existing = PartAllocationRepository.get_allocation_by_part_and_location(session, part_id, location_id)
        if existing:
            raise InvalidReferenceError(
                status="error",
                message=f"Allocation already exists for part {part_id} at location {location_id}. Use update instead.",
                data={"existing_allocation_id": existing.id},
            )

        # Create allocation
        allocation = PartLocationAllocation(
            part_id=part_id,
            location_id=location_id,
            quantity_at_location=quantity,
            is_primary_storage=is_primary,
            notes=notes,
        )

        session.add(allocation)
        session.commit()
        session.refresh(allocation)

        return allocation

    @staticmethod
    def update_allocation(
        session: Session, allocation_id: str, update_data: AllocationUpdate
    ) -> PartLocationAllocation:
        """
        Update an existing allocation.

        Args:
            session: Database session
            allocation_id: Allocation UUID
            update_data: Update payload

        Returns:
            Updated PartLocationAllocation
        """
        allocation = PartAllocationRepository.get_allocation_by_id(session, allocation_id)

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            # Map frontend field names to model field names
            if key == "quantity":
                setattr(allocation, "quantity_at_location", value)
            elif key == "is_primary":
                setattr(allocation, "is_primary_storage", value)
            else:
                setattr(allocation, key, value)

        # Update timestamp
        from datetime import datetime

        allocation.last_updated = datetime.utcnow()

        session.add(allocation)
        session.commit()
        session.refresh(allocation)

        return allocation

    @staticmethod
    def update_allocation_quantity(session: Session, allocation_id: str, new_quantity: int) -> PartLocationAllocation:
        """
        Update only the quantity of an allocation.

        Args:
            session: Database session
            allocation_id: Allocation UUID
            new_quantity: New quantity value

        Returns:
            Updated PartLocationAllocation
        """
        allocation = PartAllocationRepository.get_allocation_by_id(session, allocation_id)

        allocation.quantity_at_location = new_quantity

        from datetime import datetime

        allocation.last_updated = datetime.utcnow()

        session.add(allocation)
        session.commit()
        session.refresh(allocation)

        return allocation

    @staticmethod
    def delete_allocation(session: Session, allocation_id: str) -> bool:
        """
        Delete an allocation.

        Args:
            session: Database session
            allocation_id: Allocation UUID

        Returns:
            True if deleted successfully
        """
        allocation = PartAllocationRepository.get_allocation_by_id(session, allocation_id)

        session.delete(allocation)
        session.commit()

        return True

    @staticmethod
    def delete_allocations_for_part(session: Session, part_id: str) -> int:
        """
        Delete all allocations for a part.

        Args:
            session: Database session
            part_id: Part UUID

        Returns:
            Number of allocations deleted
        """
        allocations = PartAllocationRepository.get_all_allocations_for_part(session, part_id, include_details=False)

        count = len(allocations)
        for allocation in allocations:
            session.delete(allocation)

        session.commit()
        return count

    @staticmethod
    def get_primary_allocation(session: Session, part_id: str) -> Optional[PartLocationAllocation]:
        """Get the primary storage allocation for a part"""
        return session.exec(
            select(PartLocationAllocation)
            .options(selectinload(PartLocationAllocation.location), selectinload(PartLocationAllocation.part))
            .where(PartLocationAllocation.part_id == part_id, PartLocationAllocation.is_primary_storage == True)
        ).first()

    @staticmethod
    def calculate_total_quantity(session: Session, part_id: str) -> int:
        """Calculate total quantity across all allocations for a part"""
        from sqlalchemy import func

        result = session.exec(
            select(func.sum(PartLocationAllocation.quantity_at_location)).where(
                PartLocationAllocation.part_id == part_id
            )
        ).first()

        return result or 0
