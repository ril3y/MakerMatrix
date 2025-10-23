import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
from sqlalchemy import delete
from sqlmodel import Session, select

from MakerMatrix.models.project_models import ProjectModel, PartProjectLink
from MakerMatrix.exceptions import (
    ResourceNotFoundError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    InvalidReferenceError,
)

# Configure logging
logger = logging.getLogger(__name__)


class ProjectRepository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_project(
        session: Session, project_id: Optional[str] = None, name: Optional[str] = None, slug: Optional[str] = None
    ) -> ProjectModel:
        """
        Get a project by ID, name, or slug.

        Args:
            session: The database session
            project_id: Optional ID of the project to retrieve
            name: Optional name of the project to retrieve
            slug: Optional slug of the project to retrieve

        Returns:
            ProjectModel: The project if found

        Raises:
            InvalidReferenceError: If no identifier is provided
            ProjectNotFoundError: If project is not found
        """
        if project_id:
            project = session.exec(select(ProjectModel).where(ProjectModel.id == project_id)).first()
            identifier = f"ID '{project_id}'"
        elif name:
            project = session.exec(select(ProjectModel).where(ProjectModel.name == name)).first()
            identifier = f"name '{name}'"
        elif slug:
            project = session.exec(select(ProjectModel).where(ProjectModel.slug == slug)).first()
            identifier = f"slug '{slug}'"
        else:
            raise InvalidReferenceError(
                message="Either 'project_id', 'name', or 'slug' must be provided for project lookup",
                reference_type="project_lookup",
                reference_id=None,
            )

        if project:
            return project
        else:
            raise ProjectNotFoundError(
                message=f"Project with {identifier} not found", project_id=project_id or name or slug
            )

    @staticmethod
    def create_project(session: Session, new_project: Dict[str, Any]) -> ProjectModel:
        """
        Create a new project.

        Args:
            session: The database session
            new_project: The project data to create

        Returns:
            ProjectModel: The created project

        Raises:
            ProjectAlreadyExistsError: If project with same name or slug already exists
        """
        project_name = new_project.get("name")
        project_slug = new_project.get("slug")
        logger.debug(f"[REPO] Attempting to create project in database: {project_name}")

        # Check for duplicate project name
        if project_name:
            existing_project = session.exec(select(ProjectModel).where(ProjectModel.name == project_name)).first()
            if existing_project:
                logger.debug(f"[REPO] Project creation failed - duplicate name: {project_name}")
                raise ProjectAlreadyExistsError(
                    message=f"Project with name '{project_name}' already exists", project_name=project_name
                )

        # Check for duplicate slug
        if project_slug:
            existing_project = session.exec(select(ProjectModel).where(ProjectModel.slug == project_slug)).first()
            if existing_project:
                logger.debug(f"[REPO] Project creation failed - duplicate slug: {project_slug}")
                raise ProjectAlreadyExistsError(
                    message=f"Project with slug '{project_slug}' already exists", project_name=project_slug
                )

        try:
            project_model = ProjectModel(**new_project)
            session.add(project_model)
            session.commit()
            session.refresh(project_model)
            logger.debug(
                f"[REPO] Successfully created project in database: {project_model.name} (ID: {project_model.id})"
            )
            return project_model
        except Exception as e:
            session.rollback()
            logger.error(f"[REPO] Database error creating project {project_name}: {str(e)}")
            raise RuntimeError(f"Failed to create project: {str(e)}")

    @staticmethod
    def remove_project(session: Session, rm_project: ProjectModel) -> ProjectModel:
        """
        Remove a project and its associations.

        Args:
            session: The database session
            rm_project: The project to remove

        Returns:
            ProjectModel: The removed project
        """
        logger.debug(f"[REPO] Removing project from database: {rm_project.name} (ID: {rm_project.id})")

        # Remove associations between parts and the project
        from MakerMatrix.models.part_models import PartModel

        # Remove all part-project associations via the link table
        session.exec(delete(PartProjectLink).where(PartProjectLink.project_id == rm_project.id))
        session.commit()

        logger.debug(f"[REPO] Removed all part associations for project: {rm_project.name}")

        # Delete the project
        session.delete(rm_project)
        session.commit()
        logger.debug(f"[REPO] Successfully removed project from database: {rm_project.name}")
        return rm_project

    @staticmethod
    def delete_all_projects(session: Session) -> int:
        """
        Delete all projects from the system.

        Args:
            session: The database session

        Returns:
            int: Number of projects deleted
        """
        # Count the number of projects before deleting
        projects = session.exec(select(ProjectModel)).all()
        count = len(projects)

        # Delete all project-part associations first
        session.exec(delete(PartProjectLink))

        # Delete all projects
        session.exec(delete(ProjectModel))
        session.commit()

        return count

    @staticmethod
    def get_all_projects(session: Session) -> List[ProjectModel]:
        """
        Get all projects from the system.

        Args:
            session: The database session

        Returns:
            List[ProjectModel]: List of all projects
        """
        return session.exec(select(ProjectModel)).all()

    @staticmethod
    def update_project(session: Session, project_id: str, project_data: Dict[str, Any]) -> ProjectModel:
        """
        Update a project's fields.

        Args:
            session: The database session
            project_id: The ID of the project to update
            project_data: The fields to update

        Returns:
            ProjectModel: The updated project
        """
        logger.debug(f"[REPO] Updating project in database: {project_id} with data: {project_data}")

        project = session.get(ProjectModel, project_id)
        if not project:
            logger.debug(f"[REPO] Project update failed - not found: {project_id}")
            raise ProjectNotFoundError(message=f"Project with ID {project_id} not found", project_id=project_id)

        # Update fields that are not None
        updated_fields = []
        for key, value in project_data.items():
            if value is not None:
                old_value = getattr(project, key, None)
                setattr(project, key, value)
                updated_fields.append(f"{key}: {old_value} -> {value}")

        # Update the updated_at timestamp
        project.updated_at = datetime.utcnow()

        logger.debug(f"[REPO] Updating fields for project {project.name}: {', '.join(updated_fields)}")

        session.add(project)
        session.commit()
        session.refresh(project)
        logger.debug(f"[REPO] Successfully updated project in database: {project.name} (ID: {project_id})")
        return project

    @staticmethod
    def associate_part_with_project(
        session: Session, part_id: str, project_id: str, notes: Optional[str] = None
    ) -> bool:
        """
        Associate a part with a project.

        Args:
            session: The database session
            part_id: The ID of the part to associate
            project_id: The ID of the project to associate with
            notes: Optional notes about this part's use in the project

        Returns:
            bool: True if association was successful, False otherwise
        """
        try:
            from MakerMatrix.models.part_models import PartModel

            # Get the part and project
            part = session.get(PartModel, part_id)
            project = session.get(ProjectModel, project_id)

            if not part or not project:
                logger.warning(
                    f"[REPO] Failed to associate part {part_id} with project {project_id} - one or both not found"
                )
                return False

            # Check if association already exists
            existing_link = session.exec(
                select(PartProjectLink).where(
                    PartProjectLink.part_id == part_id, PartProjectLink.project_id == project_id
                )
            ).first()

            if existing_link:
                logger.debug(f"[REPO] Part {part_id} already associated with project {project_id}")
                # Update notes if provided
                if notes is not None:
                    existing_link.notes = notes
                    session.commit()
                return True

            # Create new association
            link = PartProjectLink(part_id=part_id, project_id=project_id, notes=notes)
            session.add(link)
            session.commit()

            # Update project statistics
            project.update_stats(session)
            session.commit()

            logger.info(f"[REPO] Successfully associated part {part_id} with project {project_id}")
            return True

        except Exception as e:
            logger.error(f"[REPO] Error associating part {part_id} with project {project_id}: {e}")
            session.rollback()
            return False

    @staticmethod
    def remove_part_from_project(session: Session, part_id: str, project_id: str) -> bool:
        """
        Remove a part from a project.

        Args:
            session: The database session
            part_id: The ID of the part to remove
            project_id: The ID of the project to remove from

        Returns:
            bool: True if removal was successful, False otherwise
        """
        try:
            # Find and delete the association
            link = session.exec(
                select(PartProjectLink).where(
                    PartProjectLink.part_id == part_id, PartProjectLink.project_id == project_id
                )
            ).first()

            if not link:
                logger.warning(f"[REPO] Association between part {part_id} and project {project_id} not found")
                return False

            session.delete(link)
            session.commit()

            # Update project statistics
            project = session.get(ProjectModel, project_id)
            if project:
                project.update_stats(session)
                session.commit()

            logger.info(f"[REPO] Successfully removed part {part_id} from project {project_id}")
            return True

        except Exception as e:
            logger.error(f"[REPO] Error removing part {part_id} from project {project_id}: {e}")
            session.rollback()
            return False

    @staticmethod
    def is_part_associated_with_project(session: Session, part_id: str, project_id: str) -> bool:
        """
        Check if a part is associated with a project.

        Args:
            session: The database session
            part_id: The ID of the part to check
            project_id: The ID of the project to check

        Returns:
            bool: True if part is associated with project, False otherwise
        """
        try:
            link = session.exec(
                select(PartProjectLink).where(
                    PartProjectLink.part_id == part_id, PartProjectLink.project_id == project_id
                )
            ).first()

            return link is not None

        except Exception as e:
            logger.error(f"[REPO] Error checking part-project association: {e}")
            return False

    @staticmethod
    def get_parts_for_project(session: Session, project_id: str) -> List[Any]:
        """
        Get all parts associated with a project.

        Args:
            session: The database session
            project_id: The ID of the project

        Returns:
            List: List of parts in the project
        """
        try:
            from MakerMatrix.models.part_models import PartModel

            # Get the project with its parts
            project = session.get(ProjectModel, project_id)
            if not project:
                logger.warning(f"[REPO] Project {project_id} not found when getting parts")
                return []

            return project.parts

        except Exception as e:
            logger.error(f"[REPO] Error getting parts for project {project_id}: {e}")
            return []

    @staticmethod
    def get_projects_for_part(session: Session, part_id: str) -> List[ProjectModel]:
        """
        Get all projects associated with a part.

        Args:
            session: The database session
            part_id: The ID of the part

        Returns:
            List[ProjectModel]: List of projects the part belongs to
        """
        try:
            from MakerMatrix.models.part_models import PartModel

            # Get the part with its projects
            part = session.get(PartModel, part_id)
            if not part:
                logger.warning(f"[REPO] Part {part_id} not found when getting projects")
                return []

            return part.projects

        except Exception as e:
            logger.error(f"[REPO] Error getting projects for part {part_id}: {e}")
            return []
