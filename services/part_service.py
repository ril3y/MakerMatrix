import logging
from typing import List, Optional, Any, Dict, Coroutine

from tinydb import Query

from lib.part_inventory import PartInventory
from models.location_model import LocationQueryModel
from models.part_model import PartModel, GenericPartQuery
from repositories.parts_repositories import PartRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartService:
    # db = PartInventory('part_inventory.json')
    part_repo = PartRepository()

    # return PartInventory.part_table.get(PartInventory.query.part_id == part_id)

    def _find_by_manufacturer_pn(self, manufacturer_pn):
        query = Query()
        # part = PartInventory.query_part_table(query.manufacturer_pn == manufacturer_pn)
        return PartInventory.part_table.get(PartInventory.query.manufacturer_pn == manufacturer_pn)

    @staticmethod
    def get_generic_part(generic_part: GenericPartQuery) -> tuple[None, str] | tuple[PartModel, str]:
        part_field = ""
        try:
            # Attempt to find the part using the provided identifiers
            part = None
            if generic_part.part_id:
                part = PartService.part_repo.get_part_by_id(generic_part.part_id)
                part_field = 'part_id'
            elif generic_part.part_number:
                part_field = 'part_number'
                part = PartService.part_repo.get_part_by_part_number(generic_part.part_number)
            elif generic_part.manufacturer_pn:
                part_field = 'manufacturer_pn'
                part = PartService.part_repo.get_part_by_manufacturer_pn(generic_part.manufacturer_pn)

            if not part:
                logger.error("Part not found using provided details.")
                return None, part_field

            return part, part_field

        except Exception as e:
            logger.error(f"Failed to update quantity: {e}")
            raise

    @staticmethod
    def update_quantity_service(new_quantity: int,
                                manufacturer_pn: str = None,
                                part_number: str = None,
                                part_id: str = None) -> bool:
        """
        Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
        Returns True if the update was successful, False if the part was not found.
        """
        try:
            # Attempt to find the part using the provided identifiers
            part = None
            _generic_part = GenericPartQuery(part_id=part_id, part_number=part_number, manufacturer_pn=manufacturer_pn)
            part, _ = PartService.get_generic_part(_generic_part)

            if not part:
                logger.error("Part not found using provided details.")
                return False

            PartService.part_repo.update_quantity(part["part_id"], new_quantity)
            logger.info(
                f"Updated quantity for part {part.get('part_number', part.get('manufacturer_pn'))} to {new_quantity}.")
            return True

        except Exception as e:
            logger.error(f"Failed to update quantity: {e}")
            raise

    @staticmethod
    def decrement_count_service(generic_part_query: GenericPartQuery) -> tuple[PartModel | None, Any, Any] | None:
        try:
            part, part_field = PartService.get_generic_part(generic_part_query)
            previous_quantity = part.get('quantity')
            if part:
                part = PartService.part_repo.decrement_count_repo(part['part_id'])
                logger.info(f"Decremented count for {part.get('part_id', part.get("part_id"))}.")
                return part, part_field, previous_quantity
            else:
                logger.error(f"Part not found using provided details.")
            return None

        except Exception as e:
            logger.error(f"Failed to decrement count for {part}: {e}")
            return None

    @staticmethod
    def get_all_parts() -> List[PartModel]:
        try:
            return PartService.part_repo.get_all_parts()
        except Exception as e:
            logger.error(f"Failed to retrieve all parts: {e}")
            return []

    @staticmethod
    def get_all_parts_paginated(page: int, page_size: int) -> tuple[Any, Any] | list[Any]:
        try:
            results = PartService.part_repo.get_all_parts_paginated(page=page, page_size=page_size)
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve paginated parts: {e}")
            return []

    @staticmethod
    def get_total_parts_count() -> int:
        try:
            return PartService.part_repo.get_total_parts_count()
        except Exception as e:
            logger.error(f"Failed to retrieve total parts count: {e}")
            return 0

    @staticmethod
    def get_part_by_id(part_id: str) -> Coroutine[Any, Any, PartModel | None] | None:
        try:
            return PartService.part_repo.get_part_by_id(part_id)
        except Exception as e:
            logger.error(f"Failed to retrieve part by ID {part_id}: {e}")
            return None

    @staticmethod
    def get_part_by_details(part_id: Optional[str] = None, part_number: Optional[str] = None,
                            part_name: Optional[str] = None) -> Optional[dict]:
        # Determine which parameter is provided and call the appropriate repo method
        if part_id:
            return PartService.part_repo.get_part_by_id(part_id)
        elif part_number:
            return PartService.part_repo.get_part_by_part_number(part_number)
        elif part_name:
            return PartService.part_repo.get_part_by_part_name(part_name)
        else:
            raise ValueError("At least one of part_id, part_number, or part_name must be provided.")

    @staticmethod
    def get_part_by_pn(pn: str) -> Optional[PartModel]:
        try:
            return PartService.part_repo.get_part_by_part_number(pn)
        except Exception as e:
            logger.error(f"Failed to retrieve part by part number {pn}: {e}")
            return None

    @staticmethod
    def get_parts_paginated(page: int, page_size: int) -> Dict[str, Any]:
        try:
            parts = PartService.part_repo.get_all_parts_paginated(page=page, page_size=page_size)
            total_count = PartService.part_repo.get_total_parts_count()
            return {"parts": parts, "page": page, "page_size": page_size, "total": total_count}
        except Exception as e:
            print(f"Failed to retrieve paginated parts: {e}")
            return {"error": str(e)}

    @staticmethod
    def add_part(part: PartModel, overwrite: bool = False) -> dict | None:
        try:
            return PartService.part_repo.add_part(part.dict(), overwrite=overwrite)
        except Exception as e:
            logger.error(f"Failed to add part {part}: {e}")
            return None

    @staticmethod
    def delete_part(part_id: str) -> Any | None:
        part_exists = PartService.get_part_by_id(part_id)
        if not part_exists:
            return None
        return PartService.part_repo.delete_part(part_id)

    @staticmethod
    def dynamic_search(search_term: str):
        try:
            return PartService.part_repo.dynamic_search(search_term)
        except Exception as e:
            print(f"Error performing dynamic search: {e}")
            return {"error": "An error occurred while searching."}

    @staticmethod
    def clear_all_parts():
        return PartService.part_repo.clear_all_parts()

    @staticmethod
    def get_parts_by_location_id(location_id: str, recursive=False) -> List[Dict]:
        return PartService.part_repo.get_parts_by_location_id(location_id, recursive)

    @staticmethod
    def preview_delete_location(location_id: str) -> Dict:
        # Get all parts affected under this location
        parts = PartService.part_repo.get_parts_by_location_id(location_id, recursive=True)
        affected_parts_count = len(parts)

        # Get all child locations under this location
        from repositories.location_repositories import LocationRepository
        location_repo = LocationRepository()
        child_locations = location_repo.get_child_locations(location_id)
        affected_children_count = len(child_locations)

        return {
            "location_id": location_id,
            "affected_parts_count": affected_parts_count,
            "affected_children_count": affected_children_count,
            "parts": parts,
            "children": child_locations
        }

    @staticmethod
    def update_part(part_model: PartModel) -> dict:
        part_id = part_model.part_id
        part_name = part_model.part_name
        part_number = part_model.part_number

        existing_part = PartService.get_part_by_details(part_id, part_number, part_name)

        if not existing_part:
            return {"status": "error", "message": "Part not found"}

        # Prepare update data: We can update fields directly on the model
        if part_model.additional_properties:
            # Merge additional_properties with existing ones if necessary
            existing_properties = existing_part.get('additional_properties', {})
            updated_properties = {**existing_properties, **part_model.additional_properties}
            part_model.additional_properties = {k: v for k, v in updated_properties.items() if v}

        # Pass the entire model to the repository
        return PartService.part_repo.update_part(part_model)

    @staticmethod
    def is_part_name_unique(part_name: str) -> bool:
        return PartService.part_repo.is_part_name_unique(part_name)
