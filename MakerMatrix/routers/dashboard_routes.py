"""
Dashboard API routes for inventory analytics.

Provides a single endpoint for dashboard summary data.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends

from MakerMatrix.auth.dependencies import get_current_user_flexible
from MakerMatrix.models.models import UserModel
from MakerMatrix.services.data.dashboard_service import dashboard_service
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.routers.base import BaseRouter, standard_error_handling

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"], dependencies=[Depends(get_current_user_flexible)])
base_router = BaseRouter()


@router.get("/summary", response_model=ResponseSchema)
@standard_error_handling
async def get_dashboard_summary(
    current_user: UserModel = Depends(get_current_user_flexible),
) -> ResponseSchema[Dict[str, Any]]:
    """
    Get complete dashboard summary with inventory analytics.

    Returns all dashboard data in a single request:
    - Inventory summary statistics
    - Parts distribution by category, location, and supplier
    - Most/least stocked parts
    - Low stock alerts
    """
    logger.info(f"User {current_user.username} requesting dashboard summary")

    summary = dashboard_service.get_dashboard_summary()

    return base_router.build_success_response(message="Retrieved dashboard summary", data=summary)
