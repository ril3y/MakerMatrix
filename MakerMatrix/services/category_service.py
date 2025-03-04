from typing import Optional, Any

from sqlmodel import Session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.category_repositories import CategoryRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.repositories.custom_exceptions import CategoryAlreadyExistsError, ResourceNotFoundError
from sqlalchemy import select, delete


class CategoryService:
    category_repo = CategoryRepository(engine)

    @staticmethod
    def add_category(category_data: CategoryModel) -> dict:
        """
        Add a new category to the system.
        
        Args:
            category_data: The category data to add
            
        Returns:
            dict: A dictionary containing the status, message, and created category data
        """
        try:
            if not category_data.name:
                raise ValueError("Category name is required")

            session = next(get_session())
            existing_category = CategoryRepository.get_category(session, name=category_data.name)
            
            if existing_category:
                return {
                    "status": "success",
                    "message": f"Category with name '{category_data.name}' already exists",
                    "data": existing_category.model_dump()
                }
            
            new_category = CategoryRepository.create_category(session, category_data.model_dump())
            if not new_category:
                raise ValueError("Failed to create category")
            
            return {
                "status": "success",
                "message": f"Category with name '{category_data.name}' created successfully",
                "data": new_category.model_dump()
            }
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to create category: {str(e)}")

    @staticmethod
    def get_category(category_id: Optional[str] = None, name: Optional[str] = None) -> dict:
        """
        Get a category by ID or name.
        
        Args:
            category_id: Optional ID of the category to retrieve
            name: Optional name of the category to retrieve
            
        Returns:
            dict: A dictionary containing the status, message, and category data
        """
        try:
            session = next(get_session())
            category = CategoryRepository.get_category(session, category_id=category_id, name=name)
            if not category:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category not found with {'ID' if category_id else 'name'} {category_id or name}",
                    data=None
                )
            return {
                "status": "success",
                "message": f"Category with name '{category.name}' retrieved successfully",
                "data": category.model_dump(),
            }
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except Exception as e:
            raise ValueError(f"Failed to retrieve category: {str(e)}")

    @staticmethod
    def remove_category(id: Optional[str] = None, name: Optional[str] = None) -> dict:
        """
        Remove a category by ID or name.
        
        Args:
            id: Optional ID of the category to remove
            name: Optional name of the category to remove
            
        Returns:
            dict: A dictionary containing the status, message, and removed category data
        """
        try:
            if not id and not name:
                raise ValueError("Either 'id' or 'name' must be provided")

            session = next(get_session())
            if id:
                identifier = id
                field = "ID"
                rm_cat = CategoryService.category_repo.get_category(session, category_id=id)
            else:
                identifier = name
                field = "name"
                rm_cat = CategoryService.category_repo.get_category(session, name=name)
                
            if not rm_cat:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with {field} {identifier} not found",
                    data=None
                )
                
            result = CategoryService.category_repo.remove_category(session, rm_cat)
            if not result:
                raise ValueError("Failed to remove category")
                
            return {
                "status": "success",
                "message": f"Category with name '{rm_cat.name}' removed",
                "data": rm_cat.model_dump()
            }
                
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to remove category: {str(e)}")
    
    @staticmethod
    def delete_all_categories() -> dict:
        """
        Delete all categories from the system.
        
        Returns:
            dict: A dictionary containing the status, message, and deletion count
        """
        try:
            session = next(get_session())
            categories = session.exec(select(CategoryModel)).all()
            count = len(categories)
            
            session.exec(delete(CategoryModel))
            session.commit()
            
            return {
                "status": "success",
                "message": f"All {count} categories removed successfully",
                "data": {"deleted_count": count}
            }
        except Exception as e:
            raise ValueError(f"Failed to delete all categories: {str(e)}")

    @staticmethod
    def get_all_categories() -> dict:
        """
        Get all categories from the system.
        
        Returns:
            dict: A dictionary containing the status, message, and all categories
        """
        try:
            session = next(get_session())
            categories = session.exec(select(CategoryModel)).all()
            return {
                "status": "success",
                "message": "All categories retrieved successfully",
                "data": {
                    "categories": [cat._asdict()['CategoryModel'].model_dump() for cat in categories] if categories else []
                }
            }
        except Exception as e:
            print(f"Error in get_all_categories: {str(e)}")  # Debug log
            raise ValueError(f"Failed to retrieve categories: {str(e)}")
    
    @staticmethod
    def update_category(category_id: str, category_update: CategoryModel) -> dict:
        """
        Update a category's fields.
        
        Args:
            category_id: The ID of the category to update
            category_update: The fields to update
            
        Returns:
            dict: A dictionary containing the status, message, and updated category data
        """
        try:
            if not category_id:
                raise ValueError("Category ID is required")
            
            session = next(get_session())
            updated_category = CategoryRepository.update_category(session, category_id, category_update)
            if not updated_category:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with ID {category_id} not found",
                    data=None
                )
            
            return {
                "status": "success",
                "message": f"Category with ID '{category_id}' updated.",
                "data": updated_category.model_dump()
            }
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to update category: {str(e)}")

    #
    # @staticmethod
    # def get_category(category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[dict]:
    #     if not category_id and not name:
    #         raise ValueError("Either 'category_id' or 'name' must be provided")
    #
    #     return CategoryService.category_repo.get_category(category_id=category_id, name=name)
    #
    # @staticmethod
    # def add_category(category_data: CategoryModel) -> dict:
    #     # Call the repository to add the category
    #     return CategoryService.category_repo.add_category(category_data)
    #
