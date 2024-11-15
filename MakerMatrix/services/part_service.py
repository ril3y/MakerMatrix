import logging
from typing import List, Optional, Any, Dict, Coroutine

from sqlalchemy import select
from sqlmodel import Session
from typing import Optional, TYPE_CHECKING

from MakerMatrix.models.models import CategoryModel
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.repositories.parts_repositories import PartRepository, handle_categories
from MakerMatrix.models.models import PartModel, UpdateQuantityRequest, GenericPartQuery
from MakerMatrix.models.models import engine  # Import the engine from db.py
from MakerMatrix.database.db import get_session
from MakerMatrix.schemas.part_create import PartUpdate

if TYPE_CHECKING:
    from MakerMatrix.models.models import PartModel  # Only imports for type checking, avoiding circular import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartService:
    # Initialize a part repository instance
    part_repo = PartRepository(engine)
    session = next(get_session())

    @staticmethod
    def add_part(part_data: Dict[str, Any], category_names: List[str]) -> Dict[str, Any]:
        """
        Add a new part to the database.

        Args:
            part_data (Dict[str, Any]): The data of the part to be added.
            category_names (List[str]): The list of category names associated with the part.

        Returns:
            Dict[str, Any]: A dictionary containing the status, message, and data of the added part.

        Raises:
            ValueError: If there is an error while adding the part.
        """
        try:
            session = next(get_session())
            # Check if the part already exists by its part name
            part_exists = PartRepository.get_part_by_name(session, part_data["part_name"])

            if part_exists:
                return {"status": "part exists", "message": "Part already exists", "data": part_exists.to_dict()}

            # Add new part to the database
            new_part = PartModel(**part_data)

            # Handle categories for the new part
            new_part.categories.extend(handle_categories(session, category_names))

            part_dict = PartRepository.add_part(session, new_part)
            # Convert categories to dict representation for the response

            return {
                "status":"added", 
                "message":"Part added successfully", 
                "data": part_dict.to_dict()}

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to add part {part_data}: {e}")

    @staticmethod
    def is_part_name_unique(part_name: str) -> bool:
        """
        Check if the part name is unique.

        Args:
            part_name (str): The name of the part to be checked.

        Returns:
            bool: True if the part name is unique, False otherwise.
        """
        return PartService.part_repo.is_part_name_unique(part_name)

    @staticmethod
    def get_part_by_part_number(part_number: str) -> dict[str, str | dict[str, Any]] | None:
        identifier = "part number"
        session = next(get_session())
        part = PartService.part_repo.get_part_by_part_number(session, part_number)
        if part:
            return {
                "status": "found",
                "message": f"Part with {identifier} '{part_number}' found.",
                "data": part.to_dict(),
            }
        

    @staticmethod
    def get_part_by_part_name(part_name: str) -> dict[str, str | dict[str, Any]] | None:
        """
        Get a part by its part name.

        Args:
            part_name (str): The name of the part to be retrieved.

        Returns:
            dict[str, str | dict[str, Any]] | None: A dictionary containing the status, message, and data of the found part, or None if not found.
        """
        identifier = "part name"
        session = next(get_session())
        part = PartService.part_repo.get_part_by_part_name(session, part_name)
        if part:
            return {
                "status": "found",
                "message": f"Part with {identifier} '{part_name}' found.",
                "data": part.model_dump(),
            }

    @staticmethod
    def get_part_by_id(part_id: str) -> Dict[str, Any]:
        try:
            # Use the get_session function to get a session
            identifier = "ID"
            session = next(get_session())

            # Fetch part using the repository layer
            part = PartRepository.get_part_by_id(session, part_id)

            if part:
                return {
                    "status": "found",
                    "message": f"Part with {identifier} '{part_id}' found.",
                    "data": part.model_dump(),
                }
    
            raise ResourceNotFoundError(
                    status="error",
                    message=f"Part with {identifier} '{part_id}' not found.",
                    data=None
                    )
            
        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def update_part( part_id: str, part_update: PartUpdate) -> Dict[str, Any]:
        try:
            session = next(get_session())
            part = PartRepository.get_part_by_id(session, part_id)
            if not part:
                raise ResourceNotFoundError(resource="Part", resource_id=part_id)

            # Update only the provided fields
            update_data = part_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if key == "category_names":
                    # Special handling for categories
                    categories = handle_categories(session, value)
                    part.categories.clear()  # Clear existing categories
                    part.categories.extend(categories)  # Add new categories
                elif hasattr(part, key):
                    try:
                        setattr(part, key, value)
                    except AttributeError as e:
                        print(f"Skipping read-only or problematic attribute '{key}': {e}")

            # Pass the updated part to the repository for the actual update
            updated_part = PartRepository.update_part(session, part)
            if update_data:
                return {"status": "success", "message": "Part updated successfully", "data": updated_part.to_dict()}
            else:
                # TODO: What should we do if no updates were made?
                # What if we return None
                return {"status": "success", "message": "No updates provided", "data": updated_part}

        except ResourceNotFoundError:
            raise
        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to update part with ID {part_id}: {e}")

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
