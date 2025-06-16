import csv
import io
from typing import List, Dict, Any, Optional, Tuple, Callable
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.csv_import import DigikeyParser, LCSCParser, MouserParser, BaseCSVParser
from MakerMatrix.parsers.mouser_xls_parser import MouserXLSParser
from MakerMatrix.models.csv_import_config_model import ImportProgressModel
import logging
import asyncio
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class CSVImportService:
    """Service for importing CSV order files from various suppliers using modular parsers"""
    
    def __init__(self, download_config=None):
        self.download_config = download_config or {
            'download_datasheets': True,
            'download_images': True,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30
        }
        
        # Register all available parsers with download config - disable downloads during parsing
        parsing_config = self.download_config.copy()
        parsing_config['download_datasheets'] = False  # Disable during parsing
        parsing_config['download_images'] = False      # Disable during parsing
        
        self.parsers: List[BaseCSVParser] = [
            DigikeyParser(),
            LCSCParser(download_config=parsing_config),
            MouserParser(),
            MouserXLSParser(),
        ]
        
        # Also create preview parsers (for CSV preview without downloads)
        self.preview_parsers: List[BaseCSVParser] = [
            DigikeyParser(),
            LCSCParser(download_config={'download_datasheets': False, 'download_images': False}),
            MouserParser(),
            MouserXLSParser(),
        ]
        
        # Set preview parsers to enrich-only mode
        for parser in self.preview_parsers:
            if hasattr(parser, 'enrich_only_mode'):
                parser.enrich_only_mode = True
        
        # Create lookup for parsers by type
        self.parser_lookup = {parser.parser_type: parser for parser in self.parsers}
        self.preview_parser_lookup = {parser.parser_type: parser for parser in self.preview_parsers}
        
        # Progress tracking
        self.current_progress: Optional[ImportProgressModel] = None
    
    def _convert_decimals_to_floats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively convert Decimal objects to floats in a dictionary"""
        if isinstance(data, dict):
            return {key: self._convert_decimals_to_floats(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_decimals_to_floats(item) for item in data]
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data

    def get_supported_types(self) -> List[Dict[str, Any]]:
        """Get list of supported CSV order file types"""
        return [parser.get_info() for parser in self.parsers]

    def detect_csv_type(self, csv_content: str) -> Optional[str]:
        """Auto-detect the CSV file type based on column headers"""
        try:
            # Parse the CSV to get headers
            csv_file = io.StringIO(csv_content)
            reader = csv.reader(csv_file)
            headers = next(reader, [])
            
            # Try each parser to see which one can handle this CSV
            for parser in self.parsers:
                if parser.can_parse(headers):
                    return parser.parser_type
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting CSV type: {e}")
            return None

    def get_parser(self, parser_type: str) -> Optional[BaseCSVParser]:
        """Get a parser by type"""
        return self.parser_lookup.get(parser_type)

    def register_parser(self, parser: BaseCSVParser):
        """Register a new parser (for adding custom parsers)"""
        if parser.parser_type not in self.parser_lookup:
            self.parsers.append(parser)
            self.parser_lookup[parser.parser_type] = parser
            logger.info(f"Registered new CSV parser: {parser.name}")

    def extract_order_info_from_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Try to extract order info using each parser's filename extraction method"""
        for parser in self.parsers:
            order_info = parser.extract_order_info_from_filename(filename)
            if order_info:
                return order_info
        return None

    def preview_csv(self, csv_content: str, max_rows: int = 10) -> Dict[str, Any]:
        """Preview CSV content with detected type and parsed data - NO file downloads"""
        try:
            # Detect CSV type
            detected_type = self.detect_csv_type(csv_content)
            # Use preview parser (no downloads) for CSV preview
            parser = self.preview_parser_lookup.get(detected_type) if detected_type else None
            
            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            headers = reader.fieldnames or []
            rows = []
            parsed_preview = []
            
            # Read preview rows
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                
                # Clean up row data (remove empty strings, strip whitespace)
                cleaned_row = {}
                for key, value in row.items():
                    if key and value is not None:
                        cleaned_value = str(value).strip()
                        if cleaned_value:  # Only include non-empty values
                            cleaned_row[key] = cleaned_value
                
                if cleaned_row:  # Only add non-empty rows
                    rows.append(cleaned_row)
                    
                    # Try to parse this row if we have a parser
                    if parser:
                        try:
                            parsed_data = parser.parse_row(cleaned_row, i + 2)
                            if parsed_data:
                                parsed_preview.append(parsed_data)
                        except Exception as e:
                            # Don't break preview for parsing errors
                            pass
            
            # Count total rows
            csv_file.seek(0)
            total_rows = sum(1 for _ in csv.DictReader(csv_file))
            
            # Validate headers if we have a parser
            validation_errors = []
            if parser:
                missing_columns = parser.validate_headers(headers)
                if missing_columns:
                    validation_errors = [f"Missing required columns: {', '.join(missing_columns)}"]
            
            return {
                "detected_type": detected_type,
                "type_info": parser.name if parser else "Unknown",
                "headers": headers,
                "preview_rows": rows,
                "parsed_preview": parsed_preview,
                "total_rows": total_rows,
                "is_supported": parser is not None,
                "validation_errors": validation_errors
            }
            
        except Exception as e:
            logger.error(f"Error previewing CSV: {e}")
            return {
                "error": f"Failed to parse CSV: {str(e)}",
                "detected_type": None,
                "headers": [],
                "preview_rows": [],
                "parsed_preview": [],
                "total_rows": 0,
                "is_supported": False,
                "validation_errors": [str(e)]
            }

    def parse_csv_to_parts(self, csv_content: str, parser_type: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Parse CSV content into standardized part data using specified parser"""
        parts_data = []
        errors = []
        
        # Get the parser
        parser = self.get_parser(parser_type)
        if not parser:
            errors.append(f"Unsupported parser type: {parser_type}")
            return parts_data, errors
        
        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # Validate headers
            headers = reader.fieldnames or []
            missing_columns = parser.validate_headers(headers)
            if missing_columns:
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")
                return parts_data, errors
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                try:
                    part_data = parser.parse_row(row, row_num)
                    
                    if part_data:
                        part_data['source_row'] = row_num
                        # Convert any Decimal objects to floats
                        part_data = self._convert_decimals_to_floats(part_data)
                        parts_data.append(part_data)
                        
                except Exception as e:
                    logger.error(f"CSV parsing error on row {row_num}: {str(e)}", exc_info=True)
                    errors.append(f"Row {row_num}: {str(e)}")
            
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return parts_data, errors

    async def import_parts_with_order(self, parts_data: List[Dict[str, Any]], part_service: PartService, 
                                    order_info: Dict[str, Any], progress_callback: Callable = None) -> Tuple[List[str], List[str]]:
        """Import parsed parts data and create order tracking"""
        from MakerMatrix.models.order_models import OrderModel, OrderItemModel, CreateOrderRequest, CreateOrderItemRequest
        from MakerMatrix.models.models import PartOrderSummary
        from MakerMatrix.services.order_service import order_service
        from MakerMatrix.database.db import get_session
        from sqlmodel import select
        # Note: datetime is already imported at module level
        
        success_parts = []
        failed_parts = []
        total_parts = len(parts_data)
        
        # Initialize progress
        if progress_callback:
            progress_callback({
                'total_parts': total_parts,
                'processed_parts': 0,
                'successful_parts': 0,
                'failed_parts': 0,
                'current_operation': 'Creating order record...',
                'is_downloading': False
            })
        
        try:
            # Create the order record
            order_data = CreateOrderRequest(
                order_number=order_info.get('order_number'),
                supplier=order_info.get('supplier', 'Unknown'),
                order_date=order_info.get('order_date'),
                import_source='CSV Import',
                status='delivered',  # Assume delivered since we're importing inventory
                order_metadata=order_info.get('order_metadata', {})
            )
            
            order = await order_service.create_order(order_data)
            
            # Update progress
            if progress_callback:
                progress_callback({
                    'current_operation': 'Processing parts...',
                    'is_downloading': self.download_config.get('download_datasheets', False) or self.download_config.get('download_images', False)
                })
            
            for index, part_data in enumerate(parts_data):
                # Update progress for current part
                if progress_callback:
                    part_name = part_data.get('part_name', 'Unknown')
                    is_downloading = False
                    current_op = f"Processing part {index + 1}/{total_parts}: {part_name}"
                    
                    # Check if this part has datasheets to download
                    if part_data.get('datasheets') and any(ds.get('is_downloaded', False) for ds in part_data['datasheets']):
                        is_downloading = True
                        current_op = f"Downloading datasheet for: {part_name}"
                    
                    progress_callback({
                        'processed_parts': index,
                        'current_operation': current_op,
                        'is_downloading': is_downloading,
                        'download_progress': {
                            'current_part': part_name,
                            'has_datasheet': bool(part_data.get('datasheets'))
                        }
                    })
                
                try:
                    # Check if part already exists with improved duplicate detection
                    existing_part = None
                    part_name = part_data.get('part_name', '')
                    part_number = part_data.get('part_number', '')
                    
                    logger.debug(f"Checking for duplicates: part_name='{part_name}', part_number='{part_number}'")
                    
                    # Check by part number first
                    if part_number:
                        try:
                            part_response = part_service.get_part_by_part_number(part_number)
                            if part_response and part_response.get('status') == 'success':
                                existing_part = part_response['data']
                                logger.debug(f"Found existing part by part_number: {existing_part['id']}")
                        except Exception as e:
                            logger.debug(f"No part found by part_number '{part_number}': {e}")
                    
                    # Also check by part name if not found by part number
                    if not existing_part and part_name:
                        try:
                            part_response = part_service.get_part_by_part_name(part_name)
                            if part_response and part_response.get('status') == 'success':
                                existing_part = part_response['data']
                                logger.debug(f"Found existing part by part_name: {existing_part['id']}")
                        except Exception as e:
                            logger.debug(f"No part found by part_name '{part_name}': {e}")
                    
                    if existing_part:
                        logger.info(f"Duplicate part detected: {part_name} (ID: {existing_part['id']}), will update quantity")
                    
                    # Create order item record with proper type conversion
                    unit_price = part_data['additional_properties'].get('unit_price', 0.0)
                    extended_price = part_data['additional_properties'].get('extended_price', 0.0)
                    
                    # Ensure prices are floats, not Decimals
                    if isinstance(unit_price, Decimal):
                        unit_price = float(unit_price)
                    if isinstance(extended_price, Decimal):
                        extended_price = float(extended_price)
                    
                    # Calculate extended_price if not provided or is 0.0
                    if extended_price == 0.0 and unit_price > 0.0:
                        extended_price = unit_price * part_data['quantity']
                    
                    order_item_data = CreateOrderItemRequest(
                        supplier_part_number=part_data['additional_properties'].get('supplier_part_number', ''),
                        manufacturer_part_number=part_data.get('part_number', ''),
                        description=part_data['additional_properties'].get('description', ''),
                        manufacturer=part_data['additional_properties'].get('manufacturer', ''),
                        quantity_ordered=part_data['quantity'],
                        quantity_received=part_data['quantity'],  # Assume fully received
                        unit_price=unit_price,
                        extended_price=extended_price,
                        package=part_data['additional_properties'].get('package', ''),
                        customer_reference=part_data['additional_properties'].get('customer_reference', ''),
                        properties=self._convert_decimals_to_floats(part_data['additional_properties'])
                    )
                    
                    order_item = await order_service.add_order_item(order.id, order_item_data)
                    
                    if existing_part:
                        # Update existing part quantity and link to order
                        new_quantity = existing_part['quantity'] + part_data['quantity']
                        
                        from MakerMatrix.schemas.part_create import PartUpdate
                        update_data = PartUpdate(quantity=new_quantity)
                        part_service.update_part(existing_part['id'], update_data)
                        
                        # Update or create order summary
                        session = next(get_session())
                        try:
                            # Get existing order summary
                            summary_stmt = select(PartOrderSummary).where(PartOrderSummary.part_id == existing_part['id'])
                            order_summary = session.exec(summary_stmt).first()
                            
                            current_price = float(part_data['additional_properties'].get('unit_price', 0.0))
                            
                            if order_summary:
                                # Update existing summary
                                order_summary.last_ordered_date = order.order_date
                                order_summary.last_ordered_price = current_price
                                order_summary.last_order_number = order.order_number
                                order_summary.supplier_url = part_data.get('supplier_url')
                                order_summary.total_orders += 1
                                
                                # Update pricing statistics
                                if order_summary.lowest_price is None or current_price < order_summary.lowest_price:
                                    order_summary.lowest_price = current_price
                                if order_summary.highest_price is None or current_price > order_summary.highest_price:
                                    order_summary.highest_price = current_price
                                
                                # Simple average calculation (could be improved with weighted average)
                                if order_summary.average_price:
                                    order_summary.average_price = (order_summary.average_price + current_price) / 2
                                else:
                                    order_summary.average_price = current_price
                                    
                                order_summary.updated_at = datetime.utcnow()
                                session.add(order_summary)
                            else:
                                # Create new summary
                                order_summary = PartOrderSummary(
                                    part_id=existing_part['id'],
                                    last_ordered_date=order.order_date,
                                    last_ordered_price=current_price,
                                    last_order_number=order.order_number,
                                    supplier_url=part_data.get('supplier_url'),
                                    total_orders=1,
                                    lowest_price=current_price,
                                    highest_price=current_price,
                                    average_price=current_price
                                )
                                session.add(order_summary)
                            
                            session.commit()
                        except Exception as e:
                            session.rollback()
                            logger.error(f"Failed to update order summary for part {existing_part['id']}: {e}")
                        finally:
                            session.close()
                        
                        # Link the order item to the existing part
                        await order_service.link_order_item_to_part(order_item.id, existing_part['id'])
                        
                        success_parts.append(f"Updated {part_data['part_name']}: quantity {existing_part['quantity']} → {new_quantity}")
                        
                        # Update progress
                        if progress_callback:
                            progress_callback({
                                'successful_parts': len(success_parts),
                                'processed_parts': index + 1
                            })
                            
                    else:
                        # Create new part and link to order
                        try:
                            new_part_result = part_service.add_part(part_data)
                            new_part_id = new_part_result['data']['id']
                        except Exception as e:
                            # Handle case where part was created between duplicate check and add_part call
                            error_msg = str(e)
                            if "already exists" in error_msg.lower():
                                logger.warning(f"Race condition detected - part {part_data['part_name']} was created by another process")
                                # Retry the duplicate check
                                try:
                                    if part_data.get('part_number'):
                                        part_response = part_service.get_part_by_part_number(part_data['part_number'])
                                        if part_response and part_response.get('status') == 'success':
                                            existing_part = part_response['data']
                                    else:
                                        part_response = part_service.get_part_by_part_name(part_data['part_name'])
                                        if part_response and part_response.get('status') == 'success':
                                            existing_part = part_response['data']
                                    
                                    if existing_part:
                                        # Update existing part quantity and link to order
                                        new_quantity = existing_part['quantity'] + part_data['quantity']
                                        
                                        from MakerMatrix.schemas.part_create import PartUpdate
                                        update_data = PartUpdate(quantity=new_quantity)
                                        part_service.update_part(existing_part['id'], update_data)
                                        
                                        # Link the order item to the existing part
                                        await order_service.link_order_item_to_part(order_item.id, existing_part['id'])
                                        
                                        success_parts.append(f"Updated {part_data['part_name']}: quantity {existing_part['quantity'] - part_data['quantity']} → {new_quantity}")
                                        
                                        # Update progress
                                        if progress_callback:
                                            progress_callback({
                                                'successful_parts': len(success_parts),
                                                'processed_parts': index + 1
                                            })
                                        continue
                                    else:
                                        # Still couldn't find the part, treat as failure
                                        failed_parts.append(f"Failed to import {part_data['part_name']}: {error_msg}")
                                        continue
                                except Exception as retry_error:
                                    failed_parts.append(f"Failed to import {part_data['part_name']}: {error_msg} (retry failed: {retry_error})")
                                    continue
                            else:
                                # Different error, treat as failure
                                failed_parts.append(f"Failed to import {part_data['part_name']}: {error_msg}")
                                continue
                        
                        # Create order summary for new part
                        session = next(get_session())
                        try:
                            current_price = float(part_data['additional_properties'].get('unit_price', 0.0))
                            
                            order_summary = PartOrderSummary(
                                part_id=new_part_id,
                                last_ordered_date=order.order_date,
                                last_ordered_price=current_price,
                                last_order_number=order.order_number,
                                supplier_url=part_data.get('supplier_url'),
                                total_orders=1,
                                lowest_price=current_price,
                                highest_price=current_price,
                                average_price=current_price
                            )
                            
                            session.add(order_summary)
                            session.commit()
                        except Exception as e:
                            session.rollback()
                            logger.error(f"Failed to create order summary for new part {new_part_id}: {e}")
                        finally:
                            session.close()
                        
                        # Link the order item to the new part
                        await order_service.link_order_item_to_part(order_item.id, new_part_id)
                        
                        success_parts.append(f"Added {part_data['part_name']}: {part_data['quantity']} units")
                        
                        # Update progress
                        if progress_callback:
                            progress_callback({
                                'successful_parts': len(success_parts),
                                'processed_parts': index + 1
                            })
                        
                except Exception as e:
                    logger.error(f"Failed to import part {part_data.get('part_name', 'Unknown')}: {str(e)}", exc_info=True)
                    failed_parts.append(f"Failed to import {part_data.get('part_name', 'Unknown')}: {str(e)}")
                    
                    # Update progress
                    if progress_callback:
                        progress_callback({
                            'failed_parts': len(failed_parts),
                            'processed_parts': index + 1
                        })
            
            # Final progress update
            if progress_callback:
                progress_callback({
                    'processed_parts': total_parts,
                    'current_operation': 'Finalizing import...',
                    'is_downloading': False
                })
            
            # Update order totals
            await order_service.calculate_order_totals(order.id)
            
            # Final completion update
            if progress_callback:
                progress_callback({
                    'current_operation': 'Import completed!',
                    'is_downloading': False
                })
            
        except Exception as e:
            failed_parts.append(f"Failed to create order: {str(e)}")
            if progress_callback:
                progress_callback({
                    'current_operation': f'Import failed: {str(e)}',
                    'is_downloading': False
                })
        
        return success_parts, failed_parts

    async def import_parts_with_progress(
        self, 
        parts_data: List[Dict[str, Any]], 
        part_service: PartService,
        order_info: Dict[str, Any],
        progress_callback: Optional[Callable[[ImportProgressModel], None]] = None
    ) -> Tuple[List[str], List[str]]:
        """Import parsed parts data with FAST progress tracking - NO enrichment or downloads during import"""
        
        # Initialize progress
        self.current_progress = ImportProgressModel(
            total_parts=len(parts_data),
            processed_parts=0,
            successful_parts=0,
            failed_parts=0,
            current_operation="Starting import...",
            start_time=datetime.utcnow().isoformat(),
            errors=[]
        )
        
        if progress_callback:
            progress_callback(self.current_progress)
        
        success_parts = []
        failed_parts = []
        enrichment_queue = []  # Store parts that need enrichment for later processing
        
        try:
            # Update progress
            self.current_progress.current_operation = "Creating order record..."
            if progress_callback:
                progress_callback(self.current_progress)
            
            # Create the order record
            from MakerMatrix.models.order_models import OrderModel, OrderItemModel, CreateOrderRequest, CreateOrderItemRequest
            from MakerMatrix.models.models import PartOrderSummary
            from MakerMatrix.services.order_service import order_service
            from MakerMatrix.database.db import get_session
            from sqlmodel import select
            
            order_data = CreateOrderRequest(
                order_number=order_info.get('order_number'),
                supplier=order_info.get('supplier', 'Unknown'),
                order_date=order_info.get('order_date'),
                import_source='CSV Import',
                status='delivered',
                order_metadata=order_info.get('order_metadata', {})
            )
            
            order = await order_service.create_order(order_data)
            
            # FAST part processing - NO enrichment or downloads, just pure import
            for i, part_data in enumerate(parts_data):
                try:
                    # Update progress at start of processing
                    self.current_progress.processed_parts = i
                    part_name = part_data.get('part_name', 'Unknown')
                    self.current_progress.current_operation = f"Importing part {i+1}/{len(parts_data)}: {part_name}"
                    
                    if progress_callback:
                        progress_callback(self.current_progress)
                    
                    # Check for existing part by multiple criteria
                    existing_part = None
                    
                    # Try to find existing part by part_number first
                    if part_data.get('part_number'):
                        try:
                            existing_part = await part_service.get_part_by_part_number(part_data['part_number'])
                        except:
                            pass
                    
                    # If not found by part_number, try by part_name
                    if not existing_part and part_data.get('part_name'):
                        try:
                            from MakerMatrix.repositories.parts_repositories import parts_repository
                            existing_parts = await parts_repository.get_parts_by_name(part_data['part_name'])
                            if existing_parts:
                                existing_part = existing_parts[0]
                        except:
                            pass
                    
                    # Create order item record with proper type conversion
                    unit_price = part_data['additional_properties'].get('unit_price', 0.0)
                    extended_price = part_data['additional_properties'].get('extended_price', 0.0)
                    
                    # Ensure prices are floats, not Decimals
                    if isinstance(unit_price, Decimal):
                        unit_price = float(unit_price)
                    if isinstance(extended_price, Decimal):
                        extended_price = float(extended_price)
                    
                    # Calculate extended_price if not provided or is 0.0
                    if extended_price == 0.0 and unit_price > 0.0:
                        extended_price = unit_price * part_data['quantity']
                    
                    order_item_data = CreateOrderItemRequest(
                        supplier_part_number=part_data['additional_properties'].get('supplier_part_number', ''),
                        manufacturer_part_number=part_data.get('part_number', ''),
                        description=part_data['additional_properties'].get('description', ''),
                        manufacturer=part_data['additional_properties'].get('manufacturer', ''),
                        quantity_ordered=part_data['quantity'],
                        quantity_received=part_data['quantity'],
                        unit_price=unit_price,
                        extended_price=extended_price,
                        package=part_data['additional_properties'].get('package', ''),
                        customer_reference=part_data['additional_properties'].get('customer_reference', ''),
                        properties=self._convert_decimals_to_floats(part_data['additional_properties'])
                    )
                    
                    order_item = await order_service.add_order_item(order.id, order_item_data)
                    
                    if existing_part:
                        # Update existing part quantity
                        new_quantity = existing_part.quantity + part_data['quantity']
                        from MakerMatrix.schemas.part_create import PartUpdate
                        update_data = PartUpdate(quantity=new_quantity)
                        part_service.update_part(existing_part.id, update_data)
                        await order_service.link_order_item_to_part(order_item.id, existing_part.id)
                        success_parts.append(f"Updated {part_name}: quantity {existing_part.quantity} → {new_quantity}")
                        
                        # Add to enrichment queue if needed (for existing parts too)
                        if part_data.get('additional_properties', {}).get('needs_enrichment'):
                            enrichment_queue.append({
                                'part_id': existing_part.id,
                                'part_data': part_data,
                                'action': 'update'
                            })
                    else:
                        # Create new part - this is the FAST path
                        try:
                            new_part_result = part_service.add_part(part_data)
                            new_part_id = new_part_result['data']['id']
                            await order_service.link_order_item_to_part(order_item.id, new_part_id)
                            success_parts.append(f"Added {part_name}: {part_data['quantity']} units")
                            
                            # Add to enrichment queue if needed
                            if part_data.get('additional_properties', {}).get('needs_enrichment'):
                                enrichment_queue.append({
                                    'part_id': new_part_id,
                                    'part_data': part_data,
                                    'action': 'create'
                                })
                                
                        except Exception as add_error:
                            # Handle duplicate part errors
                            if "PartAlreadyExistsError" in str(type(add_error)) or "already exists" in str(add_error):
                                logger.info(f"Part {part_name} already exists, trying to find and update it")
                                try:
                                    from MakerMatrix.repositories.parts_repositories import PartRepository
                                    from MakerMatrix.database.db import get_session
                                    
                                    with get_session() as session:
                                        existing_part = PartRepository.get_part_by_name(session, part_data['part_name'])
                                        if existing_part:
                                            new_quantity = existing_part.quantity + part_data['quantity']
                                            from MakerMatrix.schemas.part_create import PartUpdate
                                            update_data = PartUpdate(quantity=new_quantity)
                                            part_service.update_part(existing_part.id, update_data)
                                            await order_service.link_order_item_to_part(order_item.id, existing_part.id)
                                            success_parts.append(f"Updated existing {part_name}: quantity {existing_part.quantity} → {new_quantity}")
                                        else:
                                            raise add_error
                                except Exception as recovery_error:
                                    logger.error(f"Failed to recover from duplicate part error: {recovery_error}")
                                    raise add_error
                            else:
                                raise add_error
                    
                    self.current_progress.successful_parts += 1
                    
                    # Update progress after part completion - FAST!
                    self.current_progress.processed_parts = i + 1
                    self.current_progress.current_operation = f"Imported {i+1}/{len(parts_data)}: {part_name}"
                    if progress_callback:
                        progress_callback(self.current_progress)
                    
                except Exception as e:
                    logger.error(f"Failed to import part {part_data.get('part_name', 'Unknown')}: {str(e)}", exc_info=True)
                    failed_parts.append(f"Failed to import {part_data.get('part_name', 'Unknown')}: {str(e)}")
                    self.current_progress.failed_parts += 1
                    self.current_progress.errors.append(str(e))
                    
                    # Update progress after failed part
                    self.current_progress.processed_parts = i + 1
                    self.current_progress.current_operation = f"Failed part {i+1}/{len(parts_data)}: {part_data.get('part_name', 'Unknown')}"
                    if progress_callback:
                        progress_callback(self.current_progress)
            
            # Final progress update
            self.current_progress.processed_parts = len(parts_data)
            self.current_progress.current_operation = "Finalizing import..."
            if progress_callback:
                progress_callback(self.current_progress)
            
            # Update order totals
            await order_service.calculate_order_totals(order.id)
            
            # Schedule background enrichment if there are parts in the queue
            if enrichment_queue and (self.download_config.get('download_datasheets') or self.download_config.get('download_images')):
                self.current_progress.current_operation = f"Import complete! Creating background enrichment task for {len(enrichment_queue)} parts..."
                if progress_callback:
                    progress_callback(self.current_progress)
                
                # Create a proper task for background enrichment using the task system
                try:
                    from MakerMatrix.services.task_service import task_service
                    from MakerMatrix.models.task_models import TaskType, TaskPriority, CreateTaskRequest
                    
                    task_request = CreateTaskRequest(
                        task_type=TaskType.CSV_ENRICHMENT,
                        name=f"CSV Enrichment - {len(enrichment_queue)} parts",
                        description=f"Background enrichment for {len(enrichment_queue)} parts from CSV import",
                        priority=TaskPriority.NORMAL,
                        input_data={"enrichment_queue": enrichment_queue},
                        related_entity_type="csv_import",
                        related_entity_id=order.id if 'order' in locals() else None
                    )
                    
                    # Create the task (will be picked up by the task worker)
                    enrichment_task = await task_service.create_task(task_request)
                    logger.info(f"Created background enrichment task {enrichment_task.id} for {len(enrichment_queue)} parts")
                    
                except Exception as e:
                    logger.warning(f"Failed to create background enrichment task, falling back to direct execution: {e}")
                    # Fallback to direct execution
                    import asyncio
                    asyncio.create_task(self._background_enrichment_task(enrichment_queue))
            
            # Complete - show final status with enrichment info
            if enrichment_queue:
                self.current_progress.current_operation = f"Import completed! {len(enrichment_queue)} parts queued for background enrichment"
            else:
                self.current_progress.current_operation = "Import completed successfully!"
            
            if progress_callback:
                progress_callback(self.current_progress)
            
        except Exception as e:
            failed_parts.append(f"Failed to create order: {str(e)}")
            self.current_progress.errors.append(f"Order creation failed: {str(e)}")
            if progress_callback:
                progress_callback(self.current_progress)
        
        return success_parts, failed_parts

    async def _enrich_part_data(self, part_data: Dict[str, Any]):
        """Enrich part data after import (API calls, etc.)"""
        try:
            enrichment_source = part_data.get('additional_properties', {}).get('enrichment_source')
            
            if enrichment_source == 'LCSC':
                lcsc_part_number = part_data.get('additional_properties', {}).get('lcsc_part_number')
                if lcsc_part_number:
                    logger.info(f"Enriching LCSC part: {lcsc_part_number}")
                    
                    # Use the LCSC parser's enrichment method
                    from MakerMatrix.services.csv_import.lcsc_parser import LCSCParser
                    lcsc_parser = LCSCParser(download_config=self.download_config)
                    
                    # Call the enrichment method directly
                    lcsc_parser._enrich_with_easyeda_data(part_data, lcsc_part_number)
                    
                    # Mark as enriched
                    part_data['additional_properties']['enriched'] = True
                    part_data['additional_properties']['needs_enrichment'] = False
                    
        except Exception as e:
            logger.error(f"Error enriching part data: {e}")
            part_data['additional_properties']['enrichment_error'] = str(e)

    async def _download_part_files(self, part_data: Dict[str, Any], progress_callback: Optional[Callable] = None):
        """Download datasheet and image files for a part after it's been imported"""
        try:
            part_name = part_data.get('part_name', 'Unknown')
            
            # Download datasheet if URL is available and downloads are enabled
            if (self.download_config.get('download_datasheets', False) and 
                part_data.get('additional_properties', {}).get('datasheet_url')):
                
                datasheet_url = part_data['additional_properties']['datasheet_url']
                logger.info(f"Downloading datasheet for {part_name} from {datasheet_url}")
                
                # Use the file download service
                from MakerMatrix.services.file_download_service import file_download_service
                datasheet_info = file_download_service.download_datasheet(
                    url=datasheet_url,
                    part_number=part_data.get('part_number', part_name),
                    supplier=part_data.get('supplier', 'Unknown')
                )
                
                if datasheet_info:
                    part_data['additional_properties']['datasheet_file'] = datasheet_info
                    logger.info(f"Successfully downloaded datasheet for {part_name}")
                else:
                    logger.warning(f"Failed to download datasheet for {part_name}")
            
            # Download image if URL is available and downloads are enabled
            if (self.download_config.get('download_images', False) and 
                part_data.get('additional_properties', {}).get('image_url')):
                
                image_url = part_data['additional_properties']['image_url']
                logger.info(f"Downloading image for {part_name} from {image_url}")
                
                # Use the file download service
                from MakerMatrix.services.file_download_service import file_download_service
                image_info = file_download_service.download_image(
                    url=image_url,
                    part_number=part_data.get('part_number', part_name),
                    supplier=part_data.get('supplier', 'Unknown')
                )
                
                if image_info:
                    part_data['additional_properties']['image_file'] = image_info
                    logger.info(f"Successfully downloaded image for {part_name}")
                else:
                    logger.warning(f"Failed to download image for {part_name}")
                    
        except Exception as e:
            logger.error(f"Error downloading files for {part_data.get('part_name', 'Unknown')}: {e}")

    async def _background_enrichment_task(self, enrichment_queue: List[Dict[str, Any]]):
        """Background task to enrich parts without blocking the main import"""
        logger.info(f"Starting background enrichment for {len(enrichment_queue)} parts")
        
        for i, item in enumerate(enrichment_queue):
            try:
                part_id = item['part_id']
                part_data = item['part_data']
                part_name = part_data.get('part_name', 'Unknown')
                
                logger.info(f"Background enriching part {i+1}/{len(enrichment_queue)}: {part_name}")
                
                # Do enrichment if needed
                if part_data.get('additional_properties', {}).get('needs_enrichment'):
                    try:
                        await self._enrich_part_data(part_data)
                        logger.info(f"Successfully enriched {part_name}")
                    except Exception as enrich_error:
                        logger.warning(f"Background enrichment failed for {part_name}: {enrich_error}")
                
                # Do downloads if enabled
                if self.download_config.get('download_datasheets') or self.download_config.get('download_images'):
                    try:
                        await self._download_part_files(part_data)
                        logger.info(f"Successfully downloaded files for {part_name}")
                    except Exception as download_error:
                        logger.warning(f"Background download failed for {part_name}: {download_error}")
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Background enrichment error for part {item.get('part_data', {}).get('part_name', 'Unknown')}: {e}")
        
        logger.info(f"Background enrichment completed for {len(enrichment_queue)} parts")
    
    def get_current_progress(self) -> Optional[Dict[str, Any]]:
        """Get current import progress"""
        if self.current_progress:
            return self.current_progress.to_dict()
        return None


# Singleton instance
csv_import_service = CSVImportService()