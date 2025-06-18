"""
Supplier Configuration Module

Centralized configuration management for all supported suppliers.
Each supplier has its own configuration file with settings, capabilities, and metadata.
"""

from typing import Dict, Any, List
import importlib
import logging

from .digikey import DIGIKEY_CONFIG, DIGIKEY_CREDENTIAL_FIELDS, DIGIKEY_CAPABILITIES, DIGIKEY_CONFIG_FIELDS
from .lcsc import LCSC_CONFIG, LCSC_CREDENTIAL_FIELDS, LCSC_CAPABILITIES  
from .mouser import MOUSER_CONFIG, MOUSER_CREDENTIAL_FIELDS, MOUSER_CAPABILITIES

logger = logging.getLogger(__name__)

# Registry of all supported suppliers
SUPPLIER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "DigiKey": {
        "config": DIGIKEY_CONFIG,
        "credential_fields": DIGIKEY_CREDENTIAL_FIELDS,
        "capabilities": DIGIKEY_CAPABILITIES,
        "config_fields": DIGIKEY_CONFIG_FIELDS
    },
    "LCSC": {
        "config": LCSC_CONFIG,
        "credential_fields": LCSC_CREDENTIAL_FIELDS,
        "capabilities": LCSC_CAPABILITIES,
        "config_fields": []  # LCSC uses generic fields
    },
    "Mouser": {
        "config": MOUSER_CONFIG,
        "credential_fields": MOUSER_CREDENTIAL_FIELDS,
        "capabilities": MOUSER_CAPABILITIES,
        "config_fields": []  # Mouser uses generic fields
    }
}

def get_supplier_config(supplier_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific supplier
    
    Args:
        supplier_name: Name of the supplier
        
    Returns:
        Supplier configuration dictionary
        
    Raises:
        KeyError: If supplier not found
    """
    if supplier_name not in SUPPLIER_REGISTRY:
        available = ", ".join(SUPPLIER_REGISTRY.keys())
        raise KeyError(f"Supplier '{supplier_name}' not found. Available: {available}")
    
    return SUPPLIER_REGISTRY[supplier_name]["config"]

def get_supplier_credential_fields(supplier_name: str) -> List[Dict[str, Any]]:
    """
    Get credential field definitions for a supplier
    
    Args:
        supplier_name: Name of the supplier
        
    Returns:
        List of credential field definitions
    """
    if supplier_name not in SUPPLIER_REGISTRY:
        return []
    
    return SUPPLIER_REGISTRY[supplier_name]["credential_fields"]

def get_supplier_config_fields(supplier_name: str) -> List[Dict[str, Any]]:
    """
    Get configuration field definitions for a supplier
    
    Args:
        supplier_name: Name of the supplier
        
    Returns:
        List of configuration field definitions specific to this supplier
    """
    if supplier_name not in SUPPLIER_REGISTRY:
        return []
    
    return SUPPLIER_REGISTRY[supplier_name]["config_fields"]

def has_custom_config_fields(supplier_name: str) -> bool:
    """
    Check if a supplier has custom configuration fields
    
    Args:
        supplier_name: Name of the supplier
        
    Returns:
        True if supplier has custom config fields, False if it uses generic fields
    """
    config_fields = get_supplier_config_fields(supplier_name)
    return len(config_fields) > 0

def get_supplier_capabilities(supplier_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get capabilities for a specific supplier
    
    Args:
        supplier_name: Name of the supplier
        
    Returns:
        Dictionary of supplier capabilities
    """
    if supplier_name not in SUPPLIER_REGISTRY:
        return {}
    
    return SUPPLIER_REGISTRY[supplier_name]["capabilities"]

def get_all_suppliers() -> List[str]:
    """
    Get list of all supported supplier names
    
    Returns:
        List of supplier names
    """
    return list(SUPPLIER_REGISTRY.keys())

def get_suppliers_with_capability(capability: str) -> List[str]:
    """
    Get list of suppliers that support a specific capability
    
    Args:
        capability: Capability name (e.g., 'fetch_datasheet')
        
    Returns:
        List of supplier names that support the capability
    """
    suppliers = []
    
    for supplier_name, supplier_info in SUPPLIER_REGISTRY.items():
        capabilities = supplier_info["capabilities"]
        if capability in capabilities and capabilities[capability].get("supported", False):
            suppliers.append(supplier_name)
    
    return suppliers

def validate_supplier_credentials(supplier_name: str, credentials: Dict[str, str]) -> List[str]:
    """
    Validate credentials for a supplier
    
    Args:
        supplier_name: Name of the supplier
        credentials: Dictionary of credential values
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if supplier_name not in SUPPLIER_REGISTRY:
        errors.append(f"Unknown supplier: {supplier_name}")
        return errors
    
    credential_fields = get_supplier_credential_fields(supplier_name)
    
    for field_def in credential_fields:
        field_name = field_def["field"]
        field_label = field_def.get("label", field_name)
        required = field_def.get("required", False)
        validation = field_def.get("validation", {})
        
        value = credentials.get(field_name, "")
        
        # Check required fields
        if required and not value:
            errors.append(f"{field_label} is required")
            continue
        
        if value:
            # Check minimum length
            min_length = validation.get("min_length")
            if min_length and len(value) < min_length:
                errors.append(f"{field_label} must be at least {min_length} characters")
            
            # Check pattern matching
            pattern = validation.get("pattern")
            if pattern:
                import re
                if not re.match(pattern, value):
                    errors.append(f"{field_label} format is invalid")
    
    return errors

def get_default_supplier_configs() -> List[Dict[str, Any]]:
    """
    Get list of default supplier configurations for initialization
    
    Returns:
        List of supplier configuration dictionaries
    """
    configs = []
    
    for supplier_name in SUPPLIER_REGISTRY:
        config = get_supplier_config(supplier_name).copy()
        # Ensure supplier_name is set correctly
        config["supplier_name"] = supplier_name
        configs.append(config)
    
    logger.info(f"Generated {len(configs)} default supplier configurations")
    return configs

# Export commonly used items
__all__ = [
    "SUPPLIER_REGISTRY",
    "get_supplier_config",
    "get_supplier_credential_fields", 
    "get_supplier_config_fields",
    "has_custom_config_fields",
    "get_supplier_capabilities",
    "get_all_suppliers",
    "get_suppliers_with_capability",
    "validate_supplier_credentials",
    "get_default_supplier_configs"
]