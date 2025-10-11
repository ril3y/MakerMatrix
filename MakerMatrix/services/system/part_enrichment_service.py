"""
PartEnrichmentService - Handles core part enrichment operations.
Extracted from monolithic enrichment_task_handlers.py as part of Step 12.7.
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.services.data.enrichment_data_mapper import EnrichmentDataMapper
from MakerMatrix.services.system.supplier_integration_service import SupplierIntegrationService
from MakerMatrix.services.base_service import BaseService
from MakerMatrix.suppliers.base import SupplierCapability, PartSearchResult
from MakerMatrix.services.activity_service import get_activity_service
from MakerMatrix.services.system.file_download_service import file_download_service

logger = logging.getLogger(__name__)


class PartEnrichmentService(BaseService):
    """
    Service for handling comprehensive part enrichment operations.
    Integrates with suppliers to enhance part data with additional information.
    """

    def __init__(self):
        super().__init__()
        self.supplier_config_service = SupplierConfigService()
        # Initialize data mapper with supplier data mapper
        from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
        self.data_mapper = EnrichmentDataMapper(SupplierDataMapper())
        self.supplier_integration_service = SupplierIntegrationService(self.supplier_config_service)

    async def handle_part_enrichment(self, task: TaskModel, progress_callback: Optional[Callable] = None, session=None) -> Dict[str, Any]:
        """
        Handle comprehensive part enrichment using the supplier configuration system.
        
        Args:
            task: The task model containing enrichment parameters
            progress_callback: Optional callback for progress updates
            session: Optional database session to use (avoids DetachedInstanceError)
            
        Returns:
            Dict containing enrichment results and statistics
        """
        try:
            input_data = task.get_input_data()
            part_id = input_data.get('part_id')
            preferred_supplier = input_data.get('supplier')
            requested_capabilities = input_data.get('capabilities', [])
            force_refresh = input_data.get('force_refresh', False)
            
            logger.info(f"[ENRICHMENT] Starting enrichment for part_id={part_id}, supplier={preferred_supplier}, capabilities={requested_capabilities}")
            
            if not part_id:
                raise ValueError("part_id is required for part enrichment")
            
            # Use provided session or create new one for backward compatibility
            if session is not None:
                # Use provided session - avoid DetachedInstanceError
                return await self._handle_with_session(task, progress_callback, session, part_id, preferred_supplier, requested_capabilities, force_refresh)
            else:
                # Fallback for direct calls - create new session
                with self.get_session() as session:
                    return await self._handle_with_session(task, progress_callback, session, part_id, preferred_supplier, requested_capabilities, force_refresh)
        
        except Exception as e:
            logger.error(f"Error in part enrichment task: {e}", exc_info=True)
            raise
    
    async def _handle_with_session(self, task: TaskModel, progress_callback: Optional[Callable], session, part_id: str, preferred_supplier: str, requested_capabilities: list, force_refresh: bool) -> Dict[str, Any]:
        """Handle enrichment within a session context."""
        client = None
        supplier = None
        try:
            # Get the part and determine supplier - access attributes while session is active
            part = self._get_part_by_id_in_session(session, part_id)

            # Cache part attributes while session is active to avoid DetachedInstanceError
            part_name = part.part_name
            part_supplier = part.supplier
            part_vendor = getattr(part, 'part_vendor', None)
            part_number = part.part_number
            supplier_part_number_field = getattr(part, 'supplier_part_number', None)

            # Determine which supplier to use
            supplier = self._determine_supplier_from_cached_data(part_supplier, part_vendor, preferred_supplier)

            # Get supplier configuration and validate
            supplier_config = self._get_supplier_config(supplier)

            # Determine capabilities to use
            capabilities = self._determine_capabilities(
                supplier, supplier_config, requested_capabilities
            )

            if not capabilities:
                return {"message": "No enrichment capabilities available for this supplier"}

            # Get configured supplier client
            client = self._get_supplier_client(supplier, supplier_config)

            # Convert capabilities to supplier capability enums
            supplier_capabilities = self._convert_capabilities_to_enums(capabilities)

            # Get appropriate part number for the supplier using cached data
            supplier_part_number = self._get_supplier_part_number_from_cached_data(part_number, supplier_part_number_field)

            # Progress callback wrapper
            async def enrichment_progress(message):
                if progress_callback:
                    await progress_callback(50, message)

            # Perform enrichment
            logger.info(f"Starting unified enrichment for part {part_name} using {supplier}")
            if progress_callback:
                await progress_callback(20, f"Enriching part from {supplier}...")

            enrichment_result = await client.enrich_part(supplier_part_number, supplier_capabilities)

            # Process enrichment results
            enrichment_results = self._process_enrichment_result(enrichment_result)

            logger.info(f"Enrichment completed: {len(enrichment_result.enriched_fields)} succeeded, {len(enrichment_result.failed_fields)} failed")

            if progress_callback:
                await progress_callback(80, "Processing enrichment results...")

            # Apply enrichment results to part
            if enrichment_results:
                await self._apply_enrichment_to_part(part, enrichment_results, supplier, task)

            if progress_callback:
                await progress_callback(100, "Enrichment completed")

            # Log successful enrichment activity
            try:
                activity_service = get_activity_service()
                user = self._get_user_from_task(task)
                await activity_service.log_activity(
                    action="enriched",
                    entity_type="part",
                    entity_id=part_id,
                    entity_name=part_name,
                    user=user,
                    details={
                        "supplier": supplier,
                        "capabilities": capabilities,
                        "successful_count": len(enrichment_result.enriched_fields),
                        "failed_count": len(enrichment_result.failed_fields)
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to log enrichment activity: {log_error}")

            return {
                "part_id": part_id,
                "supplier": supplier,
                "successful_enrichments": enrichment_result.enriched_fields,
                "failed_enrichments": self._format_failed_enrichments(enrichment_result),
                "total_capabilities": len(capabilities),
                "completed_capabilities": len(enrichment_result.enriched_fields)
            }

        except Exception as e:
            logger.error(f"Error in part enrichment task: {e}", exc_info=True)

            # Log failed enrichment activity
            try:
                activity_service = get_activity_service()
                user = self._get_user_from_task(task)
                await activity_service.log_activity(
                    action="enrichment_failed",
                    entity_type="part",
                    entity_id=part_id,
                    entity_name=part_name if 'part_name' in locals() else "Unknown",
                    user=user,
                    details={
                        "supplier": supplier if supplier else "Unknown",
                        "error": str(e)
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to log enrichment failure activity: {log_error}")

            raise
        finally:
            # Always clean up supplier resources
            if client:
                try:
                    await client.close()
                    logger.debug(f"Cleaned up supplier {supplier} resources in enrichment task")
                except Exception as e:
                    logger.warning(f"Error closing supplier {supplier} in enrichment: {e}")

    def _get_part_by_id_in_session(self, session, part_id: str) -> PartModel:
        """Get part by ID using repository within an existing session."""
        part = PartRepository.get_part_by_id(session, part_id)
        if not part:
            raise ValueError(f"Part not found: {part_id}")
        
        # Ensure part is bound to the current session
        session.refresh(part)
        return part

    def _determine_supplier(self, part: PartModel, preferred_supplier: Optional[str]) -> str:
        """Determine which supplier to use for enrichment."""
        supplier = preferred_supplier or part.supplier or part.part_vendor
        if not supplier:
            raise ValueError("No supplier specified for part enrichment")
        return supplier
    
    def _determine_supplier_from_cached_data(self, part_supplier: Optional[str], part_vendor: Optional[str], preferred_supplier: Optional[str]) -> str:
        """Determine which supplier to use for enrichment using cached data."""
        supplier = preferred_supplier or part_supplier or part_vendor
        if not supplier:
            raise ValueError("No supplier specified for part enrichment")
        return supplier

    def _get_supplier_config(self, supplier: str) -> Any:
        """Get and validate supplier configuration."""
        try:
            supplier_config = self.supplier_config_service.get_supplier_config(supplier.upper())
        except Exception as e:
            raise ValueError(f"Supplier configuration not found for: {supplier}") from e
        
        if not supplier_config.get('enabled', False):
            raise ValueError(f"Supplier {supplier} is not enabled")
        
        return supplier_config

    def _determine_capabilities(
        self, 
        supplier: str, 
        supplier_config: Any, 
        requested_capabilities: List[str]
    ) -> List[str]:
        """Determine which capabilities to use for enrichment."""
        # Get actual capabilities from the supplier implementation rather than database config
        try:
            from MakerMatrix.suppliers.registry import get_supplier_registry
            supplier_registry = get_supplier_registry()
            supplier_class = supplier_registry.get(supplier.lower())
            if supplier_class:
                supplier_instance = supplier_class()
                actual_capabilities = [cap.value for cap in supplier_instance.get_capabilities()]
            else:
                # Fallback to database config if supplier not found
                actual_capabilities = supplier_config.get('capabilities', [])
        except Exception:
            # Fallback to database config if there's any error
            actual_capabilities = supplier_config.get('capabilities', [])
        
        if requested_capabilities:
            # Validate requested capabilities against actual supplier capabilities
            invalid_caps = [cap for cap in requested_capabilities if cap not in actual_capabilities]
            if invalid_caps:
                raise ValueError(f"Capabilities not supported by {supplier}: {invalid_caps}")
            return requested_capabilities
        else:
            # Use recommended capabilities based on supplier
            if supplier.upper() == 'LCSC':
                recommended = ['fetch_datasheet', 'get_part_details', 'fetch_pricing_stock']
            else:
                recommended = ['fetch_datasheet', 'get_part_details', 'fetch_pricing_stock']
            return [cap for cap in recommended if cap in actual_capabilities]

    def _get_supplier_client(self, supplier: str, supplier_config: Any) -> Any:
        """Get and configure supplier client."""
        from MakerMatrix.suppliers.registry import get_supplier
        
        client = get_supplier(supplier.lower())
        if not client:
            raise ValueError(f"Supplier implementation not found for: {supplier}")
        
        # Configure the supplier with credentials and config
        credentials = self.supplier_config_service.get_supplier_credentials(supplier.upper())
        config = supplier_config.get('custom_parameters', {})
        client.configure(credentials or {}, config)
        
        return client

    def _convert_capabilities_to_enums(self, capabilities: List[str]) -> List[SupplierCapability]:
        """Convert capability strings to SupplierCapability enums."""
        capability_map = {
            'fetch_datasheet': SupplierCapability.FETCH_DATASHEET,
            'fetch_details': SupplierCapability.GET_PART_DETAILS,
            'get_part_details': SupplierCapability.GET_PART_DETAILS,  # Frontend sends this
            'fetch_pricing_stock': SupplierCapability.FETCH_PRICING_STOCK,
            'import_orders': SupplierCapability.IMPORT_ORDERS
        }
        
        supplier_capabilities = []
        for cap in capabilities:
            if cap in capability_map:
                supplier_capabilities.append(capability_map[cap])
        
        return supplier_capabilities

    def _get_supplier_part_number(self, part: PartModel, supplier: str) -> str:
        """Get the appropriate part number for the supplier."""
        # Prefer supplier-specific part number over general part number
        # supplier_part_number is the field specifically for supplier APIs
        return part.supplier_part_number or part.part_number or ""
        
    def _get_supplier_part_number_from_cached_data(self, part_number: Optional[str], supplier_part_number: Optional[str]) -> str:
        """Get the appropriate part number for the supplier using cached data."""
        # Prefer supplier-specific part number over general part number
        # supplier_part_number is the field specifically for supplier APIs (e.g., LCSC: C25804)
        # part_number is typically the manufacturer part number
        return supplier_part_number or part_number or ""

    def _process_enrichment_result(self, enrichment_result: Any) -> Dict[str, Any]:
        """Process enrichment result into expected format."""
        enrichment_results = {}
        
        # Map enriched fields back to capability names
        field_to_capability_map = {
            'part_details': 'fetch_details',
            'datasheet_url': 'fetch_datasheet',
            'image_url': 'get_part_details',
            'pricing': 'fetch_pricing_stock',
            'stock_quantity': 'fetch_pricing_stock',
            'specifications': 'get_part_details'
        }
        
        if enrichment_result.success and enrichment_result.data:
            # Convert enriched fields to the expected enrichment_results format
            part_data = enrichment_result.data
            
            for field, cap_name in field_to_capability_map.items():
                if field in enrichment_result.enriched_fields:
                    value = getattr(part_data, field, None)
                    if value is not None:
                        # Wrap in the expected format for the conversion method
                        enrichment_results[cap_name] = {
                            'success': True,
                            field: value
                        }
            
            # Also add the full part data for direct access
            enrichment_results['part_data'] = {
                'success': True,
                'manufacturer': part_data.manufacturer,
                'manufacturer_part_number': part_data.manufacturer_part_number,
                'description': part_data.description,
                'datasheet_url': part_data.datasheet_url,
                'image_url': part_data.image_url,
                'category': part_data.category,
                'stock_quantity': part_data.stock_quantity,
                'pricing': part_data.pricing,
                'specifications': part_data.specifications,
                'additional_data': part_data.additional_data or {}
            }
        
        return enrichment_results

    def _format_failed_enrichments(self, enrichment_result: Any) -> List[Dict[str, str]]:
        """Format failed enrichments for response."""
        field_to_capability_map = {
            'part_details': 'fetch_details',
            'datasheet_url': 'fetch_datasheet',
            'image_url': 'get_part_details',
            'pricing': 'fetch_pricing_stock',
            'stock_quantity': 'fetch_pricing_stock',
            'specifications': 'get_part_details'
        }
        
        failed_enrichments = []
        for field in enrichment_result.failed_fields:
            cap_name = field_to_capability_map.get(field, field)
            error_msg = enrichment_result.errors.get(field, "Enrichment failed")
            failed_enrichments.append({"capability": cap_name, "error": error_msg})
        
        return failed_enrichments

    async def _apply_enrichment_to_part(self, part: PartModel, enrichment_results: Dict[str, Any], supplier: str, task: TaskModel) -> None:
        """Apply enrichment results to part using standardized data mapping."""
        logger.info(f"Processing enrichment results using standardized data mapping for part {part.part_name}")

        # Convert enrichment results to PartSearchResult for standardized mapping
        part_search_result = self._convert_enrichment_to_part_search_result(
            part, enrichment_results, supplier
        )

        if part_search_result:
            # Use SupplierDataMapper to get standardized part data
            standardized_data = self.data_mapper.supplier_data_mapper.map_supplier_result_to_part_data(
                part_search_result,
                supplier,
                list(enrichment_results.keys())
            )

            # Update part with standardized data
            await self._apply_standardized_data_to_part(part, standardized_data, supplier, task)
            logger.info(f"✅ Applied standardized data mapping for part {part.part_name}")
        else:
            # Fallback to legacy enrichment result processing
            logger.warning(f"Could not convert to PartSearchResult, using legacy processing for part {part.part_name}")
            await self._apply_legacy_enrichment_to_part(part, enrichment_results)

        # Save updated part to database
        await self._save_part_to_database(part)

    def _convert_enrichment_to_part_search_result(
        self, 
        part: PartModel, 
        enrichment_results: Dict[str, Any], 
        supplier_name: str
    ) -> Optional[PartSearchResult]:
        """Convert enrichment results to PartSearchResult for standardized data mapping."""
        try:
            # Extract data from enrichment results
            datasheet_url = None
            image_url = None
            pricing = None
            stock_quantity = None
            specifications = {}
            additional_data = {}
            
            # Initialize core field variables
            manufacturer = None
            manufacturer_part_number = None
            description = None
            category = None
            
            # Check if we have the consolidated part_data
            if 'part_data' in enrichment_results:
                part_data_result = enrichment_results['part_data']
                if isinstance(part_data_result, dict) and part_data_result.get('success'):
                    # Extract data directly from the unified part data
                    datasheet_url = part_data_result.get('datasheet_url')
                    logger.info(f"[DATASHEET DEBUG] Extracted datasheet_url from part_data: {datasheet_url}")
                    image_url = part_data_result.get('image_url')
                    pricing = part_data_result.get('pricing')
                    stock_quantity = part_data_result.get('stock_quantity')
                    # NO LONGER extracting specifications separately - flatten them into additional_data
                    specifications_data = part_data_result.get('specifications') or {}
                    additional_data = part_data_result.get('additional_data') or {}

                    # Flatten any nested specifications directly into additional_data
                    flattened_specs = self._flatten_nested_objects(specifications_data) if specifications_data else {}
                    additional_data.update(flattened_specs)
                    
                    # Extract core fields from part_data_result
                    manufacturer = part_data_result.get('manufacturer')
                    manufacturer_part_number = part_data_result.get('manufacturer_part_number')
                    description = part_data_result.get('description')
                    category = part_data_result.get('category')
            
            # Create PartSearchResult
            # Use the supplier part number from the part (which was provided in the enrichment modal)
            # or fall back to the enriched supplier part number from additional_data
            result = PartSearchResult(
                supplier_part_number=part.supplier_part_number or additional_data.get(f'{supplier_name.lower()}_part_number', '') or part.part_number or "",
                manufacturer=manufacturer,
                manufacturer_part_number=manufacturer_part_number,
                description=description,
                category=category,
                datasheet_url=datasheet_url,
                image_url=image_url,
                stock_quantity=stock_quantity,
                pricing=pricing,
                specifications={},  # No longer using nested specifications - all data in additional_data
                additional_data=additional_data
            )
            logger.info(f"[DATASHEET DEBUG] Created PartSearchResult with datasheet_url: {result.datasheet_url}")
            return result
            
        except Exception as e:
            logger.error(f"Error converting enrichment to PartSearchResult: {e}")
            return None

    async def _apply_standardized_data_to_part(self, part: PartModel, standardized_data: Dict[str, Any], supplier: str, task: TaskModel) -> None:
        """Apply standardized data mapping to part using the EnrichmentDataMapper results."""
        try:
            logger.info(f"Applying standardized data to part {part.part_name}")
            logger.debug(f"Standardized data keys: {list(standardized_data.keys())}")
            if 'additional_properties' in standardized_data:
                logger.debug(f"Additional properties keys: {list(standardized_data['additional_properties'].keys())}")

            logger.info(f"[APPLY DEBUG] Before applying: part.supplier_part_number = '{part.supplier_part_number}'")
            logger.info(f"[APPLY DEBUG] Standardized data has supplier_part_number = '{standardized_data.get('supplier_part_number')}'")

            # Update only fields that exist on PartModel
            model_fields = [
                'manufacturer', 'manufacturer_part_number', 'component_type',
                'image_url', 'description', 'supplier_part_number'
            ]

            # Fields that should go into additional_properties instead
            additional_fields = [
                'package', 'mounting_type', 'unit_price', 'currency', 'stock_quantity',
                'last_stock_update', 'pricing_data', 'last_price_update', 'price_source',
                'last_enrichment_date', 'enrichment_source', 'data_quality_score',
                'rohs_status', 'lifecycle_status'  # Moved from model_fields to additional_properties
            ]
            
            updated_fields = []

            # Update direct model fields
            for field in model_fields:
                if field in standardized_data:
                    old_value = getattr(part, field, None)
                    new_value = standardized_data[field]

                    # Only update if the new value is different and not None
                    if new_value is not None and old_value != new_value:
                        setattr(part, field, new_value)
                        updated_fields.append(f"{field}: '{old_value}' -> '{new_value}'")
                        logger.info(f"[APPLY DEBUG] Set part.{field} = '{new_value}'")

            logger.info(f"[APPLY DEBUG] After field updates: part.supplier_part_number = '{part.supplier_part_number}'")
            
            # Update additional_properties with fields that don't exist on the model
            if not part.additional_properties:
                part.additional_properties = {}
                
            for field in additional_fields:
                if field in standardized_data and standardized_data[field] is not None:
                    old_value = part.additional_properties.get(field)
                    new_value = standardized_data[field]
                    
                    # Ensure JSON serializable values
                    new_value = self._ensure_json_serializable(new_value)
                    
                    if old_value != new_value:
                        part.additional_properties[field] = new_value
                        updated_fields.append(f"additional_properties.{field}: '{old_value}' -> '{new_value}'")

            # Merge structured additional_properties payload from standardized data
            # Flatten any nested objects to keep database schema simple
            additional_payload = standardized_data.get('additional_properties')
            if isinstance(additional_payload, dict):
                serialized_payload = self._ensure_json_serializable(additional_payload)
                flattened_payload = self._flatten_nested_objects(serialized_payload)
                payload_updates = self._merge_additional_properties_dict(
                    part.additional_properties,
                    flattened_payload,
                    path='additional_properties'
                )
                updated_fields.extend(payload_updates)

            # Create a background task for datasheet download if URL is present
            # Check both top-level and additional_properties for datasheet_url
            datasheet_url = (
                standardized_data.get('additional_properties', {}).get('datasheet_url') or
                part.additional_properties.get('datasheet_url')
            )

            if datasheet_url:
                logger.info(f"Found datasheet URL for {part.part_name}: {datasheet_url}")
                if not part.additional_properties.get('datasheet_downloaded'):
                    # Create a datasheet download task instead of downloading synchronously
                    logger.info(f"Creating datasheet download task for {part.part_name}")
                    await self._create_datasheet_download_task(part, datasheet_url, supplier, task)
                else:
                    logger.info(f"Datasheet already downloaded for {part.part_name}, skipping")

            # Update last enrichment timestamp
            part.additional_properties['last_enrichment'] = datetime.utcnow().isoformat()

            if updated_fields:
                logger.info(f"Updated fields for part {part.part_name}: {updated_fields}")

        except Exception as e:
            logger.error(f"Error applying standardized data to part: {e}")
            raise

    def _ensure_json_serializable(self, value):
        """Ensure a value is JSON serializable by converting datetime objects to strings."""
        if hasattr(value, 'isoformat'):  # datetime object
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: self._ensure_json_serializable(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self._ensure_json_serializable(item) for item in value]
        else:
            return value

    def _merge_additional_properties_dict(self, current: Dict[str, Any], updates: Dict[str, Any], path: str = '') -> List[str]:
        """Recursively merge additional_properties dictionaries."""
        updated_fields: List[str] = []

        for key, value in updates.items():
            full_path = f"{path}.{key}" if path else key

            if isinstance(value, dict):
                existing = current.get(key)
                if not isinstance(existing, dict):
                    old_value = existing
                    current[key] = {}
                    updated_fields.append(f"{full_path}: '{old_value}' -> '{{}}'")
                    existing = current[key]
                updated_fields.extend(
                    self._merge_additional_properties_dict(existing, value, full_path)
                )
            else:
                old_value = current.get(key)
                if old_value != value:
                    current[key] = value
                    updated_fields.append(f"{full_path}: '{old_value}' -> '{value}'")

        return updated_fields

    def _flatten_nested_objects(self, obj: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """
        Flatten nested objects into simple key-value pairs.

        Example:
        {"specifications": {"voltage": "3.3V", "package": "SOT-23"}}
        becomes:
        {"voltage": "3.3V", "package": "SOT-23"}

        Args:
            obj: Dictionary that may contain nested objects
            prefix: Optional prefix for keys (used in recursion)

        Returns:
            Flattened dictionary with simple key-value pairs
        """
        flattened = {}

        for key, value in obj.items():
            if isinstance(value, dict):
                # For certain known nested structures, flatten them directly
                if key.lower() in ['specifications', 'technical_specs', 'attributes', 'specs']:
                    # Flatten the nested object directly without prefixing
                    nested_flattened = self._flatten_nested_objects(value, '')
                    flattened.update(nested_flattened)
                else:
                    # For other nested objects, use a prefix
                    current_prefix = f"{prefix}{key}_" if prefix else f"{key}_"
                    nested_flattened = self._flatten_nested_objects(value, current_prefix)
                    flattened.update(nested_flattened)
            else:
                # Simple value - add with appropriate key
                final_key = f"{prefix}{key}" if prefix else key
                # Clean up the key to be more readable
                final_key = final_key.lower().replace(' ', '_').replace('-', '_')
                flattened[final_key] = value

        return flattened

    async def _apply_legacy_enrichment_to_part(self, part: PartModel, enrichment_results: Dict[str, Any]) -> None:
        """Apply enrichment results using legacy processing."""
        if not part.additional_properties:
            part.additional_properties = {}
        
        # Store only essential enrichment metadata instead of full results
        enrichment_metadata = self._create_enrichment_metadata(enrichment_results)
        part.additional_properties.update(enrichment_metadata)
        part.additional_properties['last_enrichment'] = datetime.utcnow().isoformat()

    def _create_enrichment_metadata(self, enrichment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create enrichment metadata from results."""
        metadata = {}
        
        # Extract key information from enrichment results
        for key, result in enrichment_results.items():
            if isinstance(result, dict) and result.get('success'):
                metadata[f"{key}_enriched"] = True
                metadata[f"{key}_timestamp"] = datetime.utcnow().isoformat()
        
        return metadata

    async def _save_part_to_database(self, part: PartModel) -> None:
        """Save updated part to database with proper session handling."""
        logger.info(f"[SAVE DEBUG] _save_part_to_database called for part {part.part_name}")
        logger.info(f"[SAVE DEBUG] In-memory part.supplier_part_number = '{part.supplier_part_number}'")

        with self.get_session() as session:
            try:
                # Get fresh part instance in this session
                fresh_part = PartRepository.get_part_by_id(session, part.id)
                if fresh_part:
                    logger.info(f"[SAVE DEBUG] Fresh part from DB: supplier_part_number = '{fresh_part.supplier_part_number}'")

                    # Update main part fields that were enriched
                    if part.manufacturer and part.manufacturer != fresh_part.manufacturer:
                        logger.info(f"Updating part manufacturer: '{fresh_part.manufacturer}' -> '{part.manufacturer}'")
                        fresh_part.manufacturer = part.manufacturer

                    if part.manufacturer_part_number and part.manufacturer_part_number != fresh_part.manufacturer_part_number:
                        logger.info(f"Updating part manufacturer_part_number: '{fresh_part.manufacturer_part_number}' -> '{part.manufacturer_part_number}'")
                        fresh_part.manufacturer_part_number = part.manufacturer_part_number

                    if part.description and part.description != fresh_part.description:
                        logger.info(f"Updating part description: '{fresh_part.description}' -> '{part.description}'")
                        fresh_part.description = part.description

                    if part.image_url and part.image_url != fresh_part.image_url:
                        logger.info(f"Updating part image URL: '{fresh_part.image_url}' -> '{part.image_url}'")
                        fresh_part.image_url = part.image_url

                    # ALWAYS update supplier_part_number if it exists on the in-memory part, even if it's the same
                    # This ensures the value persists through the enrichment process
                    if part.supplier_part_number is not None:
                        logger.info(f"[SAVE DEBUG] Updating part supplier_part_number: '{fresh_part.supplier_part_number}' -> '{part.supplier_part_number}'")
                        fresh_part.supplier_part_number = part.supplier_part_number
                    else:
                        logger.info(f"[SAVE DEBUG] part.supplier_part_number is None, not updating")

                    # Update additional_properties
                    if not fresh_part.additional_properties:
                        fresh_part.additional_properties = {}
                    
                    fresh_part.additional_properties.update(part.additional_properties)
                    
                    # Force SQLAlchemy to recognize the changes
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(fresh_part, 'additional_properties')
                    if part.manufacturer:
                        flag_modified(fresh_part, 'manufacturer')
                    if part.manufacturer_part_number:
                        flag_modified(fresh_part, 'manufacturer_part_number')
                    if part.description:
                        flag_modified(fresh_part, 'description')
                    if part.image_url:
                        flag_modified(fresh_part, 'image_url')
                    if part.supplier_part_number:
                        flag_modified(fresh_part, 'supplier_part_number')

                    PartRepository.update_part(session, fresh_part)
                    logger.info(f"Successfully updated part {part.part_name} with enrichment data")
                else:
                    logger.error(f"Part {part.id} not found in fresh session")
            except Exception as e:
                logger.error(f"Failed to save enrichment results to database: {e}")
                raise

    async def _create_datasheet_download_task(self, part: PartModel, datasheet_url: str, supplier: str, parent_task: TaskModel) -> None:
        """
        Create a background task to download datasheet file for a part.

        Args:
            part: The part model with datasheet URL
            datasheet_url: URL of the datasheet to download
            supplier: Supplier name
            parent_task: The parent enrichment task for user tracking
        """
        try:
            logger.info(f"Creating datasheet download task for part {part.part_name}")

            # Get part number for filename
            part_number = part.supplier_part_number or part.part_number or part.id

            # Import here to avoid circular dependency
            from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
            from MakerMatrix.services.system.task_service import task_service

            # Create task request for datasheet download
            task_request = CreateTaskRequest(
                task_type=TaskType.DATASHEET_DOWNLOAD,
                name=f"Download datasheet for {part.part_name}",
                description=f"Download datasheet from {supplier} for part {part.part_name}",
                priority=TaskPriority.NORMAL,
                input_data={
                    'part_id': part.id,
                    'datasheet_url': datasheet_url,
                    'supplier': supplier,
                    'part_number': part_number
                },
                related_entity_type='part',
                related_entity_id=part.id,
                parent_task_id=parent_task.id if parent_task else None
            )

            # Create the task using the same user as the parent task
            user_id = parent_task.created_by_user_id if parent_task else None
            task_response = await task_service.create_task(task_request, user_id=user_id)

            if task_response.success:
                logger.info(f"✅ Created datasheet download task {task_response.data['id']} for {part.part_name}")
                # Mark that download is pending
                part.additional_properties['datasheet_download_pending'] = True
            else:
                logger.error(f"Failed to create datasheet download task: {task_response.message}")
                part.additional_properties['datasheet_downloaded'] = False

        except Exception as e:
            logger.error(f"Error creating datasheet download task for part {part.part_name}: {e}")
            part.additional_properties['datasheet_downloaded'] = False
            part.additional_properties['datasheet_download_error'] = str(e)

    def _get_user_from_task(self, task: TaskModel) -> Optional[Any]:
        """Get user object from task's created_by_user_id."""
        if not task.created_by_user_id:
            return None

        try:
            from MakerMatrix.repositories.user_repository import UserRepository
            user_repo = UserRepository()
            with self.get_session() as session:
                return user_repo.get_user_by_id(task.created_by_user_id)
        except Exception as e:
            logger.warning(f"Failed to get user for task: {e}")
            return None
