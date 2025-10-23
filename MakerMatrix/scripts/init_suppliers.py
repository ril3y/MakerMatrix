#!/usr/bin/env python3
"""
Initialize supplier configurations in the database.

This script ensures that all available suppliers are properly configured
in the database with their correct capabilities and icons.
"""

import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from MakerMatrix.models.models import engine
from sqlmodel import SQLModel, Session
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.models.supplier_config_models import SupplierConfigModel
from MakerMatrix.services.utility.favicon_fetcher import FaviconFetcherService


# Built-in advanced suppliers with hardcoded icons
BUILTIN_ICON_MAP = {
    "LCSC": "/api/utility/get_image/lcsc.ico",
    "DIGIKEY": "/api/utility/get_image/digikey.png",
    "MOUSER": "/api/utility/get_image/mouser.png",
    "MCMASTER-CARR": "/api/utility/get_image/mcmaster-carr.ico",
    "BOLT-DEPOT": "/api/utility/get_image/bolt-depot.png",
}

# Default simple suppliers (URL-only, no API enrichment)
SIMPLE_SUPPLIERS = [
    {
        "supplier_name": "AMAZON",
        "display_name": "Amazon",
        "description": "Online marketplace with wide variety of electronic components and tools",
        "website_url": "https://www.amazon.com",
        "supplier_type": "simple",
        "enabled": True,
    },
    {
        "supplier_name": "ALIEXPRESS",
        "display_name": "AliExpress",
        "description": "Chinese online retail platform with electronics and components",
        "website_url": "https://www.aliexpress.com",
        "supplier_type": "simple",
        "enabled": True,
    },
    {
        "supplier_name": "WALMART",
        "display_name": "Walmart",
        "description": "Retail marketplace with electronics and tools",
        "website_url": "https://www.walmart.com",
        "supplier_type": "simple",
        "enabled": True,
    },
    {
        "supplier_name": "ALIBABA",
        "display_name": "Alibaba",
        "description": "Chinese B2B marketplace for bulk electronic components",
        "website_url": "https://www.alibaba.com",
        "supplier_type": "simple",
        "enabled": True,
    },
]


async def init_simple_suppliers():
    """Initialize simple suppliers with auto-fetched favicons"""
    print("\nInitializing simple suppliers...")
    favicon_service = FaviconFetcherService()
    added_count = 0

    with Session(engine) as session:
        for supplier_data in SIMPLE_SUPPLIERS:
            supplier_name = supplier_data["supplier_name"]

            # Check if supplier already exists
            existing = (
                session.query(SupplierConfigModel).filter(SupplierConfigModel.supplier_name == supplier_name).first()
            )

            if existing:
                print(f"  - {supplier_name}: Already exists")
                continue

            # Fetch favicon
            print(f"  - {supplier_name}: Creating...")
            image_url = await favicon_service.fetch_and_store_favicon(
                supplier_data["website_url"], supplier_name.lower()
            )

            if image_url:
                print(f"    ✓ Favicon: {image_url}")
                supplier_data["image_url"] = image_url

            # Create supplier config (simple suppliers don't need API config)
            config = SupplierConfigModel(
                **supplier_data,
                api_type="none",
                base_url="",  # No API base URL for simple suppliers
                timeout_seconds=30,
                max_retries=0,
                retry_backoff=1.0,
            )

            session.add(config)
            added_count += 1
            print(f"    ✓ Added as simple supplier")

        session.commit()

    print(f"Simple suppliers: {added_count} added")


def set_builtin_icons():
    """Set hardcoded icons for built-in advanced suppliers"""
    print("\nSetting hardcoded icons for built-in suppliers...")
    updated_count = 0

    with Session(engine) as session:
        for supplier_name, icon_url in BUILTIN_ICON_MAP.items():
            config = (
                session.query(SupplierConfigModel).filter(SupplierConfigModel.supplier_name == supplier_name).first()
            )

            if config:
                config.image_url = icon_url
                config.supplier_type = "advanced"  # Mark as advanced supplier
                updated_count += 1
                print(f"  - {supplier_name}: {icon_url}")

        session.commit()

    print(f"Built-in icons: {updated_count} set")


def main():
    """Initialize supplier configurations"""
    print("=" * 60)
    print("SUPPLIER INITIALIZATION")
    print("=" * 60)

    # Create all tables if they don't exist
    SQLModel.metadata.create_all(engine)
    print("Database tables created/verified\n")

    # Initialize advanced supplier configurations
    print("Initializing advanced suppliers...")
    supplier_service = SupplierConfigService()
    configs = supplier_service.initialize_default_suppliers()
    print(f"Advanced suppliers: {len(configs)} initialized")

    for config in configs:
        capabilities = config.get("capabilities", [])
        print(f"  - {config['supplier_name']}: {len(capabilities)} capabilities")

    # Set hardcoded icons for built-in advanced suppliers
    set_builtin_icons()

    # Initialize simple suppliers
    asyncio.run(init_simple_suppliers())

    print("\n" + "=" * 60)
    print("SUPPLIER INITIALIZATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
