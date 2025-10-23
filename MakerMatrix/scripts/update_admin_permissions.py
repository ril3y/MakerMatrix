#!/usr/bin/env python3
"""
Update admin role with users:* permissions
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.models import engine


def update_admin_permissions():
    """Add users:* permissions to admin role"""

    user_repo = UserRepository()

    try:
        # Get admin role
        admin_role = user_repo.get_role_by_name("admin")
        print(f"Current admin permissions: {admin_role.permissions}")

        # Add users and api_keys permissions if not present
        new_permissions = admin_role.permissions.copy() if admin_role.permissions else []

        required_perms = [
            "users:read",
            "users:create",
            "users:update",
            "users:delete",
            "api_keys:read",
            "api_keys:create",
            "api_keys:update",
            "api_keys:delete",
            "api_keys:admin",
        ]

        for perm in required_perms:
            if perm not in new_permissions:
                new_permissions.append(perm)
                print(f"Adding permission: {perm}")

        # Update the role
        updated_role = user_repo.update_role(role_id=admin_role.id, permissions=new_permissions)

        print(f"\n✅ Updated admin permissions: {updated_role.permissions}")

    except Exception as e:
        print(f"❌ Error updating admin permissions: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(update_admin_permissions())
