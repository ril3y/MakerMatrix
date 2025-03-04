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
    def get_category(session: Session, category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[
        CategoryModel]:
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
                    "data": None}

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

    @staticmethod
    def update_category(session: Session, category_id: str, category_data: Dict[str, Any]) -> Type[CategoryModel]:
        category = session.get(CategoryModel, category_id)
        if not category:
            raise ResourceNotFoundError(resource="Category", resource_id=category_id)

        for key, value in category_data.model_dump().items():
            if key == "children" and value == None:
                continue
            #     elif key == "children" and value:
            #         # Update children relationships
            #         children = session.exec(select(CategoryModel).where(CategoryModel.id.in_(value))).all()
            #         for child in children:
            #             # Remove the child from any other parent category
            #             if child.parent_id and child.parent_id != category_id:
            #                 old_parent = session.get(CategoryModel, child.parent_id)
            #                 if old_parent:
            #                     old_parent.children = [c for c in old_parent.children if c.id != child.id]
            #                     session.add(old_parent)
            #             # Set the new parent_id for the child
            #             child.parent_id = category_id
            #             session.add(child)
            #         category.children = children
            else:
                if value is None:
                    continue
                else:
                    # only update values that are populated
                    setattr(category, key, value)

        session.add(category)
        session.commit()
        session.refresh(category)
        return category
