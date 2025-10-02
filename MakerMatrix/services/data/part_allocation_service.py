"""
Part Allocation Service

Business logic for multi-location inventory allocation system.
Handles transfer, split, and allocation management operations.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlmodel import Session
from datetime import datetime

from MakerMatrix.models.models import engine
from MakerMatrix.models.part_allocation_models import (
    PartLocationAllocation,
    AllocationCreate,
    AllocationUpdate,
    TransferRequest,
    SplitToCassetteRequest
)
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.repositories.part_allocation_repository import PartAllocationRepository
from MakerMatrix.services.base_service import BaseService, ServiceResponse
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    InvalidReferenceError
)

logger = logging.getLogger(__name__)


class PartAllocationService(BaseService):
    """Service for managing part-location allocations"""

    def __init__(self):
        super().__init__()
        self.entity_name = "PartAllocation"

    def get_allocations_for_part(
        self,
        part_id: str
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Get all location allocations for a part.

        Returns full allocation summary including total quantity and allocation details.
        """
        try:
            self.log_operation("get_allocations", "Part", part_id)

            with self.get_session() as session:
                # Get part to verify it exists
                part = session.get(PartModel, part_id)
                if not part:
                    raise ResourceNotFoundError(resource="Part", resource_id=part_id)

                # Get all allocations
                allocations = PartAllocationRepository.get_all_allocations_for_part(
                    session, part_id, include_details=True
                )

                # Calculate summary
                total_quantity = sum(alloc.quantity_at_location for alloc in allocations)
                location_count = len(allocations)

                # Find primary location
                primary_alloc = next(
                    (alloc for alloc in allocations if alloc.is_primary_storage),
                    allocations[0] if allocations else None
                )

                response_data = {
                    "part_id": part.id,
                    "part_name": part.part_name,
                    "part_number": part.part_number,
                    "total_quantity": total_quantity,
                    "location_count": location_count,
                    "primary_location": primary_alloc.location.to_dict() if primary_alloc else None,
                    "allocations": [alloc.to_dict() for alloc in allocations]
                }

                return self.success_response(
                    f"Retrieved {location_count} allocations for part {part.part_name}",
                    response_data
                )

        except Exception as e:
            return self.handle_exception(e, f"get allocations for part {part_id}")

    def create_allocation(
        self,
        part_id: str,
        allocation_data: AllocationCreate
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Create a new part-location allocation.

        Args:
            part_id: Part UUID
            allocation_data: Allocation creation data

        Returns:
            Created allocation
        """
        try:
            self.log_operation("create_allocation", "Part", part_id)

            with self.get_session() as session:
                allocation = PartAllocationRepository.create_allocation(
                    session=session,
                    part_id=part_id,
                    location_id=allocation_data.location_id,
                    quantity=allocation_data.quantity,
                    is_primary=allocation_data.is_primary,
                    notes=allocation_data.notes
                )

                return self.success_response(
                    f"Created allocation of {allocation.quantity_at_location} units",
                    allocation.to_dict()
                )

        except Exception as e:
            return self.handle_exception(e, f"create allocation for part {part_id}")

    def update_allocation(
        self,
        allocation_id: str,
        update_data: AllocationUpdate
    ) -> ServiceResponse[Dict[str, Any]]:
        """Update an existing allocation"""
        try:
            self.log_operation("update_allocation", "Allocation", allocation_id)

            with self.get_session() as session:
                allocation = PartAllocationRepository.update_allocation(
                    session, allocation_id, update_data
                )

                return self.success_response(
                    "Allocation updated successfully",
                    allocation.to_dict()
                )

        except Exception as e:
            return self.handle_exception(e, f"update allocation {allocation_id}")

    def delete_allocation(
        self,
        allocation_id: str
    ) -> ServiceResponse[Dict[str, Any]]:
        """Delete an allocation"""
        try:
            self.log_operation("delete_allocation", "Allocation", allocation_id)

            with self.get_session() as session:
                PartAllocationRepository.delete_allocation(session, allocation_id)

                return self.success_response(
                    "Allocation deleted successfully",
                    {"allocation_id": allocation_id, "deleted": True}
                )

        except Exception as e:
            return self.handle_exception(e, f"delete allocation {allocation_id}")

    def transfer_quantity(
        self,
        part_id: str,
        transfer_data: TransferRequest
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Transfer quantity between two locations.

        Business Logic:
        1. Validate both locations exist and have allocations
        2. Verify source has enough quantity
        3. Decrement source allocation
        4. Increment destination allocation (create if needed)
        5. Return updated allocations

        Args:
            part_id: Part UUID
            transfer_data: Transfer request with from/to locations and quantity

        Returns:
            Updated allocation details
        """
        try:
            self.log_operation(
                "transfer_quantity",
                "Part",
                f"{part_id}: {transfer_data.quantity} from {transfer_data.from_location_id} to {transfer_data.to_location_id}"
            )

            with self.get_session() as session:
                # Verify part exists
                part = session.get(PartModel, part_id)
                if not part:
                    raise ResourceNotFoundError(resource="Part", resource_id=part_id)

                # Get source allocation
                from_alloc = PartAllocationRepository.get_allocation_by_part_and_location(
                    session, part_id, transfer_data.from_location_id
                )
                if not from_alloc:
                    raise InvalidReferenceError(
                        status="error",
                        message=f"No allocation found at source location",
                        data={"location_id": transfer_data.from_location_id}
                    )

                # Verify sufficient quantity
                if from_alloc.quantity_at_location < transfer_data.quantity:
                    raise InvalidReferenceError(
                        status="error",
                        message=f"Insufficient quantity at source. Available: {from_alloc.quantity_at_location}, Requested: {transfer_data.quantity}",
                        data={
                            "available": from_alloc.quantity_at_location,
                            "requested": transfer_data.quantity
                        }
                    )

                # Decrement source
                new_from_quantity = from_alloc.quantity_at_location - transfer_data.quantity
                from_alloc.quantity_at_location = new_from_quantity
                from_alloc.last_updated = datetime.utcnow()
                session.add(from_alloc)

                # Get or create destination allocation
                to_alloc = PartAllocationRepository.get_allocation_by_part_and_location(
                    session, part_id, transfer_data.to_location_id
                )

                if to_alloc:
                    # Increment existing allocation
                    to_alloc.quantity_at_location += transfer_data.quantity
                    to_alloc.last_updated = datetime.utcnow()
                    if transfer_data.notes:
                        to_alloc.notes = transfer_data.notes
                    session.add(to_alloc)
                else:
                    # Create new allocation
                    to_alloc = PartLocationAllocation(
                        part_id=part_id,
                        location_id=transfer_data.to_location_id,
                        quantity_at_location=transfer_data.quantity,
                        is_primary_storage=False,  # Transfers are not primary
                        notes=transfer_data.notes
                    )
                    session.add(to_alloc)

                # Delete source allocation if quantity is zero
                if new_from_quantity == 0:
                    session.delete(from_alloc)
                    self.logger.info(f"Deleted source allocation (quantity reached zero)")

                session.commit()

                # Refresh to get updated data
                if new_from_quantity > 0:
                    session.refresh(from_alloc)
                session.refresh(to_alloc)

                response_data = {
                    "part_id": part_id,
                    "transferred_quantity": transfer_data.quantity,
                    "from_allocation": from_alloc.to_dict() if new_from_quantity > 0 else None,
                    "to_allocation": to_alloc.to_dict(),
                    "from_deleted": new_from_quantity == 0
                }

                return self.success_response(
                    f"Transferred {transfer_data.quantity} units from {from_alloc.location.name} to {to_alloc.location.name}",
                    response_data
                )

        except Exception as e:
            return self.handle_exception(e, f"transfer quantity for part {part_id}")

    def split_to_cassette(
        self,
        part_id: str,
        split_data: SplitToCassetteRequest
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Quick split to cassette operation.

        Business Logic:
        1. If create_new_cassette: Create cassette location
        2. Transfer quantity to cassette
        3. Return cassette and allocation details

        Args:
            part_id: Part UUID
            split_data: Split request with cassette creation options

        Returns:
            Created cassette and allocation details
        """
        try:
            self.log_operation(
                "split_to_cassette",
                "Part",
                f"{part_id}: {split_data.quantity} to cassette"
            )

            with self.get_session() as session:
                # Verify part exists
                part = session.get(PartModel, part_id)
                if not part:
                    raise ResourceNotFoundError(resource="Part", resource_id=part_id)

                cassette_id = split_data.cassette_id
                cassette = None

                # Create new cassette if requested
                if split_data.create_new_cassette:
                    if not split_data.cassette_name:
                        raise InvalidReferenceError(
                            status="error",
                            message="cassette_name is required when create_new_cassette is true",
                            data=None
                        )

                    # Create cassette location
                    cassette = LocationModel(
                        name=split_data.cassette_name,
                        parent_id=split_data.parent_location_id,
                        location_type="cassette",
                        is_mobile=True,
                        container_capacity=split_data.cassette_capacity,
                        emoji=split_data.cassette_emoji,
                        description=f"Container for {part.part_name}"
                    )
                    session.add(cassette)
                    session.flush()  # Get ID without committing
                    cassette_id = cassette.id
                else:
                    # Use existing cassette
                    if not cassette_id:
                        raise InvalidReferenceError(
                            status="error",
                            message="cassette_id is required when create_new_cassette is false",
                            data=None
                        )
                    cassette = session.get(LocationModel, cassette_id)
                    if not cassette:
                        raise ResourceNotFoundError(resource="Cassette", resource_id=cassette_id)

                # Perform transfer to cassette
                transfer_request = TransferRequest(
                    from_location_id=split_data.from_location_id,
                    to_location_id=cassette_id,
                    quantity=split_data.quantity,
                    notes=split_data.notes
                )

                # Use existing transfer logic (without calling self.transfer_quantity to avoid double session)
                from_alloc = PartAllocationRepository.get_allocation_by_part_and_location(
                    session, part_id, split_data.from_location_id
                )
                if not from_alloc:
                    raise InvalidReferenceError(
                        status="error",
                        message="No allocation found at source location",
                        data={"location_id": split_data.from_location_id}
                    )

                if from_alloc.quantity_at_location < split_data.quantity:
                    raise InvalidReferenceError(
                        status="error",
                        message=f"Insufficient quantity. Available: {from_alloc.quantity_at_location}",
                        data={"available": from_alloc.quantity_at_location}
                    )

                # Decrement source
                new_from_quantity = from_alloc.quantity_at_location - split_data.quantity
                from_alloc.quantity_at_location = new_from_quantity
                from_alloc.last_updated = datetime.utcnow()
                session.add(from_alloc)

                # Create cassette allocation
                cassette_alloc = PartLocationAllocation(
                    part_id=part_id,
                    location_id=cassette_id,
                    quantity_at_location=split_data.quantity,
                    is_primary_storage=False,
                    notes=split_data.notes
                )
                session.add(cassette_alloc)

                # Delete source if empty
                if new_from_quantity == 0:
                    session.delete(from_alloc)

                session.commit()

                # Refresh to get updated data
                session.refresh(cassette)
                session.refresh(cassette_alloc)

                response_data = {
                    "part_id": part_id,
                    "cassette": cassette.to_dict(),
                    "allocation": cassette_alloc.to_dict(),
                    "cassette_created": split_data.create_new_cassette,
                    "transferred_quantity": split_data.quantity
                }

                return self.success_response(
                    f"Split {split_data.quantity} units to cassette {cassette.name}",
                    response_data
                )

        except Exception as e:
            return self.handle_exception(e, f"split to cassette for part {part_id}")
