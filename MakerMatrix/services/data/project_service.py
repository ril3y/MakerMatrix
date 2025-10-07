import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlmodel import Session
from MakerMatrix.models.project_models import ProjectModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.project_repository import ProjectRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.exceptions import ProjectAlreadyExistsError, ProjectNotFoundError, ResourceNotFoundError
from MakerMatrix.services.base_service import BaseService, ServiceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProjectService(BaseService):
    """
    Project service with consolidated session management using BaseService.

    Provides business logic for project management including CRUD operations
    and part-project associations.
    """

    def __init__(self, engine_override=None):
        super().__init__(engine_override)
        self.project_repo = ProjectRepository(self.engine)
        self.entity_name = "Project"

    @staticmethod
    def generate_slug(name: str) -> str:
        """
        Generate a URL-friendly slug from a project name.

        Args:
            name: Project name

        Returns:
            str: URL-friendly slug
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = name.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug

    def add_project(self, project_data: Dict[str, Any]) -> ServiceResponse[dict]:
        """
        Add a new project to the system.

        Args:
            project_data: Project data dictionary

        Returns:
            ServiceResponse[dict]: Service response with created project data
        """
        try:
            # Validate required fields
            self.validate_required_fields(project_data, ["name"])

            # Generate slug if not provided
            if "slug" not in project_data or not project_data.get("slug"):
                project_data["slug"] = self.generate_slug(project_data["name"])

            self.log_operation("create", self.entity_name, project_data["name"])

            with self.get_session() as session:
                new_project = ProjectRepository.create_project(session, project_data)
                if not new_project:
                    return self.error_response(f"Failed to create {self.entity_name}")

                project_dict = new_project.to_dict()

                return self.success_response(
                    f"{self.entity_name} '{project_data['name']}' created successfully",
                    project_dict
                )

        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    def get_project(self, project_id: Optional[str] = None, name: Optional[str] = None, slug: Optional[str] = None) -> ServiceResponse[dict]:
        """
        Get a project by ID, name, or slug.

        Args:
            project_id: Optional project ID
            name: Optional project name
            slug: Optional project slug

        Returns:
            ServiceResponse[dict]: Service response with project data
        """
        try:
            if not any([project_id, name, slug]):
                return self.error_response("Either project_id, name, or slug must be provided")

            identifier = project_id or name or slug
            self.log_operation("get", self.entity_name, identifier)

            with self.get_session() as session:
                project = ProjectRepository.get_project(session, project_id=project_id, name=name, slug=slug)
                if not project:
                    return self.error_response(
                        f"{self.entity_name} not found with identifier: {identifier}"
                    )

                project_dict = project.to_dict()

                return self.success_response(
                    f"{self.entity_name} '{project.name}' retrieved successfully",
                    project_dict
                )

        except Exception as e:
            return self.handle_exception(e, f"retrieve {self.entity_name}")

    def remove_project(self, id: Optional[str] = None, name: Optional[str] = None) -> ServiceResponse[dict]:
        """
        Remove a project by ID or name.

        Args:
            id: Optional project ID
            name: Optional project name

        Returns:
            ServiceResponse[dict]: Service response with removed project data
        """
        try:
            if not id and not name:
                return self.error_response("Either 'id' or 'name' must be provided")

            identifier = id if id else name
            self.log_operation("delete", self.entity_name, identifier)

            with self.get_session() as session:
                rm_project = ProjectRepository.get_project(session, project_id=id, name=name)
                if not rm_project:
                    return self.error_response(
                        f"{self.entity_name} not found with {'ID' if id else 'name'}: {identifier}"
                    )

                result = self.project_repo.remove_project(session, rm_project)
                if not result:
                    return self.error_response(f"Failed to remove {self.entity_name}")

                project_dict = rm_project.to_dict()

                return self.success_response(
                    f"{self.entity_name} '{rm_project.name}' removed successfully",
                    project_dict
                )

        except Exception as e:
            return self.handle_exception(e, f"remove {self.entity_name}")

    @staticmethod
    def delete_all_projects() -> dict:
        """
        Delete all projects from the system.

        Returns:
            dict: A dictionary containing the status, message, and deletion count
        """
        logger.warning("Attempting to delete ALL projects from the system")
        try:
            session = next(get_session())
            count = ProjectRepository.delete_all_projects(session)

            logger.warning(f"Successfully deleted all {count} projects from the system")
            return {
                "status": "success",
                "message": f"All {count} projects removed successfully",
                "data": {"deleted_count": count}
            }
        except Exception as e:
            logger.error(f"Failed to delete all projects: {str(e)}")
            raise ValueError(f"Failed to delete all projects: {str(e)}")

    def get_all_projects(self) -> ServiceResponse[dict]:
        """
        Get all projects from the system.

        Returns:
            ServiceResponse[dict]: Service response with all projects
        """
        try:
            self.log_operation("get_all", self.entity_name)

            with self.get_session() as session:
                projects = ProjectRepository.get_all_projects(session)

                # Convert to list of dictionaries
                projects_list = [project.to_dict() for project in projects]

                return self.success_response(
                    "All projects retrieved successfully",
                    {"projects": projects_list}
                )

        except Exception as e:
            return self.handle_exception(e, f"retrieve all {self.entity_name}")

    def update_project(self, project_id: str, project_update: Dict[str, Any]) -> ServiceResponse[dict]:
        """
        Update a project's fields.

        Args:
            project_id: The ID of the project to update
            project_update: The fields to update

        Returns:
            ServiceResponse[dict]: Service response with updated project data
        """
        try:
            if not project_id:
                return self.error_response("Project ID is required")

            self.log_operation("update", self.entity_name, project_id)

            with self.get_session() as session:
                # Get the current project to show before/after changes
                current_project = ProjectRepository.get_project(session, project_id=project_id)
                if not current_project:
                    return self.error_response(f"{self.entity_name} with ID '{project_id}' not found")

                # Generate new slug if name is being updated
                if "name" in project_update and project_update["name"]:
                    if "slug" not in project_update or not project_update.get("slug"):
                        project_update["slug"] = self.generate_slug(project_update["name"])

                # Convert to dict, excluding None values
                update_dict = {k: v for k, v in project_update.items() if v is not None}

                updated_project = ProjectRepository.update_project(session, project_id, update_dict)
                if not updated_project:
                    return self.error_response(f"Failed to update {self.entity_name}")

                project_dict = updated_project.to_dict()

                return self.success_response(
                    f"{self.entity_name} '{updated_project.name}' updated successfully",
                    project_dict
                )

        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")

    def add_part_to_project(self, part_id: str, project_id: str, notes: Optional[str] = None) -> ServiceResponse[dict]:
        """
        Add a part to a project.

        Args:
            part_id: The ID of the part to add
            project_id: The ID of the project
            notes: Optional notes about this part's use in the project

        Returns:
            ServiceResponse[dict]: Service response indicating success or failure
        """
        try:
            if not part_id or not project_id:
                return self.error_response("Both part_id and project_id are required")

            self.log_operation("add_part", self.entity_name, f"part={part_id}, project={project_id}")

            with self.get_session() as session:
                success = ProjectRepository.associate_part_with_project(session, part_id, project_id, notes)

                if not success:
                    return self.error_response("Failed to add part to project")

                # Get updated project for response
                project = ProjectRepository.get_project(session, project_id=project_id)

                return self.success_response(
                    f"Part added to project '{project.name}' successfully",
                    {
                        "project_id": project_id,
                        "part_id": part_id,
                        "notes": notes,
                        "parts_count": project.parts_count
                    }
                )

        except Exception as e:
            return self.handle_exception(e, "add part to project")

    def remove_part_from_project(self, part_id: str, project_id: str) -> ServiceResponse[dict]:
        """
        Remove a part from a project.

        Args:
            part_id: The ID of the part to remove
            project_id: The ID of the project

        Returns:
            ServiceResponse[dict]: Service response indicating success or failure
        """
        try:
            if not part_id or not project_id:
                return self.error_response("Both part_id and project_id are required")

            self.log_operation("remove_part", self.entity_name, f"part={part_id}, project={project_id}")

            with self.get_session() as session:
                success = ProjectRepository.remove_part_from_project(session, part_id, project_id)

                if not success:
                    return self.error_response("Failed to remove part from project")

                # Get updated project for response
                project = ProjectRepository.get_project(session, project_id=project_id)

                return self.success_response(
                    f"Part removed from project '{project.name}' successfully",
                    {
                        "project_id": project_id,
                        "part_id": part_id,
                        "parts_count": project.parts_count
                    }
                )

        except Exception as e:
            return self.handle_exception(e, "remove part from project")

    def get_parts_for_project(self, project_id: str) -> ServiceResponse[dict]:
        """
        Get all parts associated with a project.

        Args:
            project_id: The ID of the project

        Returns:
            ServiceResponse[dict]: Service response with list of parts
        """
        try:
            if not project_id:
                return self.error_response("Project ID is required")

            self.log_operation("get_parts", self.entity_name, project_id)

            with self.get_session() as session:
                # First verify project exists
                project = ProjectRepository.get_project(session, project_id=project_id)
                if not project:
                    return self.error_response(f"Project with ID '{project_id}' not found")

                parts = ProjectRepository.get_parts_for_project(session, project_id)

                # Convert parts to dict with complete information
                parts_list = [
                    {
                        "id": part.id,
                        "name": part.part_name,  # Frontend expects "name"
                        "part_number": part.part_number,
                        "description": part.description,
                        "quantity": part.total_quantity,  # Use computed property
                        "supplier": part.supplier,
                        "supplier_url": part.supplier_url,
                        "image_url": part.image_url,
                        "manufacturer": part.manufacturer,
                        "manufacturer_part_number": part.manufacturer_part_number,
                        "location": {
                            "id": part.primary_location.id,
                            "name": part.primary_location.name,
                            "description": part.primary_location.description
                        } if part.primary_location else None
                    }
                    for part in parts
                ]

                return self.success_response(
                    f"Retrieved {len(parts)} parts for project '{project.name}'",
                    {
                        "project_id": project_id,
                        "project_name": project.name,
                        "parts": parts_list,
                        "parts_count": len(parts_list)
                    }
                )

        except Exception as e:
            return self.handle_exception(e, "get parts for project")

    def get_projects_for_part(self, part_id: str) -> ServiceResponse[dict]:
        """
        Get all projects associated with a part.

        Args:
            part_id: The ID of the part

        Returns:
            ServiceResponse[dict]: Service response with list of projects
        """
        try:
            if not part_id:
                return self.error_response("Part ID is required")

            self.log_operation("get_projects", "Part", part_id)

            with self.get_session() as session:
                projects = ProjectRepository.get_projects_for_part(session, part_id)

                # Convert projects to dict
                projects_list = [project.to_dict() for project in projects]

                return self.success_response(
                    f"Retrieved {len(projects)} projects for part",
                    {
                        "part_id": part_id,
                        "projects": projects_list,
                        "projects_count": len(projects_list)
                    }
                )

        except Exception as e:
            return self.handle_exception(e, "get projects for part")
