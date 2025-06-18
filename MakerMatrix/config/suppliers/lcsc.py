"""
LCSC Supplier Configuration

Configuration settings, capabilities, and metadata for LCSC Electronics
"""

from typing import Dict, Any, List

# LCSC supplier configuration
LCSC_CONFIG: Dict[str, Any] = {
    "supplier_name": "LCSC",
    "display_name": "LCSC Electronics",
    "description": "Chinese electronic component supplier with EasyEDA integration and competitive pricing",
    "api_type": "scraping",
    "base_url": "https://easyeda.com",
    "api_version": None,
    
    # Rate limiting and timeouts  
    "rate_limit_per_minute": 300,  # 5 requests per second (5 * 60 seconds)
    "timeout_seconds": 30,
    "max_retries": 3,
    "retry_backoff": 2.0,
    
    # Feature flags and capabilities (based on actual EasyEDA API capabilities)
    "enabled": True,
    "supports_datasheet": True,   # Via web scraping LCSC product page
    "supports_image": True,       # Via result.thumb from EasyEDA API
    "supports_pricing": True,     # Via result.lcsc pricing data
    "supports_stock": False,      # Not available via EasyEDA API
    "supports_specifications": False,  # Not available via EasyEDA API (only basic c_para data)
    
    # Authentication requirements
    "auth_type": "api_key",
    "required_credentials": ["api_key"],
    
    # Custom headers for API requests
    "custom_headers": {
        "Accept": "application/json",
        "User-Agent": "MakerMatrix/1.0"
    },
    
    # API endpoints
    "endpoints": {
        "search": "/api/products/search",
        "part_details": "/api/products/{lcsc_number}",
        "datasheet": "/api/products/{lcsc_number}/datasheet",
        "stock": "/api/products/{lcsc_number}/stock"
    }
}

# Credential field definitions for UI
LCSC_CREDENTIAL_FIELDS: List[Dict[str, Any]] = [
    {
        "field": "api_key",
        "label": "API Key",
        "description": "LCSC API key for accessing product information",
        "type": "password",
        "required": True,
        "placeholder": "Enter your LCSC API key",
        "validation": {
            "min_length": 20
        }
    }
]

# API capabilities and enrichment features
LCSC_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "fetch_datasheet": {
        "name": "Datasheet Retrieval",
        "description": "Fetch product datasheet URLs and download PDFs",
        "endpoint": "/api/products/{lcsc_number}/datasheet",
        "response_field": "datasheet_url",
        "supported": True
    },
    "fetch_image": {
        "name": "Product Images",
        "description": "Retrieve product images and photos",
        "endpoint": "/api/products/{lcsc_number}",
        "response_field": "image_url",
        "supported": True
    },
    "fetch_pricing": {
        "name": "Pricing Information", 
        "description": "Get current pricing and quantity breaks",
        "endpoint": "/api/products/{lcsc_number}",
        "response_field": "price_breaks",
        "supported": True
    },
    "fetch_stock": {
        "name": "Inventory Status",
        "description": "Check real-time stock availability",
        "endpoint": "/api/products/{lcsc_number}/stock",
        "response_field": "stock_quantity",
        "supported": False  # Not available via EasyEDA API
    },
    "fetch_specifications": {
        "name": "Technical Specifications",
        "description": "Detailed technical parameters",
        "endpoint": "/api/products/{lcsc_number}",
        "response_field": "specifications",
        "supported": False  # Only basic c_para data available
    },
    "fetch_details": {
        "name": "Component Details",
        "description": "Basic component information and parameters",
        "endpoint": "/api/products/{lcsc_number}/components",
        "response_field": "dataStr.head.c_para",
        "supported": True
    },
    "part_search": {
        "name": "Part Search",
        "description": "Search parts by keywords and categories",
        "endpoint": "/api/products/search",
        "supported": True
    }
}

# Data mapping for enrichment
LCSC_FIELD_MAPPINGS: Dict[str, str] = {
    # LCSC API field -> MakerMatrix field
    "lcsc_number": "supplier_part_number",
    "mfr_part": "part_number",
    "description": "description",
    "manufacturer": "manufacturer",
    "package": "package",
    "datasheet_url": "datasheet_url",
    "image_url": "image_url",
    "stock_quantity": "stock_quantity",
    "unit_price": "unit_price",
    "min_qty": "minimum_order_qty",
    "category": "category_name"
}

# Category mappings for part classification
LCSC_CATEGORY_MAPPINGS: Dict[str, List[str]] = {
    "Resistors": ["Electronics", "Passive Components", "Resistors"],
    "Capacitors": ["Electronics", "Passive Components", "Capacitors"],
    "Inductors": ["Electronics", "Passive Components", "Inductors"],
    "Diodes": ["Electronics", "Semiconductors", "Diodes"],
    "Transistors": ["Electronics", "Semiconductors", "Transistors"],
    "ICs": ["Electronics", "Semiconductors", "ICs"],
    "Connectors": ["Electronics", "Connectors"],
    "Crystals": ["Electronics", "Timing", "Crystals"],
    "Sensors": ["Electronics", "Sensors"],
    "LEDs": ["Electronics", "Optoelectronics", "LEDs"],
    "Switches": ["Electronics", "Switches"],
    "Modules": ["Electronics", "Modules"]
}

# Error handling
LCSC_ERROR_CODES: Dict[str, str] = {
    "401": "Invalid API key",
    "404": "Part not found in LCSC catalog",
    "429": "Rate limit exceeded",
    "500": "LCSC API server error"
}

# Configuration validation rules
LCSC_VALIDATION_RULES: Dict[str, Any] = {
    "api_key_format": r"^[A-Za-z0-9_-]+$",
    "max_requests_per_minute": 60,
    "supported_currencies": ["USD", "CNY"],
    "supported_regions": ["CN", "GLOBAL"]
}

# Test configuration
LCSC_TEST_CONFIG: Dict[str, Any] = {
    "test_part_number": "C17414",  # Common LCSC part
    "test_search_term": "resistor",
    "expected_fields": [
        "lcsc_number",
        "mfr_part",
        "description",
        "stock_quantity"
    ]
}