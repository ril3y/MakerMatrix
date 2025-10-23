#!/usr/bin/env python3
"""
Update roles with tools:* permissions
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from MakerMatrix.repositories.user_repository import UserRepository


def update_tool_permissions():
    """Add tools:* permissions to admin, manager, and user roles"""

    user_repo = UserRepository()

    roles_to_update = {
        "admin": ["tools:read", "tools:create", "tools:update", "tools:delete", "tools:use"],
        "manager": ["tools:read", "tools:create", "tools:update", "tools:delete", "tools:use"],
        "user": ["tools:read", "tools:use"],
    }

    for role_name, new_permissions in roles_to_update.items():
        try:
            # Get role
            role = user_repo.get_role_by_name(role_name)
            print(f"\nCurrent {role_name} permissions: {role.permissions}")

            # Add tool permissions if not present
            updated_permissions = role.permissions.copy() if role.permissions else []

            for perm in new_permissions:
                if perm not in updated_permissions:
                    updated_permissions.append(perm)
                    print(f"  Adding permission: {perm}")

            # Update the role
            updated_role = user_repo.update_role(role_id=role.id, permissions=updated_permissions)

            print(f"✅ Updated {role_name} permissions: {updated_role.permissions}")

        except Exception as e:
            print(f"❌ Error updating {role_name} permissions: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(update_tool_permissions())
