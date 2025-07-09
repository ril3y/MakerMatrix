"""
Common Data Extraction Utilities for Suppliers

Provides standardized data extraction patterns across all supplier implementations:
- Pricing extraction with configurable paths
- Specification parsing and normalization
- Image URL extraction and validation
- Datasheet URL extraction
- Safe data type conversion
- Common field mapping patterns
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlparse
import json

logger = logging.getLogger(__name__)


@dataclass
class PricingBreak:
    """Standardized pricing break structure"""
    quantity: int
    price: float
    currency: str = "USD"
    
    def __post_init__(self):
        # Ensure quantity is positive
        if self.quantity <= 0:
            self.quantity = 1
        
        # Ensure price is non-negative
        if self.price < 0:
            self.price = 0.0


@dataclass
class ExtractionResult:
    """Result of data extraction operation"""
    success: bool
    value: Any = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    @classmethod
    def success_result(cls, value: Any, warnings: List[str] = None):
        """Create successful extraction result"""
        return cls(success=True, value=value, warnings=warnings or [])
    
    @classmethod
    def error_result(cls, error_message: str, warnings: List[str] = None):
        """Create failed extraction result"""
        return cls(success=False, error_message=error_message, warnings=warnings or [])


class DataExtractor:
    """
    Unified data extraction utilities for supplier implementations.
    
    Provides common patterns for extracting and normalizing data from
    supplier API responses.
    """
    
    def __init__(self, supplier_name: str):
        self.supplier_name = supplier_name
    
    # ========== Safe Data Access ==========
    
    def safe_get(self, data: Dict[str, Any], keys: Union[str, List[str]], default: Any = None) -> Any:
        """
        Safely get nested dictionary values with null protection.
        
        Args:
            data: Dictionary to extract from
            keys: Single key or list of keys for nested access
            default: Default value if key not found or is None
            
        Returns:
            Extracted value or default
            
        Example:
            price = extractor.safe_get(data, ["pricing", "breaks", 0, "price"], 0.0)
        """
        if isinstance(keys, str):
            keys = [keys]
        
        current = data
        for key in keys:
            if current is None:
                return default
            
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
                current = current[key]
            else:
                return default
        
        return current if current is not None else default
    
    def safe_cast(self, value: Any, target_type: type, default: Any = None) -> Any:
        """
        Safely cast value to target type with fallback.
        
        Args:
            value: Value to cast
            target_type: Target type (int, float, str, bool)
            default: Default value if casting fails
            
        Returns:
            Casted value or default
        """
        if value is None:
            return default
        
        try:
            if target_type == bool:
                # Special handling for boolean conversion
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
                return bool(value)
            elif target_type == float:
                # Handle Decimal and string conversion
                if isinstance(value, Decimal):
                    return float(value)
                return float(value)
            elif target_type == int:
                # Handle float-to-int conversion
                if isinstance(value, float):
                    return int(value)
                return int(value)
            else:
                return target_type(value)
                
        except (ValueError, TypeError, InvalidOperation) as e:
            logger.warning(f"Failed to cast {value} to {target_type.__name__}: {e}")
            return default
    
    # ========== Pricing Extraction ==========
    
    def extract_pricing(
        self,
        data: Dict[str, Any],
        pricing_paths: List[str],
        quantity_key: str = "quantity",
        price_key: str = "price",
        currency_key: str = "currency",
        default_currency: str = "USD"
    ) -> ExtractionResult:
        """
        Extract pricing information from supplier data.
        
        Args:
            data: Source data dictionary
            pricing_paths: List of possible paths to pricing data
            quantity_key: Key name for quantity in pricing breaks
            price_key: Key name for price in pricing breaks  
            currency_key: Key name for currency in pricing breaks
            default_currency: Default currency if not specified
            
        Returns:
            ExtractionResult with list of PricingBreak objects
        """
        warnings = []
        
        for path in pricing_paths:
            pricing_data = self.safe_get(data, path.split('.'))
            
            if not pricing_data:
                continue
            
            if not isinstance(pricing_data, list):
                warnings.append(f"Pricing data at path '{path}' is not a list")
                continue
            
            pricing_breaks = []
            
            for i, break_data in enumerate(pricing_data):
                if not isinstance(break_data, dict):
                    warnings.append(f"Pricing break {i} is not a dictionary")
                    continue
                
                # Extract quantity
                quantity = self.safe_cast(
                    self.safe_get(break_data, quantity_key, 1),
                    int,
                    1
                )
                
                # Extract price
                price = self.safe_cast(
                    self.safe_get(break_data, price_key, 0.0),
                    float,
                    0.0
                )
                
                # Extract currency
                currency = self.safe_get(break_data, currency_key, default_currency)
                if not isinstance(currency, str):
                    currency = default_currency
                
                pricing_breaks.append(PricingBreak(
                    quantity=quantity,
                    price=price,
                    currency=currency.upper()
                ))
            
            if pricing_breaks:
                # Sort by quantity
                pricing_breaks.sort(key=lambda x: x.quantity)
                return ExtractionResult.success_result(pricing_breaks, warnings)
        
        return ExtractionResult.error_result(
            f"No valid pricing data found in paths: {pricing_paths}",
            warnings
        )
    
    def extract_single_price(
        self,
        data: Dict[str, Any],
        price_paths: List[str],
        quantity: int = 1,
        currency: str = "USD"
    ) -> ExtractionResult:
        """
        Extract a single price value from supplier data.
        
        Args:
            data: Source data dictionary
            price_paths: List of possible paths to price data
            quantity: Quantity for the pricing break
            currency: Currency for the price
            
        Returns:
            ExtractionResult with single PricingBreak object
        """
        warnings = []
        
        for path in price_paths:
            price_value = self.safe_get(data, path.split('.'))
            
            if price_value is None:
                continue
            
            price = self.safe_cast(price_value, float, None)
            
            if price is not None:
                return ExtractionResult.success_result(
                    [PricingBreak(quantity=quantity, price=price, currency=currency)],
                    warnings
                )
            else:
                warnings.append(f"Could not convert price value '{price_value}' to float at path '{path}'")
        
        return ExtractionResult.error_result(
            f"No valid price found in paths: {price_paths}",
            warnings
        )
    
    # ========== URL Extraction and Validation ==========
    
    def extract_url(
        self,
        data: Dict[str, Any],
        url_paths: List[str],
        base_url: Optional[str] = None,
        required_extensions: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extract and validate URL from supplier data.
        
        Args:
            data: Source data dictionary
            url_paths: List of possible paths to URL data
            base_url: Base URL for relative URLs
            required_extensions: List of required file extensions (e.g., ['.pdf', '.jpg'])
            
        Returns:
            ExtractionResult with validated URL string
        """
        warnings = []
        
        for path in url_paths:
            url_value = self.safe_get(data, path.split('.'))
            
            if not url_value or not isinstance(url_value, str):
                continue
            
            # Clean and validate URL
            cleaned_url = url_value.strip()
            
            # Handle relative URLs
            if base_url and not cleaned_url.startswith(('http://', 'https://')):
                cleaned_url = urljoin(base_url, cleaned_url)
            
            # Validate URL format
            try:
                parsed = urlparse(cleaned_url)
                if not parsed.scheme or not parsed.netloc:
                    warnings.append(f"Invalid URL format: {cleaned_url}")
                    continue
            except Exception as e:
                warnings.append(f"URL parsing failed for {cleaned_url}: {e}")
                continue
            
            # Check file extension if required
            if required_extensions:
                url_lower = cleaned_url.lower()
                if not any(url_lower.endswith(ext.lower()) for ext in required_extensions):
                    warnings.append(f"URL does not have required extension {required_extensions}: {cleaned_url}")
                    continue
            
            return ExtractionResult.success_result(cleaned_url, warnings)
        
        return ExtractionResult.error_result(
            f"No valid URL found in paths: {url_paths}",
            warnings
        )
    
    def extract_image_url(self, data: Dict[str, Any], image_paths: List[str], base_url: Optional[str] = None) -> ExtractionResult:
        """Extract and validate image URL"""
        return self.extract_url(
            data, image_paths, base_url,
            required_extensions=['.jpg', '.jpeg', '.png', '.gif', '.webp']
        )
    
    def extract_datasheet_url(self, data: Dict[str, Any], datasheet_paths: List[str], base_url: Optional[str] = None) -> ExtractionResult:
        """Extract and validate datasheet URL"""
        return self.extract_url(
            data, datasheet_paths, base_url,
            required_extensions=['.pdf', '.doc', '.docx']
        )
    
    # ========== Specification Extraction ==========
    
    def extract_specifications(
        self,
        data: Dict[str, Any],
        spec_mapping: Dict[str, Union[str, List[str]]],
        normalize_keys: bool = True
    ) -> ExtractionResult:
        """
        Extract specifications using a mapping configuration.
        
        Args:
            data: Source data dictionary
            spec_mapping: Mapping from standardized spec names to data paths
            normalize_keys: Whether to normalize specification keys
            
        Returns:
            ExtractionResult with specifications dictionary
            
        Example:
            spec_mapping = {
                "resistance": ["specs.resistance", "parameters.resistance_value"],
                "tolerance": ["specs.tolerance", "parameters.tolerance_percent"],
                "package": ["package.type", "form_factor"]
            }
        """
        specifications = {}
        warnings = []
        
        for spec_name, paths in spec_mapping.items():
            if isinstance(paths, str):
                paths = [paths]
            
            spec_value = None
            for path in paths:
                spec_value = self.safe_get(data, path.split('.'))
                if spec_value is not None:
                    break
            
            if spec_value is not None:
                # Normalize the key if requested
                if normalize_keys:
                    normalized_key = self._normalize_spec_key(spec_name)
                else:
                    normalized_key = spec_name
                
                # Convert value to string for consistency
                specifications[normalized_key] = str(spec_value)
            else:
                warnings.append(f"No value found for specification '{spec_name}' in paths: {paths}")
        
        return ExtractionResult.success_result(specifications, warnings)
    
    def _normalize_spec_key(self, key: str) -> str:
        """Normalize specification key to standard format"""
        # Convert to lowercase and replace spaces/underscores with hyphens
        normalized = re.sub(r'[_\s]+', '-', key.lower())
        # Remove special characters except hyphens
        normalized = re.sub(r'[^a-z0-9\-]', '', normalized)
        # Remove multiple consecutive hyphens
        normalized = re.sub(r'-+', '-', normalized)
        # Remove leading/trailing hyphens
        return normalized.strip('-')
    
    # ========== Text Extraction and Cleaning ==========
    
    def extract_clean_text(
        self,
        data: Dict[str, Any],
        text_paths: List[str],
        max_length: Optional[int] = None,
        strip_html: bool = True
    ) -> ExtractionResult:
        """
        Extract and clean text content from supplier data.
        
        Args:
            data: Source data dictionary
            text_paths: List of possible paths to text data
            max_length: Maximum length for extracted text
            strip_html: Whether to strip HTML tags
            
        Returns:
            ExtractionResult with cleaned text string
        """
        warnings = []
        
        for path in text_paths:
            text_value = self.safe_get(data, path.split('.'))
            
            if not text_value:
                continue
            
            # Convert to string
            text = str(text_value).strip()
            
            if not text:
                continue
            
            # Strip HTML tags if requested
            if strip_html:
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'&[a-zA-Z0-9]+;', ' ', text)  # HTML entities
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Truncate if necessary
            if max_length and len(text) > max_length:
                text = text[:max_length].rsplit(' ', 1)[0] + '...'
                warnings.append(f"Text truncated to {max_length} characters")
            
            if text:
                return ExtractionResult.success_result(text, warnings)
        
        return ExtractionResult.error_result(
            f"No valid text found in paths: {text_paths}",
            warnings
        )
    
    # ========== Stock Quantity Extraction ==========
    
    def extract_stock_quantity(
        self,
        data: Dict[str, Any],
        stock_paths: List[str],
        availability_paths: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extract stock quantity information.
        
        Args:
            data: Source data dictionary
            stock_paths: List of possible paths to stock quantity
            availability_paths: List of paths to availability status
            
        Returns:
            ExtractionResult with stock quantity (int or None if unavailable)
        """
        warnings = []
        
        # First check availability if paths provided
        if availability_paths:
            for path in availability_paths:
                availability = self.safe_get(data, path.split('.'))
                if availability is not None:
                    # Convert to string and check for availability indicators
                    avail_str = str(availability).lower()
                    if any(indicator in avail_str for indicator in ['discontinued', 'obsolete', 'not available', 'out of stock']):
                        return ExtractionResult.success_result(0, warnings)
        
        # Extract stock quantity
        for path in stock_paths:
            stock_value = self.safe_get(data, path.split('.'))
            
            if stock_value is None:
                continue
            
            # Handle string quantities like "1000+", ">500", etc.
            if isinstance(stock_value, str):
                stock_str = stock_value.strip().lower()
                
                # Extract numeric part
                match = re.search(r'(\d+)', stock_str)
                if match:
                    quantity = int(match.group(1))
                    if '+' in stock_str or '>' in stock_str:
                        warnings.append(f"Stock quantity '{stock_value}' indicates minimum, using {quantity}")
                    return ExtractionResult.success_result(quantity, warnings)
                else:
                    warnings.append(f"Could not parse stock quantity from string: {stock_value}")
                    continue
            
            # Handle numeric values
            quantity = self.safe_cast(stock_value, int, None)
            if quantity is not None:
                return ExtractionResult.success_result(max(0, quantity), warnings)  # Ensure non-negative
        
        return ExtractionResult.error_result(
            f"No valid stock quantity found in paths: {stock_paths}",
            warnings
        )
    
    # ========== Part Number Extraction ==========
    
    def extract_part_numbers(
        self,
        data: Dict[str, Any],
        supplier_part_paths: List[str],
        manufacturer_part_paths: List[str],
        manufacturer_paths: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extract part number information.
        
        Args:
            data: Source data dictionary
            supplier_part_paths: Paths to supplier part number
            manufacturer_part_paths: Paths to manufacturer part number  
            manufacturer_paths: Paths to manufacturer name
            
        Returns:
            ExtractionResult with dict containing part number info
        """
        result = {}
        warnings = []
        
        # Extract supplier part number
        supplier_result = self.extract_clean_text(data, supplier_part_paths)
        if supplier_result.success:
            result['supplier_part_number'] = supplier_result.value
        else:
            warnings.extend(supplier_result.warnings)
        
        # Extract manufacturer part number
        mfr_result = self.extract_clean_text(data, manufacturer_part_paths)
        if mfr_result.success:
            result['manufacturer_part_number'] = mfr_result.value
        else:
            warnings.extend(mfr_result.warnings)
        
        # Extract manufacturer name
        if manufacturer_paths:
            mfr_name_result = self.extract_clean_text(data, manufacturer_paths)
            if mfr_name_result.success:
                result['manufacturer'] = mfr_name_result.value
            else:
                warnings.extend(mfr_name_result.warnings)
        
        if result:
            return ExtractionResult.success_result(result, warnings)
        else:
            return ExtractionResult.error_result("No part number information found", warnings)


# ========== Convenience Functions ==========

def create_data_extractor(supplier_name: str) -> DataExtractor:
    """Factory function to create data extractor for supplier"""
    return DataExtractor(supplier_name)


def extract_common_part_data(
    extractor: DataExtractor,
    data: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract common part data using a configuration mapping.
    
    Args:
        extractor: DataExtractor instance
        data: Source data dictionary
        config: Configuration mapping for extraction paths
        
    Returns:
        Dictionary with extracted part data
        
    Example config:
    {
        "description_paths": ["description", "summary", "title"],
        "pricing_paths": ["pricing.breaks", "price_breaks"],
        "image_paths": ["image.url", "thumbnail", "photo_url"],
        "datasheet_paths": ["datasheet.url", "documents.datasheet"],
        "specifications": {
            "resistance": ["specs.resistance", "parameters.resistance_value"],
            "tolerance": ["specs.tolerance", "parameters.tolerance_percent"]
        }
    }
    """
    extracted_data = {}
    
    # Extract description
    if "description_paths" in config:
        desc_result = extractor.extract_clean_text(data, config["description_paths"])
        if desc_result.success:
            extracted_data["description"] = desc_result.value
    
    # Extract pricing
    if "pricing_paths" in config:
        pricing_result = extractor.extract_pricing(data, config["pricing_paths"])
        if pricing_result.success:
            extracted_data["pricing"] = [
                {
                    "quantity": break_item.quantity,
                    "price": break_item.price,
                    "currency": break_item.currency
                }
                for break_item in pricing_result.value
            ]
    
    # Extract image URL
    if "image_paths" in config:
        image_result = extractor.extract_image_url(data, config["image_paths"], config.get("base_url"))
        if image_result.success:
            extracted_data["image_url"] = image_result.value
    
    # Extract datasheet URL
    if "datasheet_paths" in config:
        datasheet_result = extractor.extract_datasheet_url(data, config["datasheet_paths"], config.get("base_url"))
        if datasheet_result.success:
            extracted_data["datasheet_url"] = datasheet_result.value
    
    # Extract specifications
    if "specifications" in config:
        spec_result = extractor.extract_specifications(data, config["specifications"])
        if spec_result.success:
            extracted_data["specifications"] = spec_result.value
    
    # Extract stock quantity
    if "stock_paths" in config:
        stock_result = extractor.extract_stock_quantity(data, config["stock_paths"], config.get("availability_paths"))
        if stock_result.success:
            extracted_data["stock_quantity"] = stock_result.value
    
    return extracted_data