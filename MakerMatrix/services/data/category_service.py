import logging
from typing import Optional, Any

from sqlmodel import Session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.category_repositories import CategoryRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.repositories.custom_exceptions import CategoryAlreadyExistsError, ResourceNotFoundError
from sqlalchemy import select, delete

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        logger.info(f"Attempting to create category: {category_data.name}")
        try:
            if not category_data.name:
                logger.error("Category creation failed: Category name is required")
                raise ValueError("Category name is required")

            session = next(get_session())
            new_category = CategoryRepository.create_category(session, category_data.model_dump())
            if not new_category:
                logger.error(f"Failed to create category: {category_data.name}")
                raise ValueError("Failed to create category")
            
            logger.info(f"Successfully created category: {new_category.name} (ID: {new_category.id})")
            cat_dict = new_category.model_dump()
            # Add part count (new categories start with 0 parts)
            cat_dict['part_count'] = 0
            return {
                "status": "success",
                "message": f"Category with name '{category_data.name}' created successfully",
                "data": cat_dict
            }
                
        except CategoryAlreadyExistsError as cae:
            logger.warning(f"Category creation failed - already exists: {category_data.name}")
            raise cae
        except ValueError as ve:
            logger.error(f"Category creation failed with ValueError: {str(ve)}")
            raise ve
        except Exception as e:
            logger.error(f"Unexpected error creating category {category_data.name}: {str(e)}")
            raise RuntimeError(f"Failed to create category: {str(e)}")

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
        identifier = category_id if category_id else name
        logger.info(f"Retrieving category by {'ID' if category_id else 'name'}: {identifier}")
        try:
            session = next(get_session())
            category = CategoryRepository.get_category(session, category_id=category_id, name=name)
            if not category:
                logger.warning(f"Category not found with {'ID' if category_id else 'name'}: {identifier}")
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category not found with {'ID' if category_id else 'name'} {category_id or name}",
                    data=None
                )
            logger.info(f"Successfully retrieved category: {category.name} (ID: {category.id})")
            cat_dict = category.model_dump()
            # Add part count
            cat_dict['part_count'] = len(category.parts) if hasattr(category, 'parts') else 0
            return {
                "status": "success",
                "message": f"Category with name '{category.name}' retrieved successfully",
                "data": cat_dict,
            }
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except Exception as e:
            logger.error(f"Unexpected error retrieving category {identifier}: {str(e)}")
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
        identifier = id if id else name
        logger.info(f"Attempting to remove category by {'ID' if id else 'name'}: {identifier}")
        try:
            if not id and not name:
                logger.error("Category removal failed: Either 'id' or 'name' must be provided")
                raise ValueError("Either 'id' or 'name' must be provided")

            session = next(get_session())
            if id:
                identifier = id
                field = "ID"
                rm_cat = session.get(CategoryModel, id)
            else:
                identifier = name
                field = "name"
                rm_cat = session.exec(select(CategoryModel).where(CategoryModel.name == name)).first()

            if not rm_cat:
                logger.warning(f"Category removal failed - not found with {field}: {identifier}")
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with {field} {identifier} not found",
                    data=None
                )
            
            logger.info(f"Removing category: {rm_cat.name} (ID: {rm_cat.id})")
            result = CategoryService.category_repo.remove_category(session, rm_cat)
            if not result:
                logger.error(f"Failed to remove category: {rm_cat.name}")
                raise ValueError("Failed to remove category")
            
            logger.info(f"Successfully removed category: {rm_cat.name} (ID: {rm_cat.id})")
            cat_dict = rm_cat.model_dump()
            # Add part count (usually 0 for removed categories)
            cat_dict['part_count'] = 0
            return {
                "status": "success",
                "message": f"Category with name '{rm_cat.name}' removed",
                "data": cat_dict
            }
            
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except ValueError as ve:
            logger.error(f"Category removal failed with ValueError: {str(ve)}")
            raise ve
        except Exception as e:
            logger.error(f"Unexpected error removing category {identifier}: {str(e)}")
            raise ValueError(f"Failed to remove category: {str(e)}")
    
    @staticmethod
    def delete_all_categories() -> dict:
        """
        Delete all categories from the system.
        
        Returns:
            dict: A dictionary containing the status, message, and deletion count
        """
        logger.warning("Attempting to delete ALL categories from the system")
        try:
            session = next(get_session())
            categories = session.exec(select(CategoryModel)).all()
            count = len(categories)
            
            logger.info(f"Deleting {count} categories from the system")
            session.exec(delete(CategoryModel))
            session.commit()
            
            logger.warning(f"Successfully deleted all {count} categories from the system")
            return {
                "status": "success",
                "message": f"All {count} categories removed successfully",
                "data": {"deleted_count": count}
            }
        except Exception as e:
            logger.error(f"Failed to delete all categories: {str(e)}")
            raise ValueError(f"Failed to delete all categories: {str(e)}")

    @staticmethod
    def get_all_categories() -> dict:
        """
        Get all categories from the system.
        
        Returns:
            dict: A dictionary containing the status, message, and all categories
        """
        logger.info("Retrieving all categories from the system")
        try:
            session = next(get_session())
            categories = CategoryRepository.get_all_categories(session)
            logger.info(f"Successfully retrieved {len(categories)} categories")
            
            # Convert to list of dictionaries with part counts
            categories_list = []
            for cat in categories:
                cat_dict = cat.model_dump()
                # Add part count
                cat_dict['part_count'] = len(cat.parts) if hasattr(cat, 'parts') else 0
                categories_list.append(cat_dict)
            
            return {
                "status": "success",
                "message": "All categories retrieved successfully",
                "data": {
                    "categories": categories_list
                }
            }
        except Exception as e:
            logger.error(f"Failed to retrieve all categories: {str(e)}")
            raise ValueError(f"Failed to retrieve categories: {str(e)}")
    
    @staticmethod
    def update_category(category_id: str, category_update) -> dict:
        """
        Update a category's fields.
        
        Args:
            category_id: The ID of the category to update
            category_update: The fields to update
            
        Returns:
            dict: A dictionary containing the status, message, and updated category data
        """
        logger.info(f"Attempting to update category: {category_id}")
        try:
            if not category_id:
                logger.error("Category update failed: Category ID is required")
                raise ValueError("Category ID is required")
            
            session = next(get_session())
            
            # Get the current category to show before/after changes
            current_category = CategoryRepository.get_category(session, category_id=category_id)
            if not current_category:
                logger.error(f"Category update failed: Category with ID '{category_id}' not found")
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with ID {category_id} not found",
                    data=None
                )
            
            # Log current state and planned changes
            logger.debug(f"Current category state: '{current_category.name}' (ID: {category_id})")
            
            # Convert CategoryUpdate to dict, excluding None values
            update_dict = {k: v for k, v in category_update.model_dump().items() if v is not None}
            updated_fields = []
            
            for field, new_value in update_dict.items():
                if hasattr(current_category, field):
                    old_value = getattr(current_category, field)
                    if old_value != new_value:
                        if field == "name":
                            logger.info(f"Updating category name (ID: {category_id}): '{old_value}' → '{new_value}'")
                            updated_fields.append(f"name: '{old_value}' → '{new_value}'")
                        elif field == "description":
                            logger.info(f"Updating category description for '{current_category.name}' (ID: {category_id})")
                            updated_fields.append(f"description updated")
                        else:
                            logger.info(f"Updating {field} for category '{current_category.name}' (ID: {category_id}): {old_value} → {new_value}")
                            updated_fields.append(f"{field}: {old_value} → {new_value}")
            
            updated_category = CategoryRepository.update_category(session, category_id, update_dict)
            if not updated_category:
                logger.warning(f"Category update failed - repository returned None: {category_id}")
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with ID {category_id} not found",
                    data=None
                )
            
            if updated_fields:
                logger.info(f"Successfully updated category '{updated_category.name}' (ID: {category_id}). Changes: {', '.join(updated_fields)}")
            else:
                logger.info(f"No changes made to category '{updated_category.name}' (ID: {category_id})")
            
            cat_dict = updated_category.model_dump()
            # Add part count
            cat_dict['part_count'] = len(updated_category.parts) if hasattr(updated_category, 'parts') else 0
            return {
                "status": "success",
                "message": f"Category with ID '{category_id}' updated.",
                "data": cat_dict
            }
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except ValueError as ve:
            logger.error(f"Category update failed with ValueError: {str(ve)}")
            raise ve
        except Exception as e:
            logger.error(f"Unexpected error updating category {category_id}: {str(e)}")
            raise ValueError(f"Failed to update category: {str(e)}")
