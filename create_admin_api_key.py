#!/usr/bin/env python3
"""
Create an admin API key with full permissions for testing/debugging
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from MakerMatrix.services.system.api_key_service import APIKeyService
from MakerMatrix.models.api_key_models import APIKeyCreate
from MakerMatrix.models.models import engine

def create_admin_api_key():
    """Create API key with full admin permissions"""

    # Admin user ID from database
    admin_user_id = "202fd1b2-d7d1-4b4b-bd26-7165a012c93d"

    api_key_service = APIKeyService(engine=engine)

    # Create API key with full permissions
    key_data = APIKeyCreate(
        name="Admin Debug Key",
        description="Full admin API key for debugging and testing",
        role_names=["admin"],  # Admin role should have all permissions
        expires_in_days=365,  # 1 year expiration
        allowed_ips=None  # No IP restriction for testing
    )

    print(f"Creating admin API key for user {admin_user_id}...")

    response = api_key_service.create_api_key(admin_user_id, key_data)

    if response.success:
        print("\n✅ API Key created successfully!")
        print(f"\nAPI Key: {response.data.get('api_key')}")
        print(f"\nKey Details:")
        print(f"  - Name: {response.data.get('name')}")
        print(f"  - ID: {response.data.get('id')}")
        print(f"  - Prefix: {response.data.get('key_prefix')}")
        print(f"  - Permissions: {response.data.get('permissions')}")
        print(f"  - Expires: {response.data.get('expires_at')}")
        print(f"\n⚠️  SAVE THIS KEY - It won't be shown again!")
        print(f"\nUsage:")
        print(f'  curl -H "X-API-Key: {response.data.get("api_key")}" https://192.168.1.58:8443/api/parts/get_all_parts')
    else:
        print(f"\n❌ Failed to create API key: {response.message}")
        if response.errors:
            print(f"Errors: {response.errors}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(create_admin_api_key())
