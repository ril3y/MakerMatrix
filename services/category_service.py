from typing import Optional

from models.category_model import CategoryModel
from repositories.category_repositories import CategoryRepository


class CategoryService:
    category_repo = CategoryRepository()

    @staticmethod
    def get_all_categories():
        return CategoryService.category_repo.get_all_categories()

    @staticmethod
    def get_category(category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[dict]:
        if not category_id and not name:
            raise ValueError("Either 'category_id' or 'name' must be provided")

        return CategoryService.category_repo.get_category(category_id=category_id, name=name)

    @staticmethod
    def add_category(category_data: CategoryModel) -> dict:
        # Call the repository to add the category
        return CategoryService.category_repo.add_category(category_data)

    @staticmethod
    def update_category(category_data: CategoryModel):
        return CategoryService.category_repo.update_category(category_data)

    @staticmethod
    def remove_category(id: Optional[str] = None, name: Optional[str] = None) -> (bool, str):
        if id:
            success = CategoryService.category_repo.remove_category(value=id, by="id")
            return success, f"id '{id}'"
        elif name:
            success = CategoryService.category_repo.remove_category(value=name, by="name")
            return success, f"name '{name}'"
        raise ValueError("Either 'id' or 'name' must be provided")

    @staticmethod
    def delete_all_categories() -> dict:
        return CategoryService.category_repo.delete_all_categories()
