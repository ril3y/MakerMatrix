"""
LCSC Supplier Implementation

Modernized implementation using unified supplier architecture:
- Uses SupplierHTTPClient for all HTTP operations (eliminates 100+ lines)
- Uses DataExtractor for standardized data parsing (eliminates 150+ lines)
- Implements defensive null safety patterns throughout
- No authentication required - uses public EasyEDA API
"""

import re
import logging
import pandas as pd
from typing import List, Dict, Any, Optional

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo, ConfigurationOption,
    CapabilityRequirement, ImportResult
)
from .registry import register_supplier
from .http_client import SupplierHTTPClient, RetryConfig
from .data_extraction import DataExtractor, extract_common_part_data
from .exceptions import (
    SupplierError, SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)
from MakerMatrix.services.data.unified_column_mapper import UnifiedColumnMapper
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper

logger = logging.getLogger(__name__)


@register_supplier("lcsc")
class LCSCSupplier(BaseSupplier):
    """
    LCSC supplier implementation using unified supplier architecture.
    
    Modernized with:
    - SupplierHTTPClient for unified HTTP operations 
    - DataExtractor for standardized parsing
    - Defensive null safety patterns
    - Consistent error handling
    """
    
    def __init__(self):
        super().__init__()
        self._http_client: Optional[SupplierHTTPClient] = None
        self._data_extractor: Optional[DataExtractor] = None
        
        # LCSC-specific data extraction configuration
        self._extraction_config = {
            "description_paths": ["dataStr.head.c_para.Value", "title", "description"],
            "image_paths": ["image_url", "thumbnail", "photo"],
            "datasheet_paths": [
                "packageDetail.dataStr.head.c_para.link",
                "dataStr.head.c_para.link", 
                "dataStr.head.c_para.Datasheet",
                "szlcsc.attributes.Datasheet"
            ],
            "specifications": {
                "manufacturer": ["dataStr.head.c_para.Manufacturer"],
                "manufacturer_part": ["dataStr.head.c_para.Manufacturer Part"],
                "package": ["dataStr.head.c_para.package"],
                "value": ["dataStr.head.c_para.Value"],
                "mounting": ["SMT"]
            },
            "base_url": "https://easyeda.com"
        }
    
    def _get_http_client(self) -> SupplierHTTPClient:
        """Get or create HTTP client with LCSC-specific configuration"""
        if not self._http_client:
            config = self._config or {}
            rate_limit = config.get("rate_limit_requests_per_minute", 20)
            
            # Calculate request delay from rate limit
            delay_seconds = 60.0 / max(rate_limit, 1)
            
            # Configure retry behavior for LCSC
            retry_config = RetryConfig(
                max_retries=2,
                base_delay=delay_seconds,
                max_delay=30.0,
                retry_on_status=[429, 500, 502, 503, 504]
            )
            
            # Standard headers for EasyEDA API
            default_headers = {
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "MakerMatrix/1.0 (easyeda2kicad compatible)"
            }
            
            # Add custom headers from configuration
            custom_headers_text = config.get("custom_headers", "")
            if custom_headers_text and custom_headers_text.strip():
                for line in custom_headers_text.strip().split('\n'):
                    line = line.strip()
                    if ':' in line:
                        header_name, header_value = line.split(':', 1)
                        default_headers[header_name.strip()] = header_value.strip()
            
            self._http_client = SupplierHTTPClient(
                supplier_name="lcsc",
                default_timeout=config.get("request_timeout", 30),
                default_headers=default_headers,
                retry_config=retry_config
            )
        
        return self._http_client
    
    def _get_data_extractor(self) -> DataExtractor:
        """Get or create data extractor"""
        if not self._data_extractor:
            self._data_extractor = DataExtractor("lcsc")
        return self._data_extractor
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="lcsc",
            display_name="LCSC Electronics",
            description="Chinese electronics component supplier with EasyEDA integration and competitive pricing. Modernized implementation with unified architecture.",
            website_url="https://www.lcsc.com",
            api_documentation_url="https://easyeda.com",
            supports_oauth=False,
            rate_limit_info="Configurable rate limiting (default: 20 requests per minute)",
            supported_file_types=["csv"]
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_PRICING_STOCK,
            SupplierCapability.IMPORT_ORDERS
        ]
    
    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """LCSC uses public API, so no credentials required"""
        return {
            cap: CapabilityRequirement(
                capability=cap,
                required_credentials=[],  # No credentials needed
                description=f"LCSC {cap.value} using public EasyEDA API"
            )
            for cap in self.get_capabilities()
        }
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        # No credentials required for LCSC public API
        return []
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        """Get configuration schema for LCSC supplier"""
        config_options = self.get_configuration_options()
        default_option = next((opt for opt in config_options if opt.is_default), None)
        return default_option.schema if default_option else []
    
    def get_configuration_options(self) -> List[ConfigurationOption]:
        """Configuration options for LCSC rate limiting"""
        return [
            ConfigurationOption(
                name='standard',
                label='LCSC Rate Limiting',
                description='Configure rate limiting for responsible LCSC API access.',
                schema=[
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=20,
                        description="Maximum requests per minute",
                        validation={"min": 1, "max": 60},
                        help_text="Lower values are more respectful to LCSC servers"
                    )
                ],
                is_default=True,
                requirements={
                    'api_key_required': False,
                    'complexity': 'low',
                    'data_type': 'public_api',
                    'prerequisites': ['Internet access']
                }
            ),
            ConfigurationOption(
                name='conservative',
                label='LCSC Conservative Rate Limiting',
                description='Very slow rate limiting for bulk operations.',
                schema=[
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=10,
                        description="Conservative rate limiting",
                        validation={"min": 1, "max": 60},
                        help_text="Best for large batch operations"
                    )
                ],
                is_default=False,
                requirements={
                    'api_key_required': False,
                    'complexity': 'low',
                    'data_type': 'public_api',
                    'prerequisites': ['Internet access']
                }
            )
        ]
    
    def _get_easyeda_api_url(self, lcsc_id: str) -> str:
        """Get EasyEDA API URL for a specific LCSC part"""
        config = self._config or {}
        version = config.get("api_version", "6.4.19.5")
        return f"https://easyeda.com/api/products/{lcsc_id}/components?version={version}"
    
    async def authenticate(self) -> bool:
        """No authentication required for EasyEDA public API"""
        return True
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to EasyEDA API using unified HTTP client"""
        if not self._configured:
            return {
                "success": False,
                "message": "Supplier not configured",
                "details": {"error": "Unconfigured supplier"}
            }
        
        try:
            http_client = self._get_http_client()
            
            # Test with a known LCSC part (resistor)
            test_lcsc_id = "C25804"  # Common 10K resistor
            url = self._get_easyeda_api_url(test_lcsc_id)
            
            # Make request using unified HTTP client
            response = await http_client.get(url, endpoint_type="test_connection")
            
            if response.success and response.data.get("result"):
                config = self._config or {}
                return {
                    "success": True,
                    "message": "LCSC/EasyEDA API connection successful",
                    "details": {
                        "api_endpoint": "EasyEDA API",
                        "test_part": test_lcsc_id,
                        "rate_limit": f"{config.get('rate_limit_requests_per_minute', 20)} requests per minute",
                        "response_time_ms": response.duration_ms,
                        "api_ready": True
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"API test failed: {response.error_message or 'Invalid response'}",
                    "details": {
                        "status_code": response.status,
                        "response_data": response.data
                    }
                }
                
        except Exception as e:
            logger.error(f"LCSC connection test failed: {e}")
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """
        LCSC/EasyEDA API doesn't support search - only individual part lookup.
        If query looks like an LCSC part number, try to get part details.
        """
        # Check if query looks like an LCSC part number (e.g., C25804, c123456)
        lcsc_pattern = re.compile(r'^c\d+$', re.IGNORECASE)
        if lcsc_pattern.match(query.strip()):
            part_details = await self.get_part_details(query.strip().upper())
            return [part_details] if part_details else []
        else:
            # For non-LCSC part numbers, return empty list since we can't search
            return []
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific LCSC part using unified architecture"""
        async def _impl():
            try:
                # Clean part number
                lcsc_id = supplier_part_number.strip().upper()
                
                # Get HTTP client and make request
                http_client = self._get_http_client()
                url = self._get_easyeda_api_url(lcsc_id)
                
                response = await http_client.get(url, endpoint_type="get_part_details")
                
                if not response.success:
                    return None
                
                # Check if result exists and has data
                result_data = response.data.get("result")
                if result_data is None:
                    return None
                
                # Parse response using unified data extractor
                return await self._parse_easyeda_response(response.data, lcsc_id)
                
            except Exception as e:
                logger.error(f"Failed to get LCSC part details for {supplier_part_number}: {e}")
                return None
        
        return await self._tracked_api_call("get_part_details", _impl)
    
    async def _parse_easyeda_response(self, data: Dict[str, Any], lcsc_id: str) -> PartSearchResult:
        """Parse EasyEDA API response using unified data extraction"""
        extractor = self._get_data_extractor()
        
        # Extract result data safely using defensive null safety
        result = extractor.safe_get(data, "result", {})
        
        # Extract common part data using unified extraction config
        extracted_data = extract_common_part_data(extractor, result, self._extraction_config)
        
        # Extract LCSC-specific data using safe access patterns
        manufacturer = extractor.safe_get(result, ["dataStr", "head", "c_para", "Manufacturer"])
        manufacturer_part_number = extractor.safe_get(result, ["dataStr", "head", "c_para", "Manufacturer Part"])
        value = extractor.safe_get(result, ["dataStr", "head", "c_para", "Value"])
        package = extractor.safe_get(result, ["dataStr", "head", "c_para", "package"])
        
        # Extract category from tags
        tags = result.get('tags', [])
        category = tags[0] if tags else ''
        
        # Determine part type from prefix
        prefix = extractor.safe_get(result, ["dataStr", "head", "c_para", "pre"], "")
        part_type = ""
        if prefix.startswith('C?'):
            part_type = "capacitor"
        elif prefix.startswith('R?'):
            part_type = "resistor"
        
        # Check if SMT
        is_smt = result.get('SMT', False)
        
        # Build specifications using defensive patterns
        specifications = {}
        if value:
            specifications['Value'] = value
        if package:
            specifications['Package'] = package
        if manufacturer:
            specifications['Manufacturer'] = manufacturer
        if is_smt:
            specifications['Mounting'] = 'SMT'
        
        # Merge with extracted specifications
        if extracted_data.get("specifications"):
            specifications.update(extracted_data["specifications"])
        
        # Build additional data
        additional_data = {
            "part_type": part_type,
            "is_smt": is_smt,
            "prefix": prefix,
            "easyeda_data_available": True,
            "product_url": f"https://lcsc.com/product-detail/{lcsc_id}.html"
        }
        
        # Use extracted datasheet URL or fallback to API data
        datasheet_url = extracted_data.get("datasheet_url")
        if not datasheet_url:
            datasheet_url = extractor.safe_get(result, ["dataStr", "head", "c_para", "link"])
        
        return PartSearchResult(
            supplier_part_number=lcsc_id,
            manufacturer=manufacturer,
            manufacturer_part_number=manufacturer_part_number,
            description=extracted_data.get("description", value or ""),
            category=category or (part_type.title() if part_type else ""),
            datasheet_url=datasheet_url,
            image_url=extracted_data.get("image_url"),
            stock_quantity=extracted_data.get("stock_quantity"),
            pricing=extracted_data.get("pricing"),
            specifications=specifications if specifications else None,
            additional_data=additional_data
        )
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for an LCSC part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.datasheet_url if part_details else None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    async def fetch_pricing_stock(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch pricing and stock information"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            if not part_details:
                return None
            
            result = {}
            if part_details.pricing:
                result["pricing"] = part_details.pricing
            if part_details.stock_quantity is not None:
                result["stock_quantity"] = part_details.stock_quantity
            
            return result if result else None
        
        return await self._tracked_api_call("fetch_pricing_stock", _impl)
    
    # ========== File Import Capability ==========
    
    def can_import_file(self, filename: str, file_content: bytes = None) -> bool:
        """Check if this supplier can handle this file"""
        if not filename:
            return False
        
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        return file_ext == 'csv' and 'lcsc' in filename.lower()
    
    async def import_order_file(self, file_content: bytes, file_type: str, filename: str = None) -> ImportResult:
        """Import LCSC CSV order file using unified patterns and proper data extraction"""
        async def _impl():
            if file_type.lower() != 'csv':
                return ImportResult(
                    success=False,
                    error_message="LCSC only supports CSV file imports"
                )
            
            try:
                # Decode CSV content with defensive encoding handling
                try:
                    csv_text = file_content.decode('utf-8-sig')  # Handle BOM
                except UnicodeDecodeError:
                    csv_text = file_content.decode('utf-8', errors='ignore')
                
                # Use pandas for robust CSV parsing
                from io import StringIO
                df = pd.read_csv(StringIO(csv_text))
                
                if df.empty:
                    return ImportResult(
                        success=False,
                        error_message="CSV file contains no data rows"
                    )
                
                # Initialize column mapper with LCSC-specific mappings
                column_mapper = UnifiedColumnMapper()
                lcsc_mappings = column_mapper.get_supplier_specific_mappings('lcsc')
                
                # Map columns using flexible matching
                mapped_columns = column_mapper.map_columns(df.columns.tolist(), lcsc_mappings)
                
                # Validate required columns
                required_fields = ['part_number', 'quantity']
                if not column_mapper.validate_required_columns(mapped_columns, required_fields):
                    return ImportResult(
                        success=False,
                        error_message=f"Required columns not found. Available columns: {list(df.columns)}"
                    )
                
                parts = []
                failed_items = []
                supplier_mapper = SupplierDataMapper()
                
                # Process each row with full data extraction
                for index, row in df.iterrows():
                    try:
                        # Extract all available data using column mapping
                        extracted_data = column_mapper.extract_row_data(row, mapped_columns)
                        
                        # Skip rows without part numbers
                        if not extracted_data.get('part_number'):
                            continue
                        
                        # Parse quantity safely
                        quantity = 1
                        if extracted_data.get('quantity'):
                            try:
                                quantity = max(1, int(float(str(extracted_data['quantity']).replace(',', ''))))
                            except (ValueError, TypeError):
                                quantity = 1
                        
                        # Parse pricing safely
                        unit_price = None
                        order_price = None
                        if extracted_data.get('unit_price'):
                            try:
                                unit_price = float(str(extracted_data['unit_price']).replace('$', '').replace(',', ''))
                            except (ValueError, TypeError):
                                pass
                        
                        if extracted_data.get('order_price'):
                            try:
                                order_price = float(str(extracted_data['order_price']).replace('$', '').replace(',', ''))
                            except (ValueError, TypeError):
                                pass
                        
                        # Create smart part name from available data
                        part_name = column_mapper.create_smart_part_name(extracted_data)
                        
                        # Build comprehensive additional_properties
                        additional_properties = self._build_lcsc_additional_properties(
                            extracted_data, unit_price, order_price, index
                        )
                        
                        # Create PartSearchResult object for SupplierDataMapper
                        from .base import PartSearchResult
                        part_search_result = PartSearchResult(
                            supplier_part_number=str(extracted_data['part_number']).strip(),
                            manufacturer=extracted_data.get('manufacturer', '').strip() if extracted_data.get('manufacturer') else None,
                            manufacturer_part_number=extracted_data.get('manufacturer_part_number', '').strip() if extracted_data.get('manufacturer_part_number') else None,
                            description=extracted_data.get('description', '').strip() if extracted_data.get('description') else None,
                            additional_data=additional_properties
                        )
                        
                        # Use SupplierDataMapper for standardization
                        standardized_part = supplier_mapper.map_supplier_result_to_part_data(
                            part_search_result, 'LCSC', enrichment_capabilities=['csv_import']
                        )
                        
                        # Add import-specific fields that aren't in PartSearchResult
                        standardized_part['part_name'] = part_name
                        standardized_part['quantity'] = quantity
                        standardized_part['supplier'] = 'LCSC'
                        
                        parts.append(standardized_part)
                        
                    except Exception as e:
                        failed_items.append({
                            'line_number': index + 2,  # +2 for header and 0-based index
                            'error': str(e),
                            'data': row.to_dict()
                        })
                        logger.warning(f"Failed to process LCSC CSV row {index + 2}: {e}")
                
                return ImportResult(
                    success=True,
                    imported_count=len(parts),
                    failed_count=len(failed_items),
                    parts=parts,
                    failed_items=failed_items,
                    parser_type="lcsc"
                )
                
            except Exception as e:
                logger.error(f"Failed to parse LCSC CSV: {e}")
                return ImportResult(
                    success=False,
                    error_message=f"Failed to parse LCSC CSV: {str(e)}"
                )
        
        return await self._tracked_api_call("import_orders", _impl)
    
    def _build_lcsc_additional_properties(self, extracted_data: Dict[str, Any], unit_price: Optional[float], order_price: Optional[float], row_index: int) -> Dict[str, Any]:
        """Build comprehensive additional_properties for LCSC parts"""
        additional_properties = {
            'supplier_data': {
                'supplier': 'LCSC',
                'supplier_part_number': extracted_data.get('part_number'),
                'row_index': row_index,
                'import_source': 'csv'
            },
            'order_info': {},
            'technical_specs': {},
            'compliance': {}
        }
        
        # Add customer reference if available
        if extracted_data.get('customer_reference'):
            additional_properties['order_info']['customer_reference'] = extracted_data['customer_reference']
        
        # Add minimum order quantity if available
        if extracted_data.get('min_order_qty'):
            try:
                min_qty_str = str(extracted_data['min_order_qty'])
                # Handle format like "5\5" - take the first number
                min_qty = int(min_qty_str.split('\\')[0]) if '\\' in min_qty_str else int(min_qty_str)
                additional_properties['order_info']['minimum_order_quantity'] = min_qty
            except (ValueError, TypeError):
                pass
        
        # Add pricing information
        if unit_price is not None:
            additional_properties['order_info']['unit_price'] = unit_price
        if order_price is not None:
            additional_properties['order_info']['order_price'] = order_price
        
        # Add package information to technical specs
        if extracted_data.get('package'):
            package_info = str(extracted_data['package']).strip()
            additional_properties['technical_specs']['package'] = package_info
            
            # Extract mounting type from package info
            if 'smd' in package_info.lower():
                additional_properties['technical_specs']['mounting_type'] = 'SMT'
            elif 'through' in package_info.lower() or 'th' in package_info.lower():
                additional_properties['technical_specs']['mounting_type'] = 'Through Hole'
        
        # Add RoHS compliance
        if extracted_data.get('rohs'):
            rohs_value = str(extracted_data['rohs']).strip().upper()
            if rohs_value in ['YES', 'Y', 'TRUE', '1']:
                additional_properties['compliance']['rohs_compliant'] = True
            elif rohs_value in ['NO', 'N', 'FALSE', '0']:
                additional_properties['compliance']['rohs_compliant'] = False
        
        # Clean up empty sections
        additional_properties = {k: v for k, v in additional_properties.items() if v}
        
        return additional_properties
    
    # ========== Cleanup ==========
    
    async def close(self):
        """Clean up resources"""
        await super().close()
        if self._http_client:
            await self._http_client.close()