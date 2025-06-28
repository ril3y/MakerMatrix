"""
Supplier Configuration Service

Business logic layer for managing supplier configurations and encrypted credentials.
Provides CRUD operations, validation, and integration with encryption service.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from MakerMatrix.database.db import engine
from MakerMatrix.models.supplier_config_models import (
    SupplierConfigModel,
    EnrichmentProfileModel
)
# Encryption service removed - using environment variables only
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    SupplierConfigAlreadyExistsError,
    InvalidReferenceError
)
from MakerMatrix.suppliers.base import BaseSupplier
from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers

logger = logging.getLogger(__name__)


class SupplierConfigService:
    """
    Service for managing supplier configurations and credentials
    
    Provides high-level operations for supplier configuration management
    using environment variable credentials.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SupplierConfigService")
        
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
        with Session(engine) as session:
            try:
                supplier_name = config_data.get('supplier_name', '').upper()
                self.logger.info(f"Creating supplier configuration: {supplier_name}")
                
                # Check if supplier already exists (case-insensitive)
                existing = session.query(SupplierConfigModel).filter(
                    SupplierConfigModel.supplier_name.ilike(supplier_name)
                ).first()
                
                if existing:
                    raise SupplierConfigAlreadyExistsError(
                        f"Supplier configuration for '{supplier_name}' already exists. Only one configuration per supplier type is allowed."
                    )
                
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
                
                session.add(config)
                session.commit()
                session.refresh(config)
                
                self.logger.info(f"Created supplier configuration: {config.supplier_name} (ID: {config.id})")
                return config
                
            except IntegrityError as e:
                session.rollback()
                self.logger.error(f"Integrity error creating supplier config: {e}")
                raise SupplierConfigAlreadyExistsError(
                    f"Supplier configuration '{config_data.get('supplier_name')}' already exists"
                )
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error creating supplier configuration: {e}")
                raise
    
    def get_supplier_config(self, supplier_name: str, include_credentials: bool = False) -> SupplierConfigModel:
        """
        Get supplier configuration by name
        
        Args:
            supplier_name: Name of the supplier
            include_credentials: Ignored (kept for compatibility)
            
        Returns:
            Supplier configuration
            
        Raises:
            ResourceNotFoundError: If supplier not found
        """
        with Session(engine) as session:
            config = session.query(SupplierConfigModel).filter(
                SupplierConfigModel.supplier_name == supplier_name
            ).first()
            
            if not config:
                raise ResourceNotFoundError("error", f"Supplier configuration '{supplier_name}' not found")
            
            return config
    
    def get_all_supplier_configs(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all supplier configurations as dictionaries with proper session handling
        
        Args:
            enabled_only: Whether to return only enabled configurations
            
        Returns:
            List of supplier configuration dictionaries
        """
        with Session(engine) as session:
            query = session.query(SupplierConfigModel)
            
            if enabled_only:
                query = query.filter(SupplierConfigModel.enabled == True)
            
            configs = query.all()
            
            # Convert to dictionaries while in session
            config_dicts = []
            for config in configs:
                config_dict = config.to_dict()
                config_dicts.append(config_dict)
            
            self.logger.debug(f"Retrieved {len(config_dicts)} supplier configurations")
            return config_dicts
    
    def update_supplier_config(self, supplier_name: str, update_data: Dict[str, Any]) -> SupplierConfigModel:
        """
        Update supplier configuration
        
        Args:
            supplier_name: Name of the supplier to update
            update_data: Data to update
            
        Returns:
            Updated supplier configuration
            
        Raises:
            ResourceNotFoundError: If supplier not found
        """
        with Session(engine) as session:
            config = session.query(SupplierConfigModel).filter(
                SupplierConfigModel.supplier_name == supplier_name
            ).first()
            
            if not config:
                raise ResourceNotFoundError("error", f"Supplier configuration '{supplier_name}' not found")
            
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
            
            config.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(config)
            
            self.logger.info(f"Updated supplier configuration: {supplier_name}")
            return config
    
    def delete_supplier_config(self, supplier_name: str) -> None:
        """
        Delete supplier configuration and associated credentials
        
        Args:
            supplier_name: Name of the supplier to delete
            
        Raises:
            ResourceNotFoundError: If supplier not found
        """
        with Session(engine) as session:
            config = session.query(SupplierConfigModel).filter(
                SupplierConfigModel.supplier_name == supplier_name
            ).first()
            
            if not config:
                raise ResourceNotFoundError("error", f"Supplier configuration '{supplier_name}' not found")
            
            session.delete(config)
            session.commit()
            
            self.logger.info(f"Deleted supplier configuration: {supplier_name}")
    
    def set_supplier_credentials(self, supplier_name: str, credentials: Dict[str, str], 
                               user_id: Optional[str] = None) -> None:
        """
        Database credential storage has been removed. 
        Set credentials via environment variables instead:
        
        For LCSC: No credentials needed (uses public API)
        For DigiKey: Set DIGIKEY_API_KEY and DIGIKEY_SECRET_KEY
        For Mouser: Set MOUSER_API_KEY
        
        Args:
            supplier_name: Name of the supplier
            credentials: Ignored (use environment variables)
            user_id: Ignored
        """
        self.logger.warning(
            f"Database credential storage has been removed. "
            f"To use {supplier_name}, set credentials via environment variables. "
            f"See documentation for required environment variable names."
        )
    
    def get_supplier_credentials(self, supplier_name: str, decrypt: bool = True) -> Optional[Dict[str, str]]:
        """
        Get credentials for a supplier from environment variables
        
        Args:
            supplier_name: Name of the supplier
            decrypt: Ignored (kept for compatibility)
            
        Returns:
            Dictionary of credentials or None if not found
        """
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
        credentials = self.get_supplier_credentials(supplier_name, decrypt=True)
        
        try:
            # Create supplier instance for testing
            supplier = self._create_api_client(config, credentials)
            
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
            with Session(engine) as session:
                config_db = session.query(SupplierConfigModel).filter(
                    SupplierConfigModel.supplier_name == supplier_name
                ).first()
                
                if config_db:
                    config_db.last_tested_at = start_time
                    config_db.test_status = "success" if success else "failed"
                    session.commit()
            
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
            
        except Exception as e:
            self.logger.error(f"Error testing supplier connection {supplier_name}: {e}")
            return {
                "supplier_name": supplier_name,
                "success": False,
                "error_message": str(e),
                "tested_at": datetime.utcnow().isoformat()
            }
    
    def _create_api_client(self, config: SupplierConfigModel, credentials: Optional[Dict[str, str]] = None) -> BaseSupplier:
        """
        Create supplier instance using new supplier registry
        
        Args:
            config: Supplier configuration
            credentials: Decrypted credentials
            
        Returns:
            Configured supplier instance
        """
        # Get supplier from new registry
        supplier = get_supplier(config.supplier_name.lower())
        
        # Configure the supplier with credentials and config
        config_dict = {
            'base_url': config.base_url,
            'request_timeout': config.timeout_seconds,
            'max_retries': config.max_retries,
            'rate_limit_per_minute': config.rate_limit_per_minute,
        }
        
        # Add custom parameters if available
        if config.custom_parameters:
            config_dict.update(config.custom_parameters)
        
        # Check if supplier requires credentials by looking at its schema
        try:
            credential_schema = supplier.get_credential_schema()
            required_creds = [field for field in credential_schema if field.required]
            
            if required_creds and not credentials:
                self.logger.warning(f"Supplier {config.supplier_name} requires credentials but none provided")
                # Still configure - some suppliers (like McMaster scraper mode) can work without creds
            
            # Configure the supplier
            supplier.configure(credentials or {}, config_dict)
            
        except Exception as e:
            self.logger.warning(f"Error checking credential requirements for {config.supplier_name}: {e}")
            # Still try to configure
            supplier.configure(credentials or {}, config_dict)
        
        self.logger.info(f"Successfully created {config.supplier_name} supplier instance")
        return supplier
    
    def initialize_default_suppliers(self) -> List[SupplierConfigModel]:
        """
        Initialize default supplier configurations if they don't exist
        
        Returns:
            List of created or existing supplier configurations
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
                created_configs.append(created_config)
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