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

    async def handle_part_enrichment(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Handle comprehensive part enrichment using the supplier configuration system.
        
        Args:
            task: The task model containing enrichment parameters
            progress_callback: Optional callback for progress updates
            
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
            
            # Get the part and determine supplier - access attributes while session is active
            with self.get_session() as session:
                part = self._get_part_by_id_in_session(session, part_id)
                # Determine which supplier to use
                supplier = self._determine_supplier(part, preferred_supplier)
            
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
            
            # Get appropriate part number for the supplier - access attributes while session is active
            with self.get_session() as session:
                fresh_part = self._get_part_by_id_in_session(session, part_id)
                part_number = self._get_supplier_part_number(fresh_part, supplier)
            
            # Progress callback wrapper
            async def enrichment_progress(message):
                if progress_callback:
                    await progress_callback(50, message)
            
            # Perform enrichment
            logger.info(f"Starting unified enrichment for part {part.part_name} using {supplier}")
            if progress_callback:
                await progress_callback(20, f"Enriching part from {supplier}...")
            
            enrichment_result = await client.enrich_part(part_number, supplier_capabilities)
            
            # Process enrichment results
            enrichment_results = self._process_enrichment_result(enrichment_result)
            
            logger.info(f"Enrichment completed: {len(enrichment_result.enriched_fields)} succeeded, {len(enrichment_result.failed_fields)} failed")
            
            if progress_callback:
                await progress_callback(80, "Processing enrichment results...")
            
            # Apply enrichment results to part
            if enrichment_results:
                await self._apply_enrichment_to_part(part, enrichment_results, supplier)
            
            if progress_callback:
                await progress_callback(100, "Enrichment completed")
            
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
            raise

    def _get_part_by_id_in_session(self, session, part_id: str) -> PartModel:
        """Get part by ID using repository within an existing session."""
        part = PartRepository.get_part_by_id(session, part_id)
        if not part:
            raise ValueError(f"Part not found: {part_id}")
        return part

    def _determine_supplier(self, part: PartModel, preferred_supplier: Optional[str]) -> str:
        """Determine which supplier to use for enrichment."""
        supplier = preferred_supplier or part.supplier or part.part_vendor
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
        available_capabilities = supplier_config.get('capabilities', [])
        
        if requested_capabilities:
            # Validate requested capabilities
            invalid_caps = [cap for cap in requested_capabilities if cap not in available_capabilities]
            if invalid_caps:
                raise ValueError(f"Capabilities not supported by {supplier}: {invalid_caps}")
            return requested_capabilities
        else:
            # Use recommended capabilities based on supplier
            if supplier.upper() == 'LCSC':
                recommended = ['fetch_datasheet', 'get_part_details', 'fetch_pricing_stock']
            else:
                recommended = ['fetch_datasheet', 'get_part_details', 'fetch_pricing_stock']
            return [cap for cap in recommended if cap in available_capabilities]

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
        # Implementation would depend on how part numbers are mapped to suppliers
        # For now, use the general part number logic
        return part.part_number or part.lcsc_part_number

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

    async def _apply_enrichment_to_part(self, part: PartModel, enrichment_results: Dict[str, Any], supplier: str) -> None:
        """Apply enrichment results to part using standardized data mapping."""
        logger.info(f"Processing enrichment results using standardized data mapping for part {part.part_name}")
        
        # Convert enrichment results to PartSearchResult for standardized mapping
        part_search_result = self._convert_enrichment_to_part_search_result(
            part, enrichment_results, supplier
        )
        
        if part_search_result:
            # Use EnrichmentDataMapper to get standardized part data
            standardized_data = self.data_mapper.map_supplier_result_to_part_data(
                part_search_result, 
                supplier,
                list(enrichment_results.keys())
            )
            
            # Update part with standardized data
            await self._apply_standardized_data_to_part(part, standardized_data)
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
                    image_url = part_data_result.get('image_url')
                    pricing = part_data_result.get('pricing')
                    stock_quantity = part_data_result.get('stock_quantity')
                    specifications = part_data_result.get('specifications') or {}
                    additional_data = part_data_result.get('additional_data') or {}
                    
                    # Extract core fields from part_data_result
                    manufacturer = part_data_result.get('manufacturer')
                    manufacturer_part_number = part_data_result.get('manufacturer_part_number')
                    description = part_data_result.get('description')
                    category = part_data_result.get('category')
            
            # Create PartSearchResult
            return PartSearchResult(
                part_number=part.part_number or part.lcsc_part_number,
                manufacturer=manufacturer,
                manufacturer_part_number=manufacturer_part_number,
                description=description,
                category=category,
                datasheet_url=datasheet_url,
                primary_image_url=image_url,
                stock_quantity=stock_quantity,
                pricing=pricing,
                specifications=specifications,
                additional_data=additional_data
            )
            
        except Exception as e:
            logger.error(f"Error converting enrichment to PartSearchResult: {e}")
            return None

    async def _apply_standardized_data_to_part(self, part: PartModel, standardized_data: Dict[str, Any]) -> None:
        """Apply standardized data mapping to part using the EnrichmentDataMapper results."""
        try:
            logger.info(f"Applying standardized data to part {part.part_name}")
            
            # Update only fields that exist on PartModel
            model_fields = [
                'manufacturer', 'manufacturer_part_number', 'component_type', 
                'rohs_status', 'lifecycle_status', 'image_url', 'description'
            ]
            
            # Fields that should go into additional_properties instead
            additional_fields = [
                'package', 'mounting_type', 'unit_price', 'currency', 'stock_quantity', 
                'last_stock_update', 'pricing_data', 'last_price_update', 'price_source',
                'last_enrichment_date', 'enrichment_source', 'data_quality_score'
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
            
            # Update additional_properties with fields that don't exist on the model
            if not part.additional_properties:
                part.additional_properties = {}
                
            for field in additional_fields:
                if field in standardized_data and standardized_data[field] is not None:
                    old_value = part.additional_properties.get(field)
                    new_value = standardized_data[field]
                    if old_value != new_value:
                        part.additional_properties[field] = new_value
                        updated_fields.append(f"additional_properties.{field}: '{old_value}' -> '{new_value}'")
            
            # Update last enrichment timestamp
            part.additional_properties['last_enrichment'] = datetime.utcnow().isoformat()
            
            if updated_fields:
                logger.info(f"Updated fields for part {part.part_name}: {updated_fields}")
            
        except Exception as e:
            logger.error(f"Error applying standardized data to part: {e}")
            raise

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
        with self.get_session() as session:
            try:
                # Get fresh part instance in this session
                fresh_part = PartRepository.get_part_by_id(session, part.id)
                if fresh_part:
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
                    
                    PartRepository.update_part(session, fresh_part)
                    logger.info(f"Successfully updated part {part.part_name} with enrichment data")
                else:
                    logger.error(f"Part {part.id} not found in fresh session")
            except Exception as e:
                logger.error(f"Failed to save enrichment results to database: {e}")
                raise