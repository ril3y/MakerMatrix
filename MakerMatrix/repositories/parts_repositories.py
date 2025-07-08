import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import func, or_, delete
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, select
# from MakerMatrix.models.category_model import CategoryModel
# from MakerMatrix.models.part_model import PartModel
# from MakerMatrix.repositories.base_repository import BaseRepository

from MakerMatrix.models.models import PartModel, CategoryModel, AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError, InvalidReferenceError

# Configure logging
logger = logging.getLogger(__name__)


# noinspection PyTypeChecker
def handle_categories(session: Session, category_names: List[str]) -> List[CategoryModel]:
    categories = []
    for name in category_names:
        category = session.exec(select(CategoryModel).where(CategoryModel.name == name)).first()
        if not category:
            category = CategoryModel(name=name)
            session.add(category)
            session.flush()  # Use flush instead of commit to maintain transaction integrity
            session.refresh(category)
        categories.append(category)
    return categories


# noinspection PyTypeChecker
class PartRepository:

    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_parts_by_location_id(session: Session, location_id: str, recursive: bool = False) -> List[Dict]:
        """
        Retrieve parts associated with the given location ID.

        If recursive is True, it will also fetch parts associated with child locations.
        """
        # Fetch parts directly associated with the given location
        parts = session.exec(
            select(PartModel)
            .options(joinedload(PartModel.location))
            .where(PartModel.location_id == location_id)
        ).all()

        if recursive:
            # If recursive, find parts associated with all child locations
            child_location_ids = PartRepository.get_child_location_ids(session, location_id)
            for child_id in child_location_ids:
                parts.extend(PartRepository.get_parts_by_location_id(session, child_id, recursive=True))

        return parts

    @staticmethod
    def dynamic_search(session: Session, search_term: str) -> List[PartModel]:
        """
        Search for parts by name, part_number, or any other fields you choose.
        Returns a list of PartModels or raises an error if none found.
        """
        results = session.exec(
            select(PartModel).where(
                or_(
                    PartModel.part_name.ilike(f"%{search_term}%"),
                    PartModel.part_number.ilike(f"%{search_term}%")
                )
            )
        ).all()

        if results:
            return results
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"No parts found for search term '{search_term}'",
                data=None
            )

    ###

    @staticmethod
    def delete_part(session: Session, part_id: str) -> Optional[PartModel]:
        """
        Delete a part by ID with proper cleanup of dependent records.
        Explicitly handles foreign key relationships since ORM cascade may not work.
        Raises ResourceNotFoundError if the part doesn't exist.
        Returns the deleted part.
        """
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy import text
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get the part first (will raise ResourceNotFoundError if not found)
        part = PartRepository.get_part_by_id(session, part_id)
        
        try:
            # Manual cleanup of dependent records to ensure proper deletion
            # Handle all foreign key relationships explicitly since some have NO ACTION
            
            # 1. Clear many-to-many category relationships (partcategorylink)
            if part.categories:
                num_categories = len(part.categories)
                part.categories.clear()
                logger.info(f"Cleared {num_categories} category relationships for part {part_id}")
            
            # 2. Delete datasheet files (datasheetmodel) 
            if hasattr(part, 'datasheets') and part.datasheets:
                num_datasheets = len(part.datasheets)
                for datasheet in part.datasheets:
                    session.delete(datasheet)
                logger.info(f"Deleted {num_datasheets} datasheet(s) for part {part_id}")
            
            # 3. Delete PartOrderSummary records (should CASCADE but be explicit)
            from MakerMatrix.models.models import PartOrderSummary
            order_summaries = session.exec(
                select(PartOrderSummary).where(PartOrderSummary.part_id == part_id)
            ).all()
            for summary in order_summaries:
                session.delete(summary)
                logger.info(f"Deleted order summary for part {part_id}")
            
            # 4. Update OrderItem records to set part_id to NULL (should SET NULL but be explicit)
            from MakerMatrix.models.order_models import OrderItemModel
            order_items = session.exec(
                select(OrderItemModel).where(OrderItemModel.part_id == part_id)
            ).all()
            for item in order_items:
                item.part_id = None
                session.add(item)
                logger.info(f"Cleared part reference in order item {item.id}")
            
            # 5. Delete PartOrderLink records (partorderlink)
            from MakerMatrix.models.order_models import PartOrderLink
            part_order_links = session.exec(
                select(PartOrderLink).where(PartOrderLink.part_id == part_id)
            ).all()
            for link in part_order_links:
                session.delete(link)
                logger.info(f"Deleted part-order link for part {part_id}")
            
            # 6. Flush changes to database before deleting the part
            session.flush()
            
            # 7. Now delete the part itself
            session.delete(part)
            session.commit()
            logger.info(f"Successfully deleted part {part_id} and all dependent records")
            return part
            
        except Exception as e:
            session.rollback()
            error_msg = str(e)
            logger.error(f"Failed to delete part {part_id}: {error_msg}")
            
            # Still provide helpful error information
            if isinstance(e, IntegrityError) and "FOREIGN KEY constraint failed" in error_msg:
                raise ValueError(f"Cannot delete part '{part.part_name}' due to database constraint issues. This may indicate corrupt foreign key relationships.")
            else:
                raise ValueError(f"Failed to delete part '{part.part_name}': {str(e)}")

    @staticmethod
    def get_child_location_ids(session: Session, location_id: str) -> List[str]:
        """
        Get a list of child location IDs for the given location ID.
        """
        from MakerMatrix.models.models import LocationModel
        child_locations = session.exec(
            select(LocationModel).where(LocationModel.parent_id == location_id)
        ).all()
        return [location.id for location in child_locations]

    @staticmethod
    def get_part_by_part_number(session: Session, part_number: str) -> Optional[PartModel]:
        part = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location),
                selectinload(PartModel.datasheets),
                selectinload(PartModel.order_items),
                selectinload(PartModel.order_summary)
            )
            .where(PartModel.part_number == part_number)
        ).first()
        if part:
            return part
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"Error: Part with part number {part_number} not found",
                data=None)

    @staticmethod
    def get_part_by_id(session: Session, part_id: str) -> Optional[PartModel]:
        part = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location),
                selectinload(PartModel.datasheets),
                selectinload(PartModel.order_items),
                selectinload(PartModel.order_summary)
            )
            .where(PartModel.id == part_id)
        ).first()

        if part:
            return part
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"Part with ID {part_id} not found",
                data=None
            )

    @staticmethod
    def get_part_by_name(session: Session, part_name: str) -> Optional[PartModel]:
        part = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location),
                selectinload(PartModel.datasheets),
                selectinload(PartModel.order_items),
                selectinload(PartModel.order_summary)
            )
            .where(PartModel.part_name == part_name)
        ).first()

        if part:
            return part
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"Part with name '{part_name}' not found",
                data=None
            )

    @staticmethod
    def get_all_parts(session: Session, page: int = 1, page_size: int = 10) -> List[PartModel]:
        offset = (page - 1) * page_size
        results = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location)
            )
            .offset(offset)
            .limit(page_size)
        )
        return results.unique().all()

    @staticmethod
    def get_part_counts(session: Session) -> int:
        return session.exec(select(func.count()).select_from(PartModel)).one()

    @staticmethod
    def add_part(session: Session, part_data: PartModel) -> PartModel:
        """
        Add a new part to the database. Categories are expected to be already created
        and associated with the part.
        
        Args:
            session: The database session
            part_data: The PartModel instance to add with categories already set
            
        Returns:
            PartModel: The created part with all relationships loaded
        """
        # Validate location_id if provided
        if part_data.location_id:
            from MakerMatrix.models.models import LocationModel
            location = session.exec(
                select(LocationModel).where(LocationModel.id == part_data.location_id)
            ).first()
            if not location:
                raise InvalidReferenceError(
                    status="error",
                    message=f"Location with ID '{part_data.location_id}' does not exist",
                    data={"location_id": part_data.location_id}
                )
        
        try:
            # Add the part to the session
            session.add(part_data)
            
            # Commit the transaction
            session.commit()
            
            # Refresh the part with relationships loaded
            session.refresh(part_data, ['categories', 'location'])
            
            return part_data
            
        except Exception as e:
            session.rollback()
            raise RuntimeError(f"Failed to add part: {str(e)}")

    def is_part_name_unique(self, name: str, exclude_id: Optional[str] = None) -> bool:
        with Session(self.engine) as session:
            # Create a base query to find parts with the same name
            query = select(PartModel).where(PartModel.part_name == name)

            # If exclude_id is provided, add condition to exclude that ID from the query
            if exclude_id:
                query = query.where(PartModel.id != exclude_id)

            # Execute the query
            result = session.exec(query).first()

            # Return True if no other parts with the same name exist, otherwise False
            return result is None

    @staticmethod
    def update_part(session: Session, part: PartModel) -> PartModel:
        logger.debug(f"[REPO] Attempting to update part in database: {part.part_name} (ID: {part.id})")
        
        # Validate location_id if provided
        if part.location_id:
            logger.debug(f"[REPO] Validating location_id: {part.location_id}")
            from MakerMatrix.models.models import LocationModel
            location = session.exec(
                select(LocationModel).where(LocationModel.id == part.location_id)
            ).first()
            if not location:
                logger.error(f"[REPO] Location validation failed: Location with ID '{part.location_id}' does not exist")
                raise InvalidReferenceError(
                    status="error",
                    message=f"Location with ID '{part.location_id}' does not exist",
                    data={"location_id": part.location_id}
                )
            logger.debug(f"[REPO] Location validation successful: {location.name}")
        
        try:
            session.add(part)
            session.commit()
            session.refresh(part)
            logger.debug(f"[REPO] Successfully updated part in database: {part.part_name} (ID: {part.id})")
            return part

        except ResourceNotFoundError as rnfe:
            logger.error(f"[REPO] Resource not found during part update: {rnfe}")
            raise rnfe

        except Exception as e:
            logger.error(f"[REPO] Database error during part update for '{part.id}': {e}")
            session.rollback()
            raise RuntimeError(f"Failed to update part with id '{part.id}': {str(e)}")

    @staticmethod
    def advanced_search(session: Session, search_params: AdvancedPartSearch) -> tuple[List[PartModel], int]:
        """
        Perform an advanced search on parts with multiple filters and sorting options.
        Returns a tuple of (results, total_count).
        """
        # Start with a base query
        query = select(PartModel).options(
            joinedload(PartModel.categories),
            joinedload(PartModel.location)
        )

        # Start with a base count query
        count_query = select(func.count(PartModel.id.distinct())).select_from(PartModel)

        # Apply search term filter
        if search_params.search_term:
            search_term = f"%{search_params.search_term}%"
            search_filter = or_(
                PartModel.part_name.ilike(search_term),
                PartModel.part_number.ilike(search_term),
                PartModel.description.ilike(search_term)
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Apply quantity range filter
        if search_params.min_quantity is not None:
            query = query.where(PartModel.quantity >= search_params.min_quantity)
            count_query = count_query.where(PartModel.quantity >= search_params.min_quantity)
        if search_params.max_quantity is not None:
            query = query.where(PartModel.quantity <= search_params.max_quantity)
            count_query = count_query.where(PartModel.quantity <= search_params.max_quantity)

        # Apply category filter
        if search_params.category_names:
            category_ids = [
                category.id for category in handle_categories(session, search_params.category_names)
            ]
            query = query.join(PartModel.categories).where(CategoryModel.id.in_(category_ids))
            count_query = count_query.join(PartModel.categories).where(CategoryModel.id.in_(category_ids))

        # Apply location filter
        if search_params.location_id:
            query = query.where(PartModel.location_id == search_params.location_id)
            count_query = count_query.where(PartModel.location_id == search_params.location_id)

        # Apply supplier filter
        if search_params.supplier:
            query = query.where(PartModel.supplier == search_params.supplier)
            count_query = count_query.where(PartModel.supplier == search_params.supplier)

        # Apply sorting
        if search_params.sort_by:
            sort_column = getattr(PartModel, search_params.sort_by)
            if search_params.sort_order == "desc":
                sort_column = sort_column.desc()
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (search_params.page - 1) * search_params.page_size
        query = query.offset(offset).limit(search_params.page_size)

        # Execute the queries
        results = session.exec(query).unique().all()
        total_count = session.exec(count_query).one()

        return results, total_count

    @staticmethod
    def get_orphaned_parts(session: Session, page: int = 1, page_size: int = 10) -> tuple[List[PartModel], int]:
        """
        Get parts that have NULL location_id (orphaned parts).
        Returns a tuple of (results, total_count).
        """
        # Base query for orphaned parts
        query = select(PartModel).options(
            joinedload(PartModel.categories)
        ).where(PartModel.location_id.is_(None))
        
        # Count query for orphaned parts
        count_query = select(func.count(PartModel.id.distinct())).select_from(PartModel).where(PartModel.location_id.is_(None))
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Order by part name for consistent results
        query = query.order_by(PartModel.part_name)
        
        # Execute queries
        results = session.exec(query).unique().all()
        total_count = session.exec(count_query).one()
        
        return results, total_count

    @staticmethod
    def search_parts_text(session: Session, query: str, page: int = 1, page_size: int = 20) -> tuple[List[PartModel], int]:
        """
        Simple text search across part names, part numbers, and descriptions.
        Returns a tuple of (results, total_count).
        """
        # Create search term with wildcards
        search_term = f"%{query}%"
        
        # Base query with eager loading
        base_query = select(PartModel).options(
            joinedload(PartModel.categories),
            joinedload(PartModel.location)
        )
        
        # Count query
        count_query = select(func.count(PartModel.id.distinct())).select_from(PartModel)
        
        # Apply search filter across multiple fields
        search_filter = or_(
            PartModel.part_name.ilike(search_term),
            PartModel.part_number.ilike(search_term),
            PartModel.description.ilike(search_term)
        )
        
        # Apply filter to both queries
        query_with_filter = base_query.where(search_filter)
        count_query_with_filter = count_query.where(search_filter)
        
        # Order by relevance (exact matches first, then partial matches)
        query_with_filter = query_with_filter.order_by(
            # Exact part name matches first
            func.lower(PartModel.part_name) == query.lower(),
            # Exact part number matches second
            func.lower(PartModel.part_number) == query.lower(),
            # Then by part name alphabetically
            PartModel.part_name
        )
        
        # Apply pagination
        offset = (page - 1) * page_size
        query_with_filter = query_with_filter.offset(offset).limit(page_size)
        
        # Execute queries
        results = session.exec(query_with_filter).unique().all()
        total_count = session.exec(count_query_with_filter).one()
        
        return results, total_count

    @staticmethod
    def get_part_suggestions(session: Session, query: str, limit: int = 10) -> List[str]:
        """
        Get autocomplete suggestions for part names based on search query.
        Returns part names that start with or contain the query.
        """
        search_term = f"%{query}%"
        
        # Query for part names that contain the search term
        # Prioritize names that start with the query
        suggestions_query = select(PartModel.part_name).where(
            PartModel.part_name.ilike(search_term)
        ).distinct().order_by(
            # Names starting with query come first
            ~PartModel.part_name.ilike(f"{query}%"),
            PartModel.part_name
        ).limit(limit)
        
        # Execute query and return list of part names
        suggestions = session.exec(suggestions_query).all()
        
        # Filter out None values and return as list
        return [name for name in suggestions if name is not None]

    # def add_part(self, part_data: dict, overwrite: bool) -> dict:
    #     # Check if a part with the same part_number or part_name already exists
    #     part_id = part_data.get('part_id')
    #     existing_part = self.get_part_by_id(part_id)
    #
    #     if existing_part and not overwrite:
    #         return {
    #             "status": "part exists",
    #             "message": f"Part id {part_id} already exists. Overwrite is set to False.",
    #             "data": None
    #         }
    #
    #     # Remove the existing part if overwrite is allowed
    #     if existing_part:
    #         self.table.remove(doc_ids=[existing_part.doc_id])
    #
    #     # Process categories if they are present
    #     if 'categories' in part_data and part_data['categories']:
    #         processed_categories = []
    #         for category in part_data['categories']:
    #             if isinstance(category, str):
    #                 # Convert a string category into a CategoryModel
    #                 category_obj = CategoryModel(name=category)
    #             elif isinstance(category, dict):
    #                 # Create a CategoryModel from the provided dict
    #                 category_obj = CategoryModel(**category)
    #             else:
    #                 continue
    #
    #             # Add the category to the list
    #             processed_categories.append(category_obj.dict())
    #
    #         part_data['categories'] = processed_categories
    #
    #     # Process additional_properties if present
    #     if 'additional_properties' in part_data and part_data['additional_properties']:
    #         processed_properties = {}
    #         for key, value in part_data['additional_properties'].items():
    #             # Convert the keys and values to strings for consistency
    #             processed_properties[key] = str(value)
    #
    #         part_data['additional_properties'] = processed_properties
    #
    #     # Insert or update the part record
    #     document_id = self.table.insert(part_data)
    #
    #     return {
    #         "status": "success",
    #         "message": "Part added successfully",
    #         "data": part_data,
    #         "document_id": document_id
    #     }

    # def delete_part(self, part_id: str) -> bool:
    #     part = self.table.get(self.query().part_id == part_id)
    #     if part:
    #         self.table.remove(self.query().part_id == part_id)
    #         return True
    #     return False
    #
    # def dynamic_search(self, term: str) -> List[dict]:
    #     # Search the database for all parts first
    #     all_parts = self.table.all()
    #
    #     # Filter parts based on whether they match the search term
    #     def matches(part):
    #         matched_fields = []
    #         # Check all top-level fields
    #         top_level_fields = ['part_name', 'part_number', 'description', 'supplier']
    #         for field in top_level_fields:
    #             if term.lower() in str(part.get(field, '')).lower():
    #                 matched_fields.append({"field": field})
    #
    #         # Check additional_properties
    #         additional_props = part.get('additional_properties', {})
    #         for key, value in additional_props.items():
    #             if term.lower() in str(key).lower() or term.lower() in str(value).lower():
    #                 matched_fields.append({"field": "additional_properties", "key": key})
    #
    #         return matched_fields if matched_fields else None
    #
    #     # Filter parts that match the term and include matched fields
    #     results = []
    #     for part in all_parts:
    #         matched_fields = matches(part)
    #         if matched_fields:
    #             results.append({"part": part, "matched_fields": matched_fields})
    #
    #     return results
    #
    # def update_quantity(self, part_id: str, new_quantity: int) -> bool:
    #     """
    #     Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
    #     Raises an exception if no part is found or if no identifier is provided.
    #     """
    #     # Update the quantity if the part is found
    #     self.table.update({'quantity': new_quantity}, self.query().part_id == part_id)
    #

    #
    # def decrement_count_repo(self, part_id: str) -> PartModel | None:
    #     query = self.query()
    #     try:
    #         part = self.table.get(query.part_id == part_id)
    #         if part:
    #             new_quantity = part['quantity'] - 1
    #             self.table.update({'quantity': new_quantity}, query.part_id == part_id)
    #
    #             # Fetch the updated part from the database to return the updated quantity
    #             updated_part = self.table.get(query.part_id == part_id)
    #             return updated_part
    #         else:
    #             return None
    #     except Exception as e:
    #         return None
    #
    # def get_all_parts(self) -> List[PartModel]:
    #     return self.table.all()
    #
    # def get_paginated_parts(self, page: int, page_size: int) -> List[PartModel]:
    #     offset = (page - 1) * page_size
    #     return self.table.all()[offset:offset + page_size]
    #
    # def get_total_parts_count(self) -> int:
    #     return len(self.table)
    #

    #
    # def get_child_location_ids(self, parent_id: str) -> List[str]:
    #     """
    #     Recursively retrieve all child location IDs for a given parent location.
    #     """
    #     from MakerMatrix.repositories.location_repositories import LocationRepository
    #     location_repo = LocationRepository()
    #     child_locations = location_repo.get_child_locations(parent_id)
    #
    #     # Extract IDs and recursively find all nested children
    #     child_ids = [loc['id'] for loc in child_locations]
    #     for loc in child_locations:
    #         child_ids.extend(self.get_child_location_ids(loc['id']))
    #
    #     return child_ids

    @staticmethod
    def clear_all_parts(session: Session) -> Dict[str, Any]:
        """Clear all parts from the database - USE WITH CAUTION!"""
        from sqlmodel import text
        try:
            # Get count before deletion
            count_before = session.exec(select(func.count()).select_from(PartModel)).one()
            
            # Temporarily disable foreign key constraints
            session.exec(text("PRAGMA foreign_keys = OFF"))
            
            # Delete all related records in sequence
            deleted_records = {}
            
            # Delete part-category links
            result = session.exec(text("DELETE FROM partcategorylink"))
            deleted_records['part_category_links'] = result.rowcount
            
            # Delete datasheet records
            result = session.exec(text("DELETE FROM datasheetmodel"))
            deleted_records['datasheets'] = result.rowcount
            
            # Delete part order summaries
            result = session.exec(text("DELETE FROM partordersummary"))
            deleted_records['part_order_summaries'] = result.rowcount
            
            # Delete part order links
            result = session.exec(text("DELETE FROM partorderlink"))
            deleted_records['part_order_links'] = result.rowcount
            
            # Delete order items that reference parts (set part_id to NULL instead of deleting)
            result = session.exec(text("UPDATE orderitemmodel SET part_id = NULL WHERE part_id IS NOT NULL"))
            deleted_records['order_item_part_references'] = result.rowcount
            
            # Delete activity logs related to parts
            result = session.exec(text("DELETE FROM activitylogmodel WHERE entity_type = 'part'"))
            deleted_records['activity_logs'] = result.rowcount
            
            # Finally, delete all parts
            session.exec(delete(PartModel))
            
            # Re-enable foreign key constraints
            session.exec(text("PRAGMA foreign_keys = ON"))
            
            session.commit()
            
            # Verify deletion
            count_after = session.exec(select(func.count()).select_from(PartModel)).one()
            
            return {
                "parts_deleted": count_before,
                "parts_remaining": count_after,
                "related_records_deleted": deleted_records,
                "success": True
            }
        except Exception as e:
            # Re-enable foreign keys even on error
            try:
                session.exec(text("PRAGMA foreign_keys = ON"))
            except:
                pass
            session.rollback()
            raise Exception(f"Failed to clear all parts: {str(e)}")
