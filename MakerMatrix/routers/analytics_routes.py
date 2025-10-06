"""
Analytics API routes for order and inventory analytics.

Provides endpoints for spending trends, order analysis, price trends,
and inventory insights.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException

from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.models import UserModel
from MakerMatrix.services.data.analytics_service import analytics_service
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.routers.base import BaseRouter, standard_error_handling

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)]
)
base_router = BaseRouter()


@router.get("/spending/by-supplier", response_model=ResponseSchema)
@standard_error_handling
async def get_spending_by_supplier(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suppliers"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get spending breakdown by supplier."""
    logger.info(f"User {current_user.username} requesting spending by supplier")
    
    data = analytics_service.get_spending_by_supplier(
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return base_router.build_success_response(
        message=f"Retrieved spending data for {len(data)} suppliers",
        data=data
    )


@router.get("/spending/trend", response_model=ResponseSchema)
@standard_error_handling
async def get_spending_trend(
    period: str = Query("month", regex="^(day|week|month|year)$", description="Time period"),
    lookback_periods: int = Query(6, ge=1, le=24, description="Number of periods to look back"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get spending trend over time."""
    logger.info(f"User {current_user.username} requesting spending trend by {period}")
    
    data = analytics_service.get_spending_trend(
        period=period,
        lookback_periods=lookback_periods
    )
    
    return base_router.build_success_response(
        message=f"Retrieved spending trend for {len(data)} periods",
        data=data
    )


@router.get("/parts/order-frequency", response_model=ResponseSchema)
@standard_error_handling
async def get_part_order_frequency(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of parts"),
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get most frequently ordered parts."""
    logger.info(f"User {current_user.username} requesting part order frequency")
    
    data = analytics_service.get_part_order_frequency(
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return base_router.build_success_response(
        message=f"Retrieved {len(data)} frequently ordered parts",
        data=data
    )


@router.get("/prices/trends", response_model=ResponseSchema)
@standard_error_handling
async def get_price_trends(
    part_number: Optional[str] = Query(None, description="Specific part number to analyze"),
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get price trends for parts."""
    logger.info(f"User {current_user.username} requesting price trends")
    
    data = analytics_service.get_price_trends(
        part_number=part_number,
        start_date=start_date,
        end_date=end_date
    )
    
    return base_router.build_success_response(
        message=f"Retrieved price trends for {len(data)} orders",
        data=data
    )


@router.get("/inventory/low-stock", response_model=ResponseSchema)
@standard_error_handling
async def get_low_stock_parts(
    threshold: int = Query(5, ge=1, le=100, description="Stock threshold below which parts are considered low"),
    include_zero: bool = Query(True, description="Whether to include parts with zero stock"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get parts that are low in stock."""
    logger.info(f"User {current_user.username} requesting low stock parts")
    
    data = analytics_service.get_low_stock_parts(
        threshold=threshold,
        include_zero=include_zero
    )
    
    return base_router.build_success_response(
        message=f"Found {len(data)} parts with low stock",
        data=data
    )


@router.get("/spending/by-category", response_model=ResponseSchema)
@standard_error_handling
async def get_spending_by_category(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get spending breakdown by category."""
    logger.info(f"User {current_user.username} requesting spending by category")
    
    data = analytics_service.get_category_spending(
        start_date=start_date,
        end_date=end_date
    )
    
    return base_router.build_success_response(
        message=f"Retrieved spending data for {len(data)} categories",
        data=data
    )


@router.get("/inventory/value", response_model=ResponseSchema)
@standard_error_handling
async def get_inventory_value(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Calculate total inventory value based on average prices."""
    logger.info(f"User {current_user.username} requesting inventory value")
    
    data = analytics_service.get_inventory_value()
    
    return base_router.build_success_response(
        message="Retrieved inventory value",
        data=data
    )


@router.get("/dashboard/summary", response_model=ResponseSchema)
@standard_error_handling
async def get_dashboard_summary(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Get inventory-focused analytics dashboard summary."""
    logger.info(f"User {current_user.username} requesting inventory dashboard summary")

    # Get inventory-focused analytics (no order dependency)
    inventory_summary = analytics_service.get_inventory_summary()
    parts_by_category = analytics_service.get_parts_by_category()
    parts_by_location = analytics_service.get_parts_by_location()
    parts_by_supplier = analytics_service.get_parts_by_supplier()
    most_stocked = analytics_service.get_most_stocked_parts(limit=10)
    least_stocked = analytics_service.get_least_stocked_parts(limit=10, exclude_zero=True)
    low_stock = analytics_service.get_low_stock_parts(threshold=10, include_zero=False)

    summary = {
        "summary": inventory_summary,
        "parts_by_category": parts_by_category,
        "parts_by_location": parts_by_location,
        "parts_by_supplier": parts_by_supplier,
        "most_stocked_parts": most_stocked,
        "least_stocked_parts": least_stocked,
        "low_stock_parts": low_stock[:10]  # Limit to top 10
    }

    return base_router.build_success_response(
        message="Retrieved inventory dashboard summary",
        data=summary
    )


@router.get("/inventory/parts-by-category", response_model=ResponseSchema)
@standard_error_handling
async def get_inventory_parts_by_category(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get parts distribution by category."""
    logger.info(f"User {current_user.username} requesting parts by category")

    data = analytics_service.get_parts_by_category()

    return base_router.build_success_response(
        message=f"Retrieved {len(data)} categories",
        data=data
    )


@router.get("/inventory/parts-by-location", response_model=ResponseSchema)
@standard_error_handling
async def get_inventory_parts_by_location(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get parts distribution by location."""
    logger.info(f"User {current_user.username} requesting parts by location")

    data = analytics_service.get_parts_by_location()

    return base_router.build_success_response(
        message=f"Retrieved {len(data)} locations",
        data=data
    )


@router.get("/inventory/parts-by-supplier", response_model=ResponseSchema)
@standard_error_handling
async def get_inventory_parts_by_supplier(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get parts distribution by supplier."""
    logger.info(f"User {current_user.username} requesting parts by supplier")

    data = analytics_service.get_parts_by_supplier()

    return base_router.build_success_response(
        message=f"Retrieved {len(data)} suppliers",
        data=data
    )


@router.get("/inventory/most-stocked", response_model=ResponseSchema)
@standard_error_handling
async def get_inventory_most_stocked(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of parts"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get parts with highest stock quantities."""
    logger.info(f"User {current_user.username} requesting most stocked parts")

    data = analytics_service.get_most_stocked_parts(limit=limit)

    return base_router.build_success_response(
        message=f"Retrieved {len(data)} most stocked parts",
        data=data
    )


@router.get("/inventory/least-stocked", response_model=ResponseSchema)
@standard_error_handling
async def get_inventory_least_stocked(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of parts"),
    exclude_zero: bool = Query(True, description="Exclude parts with zero stock"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get parts with lowest stock quantities."""
    logger.info(f"User {current_user.username} requesting least stocked parts")

    data = analytics_service.get_least_stocked_parts(limit=limit, exclude_zero=exclude_zero)

    return base_router.build_success_response(
        message=f"Retrieved {len(data)} least stocked parts",
        data=data
    )


@router.get("/inventory/summary-stats", response_model=ResponseSchema)
@standard_error_handling
async def get_inventory_summary_stats(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Get overall inventory summary statistics."""
    logger.info(f"User {current_user.username} requesting inventory summary stats")

    data = analytics_service.get_inventory_summary()

    return base_router.build_success_response(
        message="Retrieved inventory summary statistics",
        data=data
    )


@router.get("/suppliers/enrichment-analysis", response_model=ResponseSchema)
@standard_error_handling
async def get_supplier_enrichment_analysis(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """
    Analyze parts by supplier and show which suppliers can be enriched vs just metadata.
    
    This endpoint helps identify:
    - Parts with suppliers that have enrichment implementations
    - Parts with suppliers that are just metadata strings (e.g., Amazon, Alibaba)
    - Recommended actions for parts with non-enrichable suppliers
    """
    from sqlalchemy.orm import Session
    from sqlalchemy import func, text
    from MakerMatrix.models.models import engine, PartModel
    from MakerMatrix.suppliers.registry import SupplierRegistry
    
    logger.info(f"User {current_user.username} requesting supplier enrichment analysis")
    
    # Get all available enrichment suppliers
    available_suppliers = SupplierRegistry.get_available_suppliers()
    
    # Query parts grouped by supplier
    with Session(engine) as session:
        # Get supplier counts from parts
        supplier_counts = session.execute(
            text("""
                SELECT 
                    LOWER(supplier) as supplier_name,
                    COUNT(*) as part_count,
                    COUNT(CASE WHEN part_number IS NOT NULL AND part_number != '' THEN 1 END) as parts_with_part_numbers
                FROM parts 
                WHERE supplier IS NOT NULL AND supplier != ''
                GROUP BY LOWER(supplier)
                ORDER BY part_count DESC
            """)
        ).fetchall()
    
    # Categorize suppliers
    enrichable_suppliers = []
    metadata_only_suppliers = []
    total_enrichable_parts = 0
    total_metadata_parts = 0
    
    for row in supplier_counts:
        supplier_name = row.supplier_name
        part_count = row.part_count
        parts_with_part_numbers = row.parts_with_part_numbers
        
        supplier_info = {
            "supplier": supplier_name,
            "part_count": part_count,
            "parts_with_part_numbers": parts_with_part_numbers,
            "enrichment_ready": parts_with_part_numbers > 0
        }
        
        if supplier_name in available_suppliers:
            supplier_info["status"] = "enrichment_available"
            supplier_info["can_enrich"] = True
            enrichable_suppliers.append(supplier_info)
            total_enrichable_parts += part_count
        else:
            supplier_info["status"] = "metadata_only"
            supplier_info["can_enrich"] = False
            supplier_info["suggested_alternative"] = _suggest_alternative_supplier(supplier_name)
            metadata_only_suppliers.append(supplier_info)
            total_metadata_parts += part_count
    
    # Calculate summary statistics
    total_parts = total_enrichable_parts + total_metadata_parts
    enrichment_coverage = (total_enrichable_parts / total_parts * 100) if total_parts > 0 else 0
    
    analysis = {
        "summary": {
            "total_suppliers": len(supplier_counts),
            "enrichable_suppliers": len(enrichable_suppliers),
            "metadata_only_suppliers": len(metadata_only_suppliers),
            "total_parts": total_parts,
            "enrichable_parts": total_enrichable_parts,
            "metadata_only_parts": total_metadata_parts,
            "enrichment_coverage_percent": round(enrichment_coverage, 1)
        },
        "available_implementations": available_suppliers,
        "enrichable_suppliers": enrichable_suppliers,
        "metadata_only_suppliers": metadata_only_suppliers,
        "recommendations": {
            "message": "Suppliers like Amazon, Alibaba, etc. are stored as metadata only. For enrichment, use suppliers with implementations: " + ", ".join(available_suppliers),
            "actions": [
                "Parts with metadata-only suppliers cannot be enriched",
                "Consider updating part suppliers to enrichable ones where possible",
                f"Current enrichment coverage: {enrichment_coverage:.1f}% of parts"
            ]
        }
    }
    
    return base_router.build_success_response(
        message="Retrieved supplier enrichment analysis",
        data=analysis
    )


def _suggest_alternative_supplier(supplier_name: str) -> Optional[str]:
    """Suggest alternative enrichable supplier based on supplier name"""
    supplier_lower = supplier_name.lower()
    
    # Map common metadata suppliers to enrichable alternatives
    suggestions = {
        "amazon": "digikey",  # Amazon electronics -> DigiKey
        "alibaba": "lcsc",    # Alibaba -> LCSC (Chinese supplier)
        "aliexpress": "lcsc", # AliExpress -> LCSC
        "ebay": "digikey",    # eBay -> DigiKey
        "local": "digikey",   # Local supplier -> DigiKey
        "unknown": "digikey"  # Unknown -> DigiKey
    }
    
    for key, suggestion in suggestions.items():
        if key in supplier_lower:
            return suggestion
    
    # Default suggestion for electronic components
    return "digikey"