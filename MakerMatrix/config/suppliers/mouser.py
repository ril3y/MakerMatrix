"""
Mouser Supplier Configuration

Configuration settings, capabilities, and metadata for Mouser Electronics
"""

from typing import Dict, Any, List

# Mouser supplier configuration
MOUSER_CONFIG: Dict[str, Any] = {
    "supplier_name": "Mouser",
    "display_name": "Mouser Electronics", 
    "description": "Electronic component distributor with comprehensive inventory and global shipping",
    "api_type": "rest",
    "base_url": "https://api.mouser.com",
    "api_version": "v1",
    
    # Rate limiting and timeouts
    "rate_limit_per_minute": 1000,
    "timeout_seconds": 30,
    "max_retries": 3,
    "retry_backoff": 1.0,
    
    # Feature flags and capabilities
    "enabled": True,
    "supports_datasheet": True,
    "supports_image": True,
    "supports_pricing": True,
    "supports_stock": True,
    "supports_specifications": True,
    
    # Authentication requirements
    "auth_type": "api_key",
    "required_credentials": ["api_key"],
    
    # Custom headers for API requests
    "custom_headers": {
        "Accept": "application/json",
        "Content-Type": "application/json"
    },
    
    # API endpoints
    "endpoints": {
        "search": "/api/v1/search/partnumber",
        "part_details": "/api/v1/search/partnumber",
        "datasheet": "/api/v1/search/partnumber",
        "pricing": "/api/v1/search/partnumber"
    }
}

# Credential field definitions for UI
MOUSER_CREDENTIAL_FIELDS: List[Dict[str, Any]] = [
    {
        "field": "api_key",
        "label": "API Key",
        "description": "Mouser API key for accessing product information",
        "type": "password",
        "required": True,
        "placeholder": "Enter your Mouser API key",
        "validation": {
            "min_length": 30,
            "pattern": r"^[A-Za-z0-9-]+$"
        }
    }
]

# API capabilities and enrichment features
MOUSER_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "fetch_datasheet": {
        "name": "Datasheet Retrieval",
        "description": "Fetch product datasheet URLs and download PDFs",
        "endpoint": "/api/v1/search/partnumber",
        "response_field": "DataSheetUrl",
        "supported": True
    },
    "fetch_image": {
        "name": "Product Images",
        "description": "Retrieve high-quality product images",
        "endpoint": "/api/v1/search/partnumber",
        "response_field": "ImagePath",
        "supported": True
    },
    "fetch_pricing": {
        "name": "Pricing Information",
        "description": "Get current pricing and quantity breaks",
        "endpoint": "/api/v1/search/partnumber",
        "response_field": "PriceBreaks",
        "supported": True
    },
    "fetch_stock": {
        "name": "Inventory Status",
        "description": "Check real-time stock availability",
        "endpoint": "/api/v1/search/partnumber",
        "response_field": "AvailabilityInStock",
        "supported": True
    },
    "fetch_specifications": {
        "name": "Technical Specifications",
        "description": "Detailed technical parameters and attributes",
        "endpoint": "/api/v1/search/partnumber",
        "response_field": "ProductAttributes",
        "supported": True
    },
    "part_search": {
        "name": "Part Search",
        "description": "Search parts by keywords and part numbers",
        "endpoint": "/api/v1/search/keyword",
        "supported": True
    }
}

# Data mapping for enrichment
MOUSER_FIELD_MAPPINGS: Dict[str, str] = {
    # Mouser API field -> MakerMatrix field
    "MouserPartNumber": "supplier_part_number",
    "ManufacturerPartNumber": "part_number",
    "Description": "description",
    "Manufacturer": "manufacturer",
    "Category": "category_name",
    "DataSheetUrl": "datasheet_url",
    "ImagePath": "image_url",
    "ProductDetailUrl": "supplier_url",
    "AvailabilityInStock": "stock_quantity",
    "PriceBreaks": "pricing_info",
    "LeadTime": "lead_time",
    "LifecycleStatus": "lifecycle_status",
    "RohsStatus": "rohs_compliant"
}

# Category mappings for part classification
MOUSER_CATEGORY_MAPPINGS: Dict[str, List[str]] = {
    "Passive Components": ["Electronics", "Passive Components"],
    "Semiconductors": ["Electronics", "Semiconductors"],
    "Connectors": ["Electronics", "Connectors"],
    "Electromechanical": ["Electronics", "Electromechanical"],
    "Sensors": ["Electronics", "Sensors"],
    "Circuit Protection": ["Electronics", "Circuit Protection"],
    "Thermal Management": ["Electronics", "Thermal Management"],
    "Crystals and Oscillators": ["Electronics", "Timing"],
    "Power Supplies": ["Electronics", "Power"],
    "Optoelectronics": ["Electronics", "Optoelectronics"],
    "Test and Measurement": ["Test Equipment"],
    "Development Boards": ["Development", "Boards"]
}

# Error handling
MOUSER_ERROR_CODES: Dict[str, str] = {
    "401": "Invalid API key - check your Mouser API credentials",
    "403": "API access forbidden - verify your Mouser account permissions",
    "404": "Part not found in Mouser catalog",
    "429": "Rate limit exceeded - reduce request frequency",
    "500": "Mouser API server error - try again later"
}

# Configuration validation rules
MOUSER_VALIDATION_RULES: Dict[str, Any] = {
    "api_key_format": r"^[A-Za-z0-9-]{30,50}$",
    "max_requests_per_minute": 1000,
    "supported_currencies": ["USD", "EUR", "GBP", "CAD"],
    "supported_regions": ["US", "EU", "APAC", "GLOBAL"]
}

# Test configuration
MOUSER_TEST_CONFIG: Dict[str, Any] = {
    "test_part_number": "595-TPS7A4700RGWR",  # Common Mouser part
    "test_search_term": "resistor",
    "expected_fields": [
        "MouserPartNumber",
        "ManufacturerPartNumber",
        "Description",
        "AvailabilityInStock"
    ]
}