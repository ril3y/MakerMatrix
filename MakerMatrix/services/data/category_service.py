import logging
from typing import Optional, Any

from sqlmodel import Session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.category_repositories import CategoryRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.exceptions import CategoryAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.services.base_service import BaseService, ServiceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CategoryService(BaseService):
    """
    Category service with consolidated session management using BaseService.
    
    This migration eliminates 7+ instances of duplicated session management code.
    """
    
    def __init__(self):
        super().__init__()
        self.category_repo = CategoryRepository(engine)
        self.entity_name = "Category"

    def add_category(self, category_data: CategoryModel) -> ServiceResponse[dict]:
        """
        Add a new category to the system.
        
        CONSOLIDATED SESSION MANAGEMENT: This method previously used manual session
        management. Now uses BaseService session context manager for consistency.
        """
        try:
            # Validate required fields
            self.validate_required_fields(category_data.model_dump(), ["name"])
            
            self.log_operation("create", self.entity_name, category_data.name)
            
            with self.get_session() as session:
                new_category = CategoryRepository.create_category(session, category_data.model_dump())
                if not new_category:
                    return self.error_response(f"Failed to create {self.entity_name}")
                
                cat_dict = new_category.model_dump()
                # Add part count (new categories start with 0 parts)
                cat_dict['part_count'] = 0
                
                return self.success_response(
                    f"{self.entity_name} '{category_data.name}' created successfully",
                    cat_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    def get_category(self, category_id: Optional[str] = None, name: Optional[str] = None) -> ServiceResponse[dict]:
        """
        Get a category by ID or name.
        
        CONSOLIDATED SESSION MANAGEMENT: Eliminates manual session management.
        """
        try:
            if not any([category_id, name]):
                return self.error_response("Either category_id or name must be provided")
            
            identifier = category_id if category_id else name
            self.log_operation("get", self.entity_name, identifier)
            
            with self.get_session() as session:
                category = CategoryRepository.get_category(session, category_id=category_id, name=name)
                if not category:
                    return self.error_response(
                        f"{self.entity_name} not found with {'ID' if category_id else 'name'}: {identifier}"
                    )
                
                cat_dict = category.model_dump()
                # Add part count
                cat_dict['part_count'] = len(category.parts) if hasattr(category, 'parts') else 0
                
                return self.success_response(
                    f"{self.entity_name} '{category.name}' retrieved successfully",
                    cat_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"retrieve {self.entity_name}")

    def remove_category(self, id: Optional[str] = None, name: Optional[str] = None) -> ServiceResponse[dict]:
        """
        Remove a category by ID or name.
        
        CONSOLIDATED SESSION MANAGEMENT: Converted from static method to use BaseService patterns.
        
        Args:
            id: Optional ID of the category to remove
            name: Optional name of the category to remove
            
        Returns:
            ServiceResponse[dict]: Service response with removed category data
        """
        try:
            if not id and not name:
                return self.error_response("Either 'id' or 'name' must be provided")

            identifier = id if id else name
            self.log_operation("delete", self.entity_name, identifier)
            
            with self.get_session() as session:
                rm_cat = CategoryRepository.get_category(session, category_id=id, name=name)
                if not rm_cat:
                    return self.error_response(
                        f"{self.entity_name} not found with {'ID' if id else 'name'}: {identifier}"
                    )
                
                result = self.category_repo.remove_category(session, rm_cat)
                if not result:
                    return self.error_response(f"Failed to remove {self.entity_name}")
                
                cat_dict = rm_cat.model_dump()
                # Add part count (usually 0 for removed categories)
                cat_dict['part_count'] = 0
                
                return self.success_response(
                    f"{self.entity_name} '{rm_cat.name}' removed successfully",
                    cat_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"remove {self.entity_name}")
    
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
            count = CategoryRepository.delete_all_categories(session)
            
            logger.warning(f"Successfully deleted all {count} categories from the system")
            return {
                "status": "success",
                "message": f"All {count} categories removed successfully",
                "data": {"deleted_count": count}
            }
        except Exception as e:
            logger.error(f"Failed to delete all categories: {str(e)}")
            raise ValueError(f"Failed to delete all categories: {str(e)}")

    def get_all_categories(self) -> ServiceResponse[dict]:
        """
        Get all categories from the system.
        
        CONSOLIDATED SESSION MANAGEMENT: Converted from static method to use BaseService patterns.
        
        Returns:
            ServiceResponse[dict]: Service response with all categories
        """
        try:
            self.log_operation("get_all", self.entity_name)
            
            with self.get_session() as session:
                categories = CategoryRepository.get_all_categories(session)
                
                # Convert to list of dictionaries with part counts
                categories_list = []
                for cat in categories:
                    cat_dict = cat.model_dump()
                    # Add part count
                    cat_dict['part_count'] = len(cat.parts) if hasattr(cat, 'parts') else 0
                    categories_list.append(cat_dict)
                
                return self.success_response(
                    "All categories retrieved successfully",
                    {"categories": categories_list}
                )
                
        except Exception as e:
            return self.handle_exception(e, f"retrieve all {self.entity_name}")
    
    def update_category(self, category_id: str, category_update) -> ServiceResponse[dict]:
        """
        Update a category's fields.
        
        CONSOLIDATED SESSION MANAGEMENT: Converted from static method to use BaseService patterns.
        
        Args:
            category_id: The ID of the category to update
            category_update: The fields to update
            
        Returns:
            ServiceResponse[dict]: Service response with updated category data
        """
        try:
            if not category_id:
                return self.error_response("Category ID is required")
            
            self.log_operation("update", self.entity_name, category_id)
            
            with self.get_session() as session:
                # Get the current category to show before/after changes
                current_category = CategoryRepository.get_category(session, category_id=category_id)
                if not current_category:
                    return self.error_response(f"{self.entity_name} with ID '{category_id}' not found")
                
                # Convert CategoryUpdate to dict, excluding None values
                update_dict = {k: v for k, v in category_update.model_dump().items() if v is not None}
                
                updated_category = CategoryRepository.update_category(session, category_id, update_dict)
                if not updated_category:
                    return self.error_response(f"Failed to update {self.entity_name}")
                
                cat_dict = updated_category.model_dump()
                # Add part count
                cat_dict['part_count'] = len(updated_category.parts) if hasattr(updated_category, 'parts') else 0
                
                return self.success_response(
                    f"{self.entity_name} '{updated_category.name}' updated successfully",
                    cat_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")
