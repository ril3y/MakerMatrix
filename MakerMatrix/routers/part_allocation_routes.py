"""
Part Allocation API Routes

REST API endpoints for multi-location inventory allocation system.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from MakerMatrix.models.part_allocation_models import (
    AllocationCreate,
    AllocationUpdate,
    TransferRequest,
    SplitToCassetteRequest
)
from MakerMatrix.services.data.part_allocation_service import PartAllocationService
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.schemas.response import ResponseSchema

logger = logging.getLogger(__name__)

router = APIRouter()


def get_allocation_service():
    """Dependency injection for allocation service"""
    return PartAllocationService()


@router.get(
    "/parts/{part_id}/allocations",
    response_model=ResponseSchema,
    summary="Get all allocations for a part"
)
async def get_part_allocations(
    part_id: str,
    current_user: UserModel = Depends(get_current_user),
    service: PartAllocationService = Depends(get_allocation_service)
):
    """
    Get all location allocations for a specific part.

    Returns summary including:
    - Total quantity across all locations
    - Number of locations
    - Primary storage location
    - Detailed allocation breakdown
    """
    result = service.get_allocations_for_part(part_id)

    return ResponseSchema(
        status="success" if result.success else "error",
        message=result.message,
        data=result.data
    )


@router.post(
    "/parts/{part_id}/allocations",
    response_model=ResponseSchema,
    summary="Create new allocation"
)
async def create_allocation(
    part_id: str,
    allocation_data: AllocationCreate,
    current_user: UserModel = Depends(get_current_user),
    service: PartAllocationService = Depends(get_allocation_service)
):
    """
    Create a new part-location allocation.

    Allocates a specific quantity of a part to a location.
    """
    result = service.create_allocation(part_id, allocation_data)

    return ResponseSchema(
        status="success" if result.success else "error",
        message=result.message,
        data=result.data
    )


@router.put(
    "/parts/{part_id}/allocations/{allocation_id}",
    response_model=ResponseSchema,
    summary="Update allocation"
)
async def update_allocation(
    part_id: str,
    allocation_id: str,
    update_data: AllocationUpdate,
    current_user: UserModel = Depends(get_current_user),
    service: PartAllocationService = Depends(get_allocation_service)
):
    """
    Update an existing allocation.

    Can update quantity, primary storage flag, or notes.
    """
    result = service.update_allocation(allocation_id, update_data)

    return ResponseSchema(
        status="success" if result.success else "error",
        message=result.message,
        data=result.data
    )


@router.delete(
    "/parts/{part_id}/allocations/{allocation_id}",
    response_model=ResponseSchema,
    summary="Delete allocation"
)
async def delete_allocation(
    part_id: str,
    allocation_id: str,
    current_user: UserModel = Depends(get_current_user),
    service: PartAllocationService = Depends(get_allocation_service)
):
    """
    Delete an allocation.

    Removes the part-location allocation record.
    """
    result = service.delete_allocation(allocation_id)

    return ResponseSchema(
        status="success" if result.success else "error",
        message=result.message,
        data=result.data
    )


@router.post(
    "/parts/{part_id}/allocations/{allocation_id}/return_to_primary",
    response_model=ResponseSchema,
    summary="Return allocation to primary storage"
)
async def return_to_primary_storage(
    part_id: str,
    allocation_id: str,
    current_user: UserModel = Depends(get_current_user),
    service: PartAllocationService = Depends(get_allocation_service)
):
    """
    Return all quantity from a non-primary allocation back to primary storage.

    Deletes the allocation and adds the quantity back to the primary storage location.
    """
    result = service.return_to_primary_storage(part_id, allocation_id)

    return ResponseSchema(
        status="success" if result.success else "error",
        message=result.message,
        data=result.data
    )


@router.post(
    "/parts/{part_id}/transfer",
    response_model=ResponseSchema,
    summary="Transfer quantity between locations"
)
async def transfer_quantity(
    part_id: str,
    from_location_id: str = Query(..., description="Source location ID"),
    to_location_id: str = Query(..., description="Destination location ID"),
    quantity: int = Query(..., gt=0, description="Quantity to transfer"),
    notes: Optional[str] = Query(None, description="Transfer notes"),
    current_user: UserModel = Depends(get_current_user),
    service: PartAllocationService = Depends(get_allocation_service)
):
    """
    Transfer quantity from one location to another.

    Business logic:
    1. Validates source has sufficient quantity
    2. Decrements source allocation
    3. Increments destination allocation (creates if needed)
    4. Returns updated part with allocation data
    """
    transfer_data = TransferRequest(
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        quantity=quantity,
        notes=notes
    )

    result = service.transfer_quantity(part_id, transfer_data)

    return ResponseSchema(
        status="success" if result.success else "error",
        message=result.message,
        data=result.data
    )


@router.post(
    "/parts/{part_id}/allocations/split_to_cassette",
    response_model=ResponseSchema,
    summary="Split quantity to cassette"
)
async def split_to_cassette(
    part_id: str,
    request: SplitToCassetteRequest,
    current_user: UserModel = Depends(get_current_user),
    service: PartAllocationService = Depends(get_allocation_service)
):
    """
    Split quantity from a reel to a cassette location.

    Can either:
    - Transfer to existing cassette
    - Create new cassette and transfer
    """
    result = service.split_to_cassette(part_id, request)

    return ResponseSchema(
        status="success" if result.success else "error",
        message=result.message,
        data=result.data
    )
