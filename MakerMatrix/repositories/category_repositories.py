from typing import Any, Dict, Optional, List
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
        if category:
            return category
        else:
            return None
        
    @staticmethod
    def create_category(session: Session, new_category: CategoryModel) -> CategoryModel:
        cmodel = CategoryModel(**new_category)
        
        session.add(cmodel)
        session.commit()
        session.refresh(cmodel)
        return cmodel
    


    @staticmethod
    def remove_category(session: Session, rm_category: CategoryModel) -> CategoryModel:
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
        try:
        
            # Count the number of categories before deleting
            categories = session.exec(select(CategoryModel)).all()
            count = len(categories)
            
            # Delete all categories using SQLModel syntax
            session.exec(delete(CategoryModel))
            session.commit()

            # Return a success message with the number of categories removed
            return {"status": "success", 
                    "message": "All #{count} categories removed successfully",
                    "data":  None}

        except Exception as e:
            # Return an error message if something goes wrong
            return {"status": "error",
                    "message": f"Error deleting categories: {str(e)}",
                    "data": None}

    @staticmethod
    def get_all_categories(session: Session) -> dict:
        try:
            categories = session.exec(select(CategoryModel)).all()
            return {"status": "success",
                    "message": "All categories retrieved successfully",
                    "data": categories}
            
        except Exception as e:
            raise ValueError(f"Error retrieving categories: {str(e)}")
    #
    # def get_category(self, category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[dict]:
    #     if category_id:
    #         return self.table.get(self.query().id == category_id)
    #     elif name:
    #         return self.table.get(self.query().name == name)
    #     else:
    #         return None
    #
    # def remove_category(self, value: str, by: str = "id") -> bool:
    #     if by == "id":
    #         result = self.table.remove(self.query().id == value)
    #     elif by == "name":
    #         result = self.table.remove(self.query().name == value)
    #     else:
    #         raise ValueError("Invalid parameter for 'by'. Must be 'id' or 'name'.")
    #     return len(result) > 0
    #
    #
    # def update_category(self, category: CategoryModel) -> dict:
    #     # Prepare the fields to update
    #     update_data = {}
    #     if category.name:
    #         update_data['name'] = category.name
    #     if category.description:
    #         update_data['description'] = category.description
    #     if category.parent_id:
    #         update_data['parent_id'] = category.parent_id
    #
    #     # Ensure we have fields to update
    #     if not update_data:
    #         return {"status": "error", "message": "No valid fields provided for update"}
    #
    #     try:
    #         # Perform the update using the category ID
    #         updated_count = self.table.update(update_data, self.query().id == category.id)
    #
    #         # Check if the update was successful
    #         if len(updated_count) > 0:
    #             return {"status": "success",
    #                     "category_id": category.id,
    #                     "documents_updated": len(updated_count),
    #                     "message": f"Category with ID '{category.id}' updated successfully"}
    #         else:
    #             return {"status": "error", "category_id": category.id,
    #                     "message": f"Category with ID '{category.id}' not found"}
    #
    #     except Exception as e:
    #         return {"status": "error", "category_id": category.id,
    #                 "message": f"Error updating category: {str(e)}"}
    #
    # def add_category(self, category: CategoryModel) -> Dict[str, str]:
    #     # Check if a category with the same name already exists
    #     existing_category = existing_category = self.table.get(self.query().name == category.name)
    #
    #     if existing_category:
    #         return {
    #             "status": "exists",
    #             "message": f"Category '{category.name}' already exists.",
    #             "id": existing_category['id'],
    #             "data": existing_category
    #         }
    #
    #     # Generate a UUID for the new category if not already set
    #     category.id = str(uuid.uuid4())
    #
    #     # Convert the CategoryModel instance to a dictionary
    #     category_data = category.dict()
    #
    #     # Insert the category data into the database
    #     self.table.insert(category_data)
    #
    #     return {
    #         "status": "success",
    #         "message": f"Category '{category.name}' added successfully.",
    #         "data": category_data
    #     }
