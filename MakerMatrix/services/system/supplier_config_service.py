"""
Supplier Configuration Service

Business logic layer for managing supplier configurations and encrypted credentials.
Provides CRUD operations, validation, and integration with encryption service.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from MakerMatrix.database.db import engine
from MakerMatrix.models.supplier_config_models import (
    SupplierConfigModel,
    EnrichmentProfileModel
)
from MakerMatrix.repositories.supplier_config_repository import SupplierConfigRepository
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    SupplierConfigAlreadyExistsError,
    InvalidReferenceError
)
from MakerMatrix.suppliers.base import BaseSupplier
from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers
from MakerMatrix.services.base_service import BaseService

logger = logging.getLogger(__name__)


class SupplierConfigService(BaseService):
    """
    Service for managing supplier configurations and credentials
    
    Provides high-level operations for supplier configuration management
    using environment variable credentials.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.SupplierConfigService")
        self.supplier_config_repo = SupplierConfigRepository()
        
        # Load default supplier configurations from config files
        self.default_suppliers = self._load_default_supplier_configs()
    
    def _load_default_supplier_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load default supplier configurations from new supplier registry"""
        try:
            available_suppliers = get_available_suppliers()
            supplier_dict = {}
            
            for supplier_name in available_suppliers:
                try:
                    supplier = get_supplier(supplier_name)
                    info = supplier.get_supplier_info()
                    
                    # Get actual capabilities from the supplier instance
                    capabilities = [cap.value for cap in supplier.get_capabilities()]
                    
                    # Create default config from supplier info
                    config = {
                        "supplier_name": supplier_name.upper(),
                        "display_name": info.display_name,
                        "description": info.description,
                        "api_type": "rest",
                        "base_url": getattr(info, 'website_url', 'https://example.com'),
                        "api_version": "v1",
                        "rate_limit_per_minute": 60,
                        "timeout_seconds": 30,
                        "max_retries": 3,
                        "retry_backoff": 1.0,
                        "enabled": True,
                        # Set capability flags based on actual supplier capabilities
                        "supports_datasheet": 'fetch_datasheet' in capabilities,
                        "supports_image": 'fetch_image' in capabilities,
                        "supports_pricing": 'fetch_pricing' in capabilities,
                        "supports_stock": 'fetch_stock' in capabilities,
                        "supports_specifications": 'fetch_specifications' in capabilities,
                        # Store full capabilities list as JSON
                        "capabilities": json.dumps(capabilities)
                    }
                    
                    supplier_dict[supplier_name.upper()] = config
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load supplier {supplier_name}: {e}")
                    continue
                
            self.logger.info(f"Loaded {len(supplier_dict)} default supplier configurations from registry")
            return supplier_dict
            
        except Exception as e:
            self.logger.error(f"Error loading supplier configurations from registry: {e}")
            return {}
    
    def create_supplier_config(self, config_data: Dict[str, Any], user_id: Optional[str] = None) -> SupplierConfigModel:
        """
        Create a new supplier configuration
        
        Args:
            config_data: Configuration data
            user_id: ID of the user creating the configuration
            
        Returns:
            Created supplier configuration
            
        Raises:
            SupplierConfigAlreadyExistsError: If supplier already exists
        """
        with self.get_session() as session:
            supplier_name = config_data.get('supplier_name', '').upper()
            self.logger.info(f"Creating supplier configuration: {supplier_name}")
            
            # Create configuration with normalized supplier name
            config = SupplierConfigModel(
                supplier_name=supplier_name,
                display_name=config_data.get('display_name', config_data['supplier_name']),
                description=config_data.get('description'),
                api_type=config_data.get('api_type', 'rest'),
                base_url=config_data['base_url'],
                api_version=config_data.get('api_version'),
                rate_limit_per_minute=config_data.get('rate_limit_per_minute'),
                timeout_seconds=config_data.get('timeout_seconds', 30),
                max_retries=config_data.get('max_retries', 3),
                retry_backoff=config_data.get('retry_backoff', 1.0),
                enabled=config_data.get('enabled', True),
                supports_datasheet=config_data.get('supports_datasheet', False),
                supports_image=config_data.get('supports_image', False),
                supports_pricing=config_data.get('supports_pricing', False),
                supports_stock=config_data.get('supports_stock', False),
                supports_specifications=config_data.get('supports_specifications', False),
                created_by_user_id=user_id
            )
            
            # Set custom headers and parameters
            if 'custom_headers' in config_data:
                config.set_custom_headers(config_data['custom_headers'])
            
            if 'custom_parameters' in config_data:
                config.set_custom_parameters(config_data['custom_parameters'])
            
            # Use repository to create the configuration
            return self.supplier_config_repo.create_supplier_config(session, config)
    
    def get_supplier_config(self, supplier_name: str, include_credentials: bool = False) -> Dict[str, Any]:
        """
        Get supplier configuration by name as a dictionary
        
        Args:
            supplier_name: Name of the supplier
            include_credentials: Ignored (kept for compatibility)
            
        Returns:
            Supplier configuration as dictionary
            
        Raises:
            ResourceNotFoundError: If supplier not found
        """
        with self.get_session() as session:
            config = self.supplier_config_repo.get_by_supplier_name_required(session, supplier_name)
            # Convert to dictionary while in session to avoid detached instance issues
            return config.to_dict()
    
    def get_all_supplier_configs(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all supplier configurations as dictionaries with proper session handling
        
        Args:
            enabled_only: Whether to return only enabled configurations
            
        Returns:
            List of supplier configuration dictionaries
        """
        with self.get_session() as session:
            configs = self.supplier_config_repo.get_all_configs(session, enabled_only)
            
            # Convert to dictionaries while in session
            config_dicts = []
            for config in configs:
                config_dict = config.to_dict()
                config_dicts.append(config_dict)
            
            self.logger.debug(f"Retrieved {len(config_dicts)} supplier configurations")
            return config_dicts
    
    def update_supplier_config(self, supplier_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update supplier configuration
        
        Args:
            supplier_name: Name of the supplier to update
            update_data: Data to update
            
        Returns:
            Updated supplier configuration as dictionary
            
        Raises:
            ResourceNotFoundError: If supplier not found
        """
        with self.get_session() as session:
            config = self.supplier_config_repo.get_by_supplier_name_required(session, supplier_name)
            
            # Update fields
            updatable_fields = [
                'display_name', 'description', 'api_type', 'base_url', 'api_version',
                'rate_limit_per_minute', 'timeout_seconds', 'max_retries', 'retry_backoff',
                'enabled', 'supports_datasheet', 'supports_image', 'supports_pricing',
                'supports_stock', 'supports_specifications'
            ]
            
            for field in updatable_fields:
                if field in update_data:
                    setattr(config, field, update_data[field])
            
            # Update custom headers and parameters
            if 'custom_headers' in update_data:
                config.set_custom_headers(update_data['custom_headers'])
            
            if 'custom_parameters' in update_data:
                config.set_custom_parameters(update_data['custom_parameters'])
            
            # Update capabilities list
            if 'capabilities' in update_data:
                config.set_capabilities(update_data['capabilities'])
            
            updated_config = self.supplier_config_repo.update_supplier_config(session, config)
            # Convert to dict while still in session to avoid session binding issues
            return updated_config.to_dict()
    
    def delete_supplier_config(self, supplier_name: str) -> None:
        """
        Delete supplier configuration and associated credentials
        
        Args:
            supplier_name: Name of the supplier to delete
            
        Raises:
            ResourceNotFoundError: If supplier not found
        """
        with self.get_session() as session:
            deleted = self.supplier_config_repo.delete_supplier_config(session, supplier_name)
            if not deleted:
                raise ResourceNotFoundError("error", f"Supplier configuration '{supplier_name}' not found")
    
    def set_supplier_credentials(self, supplier_name: str, credentials: Dict[str, str],
                               user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Save credentials for a supplier by writing them to the .env file.

        Args:
            supplier_name: Name of the supplier
            credentials: Dictionary of credential fields
            user_id: User ID (for logging)

        Returns:
            Dictionary with credential storage info
        """
        try:
            # Filter out empty credentials
            filtered_creds = {k: v for k, v in credentials.items() if v and str(v).strip()}

            if not filtered_creds:
                self.logger.warning(f"No valid credentials provided for {supplier_name}")
                return {"status": "no_credentials", "message": "No valid credentials provided"}

            # Map credentials to environment variable names
            env_vars = {}
            supplier_upper = supplier_name.upper()

            if supplier_upper == 'DIGIKEY':
                if 'client_id' in filtered_creds:
                    env_vars['DIGIKEY_CLIENT_ID'] = filtered_creds['client_id']
                if 'client_secret' in filtered_creds:
                    env_vars['DIGIKEY_CLIENT_SECRET'] = filtered_creds['client_secret']
            elif supplier_upper == 'MOUSER':
                if 'api_key' in filtered_creds:
                    env_vars['MOUSER_API_KEY'] = filtered_creds['api_key']
            else:
                # Generic mapping for other suppliers
                for key, value in filtered_creds.items():
                    env_var_name = f"{supplier_upper}_{key.upper()}"
                    env_vars[env_var_name] = value

            if not env_vars:
                self.logger.warning(f"No mappable credentials for {supplier_name}")
                return {"status": "no_mapping", "message": f"No environment variable mapping for {supplier_name} credentials"}

            # Write to .env file
            env_file_path = ".env"
            self._update_env_file(env_file_path, env_vars)

            self.logger.info(f"Saved credentials for {supplier_name} to .env file (variables: {list(env_vars.keys())})")

            return {
                "id": f"{supplier_name}_env_credentials",
                "status": "env_stored",
                "message": f"Credentials saved to .env file for {supplier_name}",
                "fields": list(filtered_creds.keys()),
                "env_vars": list(env_vars.keys())
            }

        except Exception as e:
            self.logger.error(f"Error setting credentials for {supplier_name}: {e}")
            raise

    def _update_env_file(self, env_file_path: str, env_vars: Dict[str, str]):
        """
        Update .env file with new environment variables.

        Args:
            env_file_path: Path to .env file
            env_vars: Dictionary of environment variables to set
        """
        import os
        from pathlib import Path

        env_path = Path(env_file_path)

        # Read existing .env content
        existing_content = []
        existing_vars = {}

        if env_path.exists():
            with open(env_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.rstrip('\n\r')
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.split('=', 1)
                        existing_vars[key.strip()] = (value, line_num)
                    existing_content.append(line)

        # Update or add environment variables
        updated_content = existing_content[:]

        for var_name, var_value in env_vars.items():
            if var_name in existing_vars:
                # Update existing variable
                old_value, line_num = existing_vars[var_name]
                updated_content[line_num - 1] = f"{var_name}={var_value}"
                self.logger.info(f"Updated {var_name} in .env file")
            else:
                # Add new variable
                updated_content.append(f"{var_name}={var_value}")
                self.logger.info(f"Added {var_name} to .env file")

        # Write back to .env file
        with open(env_path, 'w') as f:
            for line in updated_content:
                f.write(line + '\n')

        # Update current process environment
        for var_name, var_value in env_vars.items():
            os.environ[var_name] = var_value
    
    def get_supplier_credentials(self, supplier_name: str) -> Optional[Dict[str, str]]:
        """
        Get credentials for a supplier from environment variables

        Args:
            supplier_name: Name of the supplier
            decrypt: Ignored (kept for compatibility)

        Returns:
            Dictionary of credentials or None if not found
        """
        # Ensure .env file is loaded (fallback for standalone scripts and edge cases)
        from dotenv import load_dotenv
        load_dotenv()

        from MakerMatrix.utils.env_credentials import get_supplier_credentials_from_env

        env_creds = get_supplier_credentials_from_env(supplier_name)
        if env_creds:
            self.logger.info(f"Using environment credentials for {supplier_name}")
            return env_creds
        
        self.logger.warning(f"No environment credentials found for {supplier_name}")
        return None
    
    async def test_supplier_connection(self, supplier_name: str) -> Dict[str, Any]:
        """
        Test connection to supplier API
        
        Args:
            supplier_name: Name of the supplier to test
            
        Returns:
            Dictionary with test results
            
        Raises:
            ResourceNotFoundError: If supplier configuration not found
        """
        config = self.get_supplier_config(supplier_name)
        credentials = self.get_supplier_credentials(supplier_name)
        
        try:
            # Create supplier instance for testing
            supplier = self._create_api_client(config, credentials)

            try:
                # Test connection
                start_time = datetime.utcnow()
                success = False
                error_message = None

                try:
                    # New supplier system returns dict with test results
                    test_result = await supplier.test_connection()
                    if isinstance(test_result, dict):
                        success = test_result.get("success", False)
                        if not success:
                            error_message = test_result.get("message", "Connection test failed")
                    else:
                        # Fallback for old-style boolean response
                        success = bool(test_result)
                except Exception as e:
                    error_message = str(e)

                test_duration = (datetime.utcnow() - start_time).total_seconds()

                # Update test status
                with self.get_session() as session:
                    self.supplier_config_repo.update_test_status(
                        session, supplier_name,
                        "success" if success else "failed",
                        start_time
                    )

                result = {
                    "supplier_name": supplier_name,
                    "success": success,
                    "test_duration_seconds": test_duration,
                    "tested_at": start_time.isoformat(),
                    "error_message": error_message
                }

                if success:
                    self.logger.info(f"Connection test successful for {supplier_name}")
                else:
                    self.logger.warning(f"Connection test failed for {supplier_name}: {error_message}")

                return result

            finally:
                # Always clean up supplier resources
                try:
                    await supplier.close()
                except Exception as cleanup_error:
                    self.logger.warning(f"Error cleaning up supplier {supplier_name}: {cleanup_error}")
            
        except Exception as e:
            self.logger.error(f"Error testing supplier connection {supplier_name}: {e}")
            return {
                "supplier_name": supplier_name,
                "success": False,
                "error_message": str(e),
                "tested_at": datetime.utcnow().isoformat()
            }
    
    def _create_api_client(self, config: Dict[str, Any], credentials: Optional[Dict[str, str]] = None) -> BaseSupplier:
        """
        Create supplier instance using new supplier registry
        
        Args:
            config: Supplier configuration dictionary
            credentials: Decrypted credentials
            
        Returns:
            Configured supplier instance
        """
        # Get supplier from new registry
        supplier = get_supplier(config['supplier_name'].lower())
        
        # Configure the supplier with credentials and config
        config_dict = {
            'base_url': config.get('base_url', ''),
            'request_timeout': config.get('timeout_seconds', 30),
            'max_retries': config.get('max_retries', 3),
            'rate_limit_per_minute': config.get('rate_limit_per_minute', 60),
        }
        
        # Add custom parameters if available
        custom_params = config.get('custom_parameters', {})
        if custom_params:
            config_dict.update(custom_params)
        
        # Check if supplier requires credentials by looking at its schema
        try:
            credential_schema = supplier.get_credential_schema()
            required_creds = [field for field in credential_schema if field.required]
            
            if required_creds and not credentials:
                self.logger.warning(f"Supplier {config['supplier_name']} requires credentials but none provided")
                # Still configure - some suppliers (like McMaster scraper mode) can work without creds
            
            # Configure the supplier
            supplier.configure(credentials or {}, config_dict)
            
        except Exception as e:
            self.logger.warning(f"Error checking credential requirements for {config['supplier_name']}: {e}")
            # Still try to configure
            supplier.configure(credentials or {}, config_dict)
        
        self.logger.info(f"Successfully created {config['supplier_name']} supplier instance")
        return supplier
    
    def initialize_default_suppliers(self) -> List[Dict[str, Any]]:
        """
        Initialize default supplier configurations if they don't exist
        
        Returns:
            List of created or existing supplier configurations as dictionaries
        """
        created_configs = []
        
        for supplier_name, config_data in self.default_suppliers.items():
            try:
                # Check if supplier already exists
                existing = self.get_supplier_config(supplier_name)
                created_configs.append(existing)
                self.logger.debug(f"Supplier {supplier_name} already exists")
            except ResourceNotFoundError:
                # Create default supplier
                config_data['supplier_name'] = supplier_name
                created_config = self.create_supplier_config(config_data)
                # Convert to dictionary immediately after creation while still in session context
                created_config_dict = self.get_supplier_config(supplier_name)
                created_configs.append(created_config_dict)
                self.logger.info(f"Created default supplier configuration: {supplier_name}")
        
        return created_configs
    
    
    def export_supplier_configs(self, include_credentials: bool = False) -> Dict[str, Any]:
        """
        Export all supplier configurations
        
        Args:
            include_credentials: Ignored (credentials are now environment variables)
            
        Returns:
            Dictionary with all configurations
        """
        configs = self.get_all_supplier_configs()
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "suppliers": []
        }
        
        for config in configs:
            config_dict = config.to_dict()
            export_data["suppliers"].append(config_dict)
        
        self.logger.info(f"Exported {len(configs)} supplier configurations")
        return export_data
    
    def import_supplier_configs(self, import_data: Dict[str, Any], user_id: Optional[str] = None) -> List[str]:
        """
        Import supplier configurations from exported data
        
        Args:
            import_data: Exported configuration data
            user_id: ID of the user importing
            
        Returns:
            List of imported supplier names
        """
        imported_suppliers = []
        
        for supplier_data in import_data.get("suppliers", []):
            try:
                supplier_name = supplier_data["supplier_name"]
                
                # Remove non-config fields
                config_data = {k: v for k, v in supplier_data.items() 
                             if k not in ["id", "created_at", "updated_at", "has_credentials"]}
                
                # Try to create or update
                try:
                    self.create_supplier_config(config_data, user_id)
                    imported_suppliers.append(supplier_name)
                    self.logger.info(f"Imported supplier configuration: {supplier_name}")
                except SupplierConfigAlreadyExistsError:
                    # Update existing
                    self.update_supplier_config(supplier_name, config_data)
                    imported_suppliers.append(supplier_name)
                    self.logger.info(f"Updated existing supplier configuration: {supplier_name}")
                
            except Exception as e:
                self.logger.error(f"Error importing supplier {supplier_data.get('supplier_name', 'unknown')}: {e}")
        
        return imported_suppliers