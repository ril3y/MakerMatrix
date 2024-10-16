from tinydb import TinyDB, Query
import os


class BaseRepository:
    def __init__(self, table_name: str):
        db_path = os.getenv('PART_INVENTORY_DB_PATH', 'part_inventory.json')
        self.db = TinyDB(db_path)
        self.table = self.db.table(table_name)

    def query(self):
        return Query()
