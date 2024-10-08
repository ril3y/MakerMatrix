import logging
import os

from tinydb import TinyDB, Query
from tinydb.table import Document

from lib.part_inventory import PartInventory
from models.part_model import PartModel, GenericPartQuery
from typing import List, Optional, Tuple, Any, Dict, Coroutine

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
    async def get_part_by_details(part_details: str) -> Optional[PartModel]:
        try:
            return await PartService.part_repo.get_part_by_details(part_details)
        except Exception as e:
            logger.error(f"Failed to retrieve part by ID {part_details}: {e}")
            return None

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
    def dynamic_search(criteria: dict):
        return PartService.part_repo.dynamic_search(criteria)

    @staticmethod
    def clear_all_parts():
        return PartService.part_repo.clear_all_parts()
