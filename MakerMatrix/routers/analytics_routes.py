"""
Analytics API routes for order and inventory analytics.

Provides endpoints for spending trends, order analysis, price trends,
and inventory insights.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException

from MakerMatrix.dependencies.auth import get_current_user
from MakerMatrix.models.models import UserModel
from MakerMatrix.services.analytics_service import analytics_service
from MakerMatrix.schemas.response import ResponseSchema

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/spending/by-supplier", response_model=ResponseSchema)
async def get_spending_by_supplier(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suppliers"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get spending breakdown by supplier."""
    try:
        logger.info(f"User {current_user.username} requesting spending by supplier")
        
        data = analytics_service.get_spending_by_supplier(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved spending data for {len(data)} suppliers",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting spending by supplier: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve spending data")


@router.get("/spending/trend", response_model=ResponseSchema)
async def get_spending_trend(
    period: str = Query("month", regex="^(day|week|month|year)$", description="Time period"),
    lookback_periods: int = Query(6, ge=1, le=24, description="Number of periods to look back"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get spending trend over time."""
    try:
        logger.info(f"User {current_user.username} requesting spending trend by {period}")
        
        data = analytics_service.get_spending_trend(
            period=period,
            lookback_periods=lookback_periods
        )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved spending trend for {len(data)} periods",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting spending trend: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve spending trend")


@router.get("/parts/order-frequency", response_model=ResponseSchema)
async def get_part_order_frequency(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of parts"),
    min_orders: int = Query(2, ge=1, description="Minimum number of orders to include"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get most frequently ordered parts."""
    try:
        logger.info(f"User {current_user.username} requesting part order frequency")
        
        data = analytics_service.get_part_order_frequency(
            limit=limit,
            min_orders=min_orders
        )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved {len(data)} frequently ordered parts",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting part order frequency: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve order frequency data")


@router.get("/prices/trends", response_model=ResponseSchema)
async def get_price_trends(
    part_id: Optional[str] = Query(None, description="Specific part ID (UUID) to analyze"),
    supplier: Optional[str] = Query(None, description="Filter by supplier"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of data points"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get price trends for parts."""
    try:
        logger.info(f"User {current_user.username} requesting price trends")
        
        data = analytics_service.get_price_trends(
            part_id=part_id,
            supplier=supplier,
            limit=limit
        )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved price trends for {len(data)} orders",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting price trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve price trends")


@router.get("/inventory/low-stock", response_model=ResponseSchema)
async def get_low_stock_parts(
    threshold_multiplier: float = Query(1.5, ge=0.1, le=5.0, description="Threshold multiplier for average order quantity"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get parts that are low in stock based on order history."""
    try:
        logger.info(f"User {current_user.username} requesting low stock parts")
        
        data = analytics_service.get_low_stock_parts(
            threshold_multiplier=threshold_multiplier
        )
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(data)} parts with low stock",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting low stock parts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve low stock data")


@router.get("/spending/by-category", response_model=ResponseSchema)
async def get_spending_by_category(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get spending breakdown by category."""
    try:
        logger.info(f"User {current_user.username} requesting spending by category")
        
        data = analytics_service.get_category_spending(
            start_date=start_date,
            end_date=end_date
        )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved spending data for {len(data)} categories",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting spending by category: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve category spending data")


@router.get("/inventory/value", response_model=ResponseSchema)
async def get_inventory_value(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Calculate total inventory value based on average prices."""
    try:
        logger.info(f"User {current_user.username} requesting inventory value")
        
        data = analytics_service.get_inventory_value()
        
        return ResponseSchema(
            status="success",
            message="Retrieved inventory value",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting inventory value: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve inventory value")


@router.get("/dashboard/summary", response_model=ResponseSchema)
async def get_dashboard_summary(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Get summary analytics for dashboard."""
    try:
        logger.info(f"User {current_user.username} requesting dashboard summary")
        
        # Get data for last 30 days
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        start_date = end_date - timedelta(days=30)
        
        # Collect all analytics
        spending_by_supplier = analytics_service.get_spending_by_supplier(
            start_date=start_date, end_date=end_date, limit=5
        )
        spending_trend = analytics_service.get_spending_trend(period="week", lookback_periods=4)
        frequent_parts = analytics_service.get_part_order_frequency(limit=10)
        low_stock = analytics_service.get_low_stock_parts()
        inventory_value = analytics_service.get_inventory_value()
        category_spending = analytics_service.get_category_spending(
            start_date=start_date, end_date=end_date
        )
        
        summary = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "spending_by_supplier": spending_by_supplier,
            "spending_trend": spending_trend,
            "frequent_parts": frequent_parts,
            "low_stock_count": len(low_stock),
            "low_stock_parts": low_stock[:10],  # Limit to top 10
            "inventory_value": inventory_value,
            "category_spending": category_spending
        }
        
        return ResponseSchema(
            status="success",
            message="Retrieved dashboard summary",
            data=summary
        )
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard summary")