"""
Tag Service Module

Provides business logic for tag management operations.
Handles CRUD operations, tag assignment to parts/tools, and tag-based filtering.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select, func
from sqlalchemy import or_, and_, desc, asc

from MakerMatrix.models.tag_models import TagModel, PartTagLink, ToolTagLink
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.tool_models import ToolModel
from MakerMatrix.services.base_service import BaseService, ServiceResponse
from MakerMatrix.schemas.tag_schemas import (
    TagCreate,
    TagUpdate,
    TagFilter,
    TagBulkOperation,
    TagMergeRequest,
    TagCleanupRequest,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TagService(BaseService):
    """
    Tag service with consolidated session management using BaseService.
    Handles CRUD operations, tag assignment, and tag-based search.
    """

    def __init__(self, engine_override=None):
        super().__init__(engine_override)
        self.entity_name = "Tag"

    # === CREATE OPERATIONS ===

    def create_tag(self, tag_data: TagCreate, created_by: Optional[str] = None) -> ServiceResponse[Dict[str, Any]]:
        """
        Create a new tag.

        Args:
            tag_data: TagCreate schema with tag information
            created_by: Optional username of user creating the tag

        Returns:
            ServiceResponse with created tag data
        """
        try:
            tag_name = tag_data.name
            self.log_operation("create", self.entity_name, tag_name)

            if not tag_name:
                return self.error_response("Tag name is required")

            with self.get_session() as session:
                # Check for duplicate tag name (case-insensitive)
                existing_tag = session.exec(select(TagModel).where(TagModel.name_lower == tag_name.lower())).first()

                if existing_tag:
                    return self.error_response(f"Tag '{tag_name}' already exists")

                # Create the tag
                new_tag = TagModel(
                    name=tag_name,
                    name_lower=tag_name.lower(),
                    color=tag_data.color,
                    description=tag_data.description,
                    icon=tag_data.icon,
                    is_system=tag_data.is_system,
                    created_by=created_by if not tag_data.is_system else None,
                )

                session.add(new_tag)
                session.commit()
                session.refresh(new_tag)

                self.logger.info(f"Successfully created tag: {tag_name} (ID: {new_tag.id})")
                return self.success_response("Tag created successfully", new_tag.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    # === READ OPERATIONS ===

    def get_tag_by_id(self, tag_id: str, include_items: bool = False) -> ServiceResponse[Dict[str, Any]]:
        """
        Get a tag by its ID.

        Args:
            tag_id: Tag ID
            include_items: Include tagged parts and tools

        Returns:
            ServiceResponse with tag data
        """
        try:
            self.log_operation("get", self.entity_name, tag_id)

            with self.get_session() as session:
                tag = session.get(TagModel, tag_id)

                if not tag:
                    return self.error_response(f"{self.entity_name} with ID '{tag_id}' not found")

                return self.success_response(
                    f"{self.entity_name} retrieved successfully", tag.to_dict(include_items=include_items)
                )

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by ID")

    def get_tag_by_name(self, tag_name: str, include_items: bool = False) -> ServiceResponse[Dict[str, Any]]:
        """
        Get a tag by its name (case-insensitive).

        Args:
            tag_name: Tag name (with or without #)
            include_items: Include tagged parts and tools

        Returns:
            ServiceResponse with tag data
        """
        try:
            # Normalize tag name
            if tag_name.startswith("#"):
                tag_name = tag_name[1:]

            self.log_operation("get", self.entity_name, tag_name)

            with self.get_session() as session:
                tag = session.exec(select(TagModel).where(TagModel.name_lower == tag_name.lower())).first()

                if not tag:
                    return self.error_response(f"{self.entity_name} with name '{tag_name}' not found")

                return self.success_response(
                    f"{self.entity_name} retrieved successfully", tag.to_dict(include_items=include_items)
                )

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by name")

    def get_all_tags(self, filter_params: Optional[TagFilter] = None) -> ServiceResponse[Dict[str, Any]]:
        """
        Get all tags with optional filtering and pagination.

        Args:
            filter_params: TagFilter schema with filtering options

        Returns:
            ServiceResponse with paginated tag list
        """
        try:
            self.log_operation("get_all", self.entity_name)

            if not filter_params:
                filter_params = TagFilter()

            with self.get_session() as session:
                # Build query
                query = select(TagModel)

                # Apply filters
                if filter_params.search:
                    search_term = filter_params.search.lower()
                    query = query.where(
                        or_(
                            TagModel.name_lower.ilike(f"%{search_term}%"),
                            TagModel.description.ilike(f"%{search_term}%"),
                        )
                    )

                if filter_params.is_active is not None:
                    query = query.where(TagModel.is_active == filter_params.is_active)

                if filter_params.is_system is not None:
                    query = query.where(TagModel.is_system == filter_params.is_system)

                if filter_params.min_usage is not None:
                    query = query.where(TagModel.usage_count >= filter_params.min_usage)

                if filter_params.max_usage is not None:
                    query = query.where(TagModel.usage_count <= filter_params.max_usage)

                if filter_params.has_color is not None:
                    if filter_params.has_color:
                        query = query.where(TagModel.color.is_not(None))
                    else:
                        query = query.where(TagModel.color.is_(None))

                if filter_params.created_after:
                    query = query.where(TagModel.created_at >= filter_params.created_after)

                if filter_params.created_before:
                    query = query.where(TagModel.created_at <= filter_params.created_before)

                # Get total count
                total = session.exec(select(func.count()).select_from(query.subquery())).one()

                # Apply sorting
                sort_column = getattr(TagModel, filter_params.sort_by, TagModel.name)
                if filter_params.sort_order == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))

                # Apply pagination
                offset = (filter_params.page - 1) * filter_params.page_size
                query = query.offset(offset).limit(filter_params.page_size)

                # Execute query
                tags = session.exec(query).all()

                tags_data = {
                    "tags": [tag.to_dict() for tag in tags],
                    "total": total,
                    "page": filter_params.page,
                    "page_size": filter_params.page_size,
                    "total_pages": (total + filter_params.page_size - 1) // filter_params.page_size,
                }

                return self.success_response(f"Retrieved {len(tags)} tags", tags_data)

        except Exception as e:
            return self.handle_exception(e, f"get all {self.entity_name}s")

    # === UPDATE OPERATIONS ===

    def update_tag(self, tag_id: str, tag_update: TagUpdate) -> ServiceResponse[Dict[str, Any]]:
        """
        Update a tag with provided data.

        Args:
            tag_id: Tag ID
            tag_update: TagUpdate schema with fields to update

        Returns:
            ServiceResponse with updated tag data
        """
        try:
            self.log_operation("update", self.entity_name, tag_id)

            with self.get_session() as session:
                tag = session.get(TagModel, tag_id)
                if not tag:
                    return self.error_response(f"{self.entity_name} with ID '{tag_id}' not found")

                # Check if renaming to existing tag
                if tag_update.name and tag_update.name.lower() != tag.name_lower:
                    existing = session.exec(
                        select(TagModel).where(TagModel.name_lower == tag_update.name.lower(), TagModel.id != tag_id)
                    ).first()
                    if existing:
                        return self.error_response(f"Tag '{tag_update.name}' already exists")

                # Update fields
                update_data = tag_update.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    if value is not None:
                        if key == "name":
                            tag.name = value
                            tag.name_lower = value.lower()
                        else:
                            setattr(tag, key, value)

                tag.updated_at = datetime.utcnow()
                session.add(tag)
                session.commit()
                session.refresh(tag)

                self.logger.info(f"Successfully updated tag '{tag.name}' (ID: {tag_id})")
                return self.success_response("Tag updated successfully", tag.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")

    # === DELETE OPERATIONS ===

    def delete_tag(self, tag_id: str) -> ServiceResponse[Dict[str, Any]]:
        """
        Delete a tag by ID.
        This will remove all associations but NOT delete parts/tools.

        Args:
            tag_id: Tag ID

        Returns:
            ServiceResponse with deletion confirmation
        """
        try:
            self.log_operation("delete", self.entity_name, tag_id)

            with self.get_session() as session:
                tag = session.get(TagModel, tag_id)
                if not tag:
                    return self.error_response(f"{self.entity_name} with ID '{tag_id}' not found")

                if tag.is_system:
                    return self.error_response(f"Cannot delete system tag '{tag.name}'")

                tag_name = tag.name
                session.delete(tag)
                session.commit()

                self.logger.info(f"Deleted tag '{tag_name}' (ID: {tag_id})")
                return self.success_response(f"Tag '{tag_name}' deleted successfully", {"id": tag_id})

        except Exception as e:
            return self.handle_exception(e, f"delete {self.entity_name}")

    # === TAG ASSIGNMENT OPERATIONS ===

    def assign_tag_to_part(
        self, tag_id: str, part_id: str, user_id: Optional[str] = None
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Assign a tag to a part.

        Args:
            tag_id: Tag ID
            part_id: Part ID
            user_id: User performing the assignment

        Returns:
            ServiceResponse with assignment confirmation
        """
        try:
            self.log_operation("assign_to_part", self.entity_name, f"{tag_id} -> {part_id}")

            with self.get_session() as session:
                # Verify tag exists
                tag = session.get(TagModel, tag_id)
                if not tag:
                    return self.error_response(f"Tag with ID '{tag_id}' not found")

                # Verify part exists
                part = session.get(PartModel, part_id)
                if not part:
                    return self.error_response(f"Part with ID '{part_id}' not found")

                # Check if already assigned
                existing_link = session.exec(
                    select(PartTagLink).where(and_(PartTagLink.tag_id == tag_id, PartTagLink.part_id == part_id))
                ).first()

                if existing_link:
                    return self.success_response(f"Tag '{tag.name}' is already assigned to this part", {})

                # Create the link
                link = PartTagLink(part_id=part_id, tag_id=tag_id, added_by=user_id)
                session.add(link)

                # Update tag statistics
                tag.parts_count += 1
                tag.usage_count += 1
                tag.last_used_at = datetime.utcnow()

                session.commit()

                self.logger.info(f"Assigned tag '{tag.name}' to part '{part.part_name}'")
                return self.success_response(
                    f"Tag '{tag.name}' assigned to part successfully", {"tag_id": tag_id, "part_id": part_id}
                )

        except Exception as e:
            return self.handle_exception(e, "assign tag to part")

    def remove_tag_from_part(self, tag_id: str, part_id: str) -> ServiceResponse[Dict[str, Any]]:
        """
        Remove a tag from a part.

        Args:
            tag_id: Tag ID
            part_id: Part ID

        Returns:
            ServiceResponse with removal confirmation
        """
        try:
            self.log_operation("remove_from_part", self.entity_name, f"{tag_id} <- {part_id}")

            with self.get_session() as session:
                # Find the link
                link = session.exec(
                    select(PartTagLink).where(and_(PartTagLink.tag_id == tag_id, PartTagLink.part_id == part_id))
                ).first()

                if not link:
                    return self.error_response("Tag is not assigned to this part")

                # Get tag for statistics update
                tag = session.get(TagModel, tag_id)
                if tag:
                    tag.parts_count = max(0, tag.parts_count - 1)
                    tag.usage_count = max(0, tag.usage_count - 1)

                session.delete(link)
                session.commit()

                self.logger.info(f"Removed tag ID {tag_id} from part ID {part_id}")
                return self.success_response("Tag removed from part successfully", {})

        except Exception as e:
            return self.handle_exception(e, "remove tag from part")

    def assign_tag_to_tool(
        self, tag_id: str, tool_id: str, user_id: Optional[str] = None
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Assign a tag to a tool.

        Args:
            tag_id: Tag ID
            tool_id: Tool ID
            user_id: User performing the assignment

        Returns:
            ServiceResponse with assignment confirmation
        """
        try:
            self.log_operation("assign_to_tool", self.entity_name, f"{tag_id} -> {tool_id}")

            with self.get_session() as session:
                # Verify tag exists
                tag = session.get(TagModel, tag_id)
                if not tag:
                    return self.error_response(f"Tag with ID '{tag_id}' not found")

                # Verify tool exists
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"Tool with ID '{tool_id}' not found")

                # Check if already assigned
                existing_link = session.exec(
                    select(ToolTagLink).where(and_(ToolTagLink.tag_id == tag_id, ToolTagLink.tool_id == tool_id))
                ).first()

                if existing_link:
                    return self.success_response(f"Tag '{tag.name}' is already assigned to this tool", {})

                # Create the link
                link = ToolTagLink(tool_id=tool_id, tag_id=tag_id, added_by=user_id)
                session.add(link)

                # Update tag statistics
                tag.tools_count += 1
                tag.usage_count += 1
                tag.last_used_at = datetime.utcnow()

                session.commit()

                self.logger.info(f"Assigned tag '{tag.name}' to tool '{tool.tool_name}'")
                return self.success_response(
                    f"Tag '{tag.name}' assigned to tool successfully", {"tag_id": tag_id, "tool_id": tool_id}
                )

        except Exception as e:
            return self.handle_exception(e, "assign tag to tool")

    def remove_tag_from_tool(self, tag_id: str, tool_id: str) -> ServiceResponse[Dict[str, Any]]:
        """
        Remove a tag from a tool.

        Args:
            tag_id: Tag ID
            tool_id: Tool ID

        Returns:
            ServiceResponse with removal confirmation
        """
        try:
            self.log_operation("remove_from_tool", self.entity_name, f"{tag_id} <- {tool_id}")

            with self.get_session() as session:
                # Find the link
                link = session.exec(
                    select(ToolTagLink).where(and_(ToolTagLink.tag_id == tag_id, ToolTagLink.tool_id == tool_id))
                ).first()

                if not link:
                    return self.error_response("Tag is not assigned to this tool")

                # Get tag for statistics update
                tag = session.get(TagModel, tag_id)
                if tag:
                    tag.tools_count = max(0, tag.tools_count - 1)
                    tag.usage_count = max(0, tag.usage_count - 1)

                session.delete(link)
                session.commit()

                self.logger.info(f"Removed tag ID {tag_id} from tool ID {tool_id}")
                return self.success_response("Tag removed from tool successfully", {})

        except Exception as e:
            return self.handle_exception(e, "remove tag from tool")

    # === TAG QUERY OPERATIONS ===

    def get_tags_for_part(self, part_id: str) -> ServiceResponse[List[Dict[str, Any]]]:
        """
        Get all tags assigned to a part.

        Args:
            part_id: Part ID

        Returns:
            ServiceResponse with list of tags
        """
        try:
            self.log_operation("get_tags_for_part", self.entity_name, part_id)

            with self.get_session() as session:
                # Verify part exists
                part = session.get(PartModel, part_id)
                if not part:
                    return self.error_response(f"Part with ID '{part_id}' not found")

                tags = part.tags if hasattr(part, "tags") else []
                tags_data = [tag.to_dict() for tag in tags]

                self.logger.info(f"Retrieved {len(tags_data)} tags for part ID {part_id}")
                return self.success_response(f"Found {len(tags_data)} tags", tags_data)

        except Exception as e:
            return self.handle_exception(e, "get tags for part")

    def get_tags_for_tool(self, tool_id: str) -> ServiceResponse[List[Dict[str, Any]]]:
        """
        Get all tags assigned to a tool.

        Args:
            tool_id: Tool ID

        Returns:
            ServiceResponse with list of tags
        """
        try:
            self.log_operation("get_tags_for_tool", self.entity_name, tool_id)

            with self.get_session() as session:
                # Verify tool exists
                tool = session.get(ToolModel, tool_id)
                if not tool:
                    return self.error_response(f"Tool with ID '{tool_id}' not found")

                tags = tool.tags if hasattr(tool, "tags") else []
                tags_data = [tag.to_dict() for tag in tags]

                self.logger.info(f"Retrieved {len(tags_data)} tags for tool ID {tool_id}")
                return self.success_response(f"Found {len(tags_data)} tags", tags_data)

        except Exception as e:
            return self.handle_exception(e, "get tags for tool")

    def get_parts_by_tag(self, tag_id: str, page: int = 1, page_size: int = 20) -> ServiceResponse[Dict[str, Any]]:
        """
        Get all parts with a specific tag.

        Args:
            tag_id: Tag ID
            page: Page number
            page_size: Items per page

        Returns:
            ServiceResponse with paginated part list
        """
        try:
            self.log_operation("get_parts_by_tag", self.entity_name, tag_id)

            with self.get_session() as session:
                # Verify tag exists
                tag = session.get(TagModel, tag_id)
                if not tag:
                    return self.error_response(f"Tag with ID '{tag_id}' not found")

                # Get total count
                total = len(tag.parts) if hasattr(tag, "parts") else 0

                # Get paginated parts
                offset = (page - 1) * page_size
                parts = tag.parts[offset : offset + page_size] if hasattr(tag, "parts") else []

                parts_data = {
                    "parts": [part.to_dict() for part in parts],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
                    "tag": tag.to_dict(),
                }

                self.logger.info(f"Retrieved {len(parts)} parts with tag '{tag.name}'")
                return self.success_response(f"Found {total} parts with tag", parts_data)

        except Exception as e:
            return self.handle_exception(e, "get parts by tag")

    def get_tools_by_tag(self, tag_id: str, page: int = 1, page_size: int = 20) -> ServiceResponse[Dict[str, Any]]:
        """
        Get all tools with a specific tag.

        Args:
            tag_id: Tag ID
            page: Page number
            page_size: Items per page

        Returns:
            ServiceResponse with paginated tool list
        """
        try:
            self.log_operation("get_tools_by_tag", self.entity_name, tag_id)

            with self.get_session() as session:
                # Verify tag exists
                tag = session.get(TagModel, tag_id)
                if not tag:
                    return self.error_response(f"Tag with ID '{tag_id}' not found")

                # Get total count
                total = len(tag.tools) if hasattr(tag, "tools") else 0

                # Get paginated tools
                offset = (page - 1) * page_size
                tools = tag.tools[offset : offset + page_size] if hasattr(tag, "tools") else []

                tools_data = {
                    "tools": [tool.to_dict() for tool in tools],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
                    "tag": tag.to_dict(),
                }

                self.logger.info(f"Retrieved {len(tools)} tools with tag '{tag.name}'")
                return self.success_response(f"Found {total} tools with tag", tools_data)

        except Exception as e:
            return self.handle_exception(e, "get tools by tag")

    # === BULK OPERATIONS ===

    def bulk_tag_operation(self, operation_data: TagBulkOperation) -> ServiceResponse[Dict[str, Any]]:
        """
        Perform bulk tag operations on multiple items.

        Args:
            operation_data: TagBulkOperation schema with operation details

        Returns:
            ServiceResponse with operation results
        """
        try:
            self.log_operation("bulk_operation", self.entity_name, operation_data.operation)

            with self.get_session() as session:
                results = {"successful": [], "failed": [], "skipped": []}

                # Verify all tags exist
                tags = session.exec(select(TagModel).where(TagModel.id.in_(operation_data.tag_ids))).all()

                if len(tags) != len(operation_data.tag_ids):
                    return self.error_response("One or more tags not found")

                # Process each item
                for item_id in operation_data.item_ids:
                    for tag in tags:
                        try:
                            if operation_data.item_type == "part":
                                if operation_data.operation == "add":
                                    result = self.assign_tag_to_part(tag.id, item_id)
                                else:
                                    result = self.remove_tag_from_part(tag.id, item_id)
                            else:  # tool
                                if operation_data.operation == "add":
                                    result = self.assign_tag_to_tool(tag.id, item_id)
                                else:
                                    result = self.remove_tag_from_tool(tag.id, item_id)

                            if result.success:
                                results["successful"].append({"item_id": item_id, "tag_id": tag.id})
                            else:
                                results["failed"].append(
                                    {"item_id": item_id, "tag_id": tag.id, "error": result.message}
                                )

                        except Exception as e:
                            results["failed"].append({"item_id": item_id, "tag_id": tag.id, "error": str(e)})

                summary = f"Bulk {operation_data.operation} completed: {len(results['successful'])} successful, {len(results['failed'])} failed"
                self.logger.info(summary)

                return self.success_response(summary, results)

        except Exception as e:
            return self.handle_exception(e, "bulk tag operation")

    # === TAG MANAGEMENT OPERATIONS ===

    def merge_tags(self, merge_request: TagMergeRequest) -> ServiceResponse[Dict[str, Any]]:
        """
        Merge multiple tags into one target tag.

        Args:
            merge_request: TagMergeRequest with source and target tags

        Returns:
            ServiceResponse with merge results
        """
        try:
            self.log_operation(
                "merge", self.entity_name, f"{len(merge_request.source_tag_ids)} -> {merge_request.target_tag_id}"
            )

            with self.get_session() as session:
                # Get target tag
                target_tag = session.get(TagModel, merge_request.target_tag_id)
                if not target_tag:
                    return self.error_response("Target tag not found")

                # Get source tags
                source_tags = session.exec(select(TagModel).where(TagModel.id.in_(merge_request.source_tag_ids))).all()

                if len(source_tags) != len(merge_request.source_tag_ids):
                    return self.error_response("One or more source tags not found")

                merged_parts = 0
                merged_tools = 0

                for source_tag in source_tags:
                    # Merge part associations
                    for part in source_tag.parts:
                        if part not in target_tag.parts:
                            target_tag.parts.append(part)
                            merged_parts += 1

                    # Merge tool associations
                    for tool in source_tag.tools:
                        if tool not in target_tag.tools:
                            target_tag.tools.append(tool)
                            merged_tools += 1

                    # Delete source tag if requested
                    if merge_request.delete_sources:
                        session.delete(source_tag)

                # Update target tag statistics
                target_tag.update_usage_stats(session)
                session.commit()

                result = {
                    "target_tag": target_tag.to_dict(),
                    "merged_parts": merged_parts,
                    "merged_tools": merged_tools,
                    "deleted_tags": len(source_tags) if merge_request.delete_sources else 0,
                }

                self.logger.info(f"Merged {len(source_tags)} tags into '{target_tag.name}'")
                return self.success_response("Tags merged successfully", result)

        except Exception as e:
            return self.handle_exception(e, "merge tags")

    def cleanup_unused_tags(
        self, cleanup_request: Optional[TagCleanupRequest] = None
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Clean up unused or duplicate tags.

        Args:
            cleanup_request: TagCleanupRequest with cleanup options

        Returns:
            ServiceResponse with cleanup results
        """
        try:
            self.log_operation("cleanup", self.entity_name)

            if not cleanup_request:
                cleanup_request = TagCleanupRequest()

            with self.get_session() as session:
                results = {"removed_tags": [], "merged_tags": [], "errors": []}

                if cleanup_request.remove_unused:
                    # Find unused tags
                    unused_tags = session.exec(
                        select(TagModel).where(TagModel.usage_count == 0, TagModel.is_system == False)
                    ).all()

                    for tag in unused_tags:
                        try:
                            session.delete(tag)
                            results["removed_tags"].append(tag.name)
                        except Exception as e:
                            results["errors"].append(f"Failed to remove tag '{tag.name}': {str(e)}")

                # TODO: Implement similar tag merging if needed
                # This would require a string similarity algorithm

                session.commit()

                summary = f"Cleanup completed: {len(results['removed_tags'])} tags removed"
                self.logger.info(summary)

                return self.success_response(summary, results)

        except Exception as e:
            return self.handle_exception(e, "cleanup tags")

    # === STATISTICS ===

    def get_tag_statistics(self) -> ServiceResponse[Dict[str, Any]]:
        """Get tag system statistics and summary"""
        try:
            self.log_operation("get_statistics", self.entity_name)

            with self.get_session() as session:
                # Basic counts
                total_tags = session.exec(select(func.count()).select_from(TagModel)).one()
                active_tags = session.exec(
                    select(func.count()).select_from(TagModel).where(TagModel.is_active == True)
                ).one()
                system_tags = session.exec(
                    select(func.count()).select_from(TagModel).where(TagModel.is_system == True)
                ).one()
                unused_tags = session.exec(
                    select(func.count()).select_from(TagModel).where(TagModel.usage_count == 0)
                ).one()

                # Most used tags
                most_used = session.exec(select(TagModel).order_by(desc(TagModel.usage_count)).limit(10)).all()

                # Recently used tags
                recently_used = session.exec(
                    select(TagModel)
                    .where(TagModel.last_used_at.is_not(None))
                    .order_by(desc(TagModel.last_used_at))
                    .limit(10)
                ).all()

                stats = {
                    "total_tags": total_tags,
                    "active_tags": active_tags,
                    "system_tags": system_tags,
                    "user_tags": total_tags - system_tags,
                    "unused_tags": unused_tags,
                    "most_used_tags": [tag.to_dict() for tag in most_used],
                    "recently_used_tags": [tag.to_dict() for tag in recently_used],
                }

                return self.success_response("Tag statistics retrieved successfully", stats)

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} statistics")
