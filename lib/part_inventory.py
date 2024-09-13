import uuid

from tinydb import Query, where
from tinydb import TinyDB


class PartInventory:
    def __init__(self, db_file):
        self.db = TinyDB(db_file)
        self.part_table = self.db.table('parts')
        self.location_table = self.db.table('locations')
        self.suppliers = self.db.table('suppliers')
        self.category_table = self.db.table('categories')

    def get_all_categories(self):
        return self.category_table.all()

    def get_all_locations(self):
        # Fetches all documents from the 'locations' table
        return self.location_table.all()

    async def add_part(self, part, overwrite) -> dict:
        PartQuery = Query()
        return_message = {}

        # Check if a part with the same part_number already exists
        if part.part_number:
            existing_part = self.part_table.get(PartQuery.part_number == part.part_number)
        else:
            existing_part = self.part_table.get(PartQuery.part_name == part.part_name)

        # TODO:  We need to ask if they want to register a location for this part.  If so then we can do auto location
        # or we can get existing locations from the db then present them to the UI.

        # # Handle location data
        # if 'location_name' in data:
        #     # Look for the location by name
        #     location = self.location_table.get(Query().name == data['location_name'])
        #     if location:
        #         # If location exists, add its ID to the part data
        #         data['location_id'] = location.doc_id
        #     else:
        #         # Handle case where location is not found (optional)
        #         # You can choose to create a new location, throw an error, etc.
        #         print(f"Location '{data['location_name']}' not found.")
        #         # Optionally remove location_name from data if location not found
        #         data.pop('location_name', None)

        if existing_part and not overwrite:
            # If part exists and overwrite is False, ask for confirmation
            return_message = {
                "event": "question",
                "question_text": f"Existing part found: {part.part_number}. Do you want to overwrite this entry for this part?",
                "question_type": "alert",
                "positive_text": "Yes",
                "negative_text": "Nope!"
            }
        else:
            # If part does not exist or overwrite is True, proceed to add or update
            if existing_part:
                # Remove the existing part first
                self.part_table.remove(doc_ids=[existing_part.doc_id])

            # Auto populate categories if they do not exist
            categories = part.categories
            for category_name in categories:
                for category in self.get_all_categories():
                    if category.get('name').strip() == category_name.strip():
                        break
                else:
                    self.add_category(category_name)

            # Insert or update the part record
            document_id = self.part_table.insert(part.dict())

            return_message = {
                "event": "part_added",
                "data": part.dict()
            }
            return_message['data']['document_id'] = document_id

        return return_message

    def clear_all_parts(self):
        self.part_table.truncate()

    def get_all_parts(self):
        # Retrieve all parts from the database
        return self.part_table.all()

    async def delete_part(self, part_id: str):
        # Check if the part exists in the database
        query = Query()
        part = self.part_table.get(query.part_id == part_id)
        if part is None:
            return "Part not found."

        # Delete the part from the database
        self.part_table.remove(query.part_id == part_id)
        return f"Part {part_id} deleted successfully."

    def dynamic_search(self, criteria):
        query = Query()
        queries = []

        for field, value in criteria.items():
            if '__' in field:
                # For nested fields, split and create nested queries
                field, subfield = field.split('__')

                def match(doc, field=field, subfield=subfield, value=value):
                    return value.lower() in str(doc.get(field, {}).get(subfield, '')).lower()

                queries.append(Query().fragment({field: match}))
            else:
                # For top-level fields
                queries.append(where(field).test(lambda x: value.lower() in str(x).lower()))

        final_query = queries.pop(0)
        for q in queries:
            final_query &= q  # Combine queries with logical AND

        return self.part_table.search(final_query)

    def search_parts(self, query, search_type):
        Part = Query()
        query = query.lower()  # Convert query to lowercase
        if search_type == "name":
            # Search case-insensitively by name
            return self.part_table.search(where('part_name').test(lambda x: x.lower() if x else '' == query))
        elif search_type == "number":
            # Search case-insensitively by number
            return self.part_table.search(where('part_number').test(lambda x: x.lower() if x else '' == query))
        elif search_type == "value":
            return self.part_table.search(where('value').test(lambda x: x.lower() if x else '' == query))
        return None

    def get_suggestions(self, query, search_type):
        Part = Query()
        # Search for part numbers that start with the given query
        if search_type == "name":
            matching_parts = self.part_table.search(Part.part_name.search('^' + query))
            suggestions = [part['part_name'] for part in matching_parts]
            return suggestions
        elif search_type == "number":
            matching_parts = self.part_table.search(Part.part_number.search('^' + query))
            # Extract part numbers from the results
            suggestions = [part['part_number'] for part in matching_parts]
            return suggestions
        return None

    def get_part_by_part_number(self, part_number):
        # Retrieve a part by its manufacturer_pn
        Part = Query()
        return self.part_table.get(Part.part_number == part_number)

    async def get_part_by_part_id(self, part_id):
        # Retrieve a part by its manufacturer_pn
        Part = Query()
        part = self.part_table.get(Part.part_id == part_id)
        return part

    def delete_part_by_manufacturer_pn(self, manufacturer_pn):
        # Delete a part by its manufacturer_pn
        Part = Query()
        self.part_table.remove(Part.manufacturer_pn == manufacturer_pn)

    def _find_by_manufacturer_pn(self, manufacturer_pn):
        part = Query()
        return self.part_table.get(part.manufacturer_pn == manufacturer_pn)

    def update_quantity(self, manufacturer_pn, new_quantity):
        part = self._find_by_manufacturer_pn(manufacturer_pn)
        if part:
            # Update the quantity of the part
            self.part_table.update({'quantity': new_quantity}, doc_ids=[part.doc_id])
        else:
            # Handle the case where the part was not found
            print(f"Part with manufacturer part number {manufacturer_pn} not found.")

    def decrement_count(self, manufacturer_pn, by):
        part = self._find_by_manufacturer_pn(manufacturer_pn)
        new_quantity = part.get("quantity") - by
        self.part_table.update({'quantity': new_quantity}, doc_ids=[part.doc_id])

    # LOCATIONS
    async def add_location(self, location_data):
        name = location_data['name']
        description = location_data['description']
        parent_id = location_data.get('parent_id')

        if parent_id is not None and not isinstance(parent_id, str):
            raise ValueError("parent_id must be a string or None")

        # Check if a location with the same name already exists
        location = Query()
        existing_location = self.location_table.get(location.name == name)
        if existing_location:
            return {"error": "A location with the same name already exists"}

        # Generate a UUID for the new location
        location_id = str(uuid.uuid4())

        # Create a new location record with the given data
        new_location = {
            'id': location_id,
            'name': name,
            'description': description,
            'parent_id': parent_id,
            'children': []  # Initialize an empty list for children
        }

        # If parent_id is not None, look up the parent location
        if parent_id is not None:
            parent_location = self.location_table.get(location.id == parent_id)
            if parent_location:
                parent_location['children'].append(location_id)
                self.location_table.update({'children': parent_location['children']}, location.id == parent_id)

        self.location_table.insert(new_location)
        return {"message": "Location added successfully"}

    async def update_location(self, location_id, new_data):
        # Update a location
        self.location_table.update(new_data, (Query().id == [location_id]))

    async def get_location_path(self, location_id):
        """
        Retrieves the path from a specific location to the root in a nested JSON format.

        :param location_id: The ID of the specific location.
        :return: A nested JSON object representing the path from the specified location to the root.
        """

        def construct_path(location_id):
            location = self.location_table.get(Query().id == location_id)
            if location is None:
                return None

            parent_id = location.get('parent_id')
            if parent_id:
                parent_location = construct_path(parent_id)
                if parent_location:
                    return {'location': location, 'parent': parent_location}
            return {'location': location, 'parent': None}

        return construct_path(location_id)

    async def get_location_hierarchy(self, parent_id):
        """
        Recursively retrieves all child locations for a given parent location.

        :param parent_id: The ID of the parent location.
        :return: A nested JSON structure of locations.
        """

        def fetch_children(location_id):
            children = self.location_table.search(Query().parent_id == location_id)
            for child in children:
                # Recursive call to fetch the children of the current child
                child['children'] = fetch_children(child.doc_id)
            return children

        # Start the recursion with the specified parent ID
        return fetch_children(parent_id)

    async def get_location(self, location_id):
        """
        Retrieves a location by its ID from the locations table.

        :param location_id: The ID of the location to retrieve.
        :return: The location data if found, otherwise None.
        """
        location = self.location_table.get(Query().id == location_id)
        return location if location else None

    async def delete_location(self, location_id):

        parts_affected = await self.get_parts_effected_locations(location_id)
        query = Query()

        for part in parts_affected:
            # Assuming 'id' is the unique identifier for parts
            part_id = part.doc_id
            if part_id is not None:
                # Update the part's location to an empty dictionary
                self.part_table.update({'location': {}}, doc_ids=[part_id])

        # Delete a location
        return self.location_table.remove(Query().id == location_id)

    async def get_parts_effected_locations(self, location_id):
        query = Query()
        parts_effected = self.part_table.search(location_id == query.location.id)
        return parts_effected

    async def add_supplier(self, supplier_data):
        supplier = Query()
        existing_supplier = self.suppliers.get(supplier.name == supplier_data['name'])
        if existing_supplier:
            return {"error": "A supplier with the same name already exists"}

        # Generate a UUID for the new supplier
        supplier_id = str(uuid.uuid4())
        supplier_data['id'] = supplier_id

        self.suppliers.insert(supplier_data)
        return {"message": "Supplier added successfully", "id": supplier_id}

    def update_supplier(self, supplier_id, new_data):
        supplier = Query()
        self.suppliers.update(new_data, supplier.id == supplier_id)

    def delete_supplier(self, supplier_id):
        supplier = Query()
        self.suppliers.remove(supplier.id == supplier_id)

    def find_supplier_by_name(self, name):
        supplier = Query()
        return self.suppliers.get(supplier.name == name)

    def search_suppliers(self, query):
        supplier = Query()
        return self.suppliers.search(supplier.name.search(query))

    def add_category(self, category_name):
        # Generate a UUID for the new category
        category_id = str(uuid.uuid4())
        self.category_table.insert({'id': category_id, 'name': category_name})

    def remove_category(self, category_id):
        categories = Query()
        self.category_table.remove(categories.id == category_id)

    def delete_all_categories(self):
        categories = self.get_all_categories()
        self.category_table.truncate()
        return len(categories)

    def update_category(self, category_id, new_name):
        category = Query()
        self.category_table.update({'name': new_name}, category_id == category)

    # def update_part(self, supplier_id, new_part):
    #     updated_part = Query()
    #     # self.part_table.update(new_part, supplier.id == supplier_id)
    #
    #     existing_part = self.part_table.get(updated_part.part_number == new_part['part_number'])
    #     if existing_part:
    #         self.add_part(new_part, overwrite=True)

    def update_part(self, part_id, part) -> dict:
        PartQuery = Query()
        return_message = {}

        # Initialize variables to determine how to search for the existing part
        search_criteria = None

        # Check if part_id is provided, prioritize it for searching
        if part_id:
            existing_part = self.part_table.get(PartQuery.part_number == part['part_number'])
        # else:
        #     # If part_id is not provided, search by part_number or part_name
        #     if part.part_number:
        #         search_criteria = PartQuery.part_number == part.part_number
        #     elif part.part_name:
        #         search_criteria = PartQuery.part_name == part.part_name
        #     existing_part = self.part_table.get(search_criteria) if search_criteria else None

        if not existing_part:
            return {"error": "Part not found."}

        # Convert the existing part to a dictionary for easier comparison
        existing_part_dict = dict(existing_part)

        # Convert the new part data to a dictionary
        new_part_dict = part

        # Determine the fields that have changed
        updated_fields = {key: value for key, value in new_part_dict.items() if existing_part_dict.get(key) != value}

        # Check if there are any changes
        if not updated_fields:
            return {"message": "No changes detected."}

        # Update the part record with only the changed fields
        self.part_table.update(updated_fields, doc_ids=[existing_part.doc_id])

        return_message = {
            "event": "part_updated",
            "data": updated_fields  # Return only the updated fields
        }
        return_message['data']['document_id'] = existing_part.doc_id

        return return_message

    def get_all_parts_paginated(self, page, page_size):
        # Calculate offset
        offset = (page - 1) * page_size
        # Fetch paginated results
        results = self.part_table.all()[offset:offset + page_size]
        return results

    def get_total_parts_count(self):
        # Return the total number of parts
        return len(self.part_table.all())
