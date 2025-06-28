"""
Rate limiting API routes for exposing usage statistics and monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.rate_limit_service import RateLimitService
from MakerMatrix.models.models import engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize rate limit service
rate_limit_service = RateLimitService(engine)

@router.get("/suppliers", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_all_supplier_usage(
    current_user: UserModel = Depends(get_current_user)
):
    """Get rate limit usage statistics for all suppliers"""
    try:
        usage_data = await rate_limit_service.get_all_supplier_usage()
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved usage statistics for {len(usage_data)} suppliers",
            data=usage_data
        )
    except Exception as e:
        logger.error(f"Failed to get supplier usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage statistics: {str(e)}")

@router.get("/suppliers/{supplier_name}", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier_usage(
    supplier_name: str,
    time_period: str = "24h",
    current_user: UserModel = Depends(get_current_user)
):
    """Get detailed usage statistics for a specific supplier"""
    try:
        # Check rate limit status
        rate_status = await rate_limit_service.check_rate_limit(supplier_name.upper())
        
        # Get usage statistics
        usage_stats = await rate_limit_service.get_usage_stats(supplier_name.upper(), time_period)
        
        response_data = {
            "supplier_name": supplier_name.upper(),
            "rate_limit_status": rate_status,
            "usage_statistics": usage_stats
        }
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved usage statistics for {supplier_name}",
            data=response_data
        )
    except Exception as e:
        logger.error(f"Failed to get usage for {supplier_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage statistics: {str(e)}")

@router.get("/suppliers/{supplier_name}/status", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier_rate_limit_status(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get current rate limit status for a supplier (for real-time monitoring)"""
    try:
        rate_status = await rate_limit_service.check_rate_limit(supplier_name.upper())
        
        return ResponseSchema(
            status="success",
            message=f"Rate limit status for {supplier_name}",
            data=rate_status
        )
    except Exception as e:
        logger.error(f"Failed to get rate limit status for {supplier_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rate limit status: {str(e)}")

@router.post("/initialize", response_model=ResponseSchema[Dict[str, Any]])
async def initialize_default_rate_limits(
    current_user: UserModel = Depends(get_current_user)
):
    """Initialize default rate limits for known suppliers"""
    try:
        await rate_limit_service.initialize_default_limits()
        
        return ResponseSchema(
            status="success",
            message="Default rate limits initialized successfully",
            data={"initialized": True}
        )
    except Exception as e:
        logger.error(f"Failed to initialize rate limits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize rate limits: {str(e)}")

@router.get("/summary", response_model=ResponseSchema[Dict[str, Any]])
async def get_rate_limit_summary(
    current_user: UserModel = Depends(get_current_user)
):
    """Get summary of rate limiting across all suppliers"""
    try:
        usage_data = await rate_limit_service.get_all_supplier_usage()
        
        # Calculate summary statistics
        total_suppliers = len(usage_data)
        suppliers_with_usage = len([s for s in usage_data if s["stats_24h"]["total_requests"] > 0])
        total_requests_24h = sum(s["stats_24h"]["total_requests"] for s in usage_data)
        
        # Check which suppliers are approaching limits
        approaching_limits = []
        for supplier_data in usage_data:
            for period, usage in supplier_data["usage_percentage"].items():
                if usage > 80:  # More than 80% of limit used
                    approaching_limits.append({
                        "supplier": supplier_data["supplier_name"],
                        "period": period,
                        "usage_percentage": usage
                    })
        
        summary = {
            "total_suppliers": total_suppliers,
            "suppliers_with_usage": suppliers_with_usage,
            "total_requests_24h": total_requests_24h,
            "approaching_limits": approaching_limits,
            "suppliers": usage_data
        }
        
        return ResponseSchema(
            status="success",
            message="Rate limiting summary retrieved successfully",
            data=summary
        )
    except Exception as e:
        logger.error(f"Failed to get rate limit summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rate limit summary: {str(e)}")