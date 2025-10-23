#!/usr/bin/env python3
"""
Update role permissions to add project access.

This script adds project permissions to existing roles:
- Admin: gets all project permissions (read, create, update, delete)
- User: gets projects:read (view only)
- Manager: already has project permissions (no change needed)
- Viewer: already has projects:read (no change needed)

Run with: python scripts/update_project_permissions.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from MakerMatrix.repositories.user_repository import UserRepository


def update_role_permissions():
    """Add missing project permissions to existing roles."""

    user_repo = UserRepository()

    print("Updating role permissions for project access...\n")

    # Update admin role - add all project permissions
    try:
        admin_role = user_repo.get_role_by_name("admin")
        if admin_role:
            current_permissions = admin_role.permissions or []

            # Add project permissions if not already present
            project_permissions = ["projects:read", "projects:create", "projects:update", "projects:delete"]
            permissions_to_add = [p for p in project_permissions if p not in current_permissions]

            if permissions_to_add:
                updated_permissions = current_permissions + permissions_to_add
                user_repo.update_role(admin_role.id, permissions=updated_permissions)
                print(f"✅ Admin role updated - added: {', '.join(permissions_to_add)}")
            else:
                print("✓ Admin role already has all project permissions")
        else:
            print("⚠️  Admin role not found")
    except Exception as e:
        print(f"❌ Error updating admin role: {e}")

    # Update user role - add projects:read
    try:
        user_role = user_repo.get_role_by_name("user")
        if user_role:
            current_permissions = user_role.permissions or []

            if "projects:read" not in current_permissions:
                updated_permissions = current_permissions + ["projects:read"]
                user_repo.update_role(user_role.id, permissions=updated_permissions)
                print(f"✅ User role updated - added: projects:read")
            else:
                print("✓ User role already has projects:read")
        else:
            print("⚠️  User role not found")
    except Exception as e:
        print(f"❌ Error updating user role: {e}")

    # Check manager role (should already have project permissions)
    try:
        manager_role = user_repo.get_role_by_name("manager")
        if manager_role:
            current_permissions = manager_role.permissions or []
            has_all = all(p in current_permissions for p in ["projects:read", "projects:create", "projects:update", "projects:delete"])

            if has_all:
                print("✓ Manager role already has all project permissions")
            else:
                print("⚠️  Manager role is missing some project permissions")
                print(f"   Current permissions: {current_permissions}")
    except Exception as e:
        print(f"⚠️  Error checking manager role: {e}")

    # Check viewer role (should already have projects:read)
    try:
        viewer_role = user_repo.get_role_by_name("viewer")
        if viewer_role:
            current_permissions = viewer_role.permissions or []

            if "projects:read" in current_permissions:
                print("✓ Viewer role already has projects:read")
            else:
                print("⚠️  Viewer role is missing projects:read")
    except Exception as e:
        print(f"⚠️  Error checking viewer role: {e}")

    print("\n" + "="*60)
    print("Role Permissions Summary:")
    print("="*60)

    # Display current state of all roles
    all_roles = user_repo.get_all_roles()
    for role in all_roles:
        project_perms = [p for p in (role.permissions or []) if p.startswith("projects:")]
        print(f"\n{role.name.upper()}: {role.description}")
        if project_perms:
            print(f"  Project permissions: {', '.join(project_perms)}")
        else:
            print(f"  Project permissions: None")

    print("\n" + "="*60)
    print("Update complete!")
    print("="*60)


if __name__ == "__main__":
    update_role_permissions()
