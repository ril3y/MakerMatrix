from typing import Optional, List

from models.category_model import CategoryModel
from models.part_model import PartModel
from repositories.base_repository import BaseRepository


class PartRepository(BaseRepository):
    def __init__(self):
        super().__init__('parts')

    def get_part_by_id(self, part_id: str) -> Optional[PartModel]:
        return self.table.get(self.query().part_id == part_id)

    def get_part_by_part_number(self, part_number: str) -> Optional[PartModel]:
        return self.table.get(self.query().part_number == part_number)

    def get_part_by_manufacturer_pn(self, manufacturer_part_number: str) -> Optional[PartModel]:
        return self.table.get(self.query().manufacturer_part_number == manufacturer_part_number)

    def get_part_by_details(self, part_details: str) -> Optional[PartModel]:
        # Add logic to query parts by details
        pass

    def get_all_parts_paginated(self, page, page_size):
        # Calculate offset
        offset = (page - 1) * page_size
        # Fetch paginated results
        results = self.table.all()[offset:offset + page_size]
        return results

    def clear_all_parts(self):
        # Retrieve all parts from the database
        try:
            self.table.truncate()
        except Exception as e:
            print(f"Error truncating table: {e}")

    def is_part_name_unique(self, name: str, exclude_id: Optional[str] = None) -> bool:
        # Query to find a part with the same name
        query = self.query().part_name == name
        parts = self.table.search(query)

        # If exclude_id is provided, filter out the part with that ID
        if exclude_id:
            parts = [part for part in parts if part["part_id"] != exclude_id]

        # Return True if no other parts with the same name exist, otherwise False
        return len(parts) == 0

    def add_part(self, part_data: dict, overwrite: bool) -> dict:
        # Check if a part with the same part_number or part_name already exists
        part_id = part_data.get('part_id')
        existing_part = self.get_part_by_id(part_id)

        if existing_part and not overwrite:
            return {
                "status": "part exists",
                "message": f"Part id {part_id} already exists. Overwrite is set to False.",
                "data": None
            }

        # Remove the existing part if overwrite is allowed
        if existing_part:
            self.table.remove(doc_ids=[existing_part.doc_id])

        # Process categories if they are present
        if 'categories' in part_data and part_data['categories']:
            processed_categories = []
            for category in part_data['categories']:
                if isinstance(category, str):
                    # Convert a string category into a CategoryModel
                    category_obj = CategoryModel(name=category)
                elif isinstance(category, dict):
                    # Create a CategoryModel from the provided dict
                    category_obj = CategoryModel(**category)
                else:
                    continue

                # Add the category to the list
                processed_categories.append(category_obj.dict())

            part_data['categories'] = processed_categories

        # Process additional_properties if present
        if 'additional_properties' in part_data and part_data['additional_properties']:
            processed_properties = {}
            for key, value in part_data['additional_properties'].items():
                # Convert the keys and values to strings for consistency
                processed_properties[key] = str(value)

            part_data['additional_properties'] = processed_properties

        # Insert or update the part record
        document_id = self.table.insert(part_data)

        return {
            "status": "success",
            "message": "Part added successfully",
            "data": part_data,
            "document_id": document_id
        }

    def delete_part(self, part_id: str) -> bool:
        part = self.table.get(self.query().part_id == part_id)
        if part:
            self.table.remove(self.query().part_id == part_id)
            return True
        return False

    def dynamic_search(self, term: str) -> List[dict]:
        # Search the database for all parts first
        all_parts = self.table.all()

        # Filter parts based on whether they match the search term
        def matches(part):
            matched_fields = []
            # Check all top-level fields
            top_level_fields = ['part_name', 'part_number', 'description', 'supplier']
            for field in top_level_fields:
                if term.lower() in str(part.get(field, '')).lower():
                    matched_fields.append({"field": field})

            # Check additional_properties
            additional_props = part.get('additional_properties', {})
            for key, value in additional_props.items():
                if term.lower() in str(key).lower() or term.lower() in str(value).lower():
                    matched_fields.append({"field": "additional_properties", "key": key})

            return matched_fields if matched_fields else None

        # Filter parts that match the term and include matched fields
        results = []
        for part in all_parts:
            matched_fields = matches(part)
            if matched_fields:
                results.append({"part": part, "matched_fields": matched_fields})

        return results

    def update_quantity(self, part_id: str, new_quantity: int) -> bool:
        """
        Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
        Raises an exception if no part is found or if no identifier is provided.
        """
        # Update the quantity if the part is found
        self.table.update({'quantity': new_quantity}, self.query().part_id == part_id)

    def update_part(self, part_model: PartModel) -> dict:

        # Find the part using the part_id
        existing_part = self.table.get(self.query().part_id == part_model.part_id)
        if not existing_part:
            return {"status": "error", "message": "Part not found"}

        # Convert the model to a dictionary for updating
        update_data = part_model.dict(exclude_unset=True)

        # Perform the update
        updated_count = self.table.update(update_data, doc_ids=[existing_part.doc_id])

        if updated_count:
            return {
                "status": "success",
                "message": f"Part with id '{part_model.part_id}' updated successfully",
                "data": update_data
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to update part with id '{part_model.part_id}'"
            }

    def decrement_count_repo(self, part_id: str) -> PartModel | None:
        query = self.query()
        try:
            part = self.table.get(query.part_id == part_id)
            if part:
                new_quantity = part['quantity'] - 1
                self.table.update({'quantity': new_quantity}, query.part_id == part_id)

                # Fetch the updated part from the database to return the updated quantity
                updated_part = self.table.get(query.part_id == part_id)
                return updated_part
            else:
                return None
        except Exception as e:
            return None

    def get_all_parts(self) -> List[PartModel]:
        return self.table.all()

    def get_paginated_parts(self, page: int, page_size: int) -> List[PartModel]:
        offset = (page - 1) * page_size
        return self.table.all()[offset:offset + page_size]

    def get_total_parts_count(self) -> int:
        return len(self.table)
