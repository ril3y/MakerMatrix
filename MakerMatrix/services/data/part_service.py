import logging
from http.client import HTTPException
from typing import List, Optional, Any, Dict, TYPE_CHECKING

from pydantic import ValidationError
from sqlalchemy import select
from sqlmodel import Session

from MakerMatrix.models.models import CategoryModel, LocationQueryModel, AdvancedPartSearch
from MakerMatrix.exceptions import ResourceNotFoundError, PartAlreadyExistsError
from MakerMatrix.repositories.parts_repositories import PartRepository, handle_categories
from MakerMatrix.models.models import PartModel
from MakerMatrix.models.models import engine  # Import the engine from db.py
from MakerMatrix.database.db import get_session
from MakerMatrix.schemas.part_create import PartUpdate
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.services.base_service import BaseService, ServiceResponse


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartService(BaseService):
    """
    Part service with consolidated session management using BaseService.
    
    This migration eliminates 15+ instances of duplicated session management code
    that was previously repeated throughout this service.
    """
    
    def __init__(self):
        super().__init__()
        self.part_repo = PartRepository(engine)
        self.location_service = LocationService()
        self.entity_name = "Part"

    def _load_order_relationships(self, session: Session, part: 'PartModel') -> 'PartModel':
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
    def get_part_by_details(
            self,
            part_id: Optional[str] = None,
            part_number: Optional[str] = None,
            part_name: Optional[str] = None
    ) -> ServiceResponse[dict]:
        """
        Determine which parameter is provided and call the appropriate repository method.
        
        CONSOLIDATED SESSION MANAGEMENT: This method previously used manual session
        management. Now uses BaseService session context manager for consistency.
        """
        try:
            # Validate input parameters
            if not any([part_id, part_number, part_name]):
                return self.error_response(
                    "At least one of part_id, part_number, or part_name must be provided."
                )
            
            self.log_operation("get", self.entity_name)
            
            with self.get_session() as session:
                found_part = None
                
                if part_id:
                    found_part = self.part_repo.get_part_by_id(session, part_id)
                elif part_number:
                    found_part = self.part_repo.get_part_by_part_number(session, part_number)
                elif part_name:
                    found_part = self.part_repo.get_part_by_name(session, part_name)

                if found_part:
                    # Load order relationships
                    found_part = self._load_order_relationships(session, found_part)
                    return self.success_response(
                        f"{self.entity_name} retrieved successfully",
                        found_part.to_dict()
                    )
                else:
                    return self.error_response(f"{self.entity_name} not found")

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by details")


    def update_quantity_service(
            self,
            new_quantity: int,
            manufacturer_pn: Optional[str] = None,
            part_number: Optional[str] = None,
            part_id: Optional[str] = None
    ) -> ServiceResponse[bool]:
        """
        Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
        
        CONSOLIDATED SESSION MANAGEMENT: Migrated from static method with manual session
        management to BaseService pattern for consistency.
        """
        try:
            self.validate_required_fields({"new_quantity": new_quantity}, ["new_quantity"])
            
            identifier = part_id or part_number or manufacturer_pn
            self.log_operation("update_quantity", self.entity_name, identifier)
            
            with self.get_session() as session:
                # Attempt to find the part using the provided identifier
                found_part = None
                identifier_type = None
                identifier_value = None
                
                if part_id:
                    found_part = self.part_repo.get_part_by_id(session, part_id)
                    identifier_type = "ID"
                    identifier_value = part_id
                elif part_number:
                    found_part = self.part_repo.get_part_by_part_number(session, part_number)
                    identifier_type = "part number"
                    identifier_value = part_number
                elif manufacturer_pn:
                    found_part = self.part_repo.get_part_by_manufacturer_pn(session, manufacturer_pn)
                    identifier_type = "manufacturer part number"
                    identifier_value = manufacturer_pn
                else:
                    return self.error_response("At least one of part_id, part_number, or manufacturer_pn must be provided")

                if not found_part:
                    return self.error_response(f"{self.entity_name} not found using {identifier_type} '{identifier_value}'")

                # Log old quantity before update
                old_quantity = found_part.quantity
                
                # Update the quantity using repository method
                self.part_repo.update_quantity(session, found_part.id, new_quantity)
                
                return self.success_response(
                    f"Quantity updated for part '{found_part.part_name}': {old_quantity} → {new_quantity}",
                    True
                )

        except Exception as e:
            return self.handle_exception(e, f"update quantity for {self.entity_name}")

    def delete_part(self, part_id: str) -> ServiceResponse[Dict[str, Any]]:
        """
        Delete a part by its ID using the repository.
        
        CONSOLIDATED SESSION MANAGEMENT: This method previously included 30+ lines
        of manual session, error handling, and logging. Now uses BaseService patterns.
        """
        try:
            self.log_operation("delete", self.entity_name, part_id)
            
            with self.get_session() as session:
                # Ensure the part exists before deletion
                part = self.part_repo.get_part_by_id(session, part_id)

                if not part:
                    return self.error_response(f"{self.entity_name} with ID '{part_id}' not found")

                # Log part details before deletion
                part_name = part.part_name
                part_categories = [getattr(cat, 'name', str(cat)) for cat in part.categories] if part.categories else []
                self.logger.info(f"Deleting part: '{part_name}' (ID: {part_id}) with categories: {part_categories}")

                # Perform deletion
                deleted_part = self.part_repo.delete_part(session, part_id)

                return self.success_response(
                    f"{self.entity_name} with ID '{part_id}' was deleted successfully",
                    deleted_part.to_dict()
                )

        except Exception as e:
            return self.handle_exception(e, f"delete {self.entity_name}")

    def dynamic_search(self, search_term: str) -> ServiceResponse[Any]:
        """
        Perform a dynamic search on parts using part_repo.
        
        CONSOLIDATED SESSION MANAGEMENT: Eliminates manual session management.
        """
        try:
            self.log_operation("search", self.entity_name)
            
            with self.get_session() as session:
                results = self.part_repo.dynamic_search(session, search_term)
                return self.success_response(
                    f"Search completed for term: {search_term}",
                    results
                )
                
        except Exception as e:
            return self.handle_exception(e, f"search {self.entity_name}")

    def clear_all_parts(self) -> ServiceResponse[Any]:
        """
        Clear all parts from the database using the part_repo.
        
        CONSOLIDATED SESSION MANAGEMENT: Migrated from static method with manual session
        management to BaseService pattern for consistency.
        """
        try:
            self.log_operation("clear_all", self.entity_name, "all_parts")
            
            with self.get_session() as session:
                result = self.part_repo.clear_all_parts(session)
                
                return self.success_response(
                    "All parts cleared successfully",
                    result
                )
                
        except Exception as e:
            return self.handle_exception(e, f"clear all {self.entity_name}s")


    #####

    def add_part(self, part_data: Dict[str, Any]) -> ServiceResponse[Dict[str, Any]]:
        """
        Add a new part to the database after ensuring that if a location is provided,
        it exists. Categories are created/retrieved before creating the part.
        
        CONSOLIDATED SESSION MANAGEMENT: Migrated from static method with manual session
        management to BaseService pattern for consistency.
        """
        try:
            part_name = part_data.get("part_name")
            self.log_operation("add", self.entity_name, part_name)
            
            # Validate required fields
            if not part_name:
                return self.error_response("Part name is required")

            with self.get_session() as session:
                # Check if the part already exists by its name
                try:
                    part_exists = self.part_repo.get_part_by_name(session, part_name)
                    # If we get here, the part exists
                    self.logger.warning(f"Part creation failed: Part with name '{part_name}' already exists")
                    raise PartAlreadyExistsError(f"Part with name '{part_name}' already exists")
                except ResourceNotFoundError:
                    # Part doesn't exist, which is what we want for creating a new part
                    self.logger.debug(f"Part name validation passed: '{part_name}' is unique")
                    pass

                # Clean up location_id - convert empty string to None
                location_id = part_data.get("location_id")
                if location_id == "":
                    part_data["location_id"] = None
                    location_id = None
                
                # Set default "Unsorted" location if no location specified
                if location_id is None:
                    try:
                        unsorted_response = self.location_service.get_or_create_unsorted_location()
                        if unsorted_response.success:
                            unsorted_location = unsorted_response.data
                            part_data["location_id"] = unsorted_location["id"]
                            location_id = unsorted_location["id"]
                            self.logger.debug(f"Assigned part '{part_name}' to 'Unsorted' location (ID: {location_id})")
                        else:
                            self.logger.warning(f"Could not assign default 'Unsorted' location to part '{part_name}': {unsorted_response.message}")
                    except Exception as e:
                        self.logger.warning(f"Could not assign default 'Unsorted' location to part '{part_name}': {e}")
                        # Continue without location - don't fail part creation
                
                # Verify that the location exists, but only if a location_id is provided
                if location_id:
                    self.logger.debug(f"Validating location_id: {location_id}")
                    location_response = self.location_service.get_location(LocationQueryModel(id=location_id))
                    if not location_response.success or not location_response.data:
                        return self.error_response(f"Location with id '{location_id}' does not exist.")
                    self.logger.debug(f"Location validation successful for part '{part_name}'")

                # Handle categories first
                category_names = part_data.pop("category_names", [])
                categories = []

                if category_names:
                    self.logger.debug(f"Processing {len(category_names)} categories for part '{part_name}': {category_names}")
                    # Use the handle_categories function from the repository
                    categories = handle_categories(session, category_names)
                    
                    category_names_for_log = [cat.name for cat in categories if hasattr(cat, 'name')]
                    self.logger.info(f"Assigned {len(categories)} categories to part '{part_name}': {category_names_for_log}")

                # Extract datasheets data before creating the part
                datasheets_data = part_data.pop("datasheets", [])
                if datasheets_data:
                    self.logger.debug(f"Processing {len(datasheets_data)} datasheets for part '{part_name}'")
                
                # Filter out only valid PartModel fields
                valid_part_fields = {
                    'part_number', 'part_name', 'description', 'quantity', 
                    'supplier', 'supplier_part_number', 'supplier_url', 'location_id', 'image_url', 'additional_properties',
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
                        if value == "" and key in ['location_id', 'image_url', 'description', 'part_number', 'supplier', 'supplier_part_number', 'supplier_url',
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
                
                # Create the part with categories using repository
                self.logger.debug(f"Creating PartModel with data: {filtered_part_data}")
                new_part = PartModel(**filtered_part_data)
                
                # Assign categories to the part before saving
                if categories:
                    self.logger.debug(f"Assigning {len(categories)} categories to part")
                    new_part.categories = categories
                
                # Use repository to create the part
                part_obj = self.part_repo.add_part(session, new_part)
                
                # Create datasheet records if any
                if datasheets_data:
                    from MakerMatrix.repositories.datasheet_repository import DatasheetRepository
                    datasheet_repo = DatasheetRepository()
                    for datasheet_data in datasheets_data:
                        datasheet_data['part_id'] = part_obj.id
                        datasheet_repo.create_datasheet(session, datasheet_data)
                    
                    self.logger.info(f"Added {len(datasheets_data)} datasheets to part '{part_name}'")
                
                self.logger.info(f"Successfully created part: {part_name} (ID: {part_obj.id}) with {len(categories)} categories")
                
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
                
                return self.success_response("Part added successfully", safe_part_dict)

        except Exception as e:
            return self.handle_exception(e, f"add {self.entity_name}")

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

    def get_part_by_part_number(self, part_number: str, include: List[str] = None) -> ServiceResponse[Dict[str, Any]]:
        """
        Get a part by its part number.
        
        CONSOLIDATED SESSION MANAGEMENT: Migrated from static method with manual session
        management to BaseService pattern for consistency.
        """
        try:
            self.validate_required_fields({"part_number": part_number}, ["part_number"])
            self.log_operation("get_by_part_number", self.entity_name, part_number)
            
            with self.get_session() as session:
                # Fetch part using the repository layer
                part = self.part_repo.get_part_by_part_number(session, part_number)
                
                if not part:
                    return self.error_response(f"{self.entity_name} with part number '{part_number}' not found")
                
                # Load order relationships
                part_with_orders = self._load_order_relationships(session, part)
                
                return self.success_response(
                    f"{self.entity_name} with part number '{part_number}' found",
                    part_with_orders.to_dict(include=include)
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by part number")

    def get_part_by_part_name(self, part_name: str, include: List[str] = None) -> ServiceResponse[Dict[str, Any]]:
        """
        Get a part by its part name.

        Args:
            part_name (str): The name of the part to be retrieved.
            include (List[str]): Optional list of additional data to include

        Returns:
            dict[str, str | dict[str, Any]]: A dictionary containing the status, message, and data of the found part.
        """
        try:
            self.log_operation("get", self.entity_name, part_name)
            
            with self.get_session() as session:
                # Fetch part using the repository layer
                part = self.part_repo.get_part_by_name(session, part_name)
                
                if not part:
                    raise ResourceNotFoundError(f"Part with name '{part_name}' not found.")
                
                # Load order relationships
                part_with_orders = self._load_order_relationships(session, part)
                
                return self.success_response(
                    f"Part with name '{part_name}' found.",
                    part_with_orders.to_dict(include=include)
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by part name")

    def get_part_by_id(self, part_id: str, include: List[str] = None) -> ServiceResponse[Dict[str, Any]]:
        try:
            self.log_operation("get", self.entity_name, part_id)
            
            with self.get_session() as session:
                # Fetch part using the repository layer
                part = self.part_repo.get_part_by_id(session, part_id)
                
                if not part:
                    raise ResourceNotFoundError(f"Part with ID '{part_id}' not found.")
                
                # Load order relationships
                part_with_orders = self._load_order_relationships(session, part)
                
                return self.success_response(
                    f"Part with ID '{part_id}' found.",
                    part_with_orders.to_dict(include=include)
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} by ID")

    def get_part_counts(self) -> ServiceResponse[Dict[str, int]]:
        """
        Get total part count from the database.
        
        CONSOLIDATED SESSION MANAGEMENT: Migrated from static method with manual session
        management to BaseService pattern for consistency.
        """
        try:
            self.log_operation("get_counts", self.entity_name)
            
            with self.get_session() as session:
                total_parts = self.part_repo.get_part_counts(session)
                
                return self.success_response(
                    "Total part count retrieved successfully",
                    {"total_parts": total_parts}
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name} counts")

    def get_all_parts(self, page: int = 1, page_size: int = 10) -> ServiceResponse[Dict[str, Any]]:
        """
        Get all parts with pagination.
        
        CONSOLIDATED SESSION MANAGEMENT: Migrated from static method with manual session
        management to BaseService pattern for consistency.
        """
        try:
            self.log_operation("get_all", self.entity_name)
            
            with self.get_session() as session:
                # Fetch parts using the repository
                parts = self.part_repo.get_all_parts(session=session, page=page, page_size=page_size)
                total_parts = self.part_repo.get_part_counts(session)
                
                parts_data = {
                    "items": [part.to_dict() for part in parts],
                    "page": page,
                    "page_size": page_size,
                    "total": total_parts
                }
                
                message = f"Retrieved {len(parts)} parts (Page {page}/{(total_parts + page_size - 1) // page_size})." if parts else "No parts found."
                
                return self.success_response(message, parts_data)
                
        except Exception as e:
            return self.handle_exception(e, f"get all {self.entity_name}s")

    @staticmethod
    def get_parts_by_location_id(location_id: str, recursive=False) -> List[Dict]:
        return PartService.part_repo.get_parts_by_location_id(location_id, recursive)

    def update_part(self, part_id: str, part_update: PartUpdate) -> ServiceResponse[Dict[str, Any]]:
        """
        Update a part with provided data using BaseService patterns.
        
        CONSOLIDATED SESSION MANAGEMENT: Migrated from static method with manual session
        management to BaseService pattern for consistency.
        """
        try:
            self.log_operation("update", self.entity_name, part_id)
            
            with self.get_session() as session:
                part = self.part_repo.get_part_by_id(session, part_id)
                if not part:
                    raise ResourceNotFoundError(f"Part with ID '{part_id}' not found.")
                
                # Ensure categories are properly loaded
                if hasattr(part, 'categories') and part.categories:
                    # Force load categories to ensure they're properly populated
                    for category in part.categories:
                        # Access category attributes to ensure they're loaded
                        _ = category.name, category.id

                # Log current state before update
                self.logger.debug(f"Current part state before update: {part.part_name} (ID: {part_id})")

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
                                        self.logger.warning(f"Category object missing name attribute: {cat}")
                                except Exception as e:
                                    self.logger.error(f"Error accessing category data: {e}")
                        
                        categories = handle_categories(session, value)
                        part.categories.clear()  # Clear existing categories
                        part.categories.extend(categories)  # Add new categories
                        
                        # Use repository to update the part
                        part = self.part_repo.update_part(session, part)
                        
                        new_categories = [cat.name for cat in categories if hasattr(cat, 'name')]
                        self.logger.info(f"Updated categories for part '{part.part_name}' (ID: {part_id}): {old_categories} → {new_categories}")
                        updated_fields.append(f"categories: {old_categories} → {new_categories}")
                    elif hasattr(part, key):
                        try:
                            old_value = getattr(part, key)
                            setattr(part, key, value)
                            
                            # Log specific field updates with meaningful messages
                            if key == "location_id":
                                old_location = old_value
                                new_location = value
                                self.logger.info(f"Updated location for part '{part.part_name}' (ID: {part_id}): {old_location} → {new_location}")
                                updated_fields.append(f"location: {old_location} → {new_location}")
                            elif key == "quantity":
                                self.logger.info(f"Updated quantity for part '{part.part_name}' (ID: {part_id}): {old_value} → {value}")
                                updated_fields.append(f"quantity: {old_value} → {value}")
                            elif key == "part_name":
                                self.logger.info(f"Updated part name (ID: {part_id}): '{old_value}' → '{value}'")
                                updated_fields.append(f"name: '{old_value}' → '{value}'")
                            elif key == "supplier":
                                self.logger.info(f"Updated supplier for part '{part.part_name}' (ID: {part_id}): '{old_value}' → '{value}'")
                                updated_fields.append(f"supplier: '{old_value}' → '{value}'")
                            elif key == "description":
                                self.logger.info(f"Updated description for part '{part.part_name}' (ID: {part_id})")
                                updated_fields.append(f"description updated")
                            else:
                                self.logger.info(f"Updated {key} for part '{part.part_name}' (ID: {part_id}): {old_value} → {value}")
                                updated_fields.append(f"{key}: {old_value} → {value}")
                                
                        except AttributeError as e:
                            self.logger.warning(f"Skipping read-only or problematic attribute '{key}' for part {part_id}: {e}")

                # Pass the updated part to the repository for the actual update
                updated_part = self.part_repo.update_part(session, part)
                
                if update_data:
                    self.logger.info(f"Successfully updated part '{updated_part.part_name}' (ID: {part_id}). Changes: {', '.join(updated_fields)}")
                    return self.success_response(
                        "Part updated successfully", 
                        updated_part.to_dict()
                    )
                else:
                    self.logger.info(f"No updates provided for part '{part.part_name}' (ID: {part_id})")
                    return self.success_response(
                        "No updates provided", 
                        updated_part.to_dict()
                    )

        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")

    def advanced_search(self, search_params: AdvancedPartSearch) -> ServiceResponse[Dict[str, Any]]:
        """
        Perform an advanced search on parts with multiple filters and sorting options.
        Returns a dictionary containing the search results and metadata.
        """
        try:
            self.log_operation("advanced_search", "parts", f"filters: {search_params.search_term}")
            
            with self.get_session() as session:
                results, total_count = self.part_repo.advanced_search(session, search_params)
                
                search_data = {
                    "items": [part.to_dict() for part in results],
                    "total": total_count,
                    "page": search_params.page,
                    "page_size": search_params.page_size,
                    "total_pages": (total_count + search_params.page_size - 1) // search_params.page_size
                }
                
                return self.success_response(
                    "Search completed successfully",
                    search_data
                )
                
        except Exception as e:
            return self.handle_exception(e, f"advanced search with filters")

    def search_parts_text(self, query: str, page: int = 1, page_size: int = 20) -> ServiceResponse[Dict[str, Any]]:
        """
        Simple text search across part names, part numbers, and descriptions.
        """
        try:
            self.log_operation("search", "parts", f"text query: {query}")
            
            with self.get_session() as session:
                results, total_count = self.part_repo.search_parts_text(session, query, page, page_size)
                
                search_data = {
                    "items": [part.to_dict() for part in results],
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
                
                return self.success_response(
                    f"Found {total_count} parts matching '{query}'",
                    search_data
                )
                
        except Exception as e:
            return self.handle_exception(e, f"search parts with text query '{query}'")

    def get_part_suggestions(self, query: str, limit: int = 10) -> ServiceResponse[List[str]]:
        """
        Get autocomplete suggestions for part names based on search query.
        """
        try:
            self.log_operation("get", "suggestions", f"query: {query}")
            
            with self.get_session() as session:
                suggestions = self.part_repo.get_part_suggestions(session, query, limit)
                
                return self.success_response(
                    f"Found {len(suggestions)} suggestions for '{query}'",
                    suggestions
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get part suggestions for query '{query}'")

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
