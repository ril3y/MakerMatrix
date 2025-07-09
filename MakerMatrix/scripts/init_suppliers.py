#!/usr/bin/env python3
"""
Initialize supplier configurations in the database.

This script ensures that all available suppliers are properly configured
in the database with their correct capabilities.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from MakerMatrix.models.models import engine
from sqlmodel import SQLModel
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService


def main():
    """Initialize supplier configurations"""
    print("Initializing supplier configurations...")
    
    # Create all tables if they don't exist
    SQLModel.metadata.create_all(engine)
    print("Database tables created/verified")
    
    # Initialize supplier service
    supplier_service = SupplierConfigService()
    
    # Create default supplier configurations
    configs = supplier_service.initialize_default_suppliers()
    print(f"Initialized {len(configs)} supplier configurations:")
    
    for config in configs:
        capabilities = config.get('capabilities', [])
        print(f"  - {config['supplier_name']}: {len(capabilities)} capabilities")
        print(f"    Capabilities: {', '.join(capabilities)}")
    
    print("\nSupplier initialization complete!")


if __name__ == "__main__":
    main()