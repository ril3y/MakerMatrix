"""
Dashboard Service - Provides inventory analytics for the dashboard.

Focused, lightweight service for dashboard data only.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy import func, select
from sqlmodel import Session

from MakerMatrix.services.base_service import BaseService
from MakerMatrix.models.models import (
    PartModel,
    CategoryModel,
    LocationModel,
)
from MakerMatrix.models.part_allocation_models import PartLocationAllocation

logger = logging.getLogger(__name__)


class DashboardService(BaseService):
    """Service for dashboard analytics data."""

    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get overall inventory summary statistics."""
        with self.get_session() as session:
            total_parts = session.exec(select(func.count()).select_from(PartModel)).one()[0]

            # Get total units from allocations
            total_units = session.exec(select(func.sum(PartLocationAllocation.quantity_at_location))).one()[0] or 0

            total_categories = session.exec(select(func.count()).select_from(CategoryModel)).one()[0]
            total_locations = session.exec(select(func.count()).select_from(LocationModel)).one()[0]

            # Count parts with allocations (have locations)
            parts_with_location = session.exec(select(func.count(func.distinct(PartLocationAllocation.part_id)))).one()[
                0
            ]

            parts_without_location = total_parts - parts_with_location

            # Count low stock parts (< 10 units total across all locations)
            low_stock_subquery = (
                select(
                    PartLocationAllocation.part_id,
                    func.sum(PartLocationAllocation.quantity_at_location).label("total_quantity"),
                )
                .group_by(PartLocationAllocation.part_id)
                .subquery()
            )

            low_stock_count = session.exec(
                select(func.count()).select_from(low_stock_subquery).where(low_stock_subquery.c.total_quantity < 10)
            ).one()[0]

            # Count zero stock parts
            zero_stock_count = session.exec(
                select(func.count()).select_from(low_stock_subquery).where(low_stock_subquery.c.total_quantity == 0)
            ).one()[0]

            return {
                "total_parts": total_parts,
                "total_units": int(total_units),
                "total_categories": total_categories,
                "total_locations": total_locations,
                "parts_with_location": parts_with_location,
                "parts_without_location": parts_without_location,
                "low_stock_count": low_stock_count,
                "zero_stock_count": zero_stock_count,
            }

    def get_parts_by_category(self) -> List[Dict[str, Any]]:
        """Get parts distribution by category."""
        with self.get_session() as session:
            stmt = (
                select(
                    CategoryModel.name.label("category"),
                    func.count(PartModel.id).label("part_count"),
                    func.coalesce(
                        func.sum(
                            select(func.sum(PartLocationAllocation.quantity_at_location))
                            .where(PartLocationAllocation.part_id == PartModel.id)
                            .correlate(PartModel)
                            .scalar_subquery()
                        ),
                        0,
                    ).label("total_quantity"),
                )
                .select_from(PartModel)
                .outerjoin(PartModel.categories)
                .group_by(CategoryModel.name)
                .order_by(func.count(PartModel.id).desc())
            )

            results = session.exec(stmt).all()

            return [
                {
                    "category": r.category or "Uncategorized",
                    "part_count": r.part_count,
                    "total_quantity": int(r.total_quantity),
                }
                for r in results
            ]

    def get_parts_by_location(self) -> List[Dict[str, Any]]:
        """Get parts distribution by location."""
        with self.get_session() as session:
            stmt = (
                select(
                    LocationModel.name.label("location"),
                    func.count(func.distinct(PartLocationAllocation.part_id)).label("part_count"),
                    func.sum(PartLocationAllocation.quantity_at_location).label("total_quantity"),
                )
                .select_from(PartLocationAllocation)
                .join(LocationModel, PartLocationAllocation.location_id == LocationModel.id)
                .group_by(LocationModel.name)
                .order_by(func.count(func.distinct(PartLocationAllocation.part_id)).desc())
            )

            results = session.exec(stmt).all()

            return [
                {"location": r.location, "part_count": r.part_count, "total_quantity": int(r.total_quantity)}
                for r in results
            ]

    def get_parts_by_supplier(self) -> List[Dict[str, Any]]:
        """Get parts distribution by supplier."""
        with self.get_session() as session:
            stmt = (
                select(
                    PartModel.supplier.label("supplier"),
                    func.count(PartModel.id).label("part_count"),
                    func.coalesce(
                        func.sum(
                            select(func.sum(PartLocationAllocation.quantity_at_location))
                            .where(PartLocationAllocation.part_id == PartModel.id)
                            .correlate(PartModel)
                            .scalar_subquery()
                        ),
                        0,
                    ).label("total_quantity"),
                )
                .where(PartModel.supplier.isnot(None))
                .group_by(PartModel.supplier)
                .order_by(func.count(PartModel.id).desc())
            )

            results = session.exec(stmt).all()

            return [
                {"supplier": r.supplier, "part_count": r.part_count, "total_quantity": int(r.total_quantity)}
                for r in results
            ]

    def get_most_stocked_parts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get parts with highest stock quantities."""
        with self.get_session() as session:
            # Subquery for total quantity per part
            qty_subquery = (
                select(
                    PartLocationAllocation.part_id,
                    func.sum(PartLocationAllocation.quantity_at_location).label("total_qty"),
                )
                .group_by(PartLocationAllocation.part_id)
                .subquery()
            )

            stmt = (
                select(
                    PartModel.id,
                    PartModel.part_name,
                    PartModel.part_number,
                    PartModel.supplier,
                    qty_subquery.c.total_qty.label("quantity"),
                    func.group_concat(LocationModel.name, ", ").label("location"),
                )
                .join(qty_subquery, PartModel.id == qty_subquery.c.part_id)
                .outerjoin(PartLocationAllocation, PartModel.id == PartLocationAllocation.part_id)
                .outerjoin(LocationModel, PartLocationAllocation.location_id == LocationModel.id)
                .group_by(
                    PartModel.id,
                    PartModel.part_name,
                    PartModel.part_number,
                    PartModel.supplier,
                    qty_subquery.c.total_qty,
                )
                .order_by(qty_subquery.c.total_qty.desc())
                .limit(limit)
            )

            results = session.exec(stmt).all()

            return [
                {
                    "id": r.id,
                    "part_name": r.part_name,
                    "part_number": r.part_number,
                    "supplier": r.supplier or "Unknown",
                    "quantity": int(r.quantity),
                    "location": r.location or "No Location",
                }
                for r in results
            ]

    def get_least_stocked_parts(self, limit: int = 10, exclude_zero: bool = True) -> List[Dict[str, Any]]:
        """Get parts with lowest stock quantities."""
        with self.get_session() as session:
            # Subquery for total quantity per part
            qty_subquery = (
                select(
                    PartLocationAllocation.part_id,
                    func.sum(PartLocationAllocation.quantity_at_location).label("total_qty"),
                )
                .group_by(PartLocationAllocation.part_id)
                .subquery()
            )

            stmt = (
                select(
                    PartModel.id,
                    PartModel.part_name.label("part_name"),
                    PartModel.part_number,
                    PartModel.supplier,
                    qty_subquery.c.total_qty.label("quantity"),
                    func.group_concat(LocationModel.name, ", ").label("location"),
                )
                .join(qty_subquery, PartModel.id == qty_subquery.c.part_id)
                .outerjoin(PartLocationAllocation, PartModel.id == PartLocationAllocation.part_id)
                .outerjoin(LocationModel, PartLocationAllocation.location_id == LocationModel.id)
            )

            if exclude_zero:
                stmt = stmt.where(qty_subquery.c.total_qty > 0)

            stmt = (
                stmt.group_by(
                    PartModel.id,
                    PartModel.part_name,
                    PartModel.part_number,
                    PartModel.supplier,
                    qty_subquery.c.total_qty,
                )
                .order_by(qty_subquery.c.total_qty.asc())
                .limit(limit)
            )

            results = session.exec(stmt).all()

            return [
                {
                    "id": r.id,
                    "part_name": r.part_name,
                    "part_number": r.part_number,
                    "supplier": r.supplier or "Unknown",
                    "quantity": int(r.quantity),
                    "location": r.location or "No Location",
                }
                for r in results
            ]

    def get_low_stock_parts(self, threshold: int = 10, include_zero: bool = False) -> List[Dict[str, Any]]:
        """Get parts that are low in stock."""
        with self.get_session() as session:
            # Subquery for total quantity per part
            qty_subquery = (
                select(
                    PartLocationAllocation.part_id,
                    func.sum(PartLocationAllocation.quantity_at_location).label("total_qty"),
                )
                .group_by(PartLocationAllocation.part_id)
                .subquery()
            )

            stmt = (
                select(
                    PartModel.id,
                    PartModel.part_name.label("part_name"),
                    PartModel.part_number,
                    PartModel.supplier,
                    qty_subquery.c.total_qty.label("quantity"),
                    func.group_concat(LocationModel.name, ", ").label("location_name"),
                )
                .join(qty_subquery, PartModel.id == qty_subquery.c.part_id)
                .outerjoin(PartLocationAllocation, PartModel.id == PartLocationAllocation.part_id)
                .outerjoin(LocationModel, PartLocationAllocation.location_id == LocationModel.id)
                .where(qty_subquery.c.total_qty < threshold)
            )

            if not include_zero:
                stmt = stmt.where(qty_subquery.c.total_qty > 0)

            stmt = stmt.group_by(
                PartModel.id, PartModel.part_name, PartModel.part_number, PartModel.supplier, qty_subquery.c.total_qty
            ).order_by(qty_subquery.c.total_qty.asc())

            results = session.exec(stmt).all()

            return [
                {
                    "id": r.id,
                    "part_name": r.part_name,
                    "part_number": r.part_number,
                    "supplier": r.supplier or "Unknown",
                    "quantity": int(r.quantity),
                    "location_name": r.location_name or "No Location",
                }
                for r in results
            ]

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get complete dashboard summary (all data at once)."""
        return {
            "summary": self.get_inventory_summary(),
            "parts_by_category": self.get_parts_by_category(),
            "parts_by_location": self.get_parts_by_location(),
            "parts_by_supplier": self.get_parts_by_supplier(),
            "most_stocked_parts": self.get_most_stocked_parts(limit=10),
            "least_stocked_parts": self.get_least_stocked_parts(limit=10, exclude_zero=True),
            "low_stock_parts": self.get_low_stock_parts(threshold=10, include_zero=False)[:10],
        }


# Global service instance
dashboard_service = DashboardService()
