import logging
from typing import Any, Dict, Optional, List
from sqlalchemy import delete
from sqlmodel import Session, select

from MakerMatrix.database.db import get_session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    CategoryAlreadyExistsError,
    InvalidReferenceError
)

# Configure logging
logger = logging.getLogger(__name__)


class CategoryRepository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_category(session: Session, category_id: Optional[str] = None, name: Optional[str] = None) -> CategoryModel:
        """
        Get a category by ID or name.
        
        Args:
            session: The database session
            category_id: Optional ID of the category to retrieve
            name: Optional name of the category to retrieve
            
        Returns:
            CategoryModel: The category if found
            
        Raises:
            InvalidReferenceError: If neither category_id nor name is provided
            ResourceNotFoundError: If category is not found
        """
        if category_id:
            category = session.exec(
                select(CategoryModel).where(CategoryModel.id == category_id)
            ).first()
            identifier = f"ID '{category_id}'"
        elif name:
            category = session.exec(
                select(CategoryModel).where(CategoryModel.name == name)
            ).first()
            identifier = f"name '{name}'"
        else:
            raise InvalidReferenceError(
                status="error",
                message="Either 'category_id' or 'name' must be provided for category lookup",
                data=None
            )
        
        if category:
            return category
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"Category with {identifier} not found",
                data=None
            )

    @staticmethod
    def create_category(session: Session, new_category: Dict[str, Any]) -> CategoryModel:
        """
        Create a new category.
        
        Args:
            session: The database session
            new_category: The category data to create
            
        Returns:
            CategoryModel: The created category
            
        Raises:
            CategoryAlreadyExistsError: If category with same name already exists
        """
        category_name = new_category.get("name")
        logger.debug(f"[REPO] Attempting to create category in database: {category_name}")
        
        # Check for duplicate category name
        if category_name:
            existing_category = session.exec(
                select(CategoryModel).where(CategoryModel.name == category_name)
            ).first()
            if existing_category:
                logger.debug(f"[REPO] Category creation failed - duplicate name: {category_name}")
                raise CategoryAlreadyExistsError(
                    status="error",
                    message=f"Category with name '{category_name}' already exists",
                    data={"existing_category_id": existing_category.id}
                )
        
        try:
            cmodel = CategoryModel(**new_category)
            session.add(cmodel)
            session.commit()
            session.refresh(cmodel)
            logger.debug(f"[REPO] Successfully created category in database: {cmodel.name} (ID: {cmodel.id})")
            return cmodel
        except Exception as e:
            session.rollback()
            logger.error(f"[REPO] Database error creating category {category_name}: {str(e)}")
            raise RuntimeError(f"Failed to create category: {str(e)}")

    @staticmethod
    def remove_category(session: Session, rm_category: CategoryModel) -> CategoryModel:
        """
        Remove a category and its associations.
        
        Args:
            session: The database session
            rm_category: The category to remove
            
        Returns:
            CategoryModel: The removed category
        """
        logger.debug(f"[REPO] Removing category from database: {rm_category.name} (ID: {rm_category.id})")
        
        # Remove associations between parts and the category
        from MakerMatrix.models.models import PartModel

        parts = session.exec(
            select(PartModel).where(PartModel.categories.any(id=rm_category.id))
        ).all()
        
        if parts:
            logger.debug(f"[REPO] Removing category associations from {len(parts)} parts")
            for part in parts:
                part.categories = [category for category in part.categories if category.id != rm_category.id]
                session.add(part)

        session.commit()

        # Delete the category
        session.delete(rm_category)
        session.commit()
        logger.debug(f"[REPO] Successfully removed category from database: {rm_category.name}")
        return rm_category

    @staticmethod
    def delete_all_categories(session: Session) -> int:
        """
        Delete all categories from the system.
        
        Args:
            session: The database session
            
        Returns:
            int: Number of categories deleted
        """
        # Count the number of categories before deleting
        categories = session.exec(select(CategoryModel)).all()
        count = len(categories)

        # Delete all categories using SQLModel syntax
        session.exec(delete(CategoryModel))
        session.commit()

        return count

    @staticmethod
    def get_all_categories(session: Session) -> List[CategoryModel]:
        """
        Get all categories from the system.
        
        Args:
            session: The database session
            
        Returns:
            List[CategoryModel]: List of all categories
        """
        return session.exec(select(CategoryModel)).all()

    @staticmethod
    def update_category(session: Session, category_id: str, category_data: Dict[str, Any]) -> CategoryModel:
        """
        Update a category's fields.
        
        Args:
            session: The database session
            category_id: The ID of the category to update
            category_data: The fields to update
            
        Returns:
            CategoryModel: The updated category
        """
        logger.debug(f"[REPO] Updating category in database: {category_id} with data: {category_data}")
        
        category = session.get(CategoryModel, category_id)
        if not category:
            logger.debug(f"[REPO] Category update failed - not found: {category_id}")
            raise ResourceNotFoundError(
                status="error",
                message=f"Category with ID {category_id} not found",
                data=None
            )

        # Update fields that are not None
        updated_fields = []
        for key, value in category_data.items():
            if value is not None:
                old_value = getattr(category, key, None)
                setattr(category, key, value)
                updated_fields.append(f"{key}: {old_value} -> {value}")

        logger.debug(f"[REPO] Updating fields for category {category.name}: {', '.join(updated_fields)}")
        
        session.add(category)
        session.commit()
        session.refresh(category)
        logger.debug(f"[REPO] Successfully updated category in database: {category.name} (ID: {category_id})")
        return category
