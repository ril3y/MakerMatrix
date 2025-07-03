#!/usr/bin/env python3
"""
Recreate admin user after schema update
"""

import sys
import os

# Add the MakerMatrix directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MakerMatrix'))

from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.models import engine
from MakerMatrix.database.db import create_db_and_tables
from sqlmodel import Session

def recreate_admin():
    """Recreate admin user and roles"""
    print("👤 Recreating admin user...")
    print("=" * 50)
    
    try:
        # Initialize database tables
        create_db_and_tables()
        
        user_repo = UserRepository()
        
        # Create admin role
        print("🔑 Creating admin role...")
        try:
            admin_role = user_repo.create_role(
                name="admin",
                description="Administrator with full access",
                permissions=[
                    "all", "parts:read", "parts:create", "parts:update", "parts:delete",
                    "locations:read", "locations:create", "locations:update", "locations:delete",
                    "categories:read", "categories:create", "categories:update", "categories:delete",
                    "users:read", "users:create", "users:update", "users:delete",
                    "tasks:read", "tasks:create", "tasks:update", "tasks:delete", "tasks:admin",
                    "csv:import", "printer:use", "printer:config", "system:admin"
                ]
            )
        except RuntimeError as e:
            if "already exists" in str(e):
                print("   ℹ️ Admin role already exists")
            else:
                raise
        
        # Create user role
        print("🔑 Creating user role...")
        try:
            user_role = user_repo.create_role(
                name="user",
                description="Standard user with basic access",
                permissions=[
                    "parts:read", "parts:create", "parts:update",
                    "locations:read", "categories:read",
                    "tasks:read", "tasks:create", "csv:import", "printer:use"
                ]
            )
        except RuntimeError as e:
            if "already exists" in str(e):
                print("   ℹ️ User role already exists")
            else:
                raise
        
        # Create admin user
        print("👤 Creating admin user...")
        try:
            admin_user = user_repo.create_user(
                username="admin",
                email="admin@makermatrix.local",
                password="Admin123!",
                roles=["admin"]
            )
        except RuntimeError as e:
            if "already exists" in str(e):
                print("   ℹ️ Admin user already exists")
            else:
                raise
            
            print("✅ Admin user created successfully!")
            print("   Username: admin")
            print("   Password: Admin123!")
            print("   Email: admin@makermatrix.local")
            print("   Roles: admin")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🏁 Admin recreation completed!")
    return True

if __name__ == "__main__":
    recreate_admin()