"""
Task handlers for enrichment operations.
These handlers integrate the supplier configuration system with the task system.
Now includes standardized data mapping for consistent UI display across suppliers.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlmodel import select, Session
from MakerMatrix.models.task_models import TaskModel, TaskStatus, TaskType
from MakerMatrix.models.models import PartModel, DatasheetModel, CategoryModel
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
from MakerMatrix.suppliers.base import PartSearchResult


logger = logging.getLogger(__name__)


class EnrichmentTaskHandlers:
    """Handlers for enrichment task operations with standardized data mapping"""
    
    def __init__(self, part_repository: PartRepository, part_service: PartService, download_config=None):
        self.part_repository = part_repository
        self.part_service = part_service
        self.supplier_config_service = SupplierConfigService()
        self.download_config = download_config or self._get_csv_import_config()
        self.data_mapper = SupplierDataMapper()
    
    def _get_csv_import_config(self) -> dict:
        """Get the current CSV import configuration for download settings"""
        try:
            from MakerMatrix.database.db import get_session
            from MakerMatrix.models.csv_import_config_model import CSVImportConfigModel
            from sqlmodel import select
            
            session = next(get_session())
            try:
                config = session.exec(select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")).first()
                if config:
                    return config.to_dict()
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Failed to get CSV import config, using defaults: {e}")
        
        # Return default configuration
        return {
            'download_datasheets': True,
            'download_images': True,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30
        }
    
    @staticmethod
    def _convert_enrichment_to_part_search_result(
            part: PartModel,
        enrichment_results: Dict[str, Any], 
        supplier_name: str
    ) -> Optional[PartSearchResult]:
        """
        Convert enrichment results to PartSearchResult for standardized data mapping.
        This allows us to use the SupplierDataMapper with enrichment data.
        """
        try:
            # Extract data from enrichment results
            datasheet_url = None
            image_url = None
            pricing = None
            stock_quantity = None
            specifications = {}
            additional_data = {}
            
            # Process each enrichment result
            for capability, result_data in enrichment_results.items():
                if not isinstance(result_data, dict) or not result_data.get('success'):
                    continue
                    
                if capability == 'fetch_datasheet' and result_data.get('datasheet_url'):
                    datasheet_url = result_data['datasheet_url']
                    
                elif capability == 'fetch_image':
                    if result_data.get('primary_image_url'):
                        image_url = result_data['primary_image_url']
                    elif result_data.get('images') and len(result_data['images']) > 0:
                        first_image = result_data['images'][0]
                        if isinstance(first_image, dict) and 'url' in first_image:
                            image_url = first_image['url']
                            
                elif capability == 'fetch_pricing' and result_data.get('pricing'):
                    pricing = result_data['pricing']
                    
                elif capability == 'fetch_stock' and result_data.get('quantity_available') is not None:
                    stock_quantity = result_data['quantity_available']
                    
                elif capability == 'fetch_specifications' and result_data.get('specifications'):
                    specifications.update(result_data['specifications'])
                    
                elif capability == 'fetch_details':
                    # Add any additional details to additional_data
                    for key, value in result_data.items():
                        if key not in ['success']:
                            additional_data[key] = value
            
            # Create PartSearchResult from enrichment data and existing part data
            return PartSearchResult(
                supplier_part_number=part.part_number or part.manufacturer_part_number or part.part_name,
                manufacturer=part.manufacturer or additional_data.get('manufacturer'),
                manufacturer_part_number=part.manufacturer_part_number or additional_data.get('manufacturer_part_number'),
                description=part.description or additional_data.get('product_description') or additional_data.get('description'),
                category=additional_data.get('category'),
                datasheet_url=datasheet_url,
                image_url=image_url,
                pricing=pricing,
                stock_quantity=stock_quantity,
                specifications=specifications,
                additional_data={
                    **additional_data,
                    'enrichment_source': supplier_name,
                    'enrichment_timestamp': datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to convert enrichment results to PartSearchResult: {e}")
            return None
    
    async def handle_part_enrichment(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """
        Handle comprehensive part enrichment using the new supplier configuration system.
        
        Input data should contain:
        - part_id: ID of the part to enrich
        - supplier: Preferred supplier (optional)
        - capabilities: List of capabilities to use (optional, defaults to recommended)
        - force_refresh: Whether to re-enrich already enriched data (default: False)
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
            
            # Get the part using session
            from MakerMatrix.database.db import get_session
            session = next(get_session())
            try:
                part = PartRepository.get_part_by_id(session, part_id)
                if not part:
                    raise ValueError(f"Part not found: {part_id}")
            finally:
                session.close()
            
            # Determine which supplier to use
            supplier = preferred_supplier or part.supplier or part.part_vendor
            if not supplier:
                raise ValueError("No supplier specified for part enrichment")
            
            # Use the new supplier configuration system
            supplier_service = SupplierConfigService()
            
            try:
                supplier_config = supplier_service.get_supplier_config(supplier.upper())
            except Exception as e:
                raise ValueError(f"Supplier configuration not found for: {supplier}")
            
            if not supplier_config.enabled:
                raise ValueError(f"Supplier {supplier} is not enabled")
            
            # Get available capabilities for this supplier
            available_capabilities = supplier_config.get_capabilities()
            
            # Determine capabilities to use
            if requested_capabilities:
                # Validate requested capabilities are available
                invalid_caps = [cap for cap in requested_capabilities if cap not in available_capabilities]
                if invalid_caps:
                    raise ValueError(f"Capabilities not supported by {supplier}: {invalid_caps}")
                capabilities = requested_capabilities
            else:
                # Use recommended capabilities based on supplier
                if supplier.upper() == 'LCSC':
                    recommended = ['fetch_datasheet', 'fetch_image', 'fetch_specifications']
                else:
                    recommended = ['fetch_datasheet', 'fetch_image', 'fetch_pricing', 'fetch_stock']
                capabilities = [cap for cap in recommended if cap in available_capabilities]
            
            if not capabilities:
                return {"message": "No enrichment capabilities available for this supplier"}
            
            # Create new supplier instance 
            from MakerMatrix.suppliers.registry import get_supplier
            
            client = get_supplier(supplier.lower())
            if not client:
                raise ValueError(f"Supplier implementation not found for: {supplier}")
            
            # Configure the supplier with credentials and config
            credentials = supplier_service.get_supplier_credentials(supplier.upper(), decrypt=True)
            config = supplier_config.custom_parameters or {}
            client.configure(credentials or {}, config)
            
            # Convert capability strings to SupplierCapability enums
            from MakerMatrix.suppliers.base import SupplierCapability
            capability_map = {
                'fetch_datasheet': SupplierCapability.FETCH_DATASHEET,
                'fetch_image': SupplierCapability.FETCH_IMAGE,
                'fetch_pricing': SupplierCapability.FETCH_PRICING,
                'fetch_stock': SupplierCapability.FETCH_STOCK,
                'fetch_details': SupplierCapability.GET_PART_DETAILS,
                'fetch_specifications': SupplierCapability.FETCH_SPECIFICATIONS
            }
            
            supplier_capabilities = []
            for cap in capabilities:
                if cap in capability_map:
                    supplier_capabilities.append(capability_map[cap])
            
            # Use the appropriate part number for the supplier
            part_number = self._get_supplier_part_number(part, supplier)
            
            # Progress callback wrapper
            async def enrichment_progress(message):
                if progress_callback:
                    await progress_callback(50, message)
            
            # Use the new unified enrich_part method
            logger.info(f"Starting unified enrichment for part {part.part_name} using {supplier}")
            if progress_callback:
                await progress_callback(20, f"Enriching part from {supplier}...")
            
            enrichment_result = await client.enrich_part(part_number, supplier_capabilities)
            
            # Convert EnrichmentResult to the expected format
            enrichment_results = {}
            successful_enrichments = enrichment_result.enriched_fields if enrichment_result.success else []
            failed_enrichments = []
            
            # Map enriched fields back to capability names
            field_to_capability_map = {
                'part_details': 'fetch_details',
                'datasheet_url': 'fetch_datasheet',
                'image_url': 'fetch_image',
                'pricing': 'fetch_pricing',
                'stock_quantity': 'fetch_stock',
                'specifications': 'fetch_specifications'
            }
            
            if enrichment_result.success and enrichment_result.data:
                # Convert enriched fields to the expected enrichment_results format
                part_data = enrichment_result.data
                
                for field, cap_name in field_to_capability_map.items():
                    if field in enrichment_result.enriched_fields:
                        value = getattr(part_data, field, None)
                        if value is not None:
                            enrichment_results[cap_name] = self._serialize_for_json(value)
            
            # Add failed fields to failed_enrichments
            for field in enrichment_result.failed_fields:
                cap_name = field_to_capability_map.get(field, field)
                error_msg = enrichment_result.errors.get(field, "Enrichment failed")
                failed_enrichments.append({"capability": cap_name, "error": error_msg})
            
            logger.info(f"Enrichment completed: {len(successful_enrichments)} succeeded, {len(failed_enrichments)} failed")
            
            if progress_callback:
                await progress_callback(80, "Processing enrichment results...")
                
            # Update part with enrichment results using standardized data mapping
            if enrichment_results:
                logger.info(f"Processing enrichment results using standardized data mapping for part {part.part_name}")
                
                # Convert enrichment results to PartSearchResult for standardized mapping
                part_search_result = self._convert_enrichment_to_part_search_result(
                    part, enrichment_results, supplier
                )
                
                if part_search_result:
                    # Use SupplierDataMapper to get standardized part data
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
                    if not part.additional_properties:
                        part.additional_properties = {}
                    
                    # Store only essential enrichment metadata instead of full results
                    enrichment_metadata = self._create_enrichment_metadata(enrichment_results)
                    part.additional_properties.update(enrichment_metadata)
                    part.additional_properties['last_enrichment'] = datetime.utcnow().isoformat()
                    
                    # Update specific part fields based on enrichment data (without duplication)
                    await self._update_part_from_enrichment_results(part, enrichment_results)
                
                # Update the part in database using a fresh session to avoid conflicts
                from MakerMatrix.database.db import engine
                from sqlalchemy.orm import Session
                with Session(engine) as fresh_session:
                    try:
                        # Get fresh part instance in this session
                        fresh_part = fresh_session.query(PartModel).filter(PartModel.id == part.id).first()
                        if fresh_part:
                            # Update main part fields that were enriched
                            if part.description and part.description != fresh_part.description:
                                logger.info(f"Updating part description: '{fresh_part.description}' -> '{part.description}'")
                                fresh_part.description = part.description
                            
                            if part.image_url and part.image_url != fresh_part.image_url:
                                logger.info(f"Updating part image URL: '{fresh_part.image_url}' -> '{part.image_url}'")
                                fresh_part.image_url = part.image_url
                            
                            # Update additional_properties
                            if not fresh_part.additional_properties:
                                fresh_part.additional_properties = {}
                            
                            # Log before and after
                            logger.info(f"Before update - additional_properties keys: {list(fresh_part.additional_properties.keys())}")
                            logger.info(f"Updating with data: {part.additional_properties}")
                            
                            fresh_part.additional_properties.update(part.additional_properties)
                            
                            # Force SQLAlchemy to recognize the changes
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(fresh_part, 'additional_properties')
                            if part.description:
                                flag_modified(fresh_part, 'description')
                            if part.image_url:
                                flag_modified(fresh_part, 'image_url')
                            
                            fresh_session.commit()
                            
                            # Verify the save using standardized structure
                            fresh_session.refresh(fresh_part)
                            datasheet_url = fresh_part.get_datasheet_url()
                            if datasheet_url:
                                logger.info(f"✅ Successfully saved datasheet URL: {datasheet_url}")
                            else:
                                logger.info(f"ℹ️ No datasheet URL found in standardized structure. Keys: {list(fresh_part.additional_properties.keys())}")
                            
                            logger.info(f"Successfully updated part {part.part_name} with enrichment data")
                        else:
                            logger.error(f"Part {part.id} not found in fresh session")
                    except Exception as e:
                        fresh_session.rollback()
                        logger.error(f"Failed to save enrichment results to database: {e}")
                        raise
            
            if progress_callback:
                await progress_callback(100, "Enrichment completed")
            
            return {
                "part_id": part_id,
                "supplier": supplier,
                "successful_enrichments": successful_enrichments,
                "failed_enrichments": failed_enrichments,
                "total_capabilities": len(capabilities),
                "completed_capabilities": len(successful_enrichments)
            }
            
        except Exception as e:
            logger.error(f"Error in part enrichment task: {e}", exc_info=True)
            raise
    
    async def _apply_standardized_data_to_part(self, part: PartModel, standardized_data: Dict[str, Any]):
        """
        Apply standardized data mapping to part using the SupplierDataMapper results.
        This ensures consistent data storage across all suppliers.
        """
        try:
            logger.info(f"Applying standardized data to part {part.part_name}")
            
            # Update core standardized fields
            core_fields = [
                'manufacturer', 'manufacturer_part_number', 'component_type', 
                'package', 'mounting_type', 'rohs_status', 'lifecycle_status',
                'unit_price', 'currency', 'stock_quantity', 'last_stock_update',
                'pricing_data', 'last_price_update', 'price_source',
                'last_enrichment_date', 'enrichment_source', 'data_quality_score'
            ]
            
            updated_fields = []
            for field in core_fields:
                if field in standardized_data:
                    old_value = getattr(part, field, None)
                    new_value = standardized_data[field]
                    
                    # Only update if the new value is different and not None
                    if new_value is not None and old_value != new_value:
                        setattr(part, field, new_value)
                        updated_fields.append(f"{field}: '{old_value}' -> '{new_value}'")
            
            # Update image URL if provided
            if standardized_data.get('image_url') and part.image_url != standardized_data['image_url']:
                old_url = part.image_url
                part.image_url = standardized_data['image_url']
                updated_fields.append(f"image_url: '{old_url}' -> '{standardized_data['image_url']}'")
            
            # Update description if it's better than what we have
            if standardized_data.get('description'):
                current_desc = part.description or ""
                new_desc = standardized_data['description']
                
                # Update if current description is empty or just a part identifier
                part_identifiers = [part.part_number, part.part_name, part.manufacturer_part_number]
                is_placeholder = (
                    not current_desc.strip() or 
                    current_desc.strip() in [pi for pi in part_identifiers if pi] or
                    len(current_desc.strip()) < 10
                )
                
                if is_placeholder and len(new_desc.strip()) > 10:
                    part.description = new_desc
                    updated_fields.append(f"description: '{current_desc}' -> '{new_desc}'")
            
            # Update additional_properties with standardized structure
            if standardized_data.get('additional_properties'):
                part.additional_properties = standardized_data['additional_properties']
                updated_fields.append("additional_properties: updated with standardized structure")
            
            # Handle file downloads if configured
            await self._handle_file_downloads_from_standardized_data(part, standardized_data)
            
            if updated_fields:
                logger.info(f"Updated standardized fields for part {part.part_name}:")
                for field_update in updated_fields:
                    logger.info(f"  - {field_update}")
            else:
                logger.info(f"No field updates needed for part {part.part_name} (data already current)")
                
        except Exception as e:
            logger.error(f"Error applying standardized data to part {part.part_name}: {e}")
            # Don't fail enrichment if standardized data application fails
    
    async def _handle_file_downloads_from_standardized_data(self, part: PartModel, standardized_data: Dict[str, Any]):
        """Handle datasheet and image downloads from standardized data"""
        try:
            # Check for datasheet URL in standardized additional_properties
            additional_props = standardized_data.get('additional_properties', {})
            supplier_data = additional_props.get('supplier_data', {})
            metadata = additional_props.get('metadata', {})
            
            # Handle datasheet download using standardized structure
            if metadata.get('has_datasheet') and self.download_config.get('download_datasheets', False):
                # Find datasheet URL in standardized supplier data
                datasheet_url = None
                for supplier_name, supplier_info in supplier_data.items():
                    if isinstance(supplier_info, dict):
                        datasheet_url = supplier_info.get('datasheet_url')
                        if datasheet_url:
                            break
                
                if datasheet_url:
                    logger.info(f"Downloading datasheet for part {part.part_name} from standardized data")
                    try:
                        from MakerMatrix.services.file_download_service import get_file_download_service
                        file_service = get_file_download_service(self.download_config)
                        
                        part_number = part.part_number or part.manufacturer_part_number or part.part_name
                        supplier = standardized_data.get('enrichment_source', 'Unknown')
                        
                        download_result = file_service.download_datasheet(
                            url=datasheet_url,
                            part_number=part_number,
                            supplier=supplier
                        )
                        
                        if download_result:
                            # Update additional_properties with download info
                            if not part.additional_properties:
                                part.additional_properties = {}
                            part.additional_properties.update({
                                'datasheet_filename': download_result['filename'],
                                'datasheet_local_path': f"/static/datasheets/{download_result['filename']}",
                                'datasheet_downloaded': True,
                                'datasheet_size': download_result['size'],
                                'datasheet_file_uuid': download_result['file_uuid']
                            })
                            logger.info(f"✅ Downloaded datasheet: {download_result['filename']}")
                        
                    except Exception as e:
                        logger.error(f"Error downloading datasheet from standardized data: {e}")
            
            # Handle image download
            if metadata.get('has_image') and self.download_config.get('download_images', False):
                image_url = standardized_data.get('image_url')
                if image_url and image_url.startswith('http'):
                    logger.info(f"Downloading image for part {part.part_name} from standardized data")
                    try:
                        from MakerMatrix.services.file_download_service import get_file_download_service
                        file_service = get_file_download_service(self.download_config)
                        
                        part_number = part.part_number or part.manufacturer_part_number or part.part_name
                        supplier = standardized_data.get('enrichment_source', 'Unknown')
                        
                        download_result = file_service.download_image(
                            url=image_url,
                            part_number=part_number,
                            supplier=supplier
                        )
                        
                        if download_result:
                            # Update part.image_url to local path
                            part.image_url = f"/utility/get_image/{download_result['image_uuid']}"
                            logger.info(f"✅ Downloaded image and updated URL to: {part.image_url}")
                        
                    except Exception as e:
                        logger.error(f"Error downloading image from standardized data: {e}")
                        
        except Exception as e:
            logger.error(f"Error handling file downloads from standardized data: {e}")
    
    def _serialize_for_json(self, data):
        """Convert data to JSON-serializable format, handling datetime objects"""
        if isinstance(data, dict):
            return {key: self._serialize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data
    
    def _create_enrichment_metadata(self, enrichment_results):
        """
        Create minimal enrichment metadata instead of storing full results.
        Only store essential information that's actually used by the application.
        """
        metadata = {}
        
        # Track what capabilities were successfully enriched
        successful_capabilities = []
        
        for capability, result in enrichment_results.items():
            if isinstance(result, dict) and result.get('success'):
                successful_capabilities.append(capability)
                
                # Store only essential capability-specific metadata
                if capability == 'fetch_datasheet' and result.get('datasheet_url'):
                    # Don't store datasheet_url here - it's handled in _update_part_from_enrichment_results
                    metadata['has_datasheet'] = True
                elif capability == 'fetch_image' and result.get('primary_image_url'):
                    # Don't store image URLs here - they're stored in part.image_url or local paths
                    metadata['has_image'] = True
                elif capability == 'fetch_pricing' and result.get('unit_price'):
                    # Store only current unit price for quick access
                    metadata['unit_price'] = result.get('unit_price')
                    metadata['currency'] = result.get('currency', 'USD')
                elif capability == 'fetch_stock' and result.get('quantity_available') is not None:
                    # Store only current stock for quick access
                    metadata['stock_quantity'] = result.get('quantity_available')
                elif capability == 'fetch_details':
                    # Store manufacturer info if not already in main fields
                    if result.get('manufacturer'):
                        metadata['manufacturer'] = result.get('manufacturer')
        
        # Don't store capabilities list - this is supplier config data, not part data
        # Capabilities can be queried dynamically from supplier when needed
        
        return metadata
    
    async def _update_part_from_enrichment_results(self, part, enrichment_results):
        """Update part fields based on enrichment results using standardized schemas"""
        try:
            # Update datasheet URL from DatasheetEnrichmentResponse
            if 'fetch_datasheet' in enrichment_results:
                datasheet_data = enrichment_results['fetch_datasheet']
                logger.info(f"Processing datasheet enrichment result: {datasheet_data}")
                if isinstance(datasheet_data, dict) and datasheet_data.get('success'):
                    datasheet_url = datasheet_data.get('datasheet_url')
                    logger.info(f"Found datasheet URL to save: {datasheet_url}")
                    if datasheet_url:
                        # Store datasheet URL in standardized supplier data structure
                        std_props = part.get_standardized_additional_properties()
                        supplier_data = std_props.get('supplier_data', {})
                        
                        # Update supplier data with datasheet URL
                        supplier_key = part.supplier.lower() if part.supplier else 'unknown'
                        if supplier_key not in supplier_data:
                            supplier_data[supplier_key] = {}
                        supplier_data[supplier_key]['datasheet_url'] = datasheet_url
                        
                        # Update additional_properties with standardized structure
                        if not part.additional_properties:
                            part.additional_properties = {}
                        part.additional_properties['supplier_data'] = supplier_data
                        logger.info(f"Saved datasheet URL to standardized supplier data: {datasheet_url}")
                        
                        # Download datasheet file if configured
                        if self.download_config.get('download_datasheets', False):
                            logger.info(f"Downloading datasheet file for part {part.part_name}")
                            try:
                                from MakerMatrix.services.file_download_service import get_file_download_service
                                file_service = get_file_download_service(self.download_config)
                                
                                # Use the appropriate part number for the supplier
                                part_number = getattr(part, 'part_number', None) or getattr(part, 'manufacturer_part_number', None) or part.part_name
                                supplier = getattr(part, 'supplier', None) or getattr(part, 'part_vendor', None) or 'Unknown'
                                
                                download_result = file_service.download_datasheet(
                                    url=datasheet_url,
                                    part_number=part_number,
                                    supplier=supplier
                                )
                                
                                if download_result:
                                    # Update part with local file information
                                    part.additional_properties['datasheet_filename'] = download_result['filename']
                                    part.additional_properties['datasheet_local_path'] = f"/static/datasheets/{download_result['filename']}"
                                    part.additional_properties['datasheet_downloaded'] = True
                                    part.additional_properties['datasheet_size'] = download_result['size']
                                    part.additional_properties['datasheet_file_uuid'] = download_result['file_uuid']
                                    logger.info(f"✅ Successfully downloaded datasheet: {download_result['filename']} ({download_result['size']} bytes)")
                                else:
                                    part.additional_properties['datasheet_downloaded'] = False
                                    logger.warning(f"❌ Failed to download datasheet from {datasheet_url}")
                                    
                            except Exception as e:
                                part.additional_properties['datasheet_downloaded'] = False
                                logger.error(f"❌ Error downloading datasheet: {e}")
                    else:
                        logger.warning("No datasheet_url found in successful datasheet data")
                else:
                    logger.warning(f"Datasheet enrichment failed or wrong format: success={datasheet_data.get('success') if isinstance(datasheet_data, dict) else 'not dict'}")
            else:
                logger.warning("No fetch_datasheet found in enrichment_results")
            
            # Update image URL from ImageEnrichmentResponse
            if 'fetch_image' in enrichment_results:
                image_data = enrichment_results['fetch_image']
                if isinstance(image_data, dict) and image_data.get('success'):
                    # Try primary_image_url first
                    primary_image_url = image_data.get('primary_image_url')
                    if primary_image_url:
                        part.image_url = primary_image_url
                        
                        # Download image file if configured and update part.image_url to local path
                        if self.download_config.get('download_images', False):
                            logger.info(f"Downloading image file for part {part.part_name}")
                            try:
                                from MakerMatrix.services.file_download_service import get_file_download_service
                                file_service = get_file_download_service(self.download_config)
                                
                                # Use the appropriate part number for the supplier
                                part_number = getattr(part, 'part_number', None) or getattr(part, 'manufacturer_part_number', None) or part.part_name
                                supplier = getattr(part, 'supplier', None) or getattr(part, 'part_vendor', None) or 'Unknown'
                                
                                download_result = file_service.download_image(
                                    url=primary_image_url,
                                    part_number=part_number,
                                    supplier=supplier
                                )
                                
                                if download_result:
                                    # Update part.image_url to use utility API endpoint with UUID
                                    part.image_url = f"/utility/get_image/{download_result['image_uuid']}"
                                    logger.info(f"✅ Successfully downloaded image: {download_result['filename']} ({download_result['size']} bytes)")
                                    logger.info(f"✅ Updated part.image_url to: {part.image_url}")
                                else:
                                    logger.warning(f"❌ Failed to download image from {primary_image_url}, keeping external URL")
                                    
                            except Exception as e:
                                logger.error(f"❌ Error downloading image: {e}")
                    else:
                        # Fallback to first image in images list
                        images = image_data.get('images', [])
                        if images and len(images) > 0:
                            first_image = images[0]
                            if isinstance(first_image, dict) and 'url' in first_image:
                                part.image_url = first_image['url']
                                
                                # Download image file if configured and update part.image_url to local path
                                if self.download_config.get('download_images', False):
                                    logger.info(f"Downloading image file for part {part.part_name} (from images list)")
                                    try:
                                        from MakerMatrix.services.file_download_service import get_file_download_service
                                        file_service = get_file_download_service(self.download_config)
                                        
                                        # Use the appropriate part number for the supplier
                                        part_number = getattr(part, 'part_number', None) or getattr(part, 'manufacturer_part_number', None) or part.part_name
                                        supplier = getattr(part, 'supplier', None) or getattr(part, 'part_vendor', None) or 'Unknown'
                                        
                                        download_result = file_service.download_image(
                                            url=first_image['url'],
                                            part_number=part_number,
                                            supplier=supplier
                                        )
                                        
                                        if download_result:
                                            # Update part.image_url to use utility API endpoint with UUID
                                            part.image_url = f"/utility/get_image/{download_result['image_uuid']}"
                                            logger.info(f"✅ Successfully downloaded image: {download_result['filename']} ({download_result['size']} bytes)")
                                            logger.info(f"✅ Updated part.image_url to: {part.image_url}")
                                        else:
                                            logger.warning(f"❌ Failed to download image from {first_image['url']}, keeping external URL")
                                            
                                    except Exception as e:
                                        logger.error(f"❌ Error downloading image: {e}")
            
            # Update pricing information using standardized pricing schema
            if 'fetch_pricing' in enrichment_results:
                pricing_data = enrichment_results['fetch_pricing']
                logger.info(f"Processing pricing enrichment result: {pricing_data}")
                if isinstance(pricing_data, dict) and pricing_data.get('success'):
                    # Get supplier name from context
                    supplier_name = enrichment_results.get('supplier') or getattr(part, 'supplier', None) or getattr(part, 'part_vendor', None)
                    await self._update_standardized_pricing(part, pricing_data, supplier_name)
                    
            # Stock information is handled in _create_enrichment_metadata - no additional storage needed
            
            # Update details information from DetailsEnrichmentResponse
            if 'fetch_details' in enrichment_results:
                details_data = enrichment_results['fetch_details']
                logger.info(f"Processing fetch_details data: {details_data}")
                if isinstance(details_data, dict) and details_data.get('success'):
                    # Update part description if not already set or if it's just the part number/name
                    product_description = details_data.get('product_description')
                    logger.info(f"Found product_description: {product_description}")
                    if product_description:
                        # Update description if it's empty, None, or just contains the part number/name
                        current_desc = part.description or ""
                        part_identifiers = [part.part_number, part.part_name]
                        should_update = (
                            not current_desc.strip() or  # Empty/None
                            current_desc.strip() in [pi for pi in part_identifiers if pi] or  # Just part number/name
                            len(current_desc.strip()) < 10  # Very short description (likely placeholder)
                        )
                        logger.info(f"Description update check - current: '{current_desc}', identifiers: {part_identifiers}, should_update: {should_update}")
                        if should_update:
                            logger.info(f"Updating description from '{current_desc}' to '{product_description}'")
                            part.description = product_description
                        else:
                            logger.info(f"Not updating description - current description is adequate")
                    else:
                        logger.warning("No product_description found in fetch_details data")
                else:
                    logger.warning(f"fetch_details data invalid or unsuccessful: success={details_data.get('success') if isinstance(details_data, dict) else 'not dict'}")
            else:
                logger.info("No fetch_details found in enrichment_results")
            
            # Note: Detailed information is stored in enrichment_results.fetch_details (no separate duplication needed)
            
            # Update specifications information from SpecificationsEnrichmentResponse
            if 'fetch_specifications' in enrichment_results:
                specs_data = enrichment_results['fetch_specifications']
                if isinstance(specs_data, dict) and specs_data.get('success'):
                    # Extract key specification values for quick access (no full duplication)
                    if not part.additional_properties:
                        part.additional_properties = {}
                    # Specifications information is handled in _create_enrichment_metadata - no additional storage needed
            
            # Fallback: Update description from additional_properties if main description is still placeholder
            if part.additional_properties and hasattr(part, 'description'):
                current_desc = part.description or ""
                part_identifiers = [part.part_number, part.part_name]
                is_placeholder = (
                    not current_desc.strip() or 
                    current_desc.strip() in [pi for pi in part_identifiers if pi] or
                    len(current_desc.strip()) < 10
                )
                
                logger.info(f"Fallback description check - current: '{current_desc}', is_placeholder: {is_placeholder}")
                
                if is_placeholder:
                    # Try to get enriched description from additional_properties
                    enriched_desc = part.additional_properties.get('description')
                    logger.info(f"Found fallback description in additional_properties: {enriched_desc}")
                    if enriched_desc and len(enriched_desc.strip()) > 10:
                        logger.info(f"Applying fallback description update from '{current_desc}' to '{enriched_desc}'")
                        part.description = enriched_desc
                    else:
                        logger.info("No suitable fallback description found in additional_properties")
            
            # Handle category auto-creation from enriched data
            await self._handle_category_auto_creation(part, enrichment_results)
            
            # Optimize data storage - reduce duplication in additional_properties
            self._optimize_part_data_storage(part)
            
        except Exception as e:
            logger.warning(f"Error updating part fields from enrichment: {e}")
            # Don't fail the entire enrichment if field updates fail
    
    def _optimize_part_data_storage(self, part):
        """Clean up duplicate data in additional_properties after enrichment"""
        if not part.additional_properties:
            return
            
        try:
            # Remove description from additional_properties if it matches part.description
            if (part.description and 
                part.additional_properties.get('description') == part.description):
                del part.additional_properties['description']
                logger.debug("Removed duplicate description from additional_properties")
            
            # Remove any external image URLs that were replaced with local paths
            image_url = part.image_url
            if image_url and image_url.startswith('/static/images/'):
                # Remove any external image URL references that are now obsolete
                keys_to_remove = []
                for key in part.additional_properties:
                    if 'image' in key.lower() and 'http' in str(part.additional_properties.get(key, '')):
                        keys_to_remove.append(key)
                for key in keys_to_remove:
                    del part.additional_properties[key]
                    logger.debug(f"Removed obsolete external image reference: {key}")
                    
        except Exception as e:
            logger.debug(f"Error optimizing part data storage: {e}")
            # Don't fail enrichment for optimization errors
    
    async def handle_datasheet_fetch(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """Handle datasheet fetching for a specific part using new standardized client"""
        try:
            input_data = task.get_input_data()
            part_id = input_data.get('part_id')
            part_number = input_data.get('part_number')
            supplier = input_data.get('supplier')
            
            if not (part_id or part_number):
                raise ValueError("Either part_id or part_number is required")
            
            # Get part if part_id provided
            part = None
            if part_id:
                from MakerMatrix.database.db import get_session
                session = next(get_session())
                try:
                    part = PartRepository.get_part_by_id(session, part_id)
                    if not part:
                        raise ValueError(f"Part not found: {part_id}")
                    # Use the appropriate part number for the supplier
                    part_number = self._get_supplier_part_number(part, supplier)
                    supplier = supplier or part.supplier or part.part_vendor
                finally:
                    session.close()
            
            if not supplier:
                raise ValueError("Supplier is required for datasheet fetch")
            
            # Use the new supplier configuration system
            supplier_service = SupplierConfigService()
            try:
                supplier_config = supplier_service.get_supplier_config(supplier.upper())
            except Exception as e:
                raise ValueError(f"Supplier configuration not found for: {supplier}")
            
            if not supplier_config.enabled:
                raise ValueError(f"Supplier {supplier} is not enabled")
            
            # Create new supplier instance 
            from MakerMatrix.suppliers.registry import get_supplier
            
            client = get_supplier(supplier.lower())
            if not client:
                raise ValueError(f"Supplier implementation not found for: {supplier}")
            
            # Configure the supplier with credentials and config
            credentials = supplier_service.get_supplier_credentials(supplier.upper(), decrypt=True)
            config = supplier_config.custom_parameters or {}
            client.configure(credentials or {}, config)
            
            if progress_callback:
                await progress_callback(25, "Fetching datasheet information")
            
            # Use standardized enrichment method
            result = await client.enrich_part_datasheet(part_number)
            
            if progress_callback:
                await progress_callback(75, "Processing datasheet result")
            
            # Update part if part_id was provided and download the datasheet
            if part and result.success and result.datasheet_url:
                # Store datasheet URL in standardized supplier data structure
                std_props = part.get_standardized_additional_properties()
                supplier_data = std_props.get('supplier_data', {})
                
                # Update supplier data with datasheet URL
                supplier_key = supplier.lower() if supplier else 'unknown'
                if supplier_key not in supplier_data:
                    supplier_data[supplier_key] = {}
                supplier_data[supplier_key]['datasheet_url'] = result.datasheet_url
                
                # Update additional_properties with standardized structure
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['supplier_data'] = supplier_data
                
                if progress_callback:
                    await progress_callback(80, "Downloading datasheet file...")
                
                # Download the datasheet file
                from MakerMatrix.services.file_download_service import file_download_service
                download_result = file_download_service.download_datasheet(
                    url=result.datasheet_url,
                    part_number=part_number,
                    supplier=supplier
                )
                
                if download_result:
                    # Store local file information in additional_properties for backward compatibility
                    part.additional_properties['datasheet_filename'] = download_result['filename']
                    part.additional_properties['datasheet_local_path'] = f"/static/datasheets/{download_result['filename']}"
                    part.additional_properties['datasheet_downloaded'] = True
                    part.additional_properties['datasheet_size'] = download_result['size']
                    
                    # Create proper DatasheetModel record
                    from MakerMatrix.models.models import DatasheetModel
                    datasheet = DatasheetModel(
                        part_id=part.id,
                        file_uuid=download_result['file_uuid'],
                        original_filename=download_result['original_filename'],
                        file_extension=download_result['extension'],
                        file_size=download_result['size'],
                        source_url=result.datasheet_url,
                        supplier=supplier,
                        title=f"{supplier} Datasheet - {part_number}",
                        description=f"Datasheet for {part.part_name or part_number}",
                        is_downloaded=True
                    )
                    
                    logger.info(f"Downloaded datasheet for {part.part_name}: {download_result['filename']}")
                    
                    if progress_callback:
                        await progress_callback(95, f"Downloaded {download_result['filename']}")
                else:
                    part.additional_properties['datasheet_downloaded'] = False
                    
                    # Still create a DatasheetModel record for the URL even if download failed
                    from MakerMatrix.models.models import DatasheetModel
                    datasheet = DatasheetModel(
                        part_id=part.id,
                        source_url=result.datasheet_url,
                        supplier=supplier,
                        title=f"{supplier} Datasheet - {part_number}",
                        description=f"Datasheet for {part.part_name or part_number}",
                        is_downloaded=False,
                        download_error="Failed to download datasheet file"
                    )
                    
                    logger.warning(f"Failed to download datasheet for {part.part_name}")
                    
                    if progress_callback:
                        await progress_callback(95, "Datasheet download failed")
                
                from MakerMatrix.database.db import get_session
                session = next(get_session())
                try:
                    # Check if datasheet already exists for this part and URL
                    existing_datasheet = session.exec(
                        select(DatasheetModel).where(
                            DatasheetModel.part_id == part.id,
                            DatasheetModel.source_url == result.datasheet_url
                        )
                    ).first()
                    
                    if not existing_datasheet:
                        session.add(datasheet)
                    else:
                        # Update existing datasheet record
                        if download_result:
                            existing_datasheet.file_uuid = download_result['file_uuid']
                            existing_datasheet.original_filename = download_result['original_filename']
                            existing_datasheet.file_extension = download_result['extension']
                            existing_datasheet.file_size = download_result['size']
                            existing_datasheet.is_downloaded = True
                            existing_datasheet.download_error = None
                        else:
                            existing_datasheet.is_downloaded = False
                            existing_datasheet.download_error = "Failed to download datasheet file"
                        existing_datasheet.updated_at = datetime.utcnow()
                    
                    PartRepository.update_part(session, part)
                    session.commit()
                finally:
                    session.close()
            
            if progress_callback:
                await progress_callback(100, "Datasheet fetch completed")
            
            return {
                "part_number": part_number,
                "supplier": supplier,
                "success": result.success,
                "datasheet_data": result.model_dump() if result.success else None,
                "error": result.error_message if not result.success else None
            }
            
        except Exception as e:
            logger.error(f"Error in datasheet fetch task: {e}", exc_info=True)
            raise
    
    async def handle_image_fetch(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """Handle image fetching for a specific part using new standardized client"""
        try:
            input_data = task.get_input_data()
            part_id = input_data.get('part_id')
            part_number = input_data.get('part_number')
            supplier = input_data.get('supplier')
            
            if not (part_id or part_number):
                raise ValueError("Either part_id or part_number is required")
            
            # Get part if part_id provided
            part = None
            if part_id:
                from MakerMatrix.database.db import get_session
                session = next(get_session())
                try:
                    part = PartRepository.get_part_by_id(session, part_id)
                    if not part:
                        raise ValueError(f"Part not found: {part_id}")
                    part_number = part.part_number or part.lcsc_part_number
                    supplier = supplier or part.supplier or part.part_vendor
                finally:
                    session.close()
            
            if not supplier:
                raise ValueError("Supplier is required for image fetch")
            
            # Use the new supplier configuration system
            supplier_service = SupplierConfigService()
            try:
                supplier_config = supplier_service.get_supplier_config(supplier.upper())
            except Exception as e:
                raise ValueError(f"Supplier configuration not found for: {supplier}")
            
            if not supplier_config.enabled:
                raise ValueError(f"Supplier {supplier} is not enabled")
            
            # Create new supplier instance 
            from MakerMatrix.suppliers.registry import get_supplier
            
            client = get_supplier(supplier.lower())
            if not client:
                raise ValueError(f"Supplier implementation not found for: {supplier}")
            
            # Configure the supplier with credentials and config
            credentials = supplier_service.get_supplier_credentials(supplier.upper(), decrypt=True)
            config = supplier_config.custom_parameters or {}
            client.configure(credentials or {}, config)
            
            if progress_callback:
                await progress_callback(25, "Fetching image information")
            
            # Use standardized enrichment method
            result = await client.enrich_part_image(part_number)
            
            if progress_callback:
                await progress_callback(75, "Processing image result")
            
            # Update part if part_id was provided
            if part and result.success and result.primary_image_url:
                part.image_url = result.primary_image_url
                from MakerMatrix.database.db import get_session
                session = next(get_session())
                try:
                    PartRepository.update_part(session, part)
                finally:
                    session.close()
            
            if progress_callback:
                await progress_callback(100, "Image fetch completed")
            
            return {
                "part_number": part_number,
                "supplier": supplier,
                "success": result.success,
                "image_data": result.model_dump() if result.success else None,
                "error": result.error_message if not result.success else None
            }
            
        except Exception as e:
            logger.error(f"Error in image fetch task: {e}", exc_info=True)
            raise
    
    async def handle_bulk_enrichment(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """
        Handle bulk enrichment for multiple parts.
        
        Input data should contain:
        - part_ids: List of part IDs to enrich
        - supplier_filter: Optional supplier filter
        - capabilities: List of capabilities to use
        - batch_size: Number of parts to process in parallel (default: 5)
        """
        try:
            input_data = task.get_input_data()
            part_ids = input_data.get('part_ids', [])
            supplier_filter = input_data.get('supplier_filter')
            requested_capabilities = input_data.get('capabilities', [])
            batch_size = input_data.get('batch_size', 5)
            
            if not part_ids:
                raise ValueError("part_ids list is required for bulk enrichment")
            
            total_parts = len(part_ids)
            processed_parts = 0
            successful_enrichments = []
            failed_enrichments = []
            
            # Process parts in batches
            for i in range(0, total_parts, batch_size):
                batch = part_ids[i:i + batch_size]
                batch_tasks = []
                
                for part_id in batch:
                    # Create enrichment task for each part
                    enrichment_data = {
                        'part_id': part_id,
                        'capabilities': requested_capabilities
                    }
                    if supplier_filter:
                        enrichment_data['supplier'] = supplier_filter
                    
                    # Create a mock task for the part enrichment
                    part_task = TaskModel(
                        task_type=TaskType.PART_ENRICHMENT,
                        name=f"Part Enrichment - {part_id}",
                        status=TaskStatus.RUNNING
                    )
                    part_task.set_input_data(enrichment_data)
                    
                    batch_tasks.append(self.handle_part_enrichment(part_task))
                
                # Execute batch in parallel
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process batch results
                for j, result in enumerate(batch_results):
                    part_id = batch[j]
                    if isinstance(result, Exception):
                        failed_enrichments.append({
                            "part_id": part_id,
                            "error": str(result)
                        })
                    else:
                        successful_enrichments.append({
                            "part_id": part_id,
                            "result": result
                        })
                    
                    processed_parts += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = int((processed_parts / total_parts) * 100)
                        await progress_callback(
                            progress, 
                            f"Processed {processed_parts}/{total_parts} parts"
                        )
            
            return {
                "total_parts": total_parts,
                "successful_count": len(successful_enrichments),
                "failed_count": len(failed_enrichments),
                "successful_enrichments": successful_enrichments,
                "failed_enrichments": failed_enrichments
            }
            
        except Exception as e:
            logger.error(f"Error in bulk enrichment task: {e}", exc_info=True)
            raise
    
    async def _update_part_from_enrichment(self, part, capability_name: str, enrichment_data: Dict[str, Any]):
        """Update part fields based on enrichment results using new supplier format"""
        try:
            if capability_name == 'fetch_datasheet':
                # enrichment_data contains {'datasheet': 'url'}
                if 'datasheet' in enrichment_data and enrichment_data['datasheet']:
                    # Store datasheet URL in standardized supplier data structure
                    std_props = part.get_standardized_additional_properties()
                    supplier_data = std_props.get('supplier_data', {})
                    
                    # Update supplier data with datasheet URL
                    supplier_key = part.supplier.lower() if part.supplier else 'unknown'
                    if supplier_key not in supplier_data:
                        supplier_data[supplier_key] = {}
                    supplier_data[supplier_key]['datasheet_url'] = enrichment_data['datasheet']
                    
                    # Update additional_properties with standardized structure
                    if not part.additional_properties:
                        part.additional_properties = {}
                    part.additional_properties['supplier_data'] = supplier_data
            
            elif capability_name == 'fetch_image':
                # enrichment_data contains {'image': 'url'}
                if 'image' in enrichment_data and enrichment_data['image']:
                    part.image_url = enrichment_data['image']
            
            elif capability_name == 'fetch_pricing':
                # enrichment_data contains {'pricing': [...]}
                if 'pricing' in enrichment_data and enrichment_data['pricing']:
                    if not part.additional_properties:
                        part.additional_properties = {}
                    part.additional_properties['pricing_data'] = enrichment_data['pricing']
                    
                    # Pricing data is stored in additional_properties['pricing_data']
                    # No direct 'price' field on PartModel - pricing is stored as structured data
            
            elif capability_name == 'fetch_stock':
                # enrichment_data contains {'stock': number}
                if 'stock' in enrichment_data and enrichment_data['stock'] is not None:
                    part.quantity = int(enrichment_data['stock'])
            
            elif capability_name == 'fetch_specifications':
                # enrichment_data contains {'specifications': {...}}
                if 'specifications' in enrichment_data and enrichment_data['specifications']:
                    if not part.additional_properties:
                        part.additional_properties = {}
                    part.additional_properties['specifications'] = enrichment_data['specifications']
            
            elif capability_name == 'fetch_details':
                # enrichment_data contains {'details': PartSearchResult}
                if 'details' in enrichment_data and enrichment_data['details']:
                    details = enrichment_data['details']
                    # Handle PartSearchResult object
                    if hasattr(details, 'description') and details.description:
                        part.description = details.description
                    if hasattr(details, 'manufacturer') and details.manufacturer:
                        part.manufacturer = details.manufacturer  
                    if hasattr(details, 'manufacturer_part_number') and details.manufacturer_part_number:
                        part.manufacturer_part_number = details.manufacturer_part_number
                    if hasattr(details, 'category') and details.category:
                        # Handle category assignment properly using the many-to-many relationship
                        try:
                            category_service = CategoryService(self.part_repository.engine)
                            # Try to find existing category or create new one
                            existing_categories = category_service.get_all_categories()
                            category_name = str(details.category).strip()
                            
                            # Find or create the category
                            category = None
                            for cat in existing_categories:
                                if cat.name.lower() == category_name.lower():
                                    category = cat
                                    break
                            
                            if not category:
                                # Create new category
                                from MakerMatrix.schemas.category_schemas import CategoryCreate
                                category_data = CategoryCreate(name=category_name)
                                category = category_service.add_category(category_data)
                            
                            # Add category to part if not already associated
                            if category and category not in part.categories:
                                part.categories.append(category)
                                
                        except Exception as cat_error:
                            logger.warning(f"Failed to assign category '{details.category}' to part {part.part_name}: {cat_error}")
                    
                    # Store additional data
                    if not part.additional_properties:
                        part.additional_properties = {}
                    part.additional_properties['details_data'] = self._serialize_for_json(details)
            
        except Exception as e:
            logger.error(f"Error updating part from enrichment {capability_name}: {e}", exc_info=True)
    
    def _get_supplier_part_number(self, part, supplier: str) -> str:
        """
        Get the appropriate part number for a specific supplier using new supplier system
        
        Args:
            part: Part model instance
            supplier: Supplier name (e.g., 'LCSC', 'DigiKey', 'Mouser')
            
        Returns:
            The part number to use for API calls to that supplier
        """
        if not supplier:
            return part.part_number
        
        try:
            # Use the new supplier system
            from MakerMatrix.suppliers.registry import get_supplier
            
            supplier_instance = get_supplier(supplier.lower())
            if supplier_instance:
                # For our new suppliers, the part number is typically stored in part_number
                # or can be extracted from additional_properties
                
                # Check if it's a supplier-specific part number first
                if hasattr(part, 'supplier_part_number') and part.supplier_part_number:
                    return part.supplier_part_number
                
                # Check additional properties for supplier-specific part numbers
                if part.additional_properties:
                    supplier_key = f"{supplier.lower()}_part_number"
                    if supplier_key in part.additional_properties:
                        return part.additional_properties[supplier_key]
                
                # Use manufacturer part number as fallback
                if hasattr(part, 'manufacturer_part_number') and part.manufacturer_part_number:
                    return part.manufacturer_part_number
                    
                logger.debug(f"Using part number for {supplier}: {part.part_number}")
                return part.part_number
        
        except Exception as e:
            logger.warning(f"Failed to get supplier part number using new supplier system for {supplier}: {e}")
        
        # Fallback to part number
        logger.debug(f"Using fallback part number for {supplier}: {part.part_number}")
        return part.part_number
    
    async def _handle_category_auto_creation(self, part, enrichment_results):
        """Auto-create categories from enriched data and add them to the part"""
        try:
            logger.info(f"Checking for category data in enrichment results for part {part.part_name}")
            
            categories_to_add = []
            
            # Check fetch_details for category information
            if 'fetch_details' in enrichment_results:
                details_data = enrichment_results['fetch_details']
                if isinstance(details_data, dict) and details_data.get('success'):
                    # Look for category in the details data
                    category = details_data.get('category')
                    if category and isinstance(category, str) and category.strip():
                        categories_to_add.append(category.strip())
                        logger.info(f"Found category from fetch_details: {category}")
            
            # Check fetch_specifications for category information  
            if 'fetch_specifications' in enrichment_results:
                specs_data = enrichment_results['fetch_specifications']
                if isinstance(specs_data, dict) and specs_data.get('success'):
                    specifications = specs_data.get('specifications', {})
                    if isinstance(specifications, dict):
                        # Look for category in specifications
                        category = specifications.get('Category') or specifications.get('category')
                        if category and isinstance(category, str) and category.strip():
                            categories_to_add.append(category.strip())
                            logger.info(f"Found category from specifications: {category}")
            
            # Check if category is directly in additional_properties from supplier data
            if hasattr(part, 'additional_properties') and part.additional_properties:
                category = part.additional_properties.get('Category') or part.additional_properties.get('category')
                if category and isinstance(category, str) and category.strip():
                    categories_to_add.append(category.strip())
                    logger.info(f"Found category from additional_properties: {category}")
            
            # Remove duplicates and empty categories
            unique_categories = list(set([cat for cat in categories_to_add if cat and cat.strip()]))
            
            if unique_categories:
                logger.info(f"Processing {len(unique_categories)} categories for auto-creation: {unique_categories}")
                
                # Auto-create categories and add them to the part
                from MakerMatrix.database.db import engine
                from sqlalchemy.orm import Session
                from MakerMatrix.models.models import CategoryModel
                from MakerMatrix.repositories.category_repositories import CategoryRepository
                
                with Session(engine) as session:
                    category_repo = CategoryRepository(engine)
                    
                    for category_name in unique_categories:
                        try:
                            # Check if category already exists
                            existing_category = None
                            try:
                                existing_category = category_repo.get_category_by_name(session, category_name)
                                logger.info(f"Category '{category_name}' already exists with ID: {existing_category.id}")
                            except Exception:
                                # Category doesn't exist, create it
                                logger.info(f"Creating new category: {category_name}")
                                new_category = category_repo.create_category(session, {
                                    "name": category_name,
                                    "description": f"Auto-created from enrichment data for {part.part_name}"
                                })
                                existing_category = new_category
                                logger.info(f"Successfully created category '{category_name}' with ID: {new_category.id}")
                            
                            # Add category to part if not already associated
                            if existing_category:
                                # Get fresh part instance in this session
                                fresh_part = session.query(PartModel).filter(PartModel.id == part.id).first()
                                if fresh_part:
                                    # Check if category is already associated with part
                                    category_already_associated = any(
                                        cat.id == existing_category.id for cat in fresh_part.categories
                                    )
                                    
                                    if not category_already_associated:
                                        fresh_part.categories.append(existing_category)
                                        session.commit()
                                        logger.info(f"Successfully associated part '{part.part_name}' with category '{category_name}'")
                                    else:
                                        logger.info(f"Part '{part.part_name}' already associated with category '{category_name}'")
                                else:
                                    logger.error(f"Could not find part {part.id} in fresh session")
                                    
                        except Exception as e:
                            logger.error(f"Error processing category '{category_name}': {e}")
                            session.rollback()
                            continue
            else:
                logger.info(f"No categories found in enrichment data for part {part.part_name}")
                
        except Exception as e:
            logger.error(f"Error in category auto-creation for part {part.part_name}: {e}")
            # Don't fail the entire enrichment if category creation fails
    
    async def _update_standardized_pricing(self, part, pricing_data, supplier_name):
        """
        Update part pricing using the standardized pricing schema.
        All suppliers must convert their pricing data to StandardPricing format.
        """
        try:
            from MakerMatrix.schemas.pricing_schemas import convert_generic_pricing_data
            from datetime import datetime
            
            logger.info(f"Converting supplier pricing data to standardized format for part {part.part_name}")
            
            # Extract raw pricing data from supplier response
            raw_pricing = None
            if 'pricing' in pricing_data:
                raw_pricing = pricing_data['pricing']
            elif 'price_breaks' in pricing_data:
                raw_pricing = pricing_data['price_breaks']
            elif 'unit_price' in pricing_data:
                raw_pricing = pricing_data['unit_price']
            elif 'price' in pricing_data:
                raw_pricing = pricing_data['price']
            else:
                logger.warning(f"No recognizable pricing data found in: {pricing_data.keys()}")
                return
            
            # Convert to standardized pricing format
            standard_pricing = convert_generic_pricing_data(raw_pricing, supplier=supplier_name)
            
            if standard_pricing:
                # Update PartModel pricing fields
                part.unit_price = standard_pricing.unit_price
                part.currency = standard_pricing.currency
                part.pricing_data = standard_pricing.to_dict()
                part.last_price_update = datetime.utcnow()
                part.price_source = supplier_name
                
                logger.info(f"✅ Successfully updated standardized pricing for part {part.part_name}")
                logger.info(f"   - Pricing type: {standard_pricing.pricing_type}")
                logger.info(f"   - Unit price: {standard_pricing.unit_price} {standard_pricing.currency}")
                if standard_pricing.price_breaks:
                    logger.info(f"   - Price breaks: {len(standard_pricing.price_breaks)} tiers")
            else:
                logger.warning(f"Failed to convert pricing data to standardized format for part {part.part_name}")
                
        except Exception as e:
            logger.error(f"Error updating standardized pricing for part {part.part_name}: {e}")
            # Don't fail enrichment if pricing update fails


# Task handler registry
ENRICHMENT_TASK_HANDLERS = {
    TaskType.PART_ENRICHMENT: 'handle_part_enrichment',
    TaskType.DATASHEET_FETCH: 'handle_datasheet_fetch',
    TaskType.IMAGE_FETCH: 'handle_image_fetch',
    TaskType.PRICING_FETCH: 'handle_pricing_fetch',
    TaskType.STOCK_FETCH: 'handle_stock_fetch',
    TaskType.SPECIFICATIONS_FETCH: 'handle_specifications_fetch',
    TaskType.BULK_ENRICHMENT: 'handle_bulk_enrichment',
}


def get_enrichment_task_handler(task_type: TaskType) -> Optional[str]:
    """Get the handler method name for a task type"""
    return ENRICHMENT_TASK_HANDLERS.get(task_type)


