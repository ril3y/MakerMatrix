from typing import Optional, Any

from sqlmodel import Session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.category_repositories import CategoryRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.repositories.custom_exceptions import CategoryAlreadyExistsError, ResourceNotFoundError


class CategoryService:
    category_repo = CategoryRepository(engine)

    @staticmethod
    def add_category(category_data: CategoryModel) -> CategoryModel:
        try:
            category_id = category_data.id
            category_name = category_data.name
            category_description = category_data.description
            

            session = next(get_session())
            category = CategoryRepository.get_category(session, category_id=category_id, name=category_name)
            
            if category:
                raise CategoryAlreadyExistsError(f"Category with name '{category_name}' already exists")
            else:
                new_category = CategoryRepository.create_category(session, category_data.model_dump())
            
                if new_category:
                    return {
                        "status": "created",
                        "message": f"Category with name '{category_name}' created",
                        "data": new_category.model_dump(),
                    }
                
        except Exception as e:
            raise ValueError("Cannot create a category without a name")

    @staticmethod
    def remove_category(id: Optional[str] = None, name: Optional[str] = None) -> (bool, str):
        session = next(get_session())
        try:
            if id:
                identifier = id
                field = "ID"
                rm_cat = CategoryService.category_repo.get_category(session, category_id=id)
            elif name:
                identifier = name
                field = "name"
                rm_cat = CategoryService.category_repo.get_category(session, name=name)
            else:
                raise ValueError("Either 'id' or 'name' must be provided")
            if not rm_cat:
                
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with {field} {identifier} not found",
                    data=None)
                
            result = CategoryService.category_repo.remove_category(session, rm_cat)
            
            if result:
                return {
                        "status": "removed",
                        "message": f"Category with name '{rm_cat.name}' removed",
                        "data": rm_cat.model_dump(),
                    }  
                
                
        except ResourceNotFoundError as rnfe:
            raise rnfe
        
        except Exception as e:
            raise ValueError("Cannot remove a category without a name")
        
    @staticmethod
    def delete_all_categories() -> dict:
        session = next(get_session())
        return CategoryService.category_repo.delete_all_categories(session)

    @staticmethod
    def get_all_categories() -> dict:
        session = next(get_session())
        return CategoryService.category_repo.get_all_categories(session)
    
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
    # @staticmethod
    # def update_category(category_data: CategoryModel):
    #     return CategoryService.category_repo.update_category(category_data)
    #

    #
    
