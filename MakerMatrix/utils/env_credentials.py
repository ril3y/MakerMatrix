"""
Environment Variable Credential Utility

Simple utility to read supplier credentials from environment variables
instead of using encrypted database storage.
"""

import os
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


def get_supplier_credentials_from_env(supplier_name: str) -> Optional[Dict[str, str]]:
    """
    Get supplier credentials from environment variables

    Environment variable naming convention:
    {SUPPLIER_NAME}_{CREDENTIAL_TYPE}

    For example:
    - MCMASTER_CARR_USERNAME
    - MCMASTER_CARR_PASSWORD
    - MCMASTER_CARR_CLIENT_CERT_PATH
    - MCMASTER_CARR_CLIENT_CERT_PASSWORD
    - MOUSER_API_KEY
    - DIGIKEY_CLIENT_ID
    - DIGIKEY_CLIENT_SECRET

    Args:
        supplier_name: Name of supplier (e.g. "McMaster-Carr", "Mouser", "DigiKey")

    Returns:
        Dictionary of credentials found in environment variables, or None if none found
    """
    # Normalize supplier name to uppercase with underscores
    env_prefix = supplier_name.upper().replace("-", "_").replace(" ", "_")

    # Common credential field names
    credential_fields = [
        "API_KEY",
        "SECRET_KEY",
        "CLIENT_ID",
        "CLIENT_SECRET",
        "USERNAME",
        "PASSWORD",
        "CLIENT_CERT_PATH",
        "CLIENT_CERT_PASSWORD",
        "OAUTH_TOKEN",
        "REFRESH_TOKEN",
        "ACCESS_TOKEN",
        "BASE_URL",
        "ENDPOINT_URL",
    ]

    credentials = {}

    for field in credential_fields:
        env_var_name = f"{env_prefix}_{field}"
        value = os.getenv(env_var_name)

        if value:
            # Convert back to lowercase field name for consistency with existing code
            field_name = field.lower()
            credentials[field_name] = value
            logger.debug(f"Found credential {field_name} for {supplier_name} from env var {env_var_name}")

    if credentials:
        logger.info(f"Loaded {len(credentials)} credentials for {supplier_name} from environment variables")
        return credentials
    else:
        logger.debug(f"No environment credentials found for {supplier_name} (checked prefix: {env_prefix}_*)")
        return None


def list_available_env_credentials() -> Dict[str, list]:
    """
    List all supplier credentials available in environment variables

    Returns:
        Dictionary mapping supplier names to lists of available credential fields
    """
    available = {}

    # Common supplier name patterns
    supplier_patterns = [
        "MCMASTER_CARR",
        "MCMASTER",
        "MOUSER",
        "DIGIKEY",
        "LCSC",
        "ARROW",
        "FARNELL",
        "NEWARK",
        "RS_COMPONENTS",
        "TTI",
    ]

    for env_var, value in os.environ.items():
        if not value:  # Skip empty values
            continue

        for pattern in supplier_patterns:
            if env_var.startswith(f"{pattern}_"):
                supplier_name = pattern.replace("_", "-").title()
                if supplier_name not in available:
                    available[supplier_name] = []

                field_name = env_var[len(pattern) + 1 :].lower()
                available[supplier_name].append(field_name)

    return available


def validate_supplier_env_credentials(supplier_name: str, required_fields: list) -> Dict[str, Any]:
    """
    Validate that all required credential fields are available in environment variables

    Args:
        supplier_name: Name of supplier
        required_fields: List of required credential field names

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "missing_fields": list,
            "available_fields": list,
            "message": str
        }
    """
    credentials = get_supplier_credentials_from_env(supplier_name)

    if not credentials:
        return {
            "valid": False,
            "missing_fields": required_fields,
            "available_fields": [],
            "message": f"No environment credentials found for {supplier_name}",
        }

    available_fields = list(credentials.keys())
    missing_fields = [field for field in required_fields if field not in available_fields]

    return {
        "valid": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "available_fields": available_fields,
        "message": (
            f"Found {len(available_fields)} credentials, missing {len(missing_fields)} required fields"
            if missing_fields
            else f"All {len(required_fields)} required credentials available"
        ),
    }
