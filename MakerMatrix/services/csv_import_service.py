import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.csv_import import DigikeyParser, LCSCParser, MouserParser, BaseCSVParser
import logging

logger = logging.getLogger(__name__)


class CSVImportService:
    """Service for importing CSV order files from various suppliers using modular parsers"""
    
    def __init__(self):
        # Register all available parsers
        self.parsers: List[BaseCSVParser] = [
            DigikeyParser(),
            LCSCParser(),
            MouserParser(),
        ]
        
        # Create lookup for parsers by type
        self.parser_lookup = {parser.parser_type: parser for parser in self.parsers}

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
        """Preview CSV content with detected type and parsed data"""
        try:
            # Detect CSV type
            detected_type = self.detect_csv_type(csv_content)
            parser = self.get_parser(detected_type) if detected_type else None
            
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
                        parts_data.append(part_data)
                        
                except Exception as e:
                    logger.error(f"CSV parsing error on row {row_num}: {str(e)}", exc_info=True)
                    errors.append(f"Row {row_num}: {str(e)}")
            
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return parts_data, errors

    async def import_parts_with_order(self, parts_data: List[Dict[str, Any]], part_service: PartService, 
                                    order_info: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Import parsed parts data and create order tracking"""
        from MakerMatrix.models.order_models import OrderModel, OrderItemModel, CreateOrderRequest, CreateOrderItemRequest
        from MakerMatrix.models.models import PartOrderSummary
        from MakerMatrix.services.order_service import order_service
        from MakerMatrix.database.db import get_session
        from sqlmodel import select
        from datetime import datetime
        
        success_parts = []
        failed_parts = []
        
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
            
            for part_data in parts_data:
                try:
                    # Check if part already exists
                    existing_part = None
                    if part_data.get('part_number'):
                        try:
                            existing_part = await part_service.get_part_by_part_number(part_data['part_number'])
                        except:
                            pass
                    
                    # Create order item record
                    order_item_data = CreateOrderItemRequest(
                        supplier_part_number=part_data['properties'].get('supplier_part_number', ''),
                        manufacturer_part_number=part_data.get('part_number', ''),
                        description=part_data['properties'].get('description', ''),
                        manufacturer=part_data['properties'].get('manufacturer', ''),
                        quantity_ordered=part_data['quantity'],
                        quantity_received=part_data['quantity'],  # Assume fully received
                        unit_price=part_data['properties'].get('unit_price', 0.0),
                        extended_price=part_data['properties'].get('extended_price', 0.0),
                        package=part_data['properties'].get('package', ''),
                        customer_reference=part_data['properties'].get('customer_reference', ''),
                        properties=part_data['properties']
                    )
                    
                    order_item = await order_service.add_order_item(order.id, order_item_data)
                    
                    if existing_part:
                        # Update existing part quantity and link to order
                        new_quantity = existing_part.quantity + part_data['quantity']
                        
                        from MakerMatrix.schemas.part_create import PartUpdate
                        update_data = PartUpdate(quantity=new_quantity)
                        part_service.update_part(existing_part.id, update_data)
                        
                        # Update or create order summary
                        session = next(get_session())
                        try:
                            # Get existing order summary
                            summary_stmt = select(PartOrderSummary).where(PartOrderSummary.part_id == existing_part.id)
                            order_summary = session.exec(summary_stmt).first()
                            
                            current_price = float(part_data['properties'].get('unit_price', 0.0))
                            
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
                                    part_id=existing_part.id,
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
                            logger.error(f"Failed to update order summary for part {existing_part.id}: {e}")
                        finally:
                            session.close()
                        
                        # Link the order item to the existing part
                        await order_service.link_order_item_to_part(order_item.id, existing_part.id)
                        
                        success_parts.append(f"Updated {part_data['part_name']}: quantity {existing_part.quantity} → {new_quantity}")
                    else:
                        # Create new part and link to order
                        new_part_result = part_service.add_part(part_data)
                        new_part_id = new_part_result['data']['id']
                        
                        # Create order summary for new part
                        session = next(get_session())
                        try:
                            current_price = float(part_data['properties'].get('unit_price', 0.0))
                            
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
                        
                except Exception as e:
                    logger.error(f"Failed to import part {part_data.get('part_name', 'Unknown')}: {str(e)}", exc_info=True)
                    failed_parts.append(f"Failed to import {part_data.get('part_name', 'Unknown')}: {str(e)}")
            
            # Update order totals
            await order_service.calculate_order_totals(order.id)
            
        except Exception as e:
            failed_parts.append(f"Failed to create order: {str(e)}")
        
        return success_parts, failed_parts


# Singleton instance
csv_import_service = CSVImportService()