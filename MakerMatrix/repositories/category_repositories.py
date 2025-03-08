from typing import Any, Dict, Optional, List, Type
from sqlalchemy import delete
from sqlmodel import Session, select

from MakerMatrix.database.db import get_session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError


class CategoryRepository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_category(session: Session, category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[CategoryModel]:
        """
        Get a category by ID or name.
        
        Args:
            session: The database session
            category_id: Optional ID of the category to retrieve
            name: Optional name of the category to retrieve
            
        Returns:
            Optional[CategoryModel]: The category if found, None otherwise
        """
        try:
            if category_id:
                category_identifier = "category ID"
                category = session.exec(
                    select(CategoryModel).where(CategoryModel.id == category_id)
                ).first()
            elif name:
                category_identifier = "category name"
                category = session.exec(
                    select(CategoryModel).where(CategoryModel.name == name)
                ).first()
            else:
                raise ValueError("Either 'category_id' or 'name' must be provided")
                
            return category
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to retrieve category: {str(e)}")

    @staticmethod
    def create_category(session: Session, new_category: Dict[str, Any]) -> CategoryModel:
        """
        Create a new category.
        
        Args:
            session: The database session
            new_category: The category data to create
            
        Returns:
            CategoryModel: The created category
        """
        try:
            cmodel = CategoryModel(**new_category)
            session.add(cmodel)
            session.commit()
            session.refresh(cmodel)
            return cmodel
        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to create category: {str(e)}")

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
        # Remove associations between parts and the category
        from MakerMatrix.models.models import PartModel

        parts = session.exec(
            select(PartModel).where(PartModel.categories.any(id=rm_category.id))
        ).all()
        for part in parts:
            part.categories = [category for category in part.categories if category.id != rm_category.id]
            session.add(part)

        session.commit()

        # Delete the category
        session.delete(rm_category)
        session.commit()
        return rm_category

    @staticmethod
    def delete_all_categories(session: Session) -> dict:
        """
        Delete all categories from the system.
        
        Args:
            session: The database session
            
        Returns:
            dict: A dictionary containing the status, message, and deletion count
        """
        try:
            # Count the number of categories before deleting
            categories = session.exec(select(CategoryModel)).all()
            count = len(categories)

            # Delete all categories using SQLModel syntax
            session.exec(delete(CategoryModel))
            session.commit()

            return {
                "status": "success",
                "message": f"All {count} categories removed successfully",
                "data": {"deleted_count": count}
            }

        except Exception as e:
            raise ValueError(f"Error deleting categories: {str(e)}")

    @staticmethod
    def get_all_categories(session: Session) -> dict:
        """
        Get all categories from the system.
        
        Args:
            session: The database session
            
        Returns:
            dict: A dictionary containing the status, message, and all categories
        """
        try:
            categories = session.exec(select(CategoryModel)).all()
            return {
                "status": "success",
                "message": "All categories retrieved successfully",
                "data": categories
            }
        except Exception as e:
            raise ValueError(f"Error retrieving categories: {str(e)}")

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
        category = session.get(CategoryModel, category_id)
        if not category:
            raise ResourceNotFoundError(
                status="error",
                message=f"Category with ID {category_id} not found",
                data=None
            )

        # Update fields that are not None
        for key, value in category_data.model_dump().items():
            if value is not None:
                setattr(category, key, value)

        session.add(category)
        session.commit()
        session.refresh(category)
        return category
