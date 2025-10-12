"""
Tool Service Module

Provides business logic for tool management operations.
Follows the same patterns as PartService but adapted for tools.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy import or_, func

from MakerMatrix.models.tool_models import (
    ToolModel,
    ToolLocationAllocation,
    ToolCreate,
    ToolUpdate,
    ToolCheckout,
    ToolReturn,
    ToolMaintenanceRecord
)
from MakerMatrix.models.category_models import CategoryModel
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.services.base_service import BaseService, ServiceResponse
from MakerMatrix.exceptions import ResourceNotFoundError
from MakerMatrix.repositories.parts_repositories import handle_categories

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolService(BaseService):
    """
    Tool service with consolidated session management using BaseService.
    Handles CRUD operations, checkout/return, maintenance tracking, and search.
    """

    def __init__(self, engine_override=None):
        super().__init__(engine_override)
        self.entity_name = "Tool"

    # === CREATE OPERATIONS ===

    def create_tool(self, tool_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """
        Create a new tool with optional location and categories.

        Args:
            tool_data: Dictionary containing tool creation data

        Returns:
            ServiceResponse with created tool data
        """
        try:
            tool_name = tool_data.get("tool_name")
            self.log_operation("create", self.entity_name, tool_name)

            if not tool_name:
                return self.error_response("Tool name is required")

            with self.get_session() as session:
                # Check for duplicate tool name
                existing_tool = session.exec(
                    select(ToolModel).where(ToolModel.tool_name == tool_name)
                ).first()

                if existing_tool:
                    return self.error_response(f"Tool with name '{tool_name}' already exists")

                # Handle categories
                category_ids = tool_data.pop("category_ids", [])
                categories = []
                if category_ids:
                    categories = session.exec(
                        select(CategoryModel).where(CategoryModel.id.in_(category_ids))
                    ).all()
                    self.logger.info(f"Assigned {len(categories)} categories to tool '{tool_name}'")

                # Extract allocation data
                location_id = tool_data.pop("location_id", None)
                quantity = tool_data.pop("quantity", 1)

                # Create the tool
                new_tool = ToolModel(**tool_data)
                new_tool.categories = list(categories)

                session.add(new_tool)
                session.flush()  # Get the tool ID

                # Create initial allocation if location provided
                if location_id:
                    allocation = ToolLocationAllocation(
                        tool_id=new_tool.id,
                        location_id=location_id,
                        quantity_at_location=quantity,
                        is_primary_storage=True,
                        notes="Initial allocation from tool creation"
                    )
                    session.add(allocation)

                session.commit()
                session.refresh(new_tool)

                self.logger.info(f"Successfully created tool: {tool_name} (ID: {new_tool.id})")
                return self.success_response("Tool created successfully", new_tool.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    # === READ OPERATIONS ===

    def get_tool_by_id(self, tool_id: str) -> ServiceResponse[Dict[str, Any]]:
        """Get a tool by its ID"""
        try:
            self.log_operation("get", self.entity_name, tool_id)

            with self.get_session() as session:
                tool = session.get(ToolModel, tool_id)

                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                return self.success_response(f"{self.entity_name} retrieved successfully", tool.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by ID")

    def get_tool_by_name(self, tool_name: str) -> ServiceResponse[Dict[str, Any]]:
        """Get a tool by its name"""
        try:
            self.log_operation("get", self.entity_name, tool_name)

            with self.get_session() as session:
                tool = session.exec(
                    select(ToolModel).where(ToolModel.tool_name == tool_name)
                ).first()

                if not tool:
                    return self.error_response(f"{self.entity_name} with name '{tool_name}' not found")

                return self.success_response(f"{self.entity_name} retrieved successfully", tool.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by name")

    def get_all_tools(self, page: int = 1, page_size: int = 20) -> ServiceResponse[Dict[str, Any]]:
        """Get all tools with pagination"""
        try:
            self.log_operation("get_all", self.entity_name)

            with self.get_session() as session:
                # Get total count
                total = session.exec(select(func.count()).select_from(ToolModel)).one()

                # Get paginated results
                offset = (page - 1) * page_size
                tools = session.exec(
                    select(ToolModel).offset(offset).limit(page_size)
                ).all()

                tools_data = {
                    "tools": [tool.to_dict() for tool in tools],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }

                return self.success_response(f"Retrieved {len(tools)} tools", tools_data)

        except Exception as e:
            return self.handle_exception(e, f"get all {self.entity_name}s")

    def search_tools(self, search_params: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """
        Advanced tool search with multiple filters.

        Supported filters:
        - search_term: General text search
        - manufacturer: Filter by manufacturer
        - tool_type: Filter by tool type
        - condition: Filter by condition
        - is_checked_out: Filter by checkout status
        - is_available: Filter available tools
        - needs_maintenance: Filter tools needing maintenance
        - category_ids: Filter by categories
        - location_id: Filter by location
        - sort_by, sort_order, page, page_size
        """
        try:
            self.log_operation("search", self.entity_name)

            with self.get_session() as session:
                # Build query
                query = select(ToolModel)

                # Text search
                search_term = search_params.get("search_term")
                if search_term:
                    query = query.where(
                        or_(
                            ToolModel.tool_name.ilike(f"%{search_term}%"),
                            ToolModel.description.ilike(f"%{search_term}%"),
                            ToolModel.manufacturer.ilike(f"%{search_term}%"),
                            ToolModel.model_number.ilike(f"%{search_term}%")
                        )
                    )

                # Filter by manufacturer
                if search_params.get("manufacturer"):
                    query = query.where(ToolModel.manufacturer == search_params["manufacturer"])

                # Filter by tool type
                if search_params.get("tool_type"):
                    query = query.where(ToolModel.tool_type == search_params["tool_type"])

                # Filter by condition
                if search_params.get("condition"):
                    query = query.where(ToolModel.condition == search_params["condition"])

                # Filter by checkout status
                if search_params.get("is_checked_out") is not None:
                    query = query.where(ToolModel.is_checked_out == search_params["is_checked_out"])

                # Filter available tools
                if search_params.get("is_available"):
                    query = query.where(
                        ToolModel.is_checked_out == False,
                        ToolModel.condition.not_in(['needs_repair', 'out_of_service'])
                    )

                # Filter tools needing maintenance
                if search_params.get("needs_maintenance"):
                    query = query.where(
                        ToolModel.next_maintenance_date <= datetime.utcnow()
                    )

                # Get total count before pagination
                count_query = select(func.count()).select_from(query.subquery())
                total = session.exec(count_query).one()

                # Apply sorting
                sort_by = search_params.get("sort_by", "tool_name")
                sort_order = search_params.get("sort_order", "asc")
                sort_column = getattr(ToolModel, sort_by, ToolModel.tool_name)

                if sort_order == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

                # Apply pagination
                page = search_params.get("page", 1)
                page_size = search_params.get("page_size", 20)
                offset = (page - 1) * page_size
                query = query.offset(offset).limit(page_size)

                # Execute query
                tools = session.exec(query).all()

                result_data = {
                    "tools": [tool.to_dict() for tool in tools],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }

                return self.success_response(f"Found {total} tools", result_data)

        except Exception as e:
            return self.handle_exception(e, f"search {self.entity_name}s")

    # === UPDATE OPERATIONS ===

    def update_tool(self, tool_id: str, tool_update: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """Update a tool with provided data"""
        try:
            self.log_operation("update", self.entity_name, tool_id)

            with self.get_session() as session:
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                # Handle category updates
                category_ids = tool_update.pop("category_ids", None)
                if category_ids is not None:
                    categories = session.exec(
                        select(CategoryModel).where(CategoryModel.id.in_(category_ids))
                    ).all()
                    tool.categories = list(categories)

                # Update other fields
                for key, value in tool_update.items():
                    if hasattr(tool, key) and value is not None:
                        setattr(tool, key, value)

                tool.updated_at = datetime.utcnow()
                session.add(tool)
                session.commit()
                session.refresh(tool)

                self.logger.info(f"Successfully updated tool '{tool.tool_name}' (ID: {tool_id})")
                return self.success_response("Tool updated successfully", tool.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")

    # === DELETE OPERATIONS ===

    def delete_tool(self, tool_id: str) -> ServiceResponse[Dict[str, Any]]:
        """Delete a tool by ID"""
        try:
            self.log_operation("delete", self.entity_name, tool_id)

            with self.get_session() as session:
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                tool_name = tool.tool_name
                session.delete(tool)
                session.commit()

                self.logger.info(f"Deleted tool '{tool_name}' (ID: {tool_id})")
                return self.success_response(f"Tool '{tool_name}' deleted successfully", {"id": tool_id})

        except Exception as e:
            return self.handle_exception(e, f"delete {self.entity_name}")

    # === CHECKOUT/RETURN OPERATIONS ===

    def checkout_tool(self, tool_id: str, checkout_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """Check out a tool to a user"""
        try:
            self.log_operation("checkout", self.entity_name, tool_id)

            with self.get_session() as session:
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                if tool.is_checked_out:
                    return self.error_response(
                        f"Tool '{tool.tool_name}' is already checked out to {tool.checked_out_by}"
                    )

                if not tool.is_available():
                    return self.error_response(
                        f"Tool '{tool.tool_name}' is not available (condition: {tool.condition})"
                    )

                tool.is_checked_out = True
                tool.checked_out_by = checkout_data["user_id"]
                tool.checked_out_at = datetime.utcnow()
                tool.expected_return_date = checkout_data.get("expected_return_date")

                session.add(tool)
                session.commit()
                session.refresh(tool)

                self.logger.info(f"Checked out tool '{tool.tool_name}' to user {tool.checked_out_by}")
                return self.success_response(f"Tool '{tool.tool_name}' checked out successfully", tool.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"checkout {self.entity_name}")

    def return_tool(self, tool_id: str, return_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """Return a checked-out tool"""
        try:
            self.log_operation("return", self.entity_name, tool_id)

            with self.get_session() as session:
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                if not tool.is_checked_out:
                    return self.error_response(f"Tool '{tool.tool_name}' is not checked out")

                # Update condition if provided
                if return_data.get("condition"):
                    tool.condition = return_data["condition"]

                tool.is_checked_out = False
                tool.checked_out_by = None
                tool.checked_out_at = None
                tool.expected_return_date = None

                session.add(tool)
                session.commit()
                session.refresh(tool)

                self.logger.info(f"Returned tool '{tool.tool_name}' (ID: {tool_id})")
                return self.success_response(f"Tool '{tool.tool_name}' returned successfully", tool.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"return {self.entity_name}")

    # === MAINTENANCE OPERATIONS ===

    def record_maintenance(self, tool_id: str, maintenance_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """
        Legacy method: Record maintenance on tool directly.
        Consider using create_maintenance_record instead for better tracking.
        """
        try:
            self.log_operation("maintenance", self.entity_name, tool_id)

            with self.get_session() as session:
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                tool.last_maintenance_date = maintenance_data.get("maintenance_date", datetime.utcnow())
                tool.next_maintenance_date = maintenance_data.get("next_maintenance_date")

                # Append to maintenance notes
                new_note = f"\n[{datetime.utcnow().isoformat()}] {maintenance_data.get('maintenance_type', 'maintenance')}: {maintenance_data.get('notes', '')}"
                tool.maintenance_notes = (tool.maintenance_notes or "") + new_note

                session.add(tool)
                session.commit()
                session.refresh(tool)

                self.logger.info(f"Recorded maintenance for tool '{tool.tool_name}' (ID: {tool_id})")
                return self.success_response("Maintenance recorded successfully", tool.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"record maintenance for {self.entity_name}")

    def create_maintenance_record(self, tool_id: str, maintenance_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """Create a new maintenance record for a tool"""
        try:
            self.log_operation("create_maintenance_record", self.entity_name, tool_id)

            with self.get_session() as session:
                # Verify tool exists
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                # Create maintenance record
                record = ToolMaintenanceRecord(
                    tool_id=tool_id,
                    **maintenance_data
                )

                session.add(record)

                # Update tool's maintenance dates if provided
                if maintenance_data.get("maintenance_date"):
                    tool.last_maintenance_date = maintenance_data["maintenance_date"]
                if maintenance_data.get("next_maintenance_date"):
                    tool.next_maintenance_date = maintenance_data["next_maintenance_date"]

                session.commit()
                session.refresh(record)

                self.logger.info(f"Created maintenance record for tool '{tool.tool_name}' (ID: {tool_id})")
                return self.success_response("Maintenance record created successfully", record.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"create maintenance record for {self.entity_name}")

    def get_maintenance_records(self, tool_id: str) -> ServiceResponse[List[Dict[str, Any]]]:
        """Get all maintenance records for a tool"""
        try:
            self.log_operation("get_maintenance_records", self.entity_name, tool_id)

            with self.get_session() as session:
                # Verify tool exists
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                # Get all maintenance records for this tool
                records = session.exec(
                    select(ToolMaintenanceRecord)
                    .where(ToolMaintenanceRecord.tool_id == tool_id)
                    .order_by(ToolMaintenanceRecord.maintenance_date.desc())
                ).all()

                records_data = [record.to_dict() for record in records]

                self.logger.info(f"Retrieved {len(records)} maintenance records for tool ID: {tool_id}")
                return self.success_response(f"Found {len(records)} maintenance records", records_data)

        except Exception as e:
            return self.handle_exception(e, f"get maintenance records for {self.entity_name}")

    def update_maintenance_record(self, tool_id: str, record_id: str, update_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """Update an existing maintenance record"""
        try:
            self.log_operation("update_maintenance_record", self.entity_name, f"{tool_id}/{record_id}")

            with self.get_session() as session:
                # Verify tool exists
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                # Get the maintenance record
                record = session.get(ToolMaintenanceRecord, record_id)
                if not record:
                    return self.error_response(f"Maintenance record with ID '{record_id}' not found")

                # Verify record belongs to this tool
                if record.tool_id != tool_id:
                    return self.error_response(f"Maintenance record '{record_id}' does not belong to tool '{tool_id}'")

                # Update record fields
                for key, value in update_data.items():
                    if hasattr(record, key) and value is not None:
                        setattr(record, key, value)

                session.add(record)
                session.commit()
                session.refresh(record)

                self.logger.info(f"Updated maintenance record {record_id} for tool ID: {tool_id}")
                return self.success_response("Maintenance record updated successfully", record.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"update maintenance record for {self.entity_name}")

    def delete_maintenance_record(self, tool_id: str, record_id: str) -> ServiceResponse[Dict[str, str]]:
        """Delete a maintenance record"""
        try:
            self.log_operation("delete_maintenance_record", self.entity_name, f"{tool_id}/{record_id}")

            with self.get_session() as session:
                # Verify tool exists
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"{self.entity_name} with ID '{tool_id}' not found")

                # Get the maintenance record
                record = session.get(ToolMaintenanceRecord, record_id)
                if not record:
                    return self.error_response(f"Maintenance record with ID '{record_id}' not found")

                # Verify record belongs to this tool
                if record.tool_id != tool_id:
                    return self.error_response(f"Maintenance record '{record_id}' does not belong to tool '{tool_id}'")

                session.delete(record)
                session.commit()

                self.logger.info(f"Deleted maintenance record {record_id} for tool ID: {tool_id}")
                return self.success_response("Maintenance record deleted successfully", {"id": record_id})

        except Exception as e:
            return self.handle_exception(e, f"delete maintenance record for {self.entity_name}")

    # === STATISTICS ===

    def get_tool_statistics(self) -> ServiceResponse[Dict[str, Any]]:
        """Get tool statistics and summary"""
        try:
            self.log_operation("get_statistics", self.entity_name)

            with self.get_session() as session:
                total_tools = session.exec(select(func.count()).select_from(ToolModel)).one()

                # Get tools by type
                tools_by_type = {}
                type_results = session.exec(
                    select(ToolModel.tool_type, func.count()).group_by(ToolModel.tool_type)
                ).all()
                for tool_type, count in type_results:
                    tools_by_type[tool_type or "Unknown"] = count

                # Get tools by condition
                tools_by_condition = {}
                condition_results = session.exec(
                    select(ToolModel.condition, func.count()).group_by(ToolModel.condition)
                ).all()
                for condition, count in condition_results:
                    tools_by_condition[condition] = count

                # Get checkout stats
                checked_out_count = session.exec(
                    select(func.count()).select_from(ToolModel).where(ToolModel.is_checked_out == True)
                ).one()

                available_count = session.exec(
                    select(func.count()).select_from(ToolModel).where(
                        ToolModel.is_checked_out == False,
                        ToolModel.condition.not_in(['needs_repair', 'out_of_service'])
                    )
                ).one()

                # Get maintenance needs
                needs_maintenance_count = session.exec(
                    select(func.count()).select_from(ToolModel).where(
                        ToolModel.next_maintenance_date <= datetime.utcnow()
                    )
                ).one()

                # Calculate total value
                total_value_result = session.exec(
                    select(func.sum(ToolModel.purchase_price))
                ).one()
                total_value = float(total_value_result or 0)

                stats = {
                    "total_tools": total_tools,
                    "total_by_type": tools_by_type,
                    "total_by_condition": tools_by_condition,
                    "checked_out_count": checked_out_count,
                    "available_count": available_count,
                    "needs_maintenance_count": needs_maintenance_count,
                    "total_value": total_value,
                }

                return self.success_response("Tool statistics retrieved successfully", stats)

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} statistics")
