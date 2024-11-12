import logging
from typing import List, Optional, Any, Dict, Coroutine

from sqlalchemy import select
from sqlmodel import Session
from typing import Optional, TYPE_CHECKING

from MakerMatrix.models.category_model import CategoryModel
from MakerMatrix.repositories.parts_repositories import PartRepository, handle_categories
from MakerMatrix.models.models import PartModel, UpdateQuantityRequest, GenericPartQuery
from MakerMatrix.models.models import engine  # Import the engine from db.py
from MakerMatrix.database.db import get_session

if TYPE_CHECKING:
    from MakerMatrix.models.models import PartModel  # Only imports for type checking, avoiding circular import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartService:
    # Initialize a part repository instance
    part_repo = PartRepository(engine)
    session = get_session()

    @staticmethod
    def add_part(part_data: Dict[str, Any], category_names: List[str]) -> Dict[str, Any]:

        part_data['categories'] = []  # Initialize an empty list for categories
        try:
            session = get_session()
            # Check if the part already exists by its part number
            part_exists = session.exec(
                select(PartModel).where(PartModel.part_number == part_data["part_number"])
            ).first()

            if part_exists:
                return {"status": "part exists", "message": "Part already exists", "data": part_exists[0].to_dict()}

            # Add new part to the database
            new_part = PartModel(**part_data)

            # Handle categories for the new part
            new_part.categories.extend(handle_categories(session, category_names))

            session.add(new_part)
            session.commit()
            session.refresh(new_part)
            return {"status": "added", "data": new_part}

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to add part {part_data}: {e}")

    @staticmethod
    def is_part_name_unique(part_name: str) -> bool:
        return PartService.part_repo.is_part_name_unique(part_name)

    from sqlmodel import select, Session
    from MakerMatrix.models.models import PartModel
    from MakerMatrix.database.db import get_session

    @staticmethod
    def get_part_by_id(part_id: str) -> Dict[str, Any]:
        try:
            # Use the get_session function to get a session
            session = get_session()

            # Fetch part using the repository layer
            part = PartRepository.get_part_by_id(session, part_id)

            if part:
                return {
                    "status": "found",
                    "message": "Part retrieved successfully",
                    "data": part.dict(),
                }

            # If part not found, raise a value error
            raise ValueError(f"Part ID {part_id} not found")

        except Exception as e:
            raise ValueError(f"Failed to get part by ID {part_id}: {e}")

    # @staticmethod
    # def update_part(part_model: PartModel) -> dict:
    #     part_id = part_model.part_id
    #     part_name = part_model.part_name
    #     part_number = part_model.part_number
    #
    #     existing_part = PartService.get_part_by_details(part_id, part_number, part_name)
    #
    #     if not existing_part:
    #         return {"status": "error", "message": "Part not found"}
    #
    #     # Prepare update data: We can update fields directly on the model
    #     if part_model.additional_properties:
    #         # Merge additional_properties with existing ones if necessary
    #         existing_properties = existing_part.get('additional_properties', {})
    #         updated_properties = {**existing_properties, **part_model.additional_properties}
    #         part_model.additional_properties = {k: v for k, v in updated_properties.items() if v}
    #
    #     # Pass the entire model to the repository
    #     return PartService.part_repo.update_part(part_model)

    # def get_part_by_details(part_id: Optional[str] = None, part_number: Optional[str] = None,
    #                         part_name: Optional[str] = None) -> Optional[dict]:
    #     # Determine which parameter is provided and call the appropriate repo method
    #     if part_id:
    #         return PartService.part_repo.get_part_by_id(part_id)
    #     elif part_number:
    #         return PartService.part_repo.get_part_by_part_number(part_number)
    #     elif part_name:
    #         return PartService.part_repo.get_part_by_part_name(part_name)
    #     else:
    #         raise ValueError("At least one of part_id, part_number, or part_name must be provided.")

    # @staticmethod
    # def update_quantity_service(new_quantity: int,
    #                             manufacturer_pn: str = None,
    #                             part_number: str = None,
    #                             part_id: str = None) -> bool:
    #     """
    #     Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
    #     Returns True if the update was successful, False if the part was not found.
    #     """
    #     try:
    #         # Attempt to find the part using the provided identifiers
    #         part = None
    #         _generic_part = GenericPartQuery(part_id=part_id, part_number=part_number, manufacturer_pn=manufacturer_pn)
    #         part, _ = PartService.get_generic_part(_generic_part)
    #
    #         if not part:
    #             logger.error("Part not found using provided details.")
    #             return False
    #
    #         PartService.part_repo.update_quantity(part["part_id"], new_quantity)
    #         logger.info(
    #             f"Updated quantity for part {part.get('part_number', part.get('manufacturer_pn'))} to {new_quantity}.")
    #         return True
    #
    #     except Exception as e:
    #         logger.error(f"Failed to update quantity: {e}")
    #         raise
    #
    # @staticmethod
    # def decrement_count_service(generic_part_query: GenericPartQuery) -> tuple[PartModel | None, Any, Any] | None:
    #     try:
    #         part, part_field = PartService.get_generic_part(generic_part_query)
    #         previous_quantity = part.get('quantity')
    #         if part:
    #             part = PartService.part_repo.decrement_count_repo(part['part_id'])
    #             logger.info(f"Decremented count for {part.get('part_id', part.get("part_id"))}.")
    #             return part, part_field, previous_quantity
    #         else:
    #             logger.error(f"Part not found using provided details.")
    #         return None
    #
    #     except Exception as e:
    #         logger.error(f"Failed to decrement count for {part}: {e}")
    #         return None
    #
    # @staticmethod
    # def get_all_parts() -> List[PartModel]:
    #     try:
    #         return PartService.part_repo.get_all_parts()
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve all parts: {e}")
    #         return []
    #
    # @staticmethod
    # def get_all_parts_paginated(page: int, page_size: int) -> tuple[Any, Any] | list[Any]:
    #     try:
    #         results = PartService.part_repo.get_all_parts_paginated(page=page, page_size=page_size)
    #         return results
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve paginated parts: {e}")
    #         return []
    #
    # @staticmethod
    # def get_total_parts_count() -> int:
    #     try:
    #         return PartService.part_repo.get_total_parts_count()
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve total parts count: {e}")
    #         return 0
    #
    # @staticmethod
    # def get_part_by_id(part_id: str) -> Coroutine[Any, Any, PartModel | None] | None:
    #     try:
    #         return PartService.part_repo.get_part_by_id(part_id)
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve part by ID {part_id}: {e}")
    #         return None
    #
    # @staticmethod

    #
    # @staticmethod
    # def get_part_by_pn(pn: str) -> Optional[PartModel]:
    #     try:
    #         return PartService.part_repo.get_part_by_part_number(pn)
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve part by part number {pn}: {e}")
    #         return None
    #
    # @staticmethod
    # def get_parts_paginated(page: int, page_size: int) -> Dict[str, Any]:
    #     try:
    #         parts = PartService.part_repo.get_all_parts_paginated(page=page, page_size=page_size)
    #         total_count = PartService.part_repo.get_total_parts_count()
    #         return {"parts": parts, "page": page, "page_size": page_size, "total": total_count}
    #     except Exception as e:
    #         print(f"Failed to retrieve paginated parts: {e}")
    #         return {"error": str(e)}
    #
    # @staticmethod
    # def add_part(part: PartModel, overwrite: bool = False) -> dict | None:
    #     try:
    #         return PartService.part_repo.add_part(part.dict(), overwrite=overwrite)
    #     except Exception as e:
    #         logger.error(f"Failed to add part {part}: {e}")
    #         return None
    #
    # @staticmethod
    # def delete_part(part_id: str) -> Any | None:
    #     part_exists = PartService.get_part_by_id(part_id)
    #     if not part_exists:
    #         return None
    #     return PartService.part_repo.delete_part(part_id)
    #
    # @staticmethod
    # def dynamic_search(search_term: str):
    #     try:
    #         return PartService.part_repo.dynamic_search(search_term)
    #     except Exception as e:
    #         print(f"Error performing dynamic search: {e}")
    #         return {"error": "An error occurred while searching."}
    #
    # @staticmethod
    # def clear_all_parts():
    #     return PartService.part_repo.clear_all_parts()
    #
    # @staticmethod
    # def get_parts_by_location_id(location_id: str, recursive=False) -> List[Dict]:
    #     return PartService.part_repo.get_parts_by_location_id(location_id, recursive)
    #
    # @staticmethod
    # def preview_delete_location(location_id: str) -> Dict:
    #     # Get all parts affected under this location
    #     parts = PartService.part_repo.get_parts_by_location_id(location_id, recursive=True)
    #     affected_parts_count = len(parts)
    #
    #     # Get all child locations under this location
    #     from MakerMatrix.repositories.location_repositories import LocationRepository
    #     location_repo = LocationRepository()
    #     child_locations = location_repo.get_child_locations(location_id)
    #     affected_children_count = len(child_locations)
    #
    #     return {
    #         "location_id": location_id,
    #         "affected_parts_count": affected_parts_count,
    #         "affected_children_count": affected_children_count,
    #         "parts": parts,
    #         "children": child_locations
    #     }
    #

    #
