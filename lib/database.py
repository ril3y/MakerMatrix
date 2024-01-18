from lib.part_inventory import PartInventory
from threading import Lock


class DatabaseManager:
    _instance = None
    _lock = Lock()

    @classmethod
    def get_instance(cls, db_file=None):
        with cls._lock:
            if cls._instance is None:
                if db_file is None:
                    raise ValueError("Database file must be specified for the first instance creation.")
                cls._instance = cls(db_file)
            elif db_file is not None and db_file != cls._instance.db_file:
                raise ValueError("A different database file cannot be used for the existing singleton instance.")
        return cls._instance

    def __init__(self, db_file):
        if DatabaseManager._instance is not None:
            raise Exception("This class is a singleton! Use 'get_instance()' to get its instance.")
        self.db_file = db_file
        self.db = PartInventory(db_file)

    async def add_part(self, data, overwrite=False):
        return await self.db.add_part(data, overwrite)

    async def update_quantity(self, manufacturer_pn, new_quantity):
        self.db.update_quantity(manufacturer_pn, new_quantity)

    async def decrement_count(self, manufacturer_pn, by):
        self.db.decrement_count(manufacturer_pn, by)

    async def clear_all_parts(self):
        self.db.clear_all_parts()

    async def get_all_parts(self):
        return self.db.get_all_parts()

    async def get_part_by_part_number(self, part_number):
        return self.db.get_part_by_part_number(part_number)

    async def search_parts(self, query):
        return self.db.search_parts(query)

    async def get_suggestions(self, query):
        return self.db.get_suggestions(query)

    async def get_all_categories(self):
        return self.db.get_all_categories()

    def get_all_locations(self):
        # Assuming that locations are stored in a table called 'locations'
        return self.db.get_all_locations()

    async def add_location(self, location):
        return self.db.add_location(location)

    async def add_category(self, category_name):
        return self.part_inventory.add_category(category_name)

    async def remove_category(self, category_id):
        return self.part_inventory.remove_category(category_id)

    async def update_category(self, category_id, new_name):
        return self.part_inventory.update_category(category_id, new_name)
