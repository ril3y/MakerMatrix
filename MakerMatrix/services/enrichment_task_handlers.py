"""
Task handlers for enrichment operations.
These handlers integrate the supplier configuration system with the task system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlmodel import select
from MakerMatrix.models.task_models import TaskModel, TaskStatus, TaskType
from MakerMatrix.models.models import PartModel, DatasheetModel
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.supplier_config_service import SupplierConfigService


logger = logging.getLogger(__name__)


class EnrichmentTaskHandlers:
    """Handlers for enrichment task operations"""
    
    def __init__(self, part_repository: PartRepository, part_service: PartService, download_config=None):
        self.part_repository = part_repository
        self.part_service = part_service
        self.download_config = download_config or self._get_csv_import_config()
    
    def _get_csv_import_config(self) -> dict:
        """Get current CSV import configuration for download settings"""
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
                # Use recommended capabilities (datasheet and image for LCSC)
                recommended = ['fetch_datasheet', 'fetch_image', 'fetch_pricing', 'fetch_stock']
                capabilities = [cap for cap in recommended if cap in available_capabilities]
            
            if not capabilities:
                return {"message": "No enrichment capabilities available for this supplier"}
            
            # Create API client for the supplier
            credentials = supplier_service.get_supplier_credentials(supplier.upper(), decrypt=True)
            client = supplier_service._create_api_client(supplier_config, credentials)
            
            # Progress tracking
            total_capabilities = len(capabilities)
            completed = 0
            
            # Perform enrichment for each capability
            enrichment_results = {}
            successful_enrichments = []
            failed_enrichments = []
            
            for capability in capabilities:
                if progress_callback:
                    progress = int((completed / total_capabilities) * 100)
                    await progress_callback(progress, f"Processing {capability}...")
                
                try:
                    # Use the appropriate part number for the supplier
                    part_number = self._get_supplier_part_number(part, supplier)
                    
                    if capability == 'fetch_datasheet':
                        result = await client.enrich_part_datasheet(part_number)
                    elif capability == 'fetch_image':
                        result = await client.enrich_part_image(part_number)
                    elif capability == 'fetch_pricing':
                        result = await client.enrich_part_pricing(part_number)
                    elif capability == 'fetch_stock':
                        result = await client.enrich_part_stock(part_number)
                    elif capability == 'fetch_details':
                        result = await client.enrich_part_details(part_number)
                    elif capability == 'fetch_specifications':
                        result = await client.enrich_part_specifications(part_number)
                    else:
                        continue
                    
                    if result.success:
                        # Convert Pydantic model to dict for storage, handling datetime serialization
                        result_dict = result.model_dump()
                        enrichment_results[capability] = self._serialize_for_json(result_dict)
                        successful_enrichments.append(capability)
                        logger.info(f"Successfully enriched {capability} for part {part.part_name}")
                    else:
                        failed_enrichments.append({"capability": capability, "error": result.error_message})
                        logger.warning(f"Failed to enrich {capability} for part {part.part_name}: {result.error_message}")
                        
                except Exception as e:
                    failed_enrichments.append({"capability": capability, "error": str(e)})
                    logger.error(f"Error enriching {capability} for part {part.part_name}: {e}")
                
                completed += 1
                
            # Update part with enrichment results
            if enrichment_results:
                # Save enrichment results to part
                if not part.additional_properties:
                    part.additional_properties = {}
                
                if 'enrichment_results' not in part.additional_properties:
                    part.additional_properties['enrichment_results'] = {}
                
                # Clean enrichment results by removing verbose source metadata to reduce duplication
                clean_enrichment_results = self._clean_enrichment_results(enrichment_results)
                part.additional_properties['enrichment_results'].update(clean_enrichment_results)
                part.additional_properties['last_enrichment'] = datetime.utcnow().isoformat()
                
                # Update specific part fields based on enrichment data (without duplication)
                await self._update_part_from_enrichment_results(part, clean_enrichment_results)
                
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
                            
                            # Verify the save
                            fresh_session.refresh(fresh_part)
                            if fresh_part.additional_properties.get('datasheet_url'):
                                logger.info(f"✅ Successfully saved datasheet URL: {fresh_part.additional_properties['datasheet_url']}")
                            else:
                                logger.error(f"❌ Datasheet URL not found after save. Keys: {list(fresh_part.additional_properties.keys())}")
                            
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
    
    def _clean_enrichment_results(self, enrichment_results):
        """
        Clean enrichment results by removing redundant source metadata and verbose fields
        to reduce data duplication and storage size.
        """
        clean_results = {}
        
        for capability, result in enrichment_results.items():
            if isinstance(result, dict):
                # Create a clean copy without verbose metadata
                clean_result = {}
                
                # Keep essential fields
                essential_fields = [
                    'success', 'status', 'part_number', 'error_message', 'warnings',
                    # Datasheet fields
                    'datasheet_url', 'datasheet_filename', 'datasheet_size_bytes', 'download_verified',
                    # Image fields  
                    'images', 'primary_image_url',
                    # Pricing fields
                    'unit_price', 'currency', 'price_breaks', 'minimum_order_quantity',
                    # Stock fields
                    'quantity_available', 'availability_status', 'lead_time_days',
                    # Specifications fields
                    'specifications', 'electrical_characteristics', 'mechanical_characteristics',
                    # Details fields
                    'manufacturer', 'manufacturer_part_number', 'product_description', 'package_type'
                ]
                
                for field in essential_fields:
                    if field in result:
                        clean_result[field] = result[field]
                
                # Remove verbose source metadata (supplier, api_endpoint, enriched_at, api_version)
                # These are not needed for normal operations and create significant duplication
                
                clean_results[capability] = clean_result
            else:
                # If not a dict, keep as-is
                clean_results[capability] = result
        
        return clean_results
    
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
                        # Store datasheet URL in additional_properties
                        if not part.additional_properties:
                            part.additional_properties = {}
                        part.additional_properties['datasheet_url'] = datasheet_url
                        logger.info(f"Saved datasheet URL to part: {datasheet_url}")
                        
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
                        
                        # Download image file if configured
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
                                    # Update part with local file information
                                    if not part.additional_properties:
                                        part.additional_properties = {}
                                    part.additional_properties['image_filename'] = download_result['filename']
                                    part.additional_properties['image_local_path'] = f"/static/images/{download_result['filename']}"
                                    part.additional_properties['image_downloaded'] = True
                                    part.additional_properties['image_size'] = download_result['size']
                                    logger.info(f"✅ Successfully downloaded image: {download_result['filename']} ({download_result['size']} bytes)")
                                else:
                                    if not part.additional_properties:
                                        part.additional_properties = {}
                                    part.additional_properties['image_downloaded'] = False
                                    logger.warning(f"❌ Failed to download image from {primary_image_url}")
                                    
                            except Exception as e:
                                if not part.additional_properties:
                                    part.additional_properties = {}
                                part.additional_properties['image_downloaded'] = False
                                logger.error(f"❌ Error downloading image: {e}")
                    else:
                        # Fallback to first image in images list
                        images = image_data.get('images', [])
                        if images and len(images) > 0:
                            first_image = images[0]
                            if isinstance(first_image, dict) and 'url' in first_image:
                                part.image_url = first_image['url']
                                
                                # Download image file if configured
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
                                            # Update part with local file information
                                            if not part.additional_properties:
                                                part.additional_properties = {}
                                            part.additional_properties['image_filename'] = download_result['filename']
                                            part.additional_properties['image_local_path'] = f"/static/images/{download_result['filename']}"
                                            part.additional_properties['image_downloaded'] = True
                                            part.additional_properties['image_size'] = download_result['size']
                                            logger.info(f"✅ Successfully downloaded image: {download_result['filename']} ({download_result['size']} bytes)")
                                        else:
                                            if not part.additional_properties:
                                                part.additional_properties = {}
                                            part.additional_properties['image_downloaded'] = False
                                            logger.warning(f"❌ Failed to download image from {first_image['url']}")
                                            
                                    except Exception as e:
                                        if not part.additional_properties:
                                            part.additional_properties = {}
                                        part.additional_properties['image_downloaded'] = False
                                        logger.error(f"❌ Error downloading image: {e}")
            
            # Update pricing information from PricingEnrichmentResponse
            if 'fetch_pricing' in enrichment_results:
                pricing_data = enrichment_results['fetch_pricing']
                if isinstance(pricing_data, dict) and pricing_data.get('success'):
                    unit_price = pricing_data.get('unit_price')
                    if unit_price:
                        # Store pricing in additional_properties (quick access only)
                        if not part.additional_properties:
                            part.additional_properties = {}
                        part.additional_properties['unit_price'] = unit_price
                        # Note: Full pricing data is in enrichment_results.fetch_pricing (no duplication)
            
            # Update stock information from StockEnrichmentResponse
            if 'fetch_stock' in enrichment_results:
                stock_data = enrichment_results['fetch_stock']
                if isinstance(stock_data, dict) and stock_data.get('success'):
                    # Extract key stock values for quick access (no full duplication)
                    if not part.additional_properties:
                        part.additional_properties = {}
                    quantity_available = stock_data.get('quantity_available')
                    if quantity_available is not None:
                        part.additional_properties['stock_quantity'] = quantity_available
                    # Note: Full stock data is in enrichment_results.fetch_stock (no duplication)
            
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
                    # Note: Full specifications data is in enrichment_results.fetch_specifications (no duplication)
                    
                    # Extract manufacturer from specifications if available and store in additional_properties
                    specifications = specs_data.get('specifications', [])
                    for spec in specifications:
                        if isinstance(spec, dict) and spec.get('name', '').lower() == 'manufacturer':
                            manufacturer_value = spec.get('value')
                            if manufacturer_value:
                                if not part.additional_properties:
                                    part.additional_properties = {}
                                # Only update if not already set
                                if not part.additional_properties.get('manufacturer'):
                                    part.additional_properties['manufacturer'] = manufacturer_value
            
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
            
            # Optimize data storage - reduce duplication in additional_properties
            self._optimize_part_data_storage(part)
            
        except Exception as e:
            logger.warning(f"Error updating part fields from enrichment: {e}")
            # Don't fail the entire enrichment if field updates fail
    
    def _optimize_part_data_storage(self, part):
        """Optimize part data storage by removing redundant duplicates"""
        if not part.additional_properties:
            return
            
        try:
            # Remove duplicate URLs if they match the main fields
            if part.image_url and part.additional_properties.get('enrichment_results', {}).get('fetch_image', {}).get('primary_image_url') == part.image_url:
                # Keep the enrichment result for audit trail but note it's duplicated in main field
                if 'fetch_image' in part.additional_properties.get('enrichment_results', {}):
                    part.additional_properties['enrichment_results']['fetch_image']['_note'] = "primary_image_url duplicated in part.image_url"
            
            # Remove duplicate datasheet URLs
            datasheet_url = part.additional_properties.get('datasheet_url')
            enrichment_datasheet = part.additional_properties.get('enrichment_results', {}).get('fetch_datasheet', {}).get('datasheet_url')
            if datasheet_url and enrichment_datasheet == datasheet_url:
                if 'fetch_datasheet' in part.additional_properties.get('enrichment_results', {}):
                    part.additional_properties['enrichment_results']['fetch_datasheet']['_note'] = "datasheet_url duplicated in additional_properties.datasheet_url"
            
            # Clean up redundant description storage if main description was updated
            if part.description and len(part.description.strip()) > 10:
                stored_desc = part.additional_properties.get('description')
                if stored_desc == part.description:
                    # Mark as duplicated rather than removing (for audit purposes)
                    part.additional_properties['_description_note'] = "description duplicated in part.description field"
                    
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
            
            # Create API client for the supplier
            credentials = supplier_service.get_supplier_credentials(supplier.upper(), decrypt=True)
            client = supplier_service._create_api_client(supplier_config, credentials)
            
            if progress_callback:
                await progress_callback(25, "Fetching datasheet information")
            
            # Use standardized enrichment method
            result = await client.enrich_part_datasheet(part_number)
            
            if progress_callback:
                await progress_callback(75, "Processing datasheet result")
            
            # Update part if part_id was provided and download the datasheet
            if part and result.success and result.datasheet_url:
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['datasheet_url'] = result.datasheet_url
                
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
            
            # Create API client for the supplier
            credentials = supplier_service.get_supplier_credentials(supplier.upper(), decrypt=True)
            client = supplier_service._create_api_client(supplier_config, credentials)
            
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
        """Update part fields based on enrichment results using standardized schemas"""
        try:
            if capability_name == 'fetch_datasheet':
                if 'datasheet_url' in enrichment_data:
                    if not part.additional_properties:
                        part.additional_properties = {}
                    part.additional_properties['datasheet_url'] = enrichment_data['datasheet_url']
            
            elif capability_name == 'fetch_image':
                if 'primary_image_url' in enrichment_data:
                    part.image_url = enrichment_data['primary_image_url']
            
            elif capability_name == 'fetch_pricing':
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['pricing_data'] = enrichment_data
                
                # Update price if available
                if 'unit_price' in enrichment_data:
                    part.price = float(enrichment_data['unit_price'])
            
            elif capability_name == 'fetch_specifications':
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['specifications'] = enrichment_data
                
                # Update specific fields if available
                if 'specifications' in enrichment_data:
                    specs = enrichment_data['specifications']
                    for spec in specs:
                        if isinstance(spec, dict) and spec.get('name') == 'manufacturer':
                            part.manufacturer = spec.get('value')
            
            elif capability_name == 'fetch_details':
                # Update basic fields from details enrichment
                if 'product_description' in enrichment_data:
                    part.description = enrichment_data['product_description']
                if 'manufacturer' in enrichment_data:
                    part.manufacturer = enrichment_data['manufacturer']
                if 'manufacturer_part_number' in enrichment_data:
                    part.manufacturer_part_number = enrichment_data['manufacturer_part_number']
                
                # Update additional properties
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['details_data'] = enrichment_data
            
        except Exception as e:
            logger.error(f"Error updating part from enrichment {capability_name}: {e}", exc_info=True)
    
    def _get_supplier_part_number(self, part, supplier: str) -> str:
        """
        Get the appropriate part number for a specific supplier using dynamic registry
        
        Args:
            part: Part model instance
            supplier: Supplier name (e.g., 'LCSC', 'DigiKey', 'Mouser')
            
        Returns:
            The part number to use for API calls to that supplier
        """
        if not supplier:
            return part.part_number
        
        try:
            # Use the supplier registry to get the client class
            from MakerMatrix.clients.suppliers.supplier_registry import get_supplier_class
            
            supplier_class = get_supplier_class(supplier)
            if supplier_class:
                # Create a temporary instance to use the part number extraction method
                temp_client = supplier_class()
                
                # Convert part to dictionary format
                part_data = {
                    'part_number': part.part_number,
                    'additional_properties': part.additional_properties or {}
                }
                
                # Use the supplier's own method to extract their part number
                supplier_part_number = temp_client.get_supplier_part_number(part_data)
                if supplier_part_number:
                    logger.debug(f"Using {supplier} part number: {supplier_part_number}")
                    return supplier_part_number
        
        except Exception as e:
            logger.warning(f"Failed to get supplier part number using registry for {supplier}: {e}")
        
        # Fallback to manufacturer part number
        logger.debug(f"Using manufacturer part number for {supplier}: {part.part_number}")
        return part.part_number


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


