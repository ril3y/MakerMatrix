from lib.part_inventory import PartInventory
from typing import Optional


class LocationService:
    db = PartInventory('part_inventory.json')

    @staticmethod
    def get_all_locations():
        return LocationService.db.get_all_locations()

    @staticmethod
    async def get_location(location_id: str):
        return await LocationService.db.get_location(location_id)

    @staticmethod
    async def add_location(location_data: dict):
        return await LocationService.db.add_location(location_data)

    @staticmethod
    async def get_parts_effected_locations(location_id: str):
        return await LocationService.db.get_parts_effected_locations(location_id)

    @staticmethod
    async def edit_location(location_id: str, name: Optional[str] = None, description: Optional[str] = None,
                            parent_id: Optional[int] = None):
        return await LocationService.db.edit_location(location_id, name, description, parent_id)

    @staticmethod
    async def delete_location(location_id: str):
        # Fetch all child locations
        child_locations = await LocationService.db.get_location_hierarchy(location_id)

        # Delete each child location
        for child_location in child_locations:
            await LocationService.db.delete_location(child_location['id'])

        # Delete the specified location
        return await LocationService.db.delete_location(location_id)
