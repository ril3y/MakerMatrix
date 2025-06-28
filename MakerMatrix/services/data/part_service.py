import logging
from http.client import HTTPException
from typing import List, Optional, Any, Dict

from pydantic import ValidationError
from sqlalchemy import select
from sqlmodel import Session
from typing import Optional, TYPE_CHECKING

from MakerMatrix.models.models import CategoryModel, LocationQueryModel, AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError, PartAlreadyExistsError
from MakerMatrix.repositories.parts_repositories import PartRepository, handle_categories
from MakerMatrix.models.models import PartModel
from MakerMatrix.models.models import engine  # Import the engine from db.py
from MakerMatrix.database.db import get_session
from MakerMatrix.schemas.part_create import PartUpdate
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.services.data.location_service import LocationService

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
    def _load_order_relationships(session: Session, part: 'PartModel') -> 'PartModel':
        """
        Load order relationships for a part (order_items and order_summary).
        This centralizes the order loading logic in one place.
        
        TODO: Re-enable order relationship loading once OrderItemModel import is fixed
        """
        # Location relationships should already be loaded by repository joinedload
        # No additional loading needed for now
        
        # Temporarily disabled order relationship loading to fix immediate issue
        # The order relationships are already loaded in the repository methods
        return part


    #####
    @staticmethod
    def get_part_by_details(
            part_id: Optional[str] = None,
            part_number: Optional[str] = None,
            part_name: Optional[str] = None
    ) -> Optional[dict]:
        """
        Determine which parameter is provided and call the appropriate repository method.
        Returns the part as a dict, or None if not found.
        """
        session = next(get_session())
        try:
            found_part = None
            if part_id:
                found_part = PartService.part_repo.get_part_by_id(session, part_id)
            elif part_number:
                found_part = PartService.part_repo.get_part_by_part_number(session, part_number)
            elif part_name:
                found_part = PartService.part_repo.get_part_by_name(session, part_name)
            else:
                raise ValueError("At least one of part_id, part_number, or part_name must be provided.")

            if found_part:
                # Load order relationships
                found_part = PartService._load_order_relationships(session, found_part)
                return found_part.to_dict()
            return None

        except Exception as e:
            logger.error(f"Failed to get part by details: {e}")
            return None


    @staticmethod
    def update_quantity_service(
            new_quantity: int,
            manufacturer_pn: Optional[str] = None,
            part_number: Optional[str] = None,
            part_id: Optional[str] = None
    ) -> bool:
        """
        Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
        Returns True if the update was successful, False otherwise.
        """
        session = next(get_session())
        try:
            logger.info(f"Attempting to update quantity to {new_quantity} for part (ID: {part_id}, PN: {part_number}, MPN: {manufacturer_pn})")
            
            # Attempt to find the part using the provided identifier
            found_part = None
            identifier_type = None
            identifier_value = None
            
            if part_id:
                found_part = PartService.part_repo.get_part_by_id(session, part_id)
                identifier_type = "ID"
                identifier_value = part_id
            elif part_number:
                found_part = PartService.part_repo.get_part_by_part_number(session, part_number)
                identifier_type = "part number"
                identifier_value = part_number
            elif manufacturer_pn:
                # Example method if it exists in your repository:
                found_part = PartService.part_repo.get_part_by_manufacturer_pn(session, manufacturer_pn)
                identifier_type = "manufacturer part number"
                identifier_value = manufacturer_pn
            else:
                logger.error("Quantity update failed: At least one of part_id, part_number, or manufacturer_pn must be provided")
                raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")

            if not found_part:
                logger.error(f"Quantity update failed: Part not found using {identifier_type} '{identifier_value}'")
                return False

            # Log old quantity before update
            old_quantity = found_part.quantity
            logger.info(f"Updating quantity for part '{found_part.part_name}' (ID: {found_part.id}): {old_quantity} → {new_quantity}")

            # Update the quantity using a hypothetical repo method
            PartService.part_repo.update_quantity(session, found_part.id, new_quantity)
            logger.info(f"Successfully updated quantity for part '{found_part.part_name}' to {new_quantity}")
            return True

        except Exception as e:
            logger.error(f"Failed to update quantity: {e}")
            raise

    @staticmethod
    def delete_part(part_id: str) -> Dict[str, Any]:
        """
        Delete a part by its ID using the repository.
        Returns a structured response dictionary with deleted part info.
        """
        session = next(get_session())
        try:
            logger.info(f"Attempting to delete part: {part_id}")
            
            # Ensure the part exists before deletion
            part = PartService.part_repo.get_part_by_id(session, part_id)

            if not part:
                logger.error(f"Part deletion failed: Part with ID '{part_id}' not found")
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Part with ID '{part_id}' not found.",
                    data=None
                )

            # Log part details before deletion
            part_name = part.part_name
            part_categories = [getattr(cat, 'name', str(cat)) for cat in part.categories] if part.categories else []
            logger.info(f"Deleting part: '{part_name}' (ID: {part_id}) with categories: {part_categories}")

            # Perform deletion
            deleted_part = PartService.part_repo.delete_part(session, part_id)

            logger.info(f"Successfully deleted part: '{part_name}' (ID: {part_id})")
            return {
                "status": "success",
                "message": f"Part with ID '{part_id}' was deleted.",
                "data": deleted_part.model_dump()
            }

        except ResourceNotFoundError as rnfe:
            raise rnfe  # Propagate known error

        except ValueError as ve:
            # Handle user-friendly constraint errors from repository
            logger.error(f"Part deletion constraint error: {ve}")
            raise ve  # Propagate the user-friendly error message

        except Exception as e:
            logger.error(f"Failed to delete part {part_id}: {e}")
            raise ValueError(f"Failed to delete part {part_id}: {str(e)}")

    @staticmethod
    def dynamic_search(search_term: str) -> Any:
        """
        Perform a dynamic search on parts using part_repo.
        """
        session = next(get_session())
        try:
            return PartService.part_repo.dynamic_search(session, search_term)
        except Exception as e:
            logger.error(f"Error performing dynamic search: {e}")
            raise RuntimeError("An error occurred while searching.")

    @staticmethod
    def clear_all_parts() -> Any:
        """
        Clear all parts from the database using the part_repo.
        """
        session = next(get_session())
        try:
            result = PartService.part_repo.clear_all_parts(session)
            logger.info(f"Clear all parts result: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to clear all parts: {e}")
            raise e
        finally:
            session.close()


    #####

    @staticmethod
    def add_part(part_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new part to the database after ensuring that if a location is provided,
        it exists. Categories are created/retrieved before creating the part.
        """
        session = next(get_session())
        try:
            part_name = part_data.get("part_name")
            logger.info(f"Attempting to create new part: {part_name}")
            
            # Validate required fields
            if not part_name:
                logger.error("Part creation failed: Part name is required")
                raise ValueError("Part name is required")

            # Check if the part already exists by its name
            try:
                part_exists = PartRepository.get_part_by_name(session, part_name)
                # If we get here, the part exists
                logger.warning(f"Part creation failed: Part with name '{part_name}' already exists")
                raise PartAlreadyExistsError(
                    status="error",
                    message=f"Part with name '{part_name}' already exists",
                    data=part_exists.model_dump()
                )
            except ResourceNotFoundError:
                # Part doesn't exist, which is what we want for creating a new part
                logger.debug(f"Part name validation passed: '{part_name}' is unique")
                pass

            # Clean up location_id - convert empty string to None
            location_id = part_data.get("location_id")
            if location_id == "":
                part_data["location_id"] = None
                location_id = None
            
            # Set default "Unsorted" location if no location specified
            if location_id is None:
                try:
                    from MakerMatrix.services.data.location_service import LocationService
                    unsorted_location = LocationService.get_or_create_unsorted_location()
                    part_data["location_id"] = unsorted_location.id
                    location_id = unsorted_location.id
                    logger.debug(f"Assigned part '{part_name}' to 'Unsorted' location (ID: {location_id})")
                except Exception as e:
                    logger.warning(f"Could not assign default 'Unsorted' location to part '{part_name}': {e}")
                    # Continue without location - don't fail part creation
            
            # Verify that the location exists, but only if a location_id is provided
            if location_id:
                logger.debug(f"Validating location_id: {location_id}")
                location = LocationService.get_location(LocationQueryModel(id=location_id))
                if not location:
                    logger.error(f"Part creation failed: Location with id '{location_id}' does not exist")
                    raise ResourceNotFoundError(
                        status="error",
                        message=f"Location with id '{location_id}' does not exist.",
                        data=None
                    )
                logger.debug(f"Location validation successful for part '{part_name}'")

            try:
                # Handle categories first
                category_names = part_data.pop("category_names", [])
                categories = []

                if category_names:
                    logger.debug(f"Processing {len(category_names)} categories for part '{part_name}': {category_names}")
                    # Use the handle_categories function from the repository
                    from MakerMatrix.repositories.parts_repositories import handle_categories
                    categories = handle_categories(session, category_names)
                    
                    category_names_for_log = [cat.name for cat in categories if hasattr(cat, 'name')]
                    logger.info(f"Assigned {len(categories)} categories to part '{part_name}': {category_names_for_log}")

                # Extract datasheets data before creating the part
                datasheets_data = part_data.pop("datasheets", [])
                if datasheets_data:
                    logger.debug(f"Processing {len(datasheets_data)} datasheets for part '{part_name}'")
                
                # Filter out only valid PartModel fields
                valid_part_fields = {
                    'part_number', 'part_name', 'description', 'quantity', 
                    'supplier', 'location_id', 'image_url', 'additional_properties',
                    # Pricing fields
                    'unit_price', 'currency', 'pricing_data',
                    # Enhanced fields from PartModel
                    'manufacturer', 'manufacturer_part_number', 'component_type', 
                    'package', 'mounting_type', 'rohs_status', 'lifecycle_status',
                    'last_price_update', 'price_source', 'stock_quantity', 
                    'last_stock_update', 'last_enrichment_date', 'enrichment_source',
                    'data_quality_score'
                }
                
                # Create part data dict with only valid fields
                filtered_part_data = {}
                for key, value in part_data.items():
                    if key in valid_part_fields:
                        # Convert empty strings to None for optional fields
                        if value == "" and key in ['location_id', 'image_url', 'description', 'part_number', 'supplier', 
                                                  'manufacturer', 'manufacturer_part_number', 'component_type', 
                                                  'package', 'mounting_type', 'rohs_status', 'lifecycle_status',
                                                  'price_source', 'enrichment_source']:
                            filtered_part_data[key] = None
                        # Handle additional_properties - convert None/undefined to empty dict
                        elif key == 'additional_properties' and value is None:
                            filtered_part_data[key] = {}
                        # Handle pricing_data - convert None/undefined to None (optional dict field)
                        elif key == 'pricing_data' and value is None:
                            filtered_part_data[key] = None
                        # Handle currency field - set default to USD if not provided
                        elif key == 'currency' and (value is None or value == ""):
                            filtered_part_data[key] = "USD"
                        else:
                            filtered_part_data[key] = value
                
                # Create the part without categories first
                logger.debug(f"Creating PartModel with data: {filtered_part_data}")
                new_part = PartModel(**filtered_part_data)

                # Add the part to session and flush to get ID
                session.add(new_part)
                session.flush()  # Get the ID without committing
                
                # Now assign categories after the part has an ID
                if categories:
                    logger.debug(f"Assigning {len(categories)} categories to part")
                    new_part.categories = categories
                    session.flush()  # Flush category relationships
                
                # Commit everything
                session.commit()
                
                # Refresh to get all relationships loaded
                session.refresh(new_part, ['categories', 'location'])
                part_obj = new_part
                
                # Create datasheet records if any
                if datasheets_data:
                    from MakerMatrix.models.models import DatasheetModel
                    for datasheet_data in datasheets_data:
                        datasheet_data['part_id'] = part_obj.id
                        datasheet = DatasheetModel(**datasheet_data)
                        session.add(datasheet)
                    
                    session.commit()  # Commit datasheets
                    session.refresh(part_obj)  # Refresh to get updated datasheets
                    logger.info(f"Added {len(datasheets_data)} datasheets to part '{part_name}'")
                
                logger.info(f"Successfully created part: {part_name} (ID: {part_obj.id}) with {len(categories)} categories")
                
                # Create a safe dict without accessing potentially unloaded relationships
                safe_part_dict = {
                    "id": part_obj.id,
                    "part_name": part_obj.part_name,
                    "part_number": part_obj.part_number,
                    "description": part_obj.description,
                    "quantity": part_obj.quantity,
                    "supplier": part_obj.supplier,
                    "location_id": part_obj.location_id,
                    "image_url": part_obj.image_url,
                    "categories": [{"id": cat.id, "name": cat.name} for cat in categories] if categories else []
                }
                
                return {
                    "status": "success",
                    "message": "Part added successfully",
                    "data": safe_part_dict
                }
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Raw error creating part '{part_name}': {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Filtered part data was: {filtered_part_data}")
                categories_debug = []
                for cat in categories:
                    try:
                        categories_debug.append(f"Category(name={cat.name})")
                    except:
                        categories_debug.append("Category(invalid)")
                logger.error(f"Categories were: {categories_debug}")
                
                # Clean up SQLAlchemy internal references from error message
                if "_sa_instance_state" in error_msg:
                    error_msg = "Database object creation error - invalid field or data type"
                logger.error(f"Failed to create part '{part_name}': {error_msg}")
                raise ValueError(f"Failed to create part: {error_msg}")

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

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
    def get_part_by_part_number(part_number: str, include: List[str] = None) -> dict[str, str | dict[str, Any]]:
        try:
            identifier = "part number"
            session = next(get_session())
            
            # Fetch part using the repository layer
            part = PartService.part_repo.get_part_by_part_number(session, part_number)
            
            if part:
                # Load order relationships
                part_with_orders = PartService._load_order_relationships(session, part)
                
                return {
                    "status": "success",
                    "message": f"Part with {identifier} '{part_number}' found.",
                    "data": part_with_orders.to_dict(include=include),
                }
            
            raise ResourceNotFoundError(
                status="error",
                message=f"Part with {identifier} '{part_number}' not found.",
                data=None
            )
            
        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_part_by_part_name(part_name: str, include: List[str] = None) -> dict[str, str | dict[str, Any]]:
        """
        Get a part by its part name.

        Args:
            part_name (str): The name of the part to be retrieved.
            include (List[str]): Optional list of additional data to include

        Returns:
            dict[str, str | dict[str, Any]]: A dictionary containing the status, message, and data of the found part.
        """
        try:
            identifier = "part name"
            session = next(get_session())
            
            # Fetch part using the repository layer
            part = PartService.part_repo.get_part_by_name(session, part_name)
            
            if part:
                # Load order relationships
                part_with_orders = PartService._load_order_relationships(session, part)
                
                return {
                    "status": "success",
                    "message": f"Part with {identifier} '{part_name}' found.",
                    "data": part_with_orders.to_dict(include=include),
                }
            
            raise ResourceNotFoundError(
                status="error",
                message=f"Part with {identifier} '{part_name}' not found.",
                data=None
            )
            
        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_part_by_id(part_id: str, include: List[str] = None) -> Dict[str, Any]:
        try:
            # Use the get_session function to get a session
            identifier = "ID"
            session = next(get_session())

            # Fetch part using the repository layer
            part = PartRepository.get_part_by_id(session, part_id)

            if part:
                # Load order relationships
                part_with_orders = PartService._load_order_relationships(session, part)
                
                return {
                    "status": "success",
                    "message": f"Part with {identifier} '{part_id}' found.",
                    "data": part_with_orders.to_dict(include=include),
                }

            raise ResourceNotFoundError(
                status="error",
                message=f"Part with {identifier} '{part_id}' not found.",
                data=None
            )

        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_part_counts() -> Dict[str, int]:
        try:
            session = next(get_session())
            total_parts = PartRepository.get_part_counts(session)

            return {
                "status": "success",
                "message": "Total part count retrieved successfully.",
                "total_parts": total_parts
            }
        except Exception as e:
            raise Exception(f"Error retrieving part counts: {str(e)}")

    @staticmethod
    def get_all_parts(page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        try:
            session = next(get_session())

            # Fetch parts using the repository
            parts = PartRepository.get_all_parts(session=session, page=page, page_size=page_size)
            total_parts = PartRepository.get_part_counts(session)

            return {
                "status": "success",
                "message": f"Retrieved {len(parts)} parts (Page {page}/{(total_parts + page_size - 1) // page_size})." if parts else "No parts found.",
                "data": [part.to_dict() for part in parts],
                "page": page,
                "page_size": page_size,
                "total_parts": total_parts
            }

        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_parts_by_location_id(location_id: str, recursive=False) -> List[Dict]:
        return PartService.part_repo.get_parts_by_location_id(location_id, recursive)

    @staticmethod
    def update_part(part_id: str, part_update: PartUpdate) -> Dict[str, Any]:
        try:
            session = next(get_session())
            logger.info(f"Attempting to update part: {part_id}")
            
            part = PartRepository.get_part_by_id(session, part_id)
            if not part:
                logger.error(f"Part not found for update: {part_id}")
                raise ResourceNotFoundError(resource="Part", resource_id=part_id)
            
            # Ensure categories are properly loaded
            if hasattr(part, 'categories') and part.categories:
                # Force load categories to ensure they're properly populated
                for category in part.categories:
                    # Access category attributes to ensure they're loaded
                    _ = category.name, category.id

            # Log current state before update
            logger.debug(f"Current part state before update: {part.part_name} (ID: {part_id})")

            # Update only the provided fields
            update_data = part_update.model_dump(exclude_unset=True)
            updated_fields = []
            
            for key, value in update_data.items():
                if key == "category_names" and value is not None:
                    # Special handling for categories
                    old_categories = []
                    if part.categories:
                        for cat in part.categories:
                            try:
                                # Safely get category name, ensuring it's a proper CategoryModel
                                if hasattr(cat, 'name') and cat.name:
                                    old_categories.append(cat.name)
                                else:
                                    logger.warning(f"Category object missing name attribute: {cat}")
                            except Exception as e:
                                logger.error(f"Error accessing category data: {e}")
                    
                    categories = handle_categories(session, value)
                    part.categories.clear()  # Clear existing categories
                    part.categories.extend(categories)  # Add new categories
                    
                    # Commit to ensure the relationship is properly saved
                    session.commit()
                    session.refresh(part)
                    
                    new_categories = [cat.name for cat in categories if hasattr(cat, 'name')]
                    logger.info(f"Updated categories for part '{part.part_name}' (ID: {part_id}): {old_categories} → {new_categories}")
                    updated_fields.append(f"categories: {old_categories} → {new_categories}")
                elif hasattr(part, key):
                    try:
                        old_value = getattr(part, key)
                        setattr(part, key, value)
                        
                        # Log specific field updates with meaningful messages
                        if key == "location_id":
                            old_location = old_value
                            new_location = value
                            logger.info(f"Updated location for part '{part.part_name}' (ID: {part_id}): {old_location} → {new_location}")
                            updated_fields.append(f"location: {old_location} → {new_location}")
                        elif key == "quantity":
                            logger.info(f"Updated quantity for part '{part.part_name}' (ID: {part_id}): {old_value} → {value}")
                            updated_fields.append(f"quantity: {old_value} → {value}")
                        # minimum_quantity field doesn't exist in PartModel - removed
                        elif key == "part_name":
                            logger.info(f"Updated part name (ID: {part_id}): '{old_value}' → '{value}'")
                            updated_fields.append(f"name: '{old_value}' → '{value}'")
                        elif key == "supplier":
                            logger.info(f"Updated supplier for part '{part.part_name}' (ID: {part_id}): '{old_value}' → '{value}'")
                            updated_fields.append(f"supplier: '{old_value}' → '{value}'")
                        elif key == "description":
                            logger.info(f"Updated description for part '{part.part_name}' (ID: {part_id})")
                            updated_fields.append(f"description updated")
                        else:
                            logger.info(f"Updated {key} for part '{part.part_name}' (ID: {part_id}): {old_value} → {value}")
                            updated_fields.append(f"{key}: {old_value} → {value}")
                            
                    except AttributeError as e:
                        logger.warning(f"Skipping read-only or problematic attribute '{key}' for part {part_id}: {e}")

            # Pass the updated part to the repository for the actual update
            updated_part = PartRepository.update_part(session, part)
            
            if update_data:
                logger.info(f"Successfully updated part '{updated_part.part_name}' (ID: {part_id}). Changes: {', '.join(updated_fields)}")
                return {"status": "success", "message": "Part updated successfully", "data": updated_part.to_dict()}
            else:
                logger.info(f"No updates provided for part '{part.part_name}' (ID: {part_id})")
                return {"status": "success", "message": "No updates provided", "data": updated_part.to_dict()}

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update part {part_id}: {e}")
            session.rollback()
            raise ValueError(f"Failed to update part with ID {part_id}: {e}")

    @staticmethod
    def advanced_search(search_params: AdvancedPartSearch) -> Dict[str, Any]:
        """
        Perform an advanced search on parts with multiple filters and sorting options.
        Returns a dictionary containing the search results and metadata.
        """
        session = next(get_session())
        try:
            results, total_count = PartService.part_repo.advanced_search(session, search_params)
            
            return {
                "status": "success",
                "message": "Search completed successfully",
                "data": {
                    "items": [part.to_dict() for part in results],
                    "total": total_count,
                    "page": search_params.page,
                    "page_size": search_params.page_size,
                    "total_pages": (total_count + search_params.page_size - 1) // search_params.page_size
                }
            }
        except Exception as e:
            logger.error(f"Error performing advanced search: {e}")
            raise RuntimeError(f"An error occurred while searching: {str(e)}")

    @staticmethod
    def search_parts_text(query: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Simple text search across part names, part numbers, and descriptions.
        """
        session = next(get_session())
        try:
            results, total_count = PartService.part_repo.search_parts_text(session, query, page, page_size)
            
            return {
                "status": "success",
                "message": f"Found {total_count} parts matching '{query}'",
                "data": {
                    "items": [part.to_dict() for part in results],
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
        except Exception as e:
            logger.error(f"Error performing text search: {e}")
            raise RuntimeError(f"An error occurred while searching: {str(e)}")

    @staticmethod
    def get_part_suggestions(query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get autocomplete suggestions for part names based on search query.
        """
        session = next(get_session())
        try:
            suggestions = PartService.part_repo.get_part_suggestions(session, query, limit)
            
            return {
                "status": "success",
                "message": f"Found {len(suggestions)} suggestions for '{query}'",
                "data": suggestions
            }
        except Exception as e:
            logger.error(f"Error getting part suggestions: {e}")
            raise RuntimeError(f"An error occurred while getting suggestions: {str(e)}")

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
