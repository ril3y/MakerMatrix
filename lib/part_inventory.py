from tinydb import TinyDB, Query
from datetime import datetime

import uuid
class PartInventory:
    def __init__(self, db_file):
        self.db = TinyDB(db_file)
        self.part_table = self.db.table('parts')
        self.location_table = self.db.table('locations')

    def get_all_categories(self):
        unique_categories = set()
        for part in self.part_table.all():
            if 'categories' in part:
                unique_categories.update(part['categories'])
        return list(unique_categories)

    def get_all_locations(self):
        # Fetches all documents from the 'locations' table
        return self.location_table.all()

    async def add_part(self, data, overwrite) -> dict:
        PartQuery = Query()
        return_message = {}

        # Check if a part with the same part_number already exists
        existing_part = self.part_table.get(PartQuery.part_number ==  data.part.part_number)

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
                "question_text": f"Existing part found: {data.part.part_number}. Do you want to overwrite this entry for this part?",
                "question_type": "alert",
                "positive_text": "Yes",
                "negative_text": "Nope!"
            }
        else:
            # If part does not exist or overwrite is True, proceed to add or update
            if existing_part:
                # Remove the existing part first
                self.part_table.remove(doc_ids=[existing_part.doc_id])

            # Insert or update the part record
            document_id = self.part_table.insert(data.to_dict(data.part))

            return_message = {
                "event": "part_added",
                "data": data.to_dict(data.part)
            }
            return_message['data']['document_id'] = document_id

        return return_message

    def clear_all_parts(self):
        self.part_table.truncate()

    def get_all_parts(self):
        # Retrieve all parts from the database
        return self.part_table.all()

    def search_parts(self, query):
        Part = Query()
        return self.part_table.search(Part.part_number.search(query))

    def get_suggestions(self, query):
        Part = Query()
        # Search for part numbers that start with the given query
        matching_parts = self.part_table.search(Part.part_number.search('^' + query))
        # Extract part numbers from the results
        suggestions = [part['part_number'] for part in matching_parts]
        return suggestions

    def get_part_by_part_number(self, part_number):
        # Retrieve a part by its manufacturer_pn
        Part = Query()
        return self.part_table.get(Part.part_number == part_number)

    def delete_part_by_manufacturer_pn(self, manufacturer_pn):
        # Delete a part by its manufacturer_pn
        Part = Query()
        self.part_table.remove(Part.manufacturer_pn == manufacturer_pn)

    def _find_by_manufacturer_pn(self, manufacturer_pn):
        Part = Query()
        return self.part_table.get(Part.manufacturer_pn == manufacturer_pn)

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
    def add_location(self, location_data):
        name = location_data['name']
        description = location_data['description']
        parent_id = location_data.get('parent_id')

        if parent_id is not None and not isinstance(parent_id, str):
            raise ValueError("parent_id must be a string or None")

        # Check if a location with the same name already exists
        Location = Query()
        existing_location = self.location_table.get(Location.name == name)
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
            parent_location = self.location_table.get(Location.id == parent_id)
            if parent_location:
                parent_location['children'].append(location_id)
                self.location_table.update({'children': parent_location['children']}, Location.id == parent_id)

        self.location_table.insert(new_location)
        return {"message": "Location added successfully"}

    def update_location(self, location_id, new_data):
        # Update a location
        self.location_table.update(new_data, doc_ids=[location_id])

    def get_location(self, location_id):
        # Retrieve a location by its ID
        return self.location_table.get(doc_id=location_id)

    def delete_location(self, location_id):
        # Delete a location
        self.location_table.remove(doc_ids=[location_id])