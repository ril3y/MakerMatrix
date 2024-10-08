import uuid
from typing import Dict, Optional

from models.category_model import CategoryModel
from repositories.base_repository import BaseRepository


class CategoryRepository(BaseRepository):
    def __init__(self):
        super().__init__('categories')

    def get_all_categories(self):
        return self.table.all()

    def get_category(self, category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[dict]:
        if category_id:
            return self.table.get(self.query().id == category_id)
        elif name:
            return self.table.get(self.query().name == name)
        else:
            return None

    def remove_category(self, value: str, by: str = "id") -> bool:
        if by == "id":
            result = self.table.remove(self.query().id == value)
        elif by == "name":
            result = self.table.remove(self.query().name == value)
        else:
            raise ValueError("Invalid parameter for 'by'. Must be 'id' or 'name'.")
        return len(result) > 0

    def delete_all_categories(self) -> dict:
        try:
            # Count the number of categories before truncating
            count = len(self.table)

            # Truncate the table to remove all categories
            self.table.truncate()

            # Return a success message with the number of categories removed
            return {"status": "success", "count": count, "message": "All categories removed successfully"}

        except Exception as e:
            # Return an error message if something goes wrong
            return {"status": "error", "message": f"Error truncating categories table: {str(e)}"}

    def update_category(self, category: CategoryModel) -> dict:
        # Prepare the fields to update
        update_data = {}
        if category.name:
            update_data['name'] = category.name
        if category.description:
            update_data['description'] = category.description
        if category.parent_id:
            update_data['parent_id'] = category.parent_id

        # Ensure we have fields to update
        if not update_data:
            return {"status": "error", "message": "No valid fields provided for update"}

        try:
            # Perform the update using the category ID
            updated_count = self.table.update(update_data, self.query().id == category.id)

            # Check if the update was successful
            if len(updated_count) > 0:
                return {"status": "success",
                        "category_id": category.id,
                        "documents_updated": len(updated_count),
                        "message": f"Category with ID '{category.id}' updated successfully"}
            else:
                return {"status": "error", "category_id": category.id,
                        "message": f"Category with ID '{category.id}' not found"}

        except Exception as e:
            return {"status": "error", "category_id": category.id,
                    "message": f"Error updating category: {str(e)}"}

    def add_category(self, category: CategoryModel) -> Dict[str, str]:
        # Check if a category with the same name already exists
        existing_category = existing_category = self.table.get(self.query().name == category.name)

        if existing_category:
            return {
                "status": "exists",
                "message": f"Category '{category.name}' already exists.",
                "id": existing_category['id'],
                "data": existing_category
            }

        # Generate a UUID for the new category if not already set
        category.id = str(uuid.uuid4())

        # Convert the CategoryModel instance to a dictionary
        category_data = category.dict()

        # Insert the category data into the database
        self.table.insert(category_data)

        return {
            "status": "success",
            "message": f"Category '{category.name}' added successfully.",
            "data": category_data
        }
