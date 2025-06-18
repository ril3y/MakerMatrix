"""
DigiKey Supplier Configuration

Configuration settings, capabilities, and metadata for DigiKey Electronics
"""

from typing import Dict, Any, List

# DigiKey supplier configuration
DIGIKEY_CONFIG: Dict[str, Any] = {
    "supplier_name": "DigiKey",
    "display_name": "DigiKey Electronics",
    "description": "Global electronic component distributor with comprehensive inventory and fast shipping",
    "api_type": "rest",
    "base_url": "https://api.digikey.com",  # Production URL
    "api_version": "v4",
    
    # Rate limiting and timeouts (DigiKey specific)
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
    "auth_type": "oauth2_client_credentials",
    "required_credentials": ["api_key", "secret_key"],  # client_id, client_secret
    
    # DigiKey specific settings
    "oauth_callback_url": "https://localhost:8139/digikey_callback",
    "sandbox_mode": True,  # Default to sandbox for safety
    "storage_path": "/tmp/digikey_cache",  # Default cache path
    "sandbox_base_url": "https://api-sandbox.digikey.com",
    "production_base_url": "https://api.digikey.com",
    
    # Custom headers for API requests
    "custom_headers": {
        "Accept": "application/json",
        "Content-Type": "application/json"
    },
    
    # API endpoints
    "endpoints": {
        "auth": "/v1/oauth2/token",
        "search": "/v4/Search/Product",
        "part_details": "/v4/Search/Product/{part_number}",
        "part_count": "/v4/Search/productcount"
    }
}

# Configuration field definitions for DigiKey setup
DIGIKEY_CONFIG_FIELDS: List[Dict[str, Any]] = [
    {
        "field": "sandbox_mode",
        "label": "Environment Mode",
        "description": "Choose between sandbox (testing) or production environment",
        "type": "select",
        "required": True,
        "default": True,
        "options": [
            {"value": True, "label": "Sandbox (Testing) - api-sandbox.digikey.com"},
            {"value": False, "label": "Production - api.digikey.com"}
        ],
        "help_text": "Sandbox mode is safe for testing. Use production only with valid production credentials."
    },
    {
        "field": "oauth_callback_url",
        "label": "OAuth Callback URL",
        "description": "OAuth callback URL for DigiKey authentication",
        "type": "text",
        "required": True,
        "default": "https://localhost:8139/digikey_callback",
        "help_text": "This must match the callback URL registered in your DigiKey app settings",
        "validation": {
            "pattern": r"^https?://.*"
        }
    },
    {
        "field": "storage_path",
        "label": "Token Storage Path",
        "description": "Directory path for storing OAuth tokens and cache",
        "type": "text",
        "required": True,
        "default": "/tmp/digikey_cache",
        "help_text": "Tokens are cached here to avoid re-authentication. Use absolute path."
    }
]

# Credential field definitions for UI
DIGIKEY_CREDENTIAL_FIELDS: List[Dict[str, Any]] = [
    {
        "field": "api_key",
        "label": "Client ID",
        "description": "DigiKey API Client ID from your developer application at developer.digikey.com",
        "type": "text",
        "required": True,
        "placeholder": "Enter your DigiKey Client ID",
        "help_text": "Found in your DigiKey Developer Portal under 'Production App' settings",
        "validation": {
            "min_length": 40,
            "max_length": 60,
            "pattern": r"^[A-Za-z0-9]+$"
        }
    },
    {
        "field": "secret_key", 
        "label": "Client Secret",
        "description": "DigiKey API Client Secret from your developer application at developer.digikey.com",
        "type": "password",
        "required": True,
        "placeholder": "Enter your DigiKey Client Secret",
        "help_text": "Found in your DigiKey Developer Portal under 'Production App' settings",
        "validation": {
            "min_length": 50,
            "max_length": 80,
            "pattern": r"^[A-Za-z0-9]+$"
        }
    }
]

# API capabilities and enrichment features
DIGIKEY_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "fetch_datasheet": {
        "name": "Datasheet Retrieval",
        "description": "Fetch product datasheet URLs and download PDFs",
        "endpoint": "/v4/Search/Product/{part_number}",
        "response_field": "PrimaryDatasheet",
        "supported": True
    },
    "fetch_image": {
        "name": "Product Images",
        "description": "Retrieve high-quality product images",
        "endpoint": "/v4/Search/Product/{part_number}",
        "response_field": "PrimaryPhoto",
        "supported": True
    },
    "fetch_pricing": {
        "name": "Pricing Information",
        "description": "Get current pricing and quantity breaks",
        "endpoint": "/v4/Search/Product/{part_number}",
        "response_field": "StandardPricing",
        "supported": True
    },
    "fetch_stock": {
        "name": "Inventory Status",
        "description": "Check real-time stock availability",
        "endpoint": "/v4/Search/Product/{part_number}",
        "response_field": "QuantityAvailable",
        "supported": True
    },
    "fetch_specifications": {
        "name": "Technical Specifications",
        "description": "Detailed technical parameters and characteristics",
        "endpoint": "/v4/Search/Product/{part_number}",
        "response_field": "Parameters",
        "supported": True
    },
    "part_search": {
        "name": "Part Search",
        "description": "Search parts by keywords, categories, and filters",
        "endpoint": "/v4/Search/Product",
        "supported": True
    }
}

# Data mapping for enrichment
DIGIKEY_FIELD_MAPPINGS: Dict[str, str] = {
    # DigiKey API field -> MakerMatrix field
    "DigiKeyPartNumber": "supplier_part_number",
    "ManufacturerPartNumber": "part_number",
    "ProductDescription": "description",
    "DetailedDescription": "detailed_description",
    "Manufacturer": "manufacturer",
    "ManufacturerProductPage": "manufacturer_url",
    "PrimaryDatasheet": "datasheet_url",
    "PrimaryPhoto": "image_url",
    "ProductUrl": "supplier_url",
    "QuantityAvailable": "stock_quantity",
    "UnitPrice": "unit_price",
    "MinimumOrderQuantity": "minimum_order_qty",
    "PackageType": "package",
    "Series": "series",
    "ProductStatus": "lifecycle_status",
    "RohsStatus": "rohs_compliant"
}

# Category mappings for part classification
DIGIKEY_CATEGORY_MAPPINGS: Dict[str, List[str]] = {
    # DigiKey category -> MakerMatrix categories
    "Resistors": ["Electronics", "Passive Components", "Resistors"],
    "Capacitors": ["Electronics", "Passive Components", "Capacitors"],
    "Inductors": ["Electronics", "Passive Components", "Inductors"],
    "Diodes": ["Electronics", "Semiconductors", "Diodes"],
    "Transistors": ["Electronics", "Semiconductors", "Transistors"],
    "Integrated Circuits": ["Electronics", "Semiconductors", "ICs"],
    "Connectors": ["Electronics", "Connectors"],
    "Crystals": ["Electronics", "Timing", "Crystals"],
    "Sensors": ["Electronics", "Sensors"],
    "LEDs": ["Electronics", "Optoelectronics", "LEDs"],
    "Switches": ["Electronics", "Switches"],
    "Relays": ["Electronics", "Relays"],
    "Transformers": ["Electronics", "Magnetics", "Transformers"],
    "Batteries": ["Power", "Batteries"],
    "Development Boards": ["Development", "Boards", "Evaluation"]
}

# Error handling and validation
DIGIKEY_ERROR_CODES: Dict[str, str] = {
    "401": "Invalid API credentials - check Client ID and Client Secret",
    "403": "API access forbidden - verify your DigiKey developer account permissions",
    "429": "Rate limit exceeded - reduce request frequency",
    "404": "Part not found in DigiKey catalog",
    "500": "DigiKey API server error - try again later",
    "503": "DigiKey API temporarily unavailable"
}

# Configuration validation rules
DIGIKEY_VALIDATION_RULES: Dict[str, Any] = {
    "client_id_format": r"^[A-Za-z0-9]{40,60}$",
    "client_secret_format": r"^[A-Za-z0-9]{40,80}$",
    "max_requests_per_minute": 1000,
    "supported_currencies": ["USD"],
    "supported_regions": ["US", "CA", "GLOBAL"]
}

# Test credentials for connection validation
DIGIKEY_TEST_CONFIG: Dict[str, Any] = {
    "test_part_number": "296-6501-1-ND",  # Common DigiKey part for testing
    "test_search_term": "resistor",
    "expected_fields": [
        "DigiKeyPartNumber",
        "ManufacturerPartNumber", 
        "ProductDescription",
        "QuantityAvailable"
    ]
}