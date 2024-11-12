from typing import Optional, List, Dict

from sqlmodel import Session, select
# from MakerMatrix.models.category_model import CategoryModel
# from MakerMatrix.models.part_model import PartModel
# from MakerMatrix.repositories.base_repository import BaseRepository

from MakerMatrix.models.models import PartModel, CategoryModel


def handle_categories(session: Session, categories_data: list) -> list:
    categories = []
    for category_name in categories_data:
        category = session.exec(
            select(CategoryModel).where(CategoryModel.name == category_name)
        ).first()
        if not category:
            category = CategoryModel(name=category_name)
            session.add(category)
        categories.append(category)
    return categories




class PartRepository:
    # def __init__(self):
    #     super().__init__('parts')


    #
    # def get_part_by_part_number(self, part_number: str) -> Optional[PartModel]:
    #     return self.table.get(self.query().part_number == part_number)
    #
    # def get_part_by_part_name(self, part_name: str) -> Optional[PartModel]:
    #     return self.table.get(self.query().part_name == part_name)
    #
    # def get_part_by_manufacturer_pn(self, manufacturer_part_number: str) -> Optional[PartModel]:
    #     return self.table.get(self.query().manufacturer_part_number == manufacturer_part_number)
    #
    # def get_all_parts_paginated(self, page, page_size):
    #     # Calculate offset
    #     offset = (page - 1) * page_size
    #     # Fetch paginated results
    #     results = self.table.all()[offset:offset + page_size]
    #     return results
    #
    # def clear_all_parts(self):
    #     # Retrieve all parts from the database
    #     try:
    #         self.table.truncate()
    #     except Exception as e:
    #         print(f"Error truncating table: {e}")
    #
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_part_by_id(session: Session, part_id: str) -> Optional[PartModel]:
        try:
            return session.exec(
                select(PartModel).where(PartModel.id == part_id)
            ).first()
        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to get part by ID {part_id}: {e}")

    @staticmethod
    def add_part(session: Session, part_data: dict) -> dict:
        try:
            from MakerMatrix.repositories.category_repositories import CategoryRepository
            # Extract categories from part_data
            categories_data = part_data.pop("categories", [])

            # Check if part already exists by its part number
            part_exists = session.exec(
                select(PartModel).where(PartModel.part_number == part_data["part_number"])
            ).first()

            if part_exists:
                    return {"status": "part exists", "message": "Part already exists", "data": part_exists}

            # Add new part to the database
            new_part = PartModel(**part_data)

            # Handle categories for the new part using CategoriesRepo
            new_part.categories.extend(handle_categories(session, categories_data))

            session.add(new_part)
            session.commit()
            session.refresh(new_part)
            return {"status": "added", "data": new_part}

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to add part {part_data}: {e}")

    def is_part_name_unique(self, name: str, exclude_id: Optional[str] = None) -> bool:
        with Session(self.engine) as session:
            # Create a base query to find parts with the same name
            query = select(PartModel).where(PartModel.part_name == name)

            # If exclude_id is provided, add condition to exclude that ID from the query
            if exclude_id:
                query = query.where(PartModel.id != exclude_id)

            # Execute the query
            result = session.exec(query).first()

            # Return True if no other parts with the same name exist, otherwise False
            return result is None

    # def add_part(self, part_data: dict, overwrite: bool) -> dict:
    #     # Check if a part with the same part_number or part_name already exists
    #     part_id = part_data.get('part_id')
    #     existing_part = self.get_part_by_id(part_id)
    #
    #     if existing_part and not overwrite:
    #         return {
    #             "status": "part exists",
    #             "message": f"Part id {part_id} already exists. Overwrite is set to False.",
    #             "data": None
    #         }
    #
    #     # Remove the existing part if overwrite is allowed
    #     if existing_part:
    #         self.table.remove(doc_ids=[existing_part.doc_id])
    #
    #     # Process categories if they are present
    #     if 'categories' in part_data and part_data['categories']:
    #         processed_categories = []
    #         for category in part_data['categories']:
    #             if isinstance(category, str):
    #                 # Convert a string category into a CategoryModel
    #                 category_obj = CategoryModel(name=category)
    #             elif isinstance(category, dict):
    #                 # Create a CategoryModel from the provided dict
    #                 category_obj = CategoryModel(**category)
    #             else:
    #                 continue
    #
    #             # Add the category to the list
    #             processed_categories.append(category_obj.dict())
    #
    #         part_data['categories'] = processed_categories
    #
    #     # Process additional_properties if present
    #     if 'additional_properties' in part_data and part_data['additional_properties']:
    #         processed_properties = {}
    #         for key, value in part_data['additional_properties'].items():
    #             # Convert the keys and values to strings for consistency
    #             processed_properties[key] = str(value)
    #
    #         part_data['additional_properties'] = processed_properties
    #
    #     # Insert or update the part record
    #     document_id = self.table.insert(part_data)
    #
    #     return {
    #         "status": "success",
    #         "message": "Part added successfully",
    #         "data": part_data,
    #         "document_id": document_id
    #     }

    # def delete_part(self, part_id: str) -> bool:
    #     part = self.table.get(self.query().part_id == part_id)
    #     if part:
    #         self.table.remove(self.query().part_id == part_id)
    #         return True
    #     return False
    #
    # def dynamic_search(self, term: str) -> List[dict]:
    #     # Search the database for all parts first
    #     all_parts = self.table.all()
    #
    #     # Filter parts based on whether they match the search term
    #     def matches(part):
    #         matched_fields = []
    #         # Check all top-level fields
    #         top_level_fields = ['part_name', 'part_number', 'description', 'supplier']
    #         for field in top_level_fields:
    #             if term.lower() in str(part.get(field, '')).lower():
    #                 matched_fields.append({"field": field})
    #
    #         # Check additional_properties
    #         additional_props = part.get('additional_properties', {})
    #         for key, value in additional_props.items():
    #             if term.lower() in str(key).lower() or term.lower() in str(value).lower():
    #                 matched_fields.append({"field": "additional_properties", "key": key})
    #
    #         return matched_fields if matched_fields else None
    #
    #     # Filter parts that match the term and include matched fields
    #     results = []
    #     for part in all_parts:
    #         matched_fields = matches(part)
    #         if matched_fields:
    #             results.append({"part": part, "matched_fields": matched_fields})
    #
    #     return results
    #
    # def update_quantity(self, part_id: str, new_quantity: int) -> bool:
    #     """
    #     Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
    #     Raises an exception if no part is found or if no identifier is provided.
    #     """
    #     # Update the quantity if the part is found
    #     self.table.update({'quantity': new_quantity}, self.query().part_id == part_id)
    #
    # def update_part(self, part_model: PartModel) -> dict:
    #
    #     # Find the part using the part_id
    #     existing_part = self.table.get(self.query().part_id == part_model.part_id)
    #     if not existing_part:
    #         return {"status": "error", "message": "Part not found"}
    #
    #     # Convert the model to a dictionary for updating
    #     update_data = part_model.dict(exclude_unset=True)
    #
    #     # Perform the update
    #     updated_count = self.table.update(update_data, doc_ids=[existing_part.doc_id])
    #
    #     if updated_count:
    #         return {
    #             "status": "success",
    #             "message": f"Part with id '{part_model.part_id}' updated successfully",
    #             "data": update_data
    #         }
    #     else:
    #         return {
    #             "status": "error",
    #             "message": f"Failed to update part with id '{part_model.part_id}'"
    #         }
    #
    # def decrement_count_repo(self, part_id: str) -> PartModel | None:
    #     query = self.query()
    #     try:
    #         part = self.table.get(query.part_id == part_id)
    #         if part:
    #             new_quantity = part['quantity'] - 1
    #             self.table.update({'quantity': new_quantity}, query.part_id == part_id)
    #
    #             # Fetch the updated part from the database to return the updated quantity
    #             updated_part = self.table.get(query.part_id == part_id)
    #             return updated_part
    #         else:
    #             return None
    #     except Exception as e:
    #         return None
    #
    # def get_all_parts(self) -> List[PartModel]:
    #     return self.table.all()
    #
    # def get_paginated_parts(self, page: int, page_size: int) -> List[PartModel]:
    #     offset = (page - 1) * page_size
    #     return self.table.all()[offset:offset + page_size]
    #
    # def get_total_parts_count(self) -> int:
    #     return len(self.table)
    #
    # def get_parts_by_location_id(self, location_id: str, recursive: bool = False) -> List[Dict]:
    #     """
    #     Retrieve parts associated with the given location ID.
    #
    #     If recursive is True, it will also fetch parts associated with child locations.
    #     """
    #     # Fetch parts directly associated with the given location
    #     parts = self.table.search(self.query().location.id == location_id)
    #
    #     if recursive:
    #         # If recursive, find parts associated with all child locations
    #         child_location_ids = self.get_child_location_ids(location_id)
    #         for child_id in child_location_ids:
    #             parts.extend(self.get_parts_by_location_id(child_id, recursive=True))
    #
    #     return parts
    #
    # def get_child_location_ids(self, parent_id: str) -> List[str]:
    #     """
    #     Recursively retrieve all child location IDs for a given parent location.
    #     """
    #     from MakerMatrix.repositories.location_repositories import LocationRepository
    #     location_repo = LocationRepository()
    #     child_locations = location_repo.get_child_locations(parent_id)
    #
    #     # Extract IDs and recursively find all nested children
    #     child_ids = [loc['id'] for loc in child_locations]
    #     for loc in child_locations:
    #         child_ids.extend(self.get_child_location_ids(loc['id']))
    #
    #     return child_ids
