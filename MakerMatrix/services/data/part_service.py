import logging
from http.client import HTTPException
from typing import List, Optional, Any, Dict, TYPE_CHECKING

from pydantic import ValidationError
from sqlalchemy import select
from sqlmodel import Session

from MakerMatrix.models.models import CategoryModel, LocationQueryModel, AdvancedPartSearch
from MakerMatrix.models.part_allocation_models import PartLocationAllocation
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

    def __init__(self, engine_override=None):
        super().__init__(engine_override)
        self.part_repo = PartRepository(self.engine)
        self.location_service = LocationService(self.engine)
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

                # Get old quantity from computed property
                old_quantity = found_part.total_quantity

                # Update the primary allocation quantity
                if not found_part.allocations:
                    return self.error_response(f"Part '{found_part.part_name}' has no allocations. Cannot update quantity.")

                # Find primary allocation or use first allocation
                primary_alloc = next(
                    (alloc for alloc in found_part.allocations if alloc.is_primary_storage),
                    found_part.allocations[0] if found_part.allocations else None
                )

                if not primary_alloc:
                    return self.error_response(f"Part '{found_part.part_name}' has no primary allocation.")

                # Update the allocation quantity
                primary_alloc.quantity_at_location = new_quantity
                from datetime import datetime
                primary_alloc.last_updated = datetime.utcnow()
                session.add(primary_alloc)
                session.commit()

                return self.success_response(
                    f"Quantity updated for part '{found_part.part_name}': {old_quantity} → {new_quantity}",
                    True
                )

        except Exception as e:
            return self.handle_exception(e, f"update quantity for {self.entity_name}")

    def delete_part(self, part_id: str) -> ServiceResponse[Dict[str, Any]]:
        """
        Delete a part by its ID using the repository.
        Also cleans up associated files (images and datasheets).

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

                # Clean up associated files before deleting the part record
                files_deleted = self._cleanup_part_files(part)
                if files_deleted:
                    self.logger.info(f"Deleted {files_deleted} file(s) for part '{part_name}' (ID: {part_id})")

                # Perform deletion
                deleted_part = self.part_repo.delete_part(session, part_id)

                return self.success_response(
                    f"{self.entity_name} with ID '{part_id}' was deleted successfully",
                    deleted_part.to_dict()
                )

        except Exception as e:
            return self.handle_exception(e, f"delete {self.entity_name}")

    def _cleanup_part_files(self, part: 'PartModel') -> int:
        """
        Clean up image and datasheet files associated with a part.

        Args:
            part: The part model to clean up files for

        Returns:
            Number of files deleted
        """
        import os
        from pathlib import Path

        deleted_count = 0
        static_dir = Path(__file__).parent.parent / "static"

        # Clean up image file
        if part.image_url:
            try:
                # Extract filename from URL (handle both full URLs and relative paths)
                if '/static/images/' in part.image_url:
                    filename = part.image_url.split('/static/images/')[-1]
                    image_path = static_dir / "images" / filename

                    if image_path.exists() and image_path.is_file():
                        os.remove(image_path)
                        deleted_count += 1
                        self.logger.debug(f"Deleted image file: {image_path}")
            except Exception as e:
                self.logger.warning(f"Failed to delete image file for part {part.part_name}: {e}")

        # Clean up datasheet files from PartDatasheet records
        if hasattr(part, 'datasheets') and part.datasheets:
            for datasheet in part.datasheets:
                try:
                    if hasattr(datasheet, 'file_url') and datasheet.file_url:
                        # Extract filename from URL
                        if '/static/datasheets/' in datasheet.file_url:
                            filename = datasheet.file_url.split('/static/datasheets/')[-1]
                            datasheet_path = static_dir / "datasheets" / filename

                            if datasheet_path.exists() and datasheet_path.is_file():
                                os.remove(datasheet_path)
                                deleted_count += 1
                                self.logger.debug(f"Deleted datasheet file: {datasheet_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete datasheet file for part {part.part_name}: {e}")

        # Clean up enriched datasheet file from additional_properties
        if part.additional_properties and part.additional_properties.get('datasheet_filename'):
            try:
                filename = part.additional_properties['datasheet_filename']
                datasheet_path = static_dir / "datasheets" / filename

                if datasheet_path.exists() and datasheet_path.is_file():
                    os.remove(datasheet_path)
                    deleted_count += 1
                    self.logger.debug(f"Deleted enriched datasheet file: {datasheet_path}")
            except Exception as e:
                self.logger.warning(f"Failed to delete enriched datasheet file for part {part.part_name}: {e}")

        return deleted_count

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

            # Normalize supplier name to lowercase for consistency
            if "supplier" in part_data and part_data["supplier"]:
                part_data["supplier"] = part_data["supplier"].lower()
                self.logger.debug(f"Normalized supplier name to lowercase: {part_data['supplier']}")

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

                # Auto-assign "Hardware" category for Bolt Depot parts
                supplier = (part_data.get("supplier") or "").lower()
                self.logger.debug(f"Checking hardware category auto-assign: supplier='{supplier}', category_names={category_names}")
                if supplier == "boltdepot" and "hardware" not in [cat.lower() for cat in category_names]:
                    category_names.append("hardware")
                    self.logger.info(f"✅ Auto-assigned 'hardware' category for Bolt Depot part '{part_name}'")

                # Check for supplier categories in additional_properties and auto-assign
                additional_props = part_data.get("additional_properties", {})
                if isinstance(additional_props, dict):
                    # Check for any {supplier}_category fields (e.g., digikey_category, mouser_category)
                    for key in additional_props:
                        if key.endswith("_category"):
                            supplier_category = additional_props[key]
                            if supplier_category and isinstance(supplier_category, str):
                                # Convert to lowercase as requested by user
                                auto_category_name = supplier_category.lower()
                                if auto_category_name not in category_names:
                                    category_names.append(auto_category_name)
                                    self.logger.info(f"Auto-assigned category '{auto_category_name}' from {key} '{supplier_category}' for part '{part_name}'")

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

                # Extract pricing tiers for history BEFORE filtering
                pricing_tiers_for_history = part_data.pop("pricing_tiers_for_history", None)
                if pricing_tiers_for_history:
                    self.logger.debug(f"Pricing history data found for part '{part_name}': {pricing_tiers_for_history}")
                
                # Extract allocation data BEFORE filtering (these are not PartModel fields anymore)
                allocation_quantity = part_data.pop('quantity', 0)
                allocation_location_id = part_data.pop('location_id', None)

                # Filter out only valid PartModel fields (removed 'quantity', 'location_id', and 'pricing_data')
                valid_part_fields = {
                    'part_number', 'part_name', 'description',
                    'supplier', 'supplier_part_number', 'supplier_url', 'product_url', 'image_url', 'emoji', 'additional_properties',
                    # Pricing fields (removed pricing_data - goes to PartPricingHistory instead)
                    'unit_price', 'currency',
                    # Enhanced fields from PartModel
                    'manufacturer', 'manufacturer_part_number', 'component_type',
                    'package', 'mounting_type',
                    'stock_quantity',
                    'last_enrichment_date', 'enrichment_source',
                    'data_quality_score'
                }
                
                # Create part data dict with only valid fields
                filtered_part_data = {}
                for key, value in part_data.items():
                    if key in valid_part_fields:
                        # Convert empty strings to None for optional fields (removed location_id - no longer a part field)
                        if value == "" and key in ['image_url', 'description', 'part_number', 'supplier', 'supplier_part_number', 'supplier_url', 'product_url',
                                                  'manufacturer', 'manufacturer_part_number', 'component_type',
                                                  'package', 'mounting_type',
                                                  'price_source', 'enrichment_source']:
                            filtered_part_data[key] = None
                        # Handle additional_properties - convert None/undefined to empty dict
                        elif key == 'additional_properties' and value is None:
                            filtered_part_data[key] = {}
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

                # Create allocation if location_id provided (quantity can be 0)
                if allocation_location_id and allocation_quantity is not None:
                    allocation = PartLocationAllocation(
                        part_id=part_obj.id,
                        location_id=allocation_location_id,
                        quantity_at_location=allocation_quantity,
                        is_primary_storage=True,
                        notes="Initial allocation from part creation"
                    )
                    session.add(allocation)
                    session.commit()
                    session.refresh(part_obj)  # Refresh to load the new allocation

                    self.logger.info(f"Created allocation for part '{part_name}': {allocation_quantity} units at location {allocation_location_id}")

                # Create datasheet records if any
                if datasheets_data:
                    from MakerMatrix.repositories.datasheet_repository import DatasheetRepository
                    datasheet_repo = DatasheetRepository()
                    for datasheet_data in datasheets_data:
                        datasheet_data['part_id'] = part_obj.id
                        datasheet_repo.create_datasheet(session, datasheet_data)

                    self.logger.info(f"Added {len(datasheets_data)} datasheets to part '{part_name}'")

                # Create PartPricingHistory record if pricing data available
                if pricing_tiers_for_history:
                    from MakerMatrix.models.part_metadata_models import PartPricingHistory

                    pricing_history = PartPricingHistory(
                        part_id=part_obj.id,
                        supplier=pricing_tiers_for_history.get('supplier', part_obj.supplier or 'Unknown'),
                        unit_price=part_obj.unit_price,
                        currency=pricing_tiers_for_history.get('currency', 'USD'),
                        stock_quantity=part_obj.stock_quantity,
                        pricing_tiers=pricing_tiers_for_history.get('tiers', []),
                        source=pricing_tiers_for_history.get('source', 'enrichment'),
                        is_current=True
                    )
                    session.add(pricing_history)
                    session.commit()

                    self.logger.info(f"Created pricing history for part '{part_name}' with {len(pricing_tiers_for_history.get('tiers', []))} price tiers")
                
                self.logger.info(f"Successfully created part: {part_name} (ID: {part_obj.id}) with {len(categories)} categories")

                # Create a safe dict using computed properties for quantity and location
                safe_part_dict = {
                    "id": part_obj.id,
                    "part_name": part_obj.part_name,
                    "part_number": part_obj.part_number,
                    "description": part_obj.description,
                    "quantity": part_obj.total_quantity,  # Computed from allocations
                    "supplier": part_obj.supplier,
                    "image_url": part_obj.image_url,
                    "emoji": part_obj.emoji,
                    "categories": [{"id": cat.id, "name": cat.name} for cat in categories] if categories else []
                }

                # Add location from computed property if available
                primary_loc = part_obj.primary_location
                if primary_loc:
                    safe_part_dict["location"] = {
                        "id": primary_loc.id,
                        "name": primary_loc.name,
                        "description": primary_loc.description,
                        "location_type": primary_loc.location_type
                    }
                    safe_part_dict["location_id"] = primary_loc.id
                else:
                    safe_part_dict["location"] = None
                    safe_part_dict["location_id"] = None

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

                # Normalize supplier name to lowercase for consistency
                if "supplier" in update_data and update_data["supplier"]:
                    update_data["supplier"] = update_data["supplier"].lower()
                    self.logger.debug(f"Normalized supplier name to lowercase: {update_data['supplier']}")

                updated_fields = []

                for key, value in update_data.items():
                    if key == "category_names":
                        # Skip if None or if empty list (preserve existing categories)
                        if value is None:
                            continue

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

                        # Only update categories if a non-empty list was provided
                        if value:  # Non-empty list
                            categories = handle_categories(session, value)
                            part.categories.clear()  # Clear existing categories
                            part.categories.extend(categories)  # Add new categories

                            # Use repository to update the part
                            part = self.part_repo.update_part(session, part)

                            new_categories = [cat.name for cat in categories if hasattr(cat, 'name')]
                            self.logger.info(f"Updated categories for part '{part.part_name}' (ID: {part_id}): {old_categories} → {new_categories}")
                            updated_fields.append(f"categories: {old_categories} → {new_categories}")
                        else:
                            # Empty list provided - preserve existing categories
                            self.logger.debug(f"Empty category_names provided for part '{part.part_name}' (ID: {part_id}) - preserving existing categories")
                    elif key == "quantity":
                        # Special handling for quantity - update primary allocation
                        old_quantity = part.total_quantity

                        if not part.allocations:
                            # No allocations exist - need location_id to create allocation
                            location_id_for_allocation = update_data.get('location_id')

                            if not location_id_for_allocation:
                                # Get or create "Unsorted" location as default
                                from MakerMatrix.models.location_models import LocationModel
                                unsorted_location = session.query(LocationModel).filter_by(name="Unsorted").first()
                                if not unsorted_location:
                                    unsorted_location = LocationModel(
                                        name="Unsorted",
                                        description="Default location for parts without a specified location",
                                        location_type="standard"
                                    )
                                    session.add(unsorted_location)
                                    session.flush()
                                    self.logger.info(f"Created 'Unsorted' location (ID: {unsorted_location.id})")

                                location_id_for_allocation = unsorted_location.id
                                self.logger.info(
                                    f"Using 'Unsorted' location for part '{part.part_name}' (ID: {part_id}) allocation"
                                )

                            # Create new allocation with this quantity at specified location
                            allocation = PartLocationAllocation(
                                part_id=part.id,
                                location_id=location_id_for_allocation,
                                quantity_at_location=value,
                                is_primary_storage=True,
                                notes="Allocation created during quantity update"
                            )
                            session.add(allocation)
                            self.logger.info(f"Created new allocation with quantity {value} at location {location_id_for_allocation} for part '{part.part_name}' (ID: {part_id})")
                            updated_fields.append(f"quantity: {old_quantity} → {value}")
                        else:
                            # Find primary allocation or use first
                            primary_alloc = next(
                                (alloc for alloc in part.allocations if alloc.is_primary_storage),
                                part.allocations[0] if part.allocations else None
                            )

                            if primary_alloc:
                                primary_alloc.quantity_at_location = value
                                from datetime import datetime
                                primary_alloc.last_updated = datetime.utcnow()
                                session.add(primary_alloc)
                                self.logger.info(f"Updated quantity for part '{part.part_name}' (ID: {part_id}): {old_quantity} → {value}")
                                updated_fields.append(f"quantity: {old_quantity} → {value}")
                    elif key == "location_id":
                        # Special handling for location_id - move primary allocation to new location
                        old_location = part.primary_location
                        old_location_name = old_location.name if old_location else "None"

                        if not part.allocations:
                            # No allocations exist - create new allocation at this location
                            allocation = PartLocationAllocation(
                                part_id=part.id,
                                location_id=value,
                                quantity_at_location=0,
                                is_primary_storage=True,
                                notes="Location updated from part edit"
                            )
                            session.add(allocation)
                            self.logger.info(f"Created new allocation at location {value} for part '{part.part_name}' (ID: {part_id})")
                        else:
                            # Update primary allocation location
                            primary_alloc = next(
                                (alloc for alloc in part.allocations if alloc.is_primary_storage),
                                part.allocations[0] if part.allocations else None
                            )

                            if primary_alloc:
                                primary_alloc.location_id = value
                                from datetime import datetime
                                primary_alloc.last_updated = datetime.utcnow()
                                session.add(primary_alloc)
                                self.logger.info(f"Updated location for part '{part.part_name}' (ID: {part_id}): {old_location_name} → {value}")

                        updated_fields.append(f"location: {old_location_name} → {value}")
                    elif hasattr(part, key):
                        try:
                            old_value = getattr(part, key)
                            setattr(part, key, value)

                            # Log specific field updates with meaningful messages
                            if key == "part_name":
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

    # === ALLOCATION TRANSFER METHODS ===

    def transfer_quantity(
        self,
        part_id: str,
        from_location_id: str,
        to_location_id: str,
        quantity: int,
        notes: Optional[str] = None
    ) -> ServiceResponse:
        """
        Transfer quantity from one location to another for a part.

        Args:
            part_id: Part to transfer
            from_location_id: Source location
            to_location_id: Destination location
            quantity: Amount to transfer
            notes: Optional transfer notes

        Returns:
            ServiceResponse with updated part
        """
        try:
            with Session(self.engine) as session:
                # Get part
                part = session.get(PartModel, part_id)
                if not part:
                    return ServiceResponse(
                        success=False,
                        message=f"Part {part_id} not found",
                        data=None
                    )

                # Get source allocation
                from_alloc = session.exec(
                    select(PartLocationAllocation).where(
                        PartLocationAllocation.part_id == part_id,
                        PartLocationAllocation.location_id == from_location_id
                    )
                ).first()

                if not from_alloc:
                    return ServiceResponse(
                        success=False,
                        message=f"No allocation found at source location",
                        data=None
                    )

                if from_alloc.quantity_at_location < quantity:
                    return ServiceResponse(
                        success=False,
                        message=f"Insufficient quantity at source (have {from_alloc.quantity_at_location}, need {quantity})",
                        data=None
                    )

                # Reduce source quantity
                from_alloc.quantity_at_location -= quantity
                from_alloc.last_updated = datetime.utcnow()
                if notes:
                    from_alloc.notes = f"{from_alloc.notes or ''}\nTransfer out: {notes}".strip()

                # If source is now empty, delete the allocation
                if from_alloc.quantity_at_location == 0:
                    session.delete(from_alloc)

                # Get or create destination allocation
                to_alloc = session.exec(
                    select(PartLocationAllocation).where(
                        PartLocationAllocation.part_id == part_id,
                        PartLocationAllocation.location_id == to_location_id
                    )
                ).first()

                if to_alloc:
                    # Add to existing allocation
                    to_alloc.quantity_at_location += quantity
                    to_alloc.last_updated = datetime.utcnow()
                    if notes:
                        to_alloc.notes = f"{to_alloc.notes or ''}\nTransfer in: {notes}".strip()
                else:
                    # Create new allocation
                    to_alloc = PartLocationAllocation(
                        part_id=part_id,
                        location_id=to_location_id,
                        quantity_at_location=quantity,
                        is_primary_storage=False,  # Transfers are typically to working stock
                        notes=f"Transferred from {from_location_id}: {notes}" if notes else None
                    )
                    session.add(to_alloc)

                session.commit()
                session.refresh(part)

                logger.info(
                    f"Transferred {quantity} of part {part.part_name} from {from_location_id} to {to_location_id}"
                )

                return ServiceResponse(
                    success=True,
                    message=f"Successfully transferred {quantity} units",
                    data=part
                )

        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            return ServiceResponse(
                success=False,
                message=f"Transfer failed: {str(e)}",
                data=None
            )

    def bulk_update_parts(self, update_request: dict) -> ServiceResponse[Dict[str, Any]]:
        """
        Bulk update multiple parts with shared field values.

        Args:
            update_request: Dictionary containing:
                - part_ids: List of part IDs to update
                - supplier: Optional supplier name
                - location_id: Optional location ID
                - minimum_quantity: Optional minimum quantity
                - add_categories: Optional list of category names to add
                - remove_categories: Optional list of category names to remove

        Returns:
            ServiceResponse with update summary
        """
        try:
            part_ids = update_request.get('part_ids', [])
            supplier = update_request.get('supplier')
            location_id = update_request.get('location_id')
            minimum_quantity = update_request.get('minimum_quantity')
            add_categories = update_request.get('add_categories', [])
            remove_categories = update_request.get('remove_categories', [])

            updated_count = 0
            failed_count = 0
            errors = []

            with self.get_session() as session:
                for part_id in part_ids:
                    try:
                        # Get the part
                        part = self.part_repo.get_part_by_id(session, part_id)
                        if not part:
                            failed_count += 1
                            errors.append({
                                'part_id': part_id,
                                'error': 'Part not found'
                            })
                            continue

                        # Update simple fields
                        if supplier is not None:
                            part.supplier = supplier

                        if minimum_quantity is not None:
                            part.minimum_quantity = minimum_quantity

                        # Update location (primary allocation)
                        if location_id is not None:
                            from MakerMatrix.models.part_allocation_models import PartLocationAllocation
                            from datetime import datetime

                            # Find or create primary allocation
                            primary_alloc = next(
                                (alloc for alloc in part.allocations if alloc.is_primary_storage),
                                part.allocations[0] if part.allocations else None
                            )

                            if primary_alloc:
                                primary_alloc.location_id = location_id
                                primary_alloc.last_updated = datetime.utcnow()
                                session.add(primary_alloc)

                        # Handle categories
                        if add_categories:
                            from MakerMatrix.repositories.parts_repositories import handle_categories
                            categories_to_add = handle_categories(session, add_categories)
                            for category in categories_to_add:
                                if category not in part.categories:
                                    part.categories.append(category)

                        if remove_categories:
                            part.categories = [
                                cat for cat in part.categories
                                if cat.name not in remove_categories
                            ]

                        # Save the part
                        session.add(part)
                        updated_count += 1

                    except Exception as e:
                        failed_count += 1
                        errors.append({
                            'part_id': part_id,
                            'error': str(e)
                        })
                        logger.error(f"Failed to update part {part_id}: {e}")

                # Commit all updates
                session.commit()

            result = {
                'updated_count': updated_count,
                'failed_count': failed_count,
                'errors': errors
            }

            return self.success_response(
                f"Bulk update completed: {updated_count} succeeded, {failed_count} failed",
                result
            )

        except Exception as e:
            return self.handle_exception(e, "bulk update parts")

    def bulk_delete_parts(self, part_ids: list[str]) -> ServiceResponse[Dict[str, Any]]:
        """
        Bulk delete multiple parts with associated file cleanup.

        Args:
            part_ids: List of part IDs to delete

        Returns:
            ServiceResponse with deletion summary
        """
        try:
            if not part_ids:
                return self.error_response("No part IDs provided for deletion")

            deleted_count = 0
            failed_count = 0
            errors = []
            total_files_deleted = 0

            with self.get_session() as session:
                for part_id in part_ids:
                    try:
                        # Get the part
                        part = self.part_repo.get_part_by_id(session, part_id)
                        if not part:
                            failed_count += 1
                            errors.append({
                                'part_id': part_id,
                                'error': 'Part not found'
                            })
                            continue

                        part_name = part.part_name

                        # Clean up associated files
                        files_deleted = self._cleanup_part_files(part)
                        total_files_deleted += files_deleted

                        # Delete the part
                        self.part_repo.delete_part(session, part_id)
                        deleted_count += 1

                        self.logger.info(f"Deleted part '{part_name}' (ID: {part_id}) and {files_deleted} associated file(s)")

                    except Exception as e:
                        failed_count += 1
                        errors.append({
                            'part_id': part_id,
                            'error': str(e)
                        })
                        self.logger.error(f"Failed to delete part {part_id}: {e}")

                # Commit all deletions
                session.commit()

            result = {
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'files_deleted': total_files_deleted,
                'errors': errors
            }

            return self.success_response(
                f"Bulk delete completed: {deleted_count} part(s) deleted, {total_files_deleted} file(s) removed, {failed_count} failed",
                result
            )

        except Exception as e:
            return self.handle_exception(e, "bulk delete parts")

    #
