#!/usr/bin/env python3
"""
Emergency Admin Password Reset Script

This script allows you to reset the admin user's password when:
- You've forgotten the admin password
- The admin account is locked
- You need emergency access to the system

SECURITY WARNING: This script has direct database access and bypasses
normal authentication. Only run this on your own server with physical access.

Usage:
    python scripts/reset_admin_password.py

The script will:
1. Prompt for a new password
2. Validate password strength
3. Update the admin user's password
4. Remove password_change_required flag
"""

import sys
import os
from getpass import getpass
from pathlib import Path

# Add parent directory to path to import MakerMatrix modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.database.db import create_db_and_tables


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number

    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    return True, ""


def reset_admin_password():
    """Reset the admin user's password."""
    print("=" * 60)
    print("🔐 MakerMatrix Admin Password Reset Tool")
    print("=" * 60)
    print()
    print("⚠️  WARNING: This tool has direct database access!")
    print("   Only use this for emergency password recovery.")
    print()

    # Confirm intention
    confirm = input("Do you want to reset the admin password? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ Aborted.")
        return

    print()

    # Initialize database
    try:
        create_db_and_tables()
        user_repo = UserRepository()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("   Make sure the database exists and is accessible.")
        return

    # Check if admin user exists
    try:
        admin_user = user_repo.get_user_by_username("admin")
        print(f"✅ Found admin user: {admin_user.username} ({admin_user.email})")
    except Exception as e:
        print(f"❌ Admin user not found: {e}")
        print("   The 'admin' user does not exist in the database.")
        print("   You may need to run: python MakerMatrix/scripts/setup_admin.py")
        return

    print()
    print("Password Requirements:")
    print("  • At least 8 characters")
    print("  • At least one uppercase letter")
    print("  • At least one lowercase letter")
    print("  • At least one number")
    print()

    # Get new password with validation
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        new_password = getpass("Enter new admin password: ")
        confirm_password = getpass("Confirm new password: ")

        if new_password != confirm_password:
            print("❌ Passwords do not match! Try again.\n")
            attempts += 1
            continue

        # Validate password strength
        is_valid, error = validate_password(new_password)
        if not is_valid:
            print(f"❌ {error}\n")
            attempts += 1
            continue

        # Password is valid
        break
    else:
        print(f"❌ Too many failed attempts ({max_attempts}). Exiting.")
        return

    # Update password
    try:
        print("\n🔄 Updating password...")
        hashed_password = user_repo.get_password_hash(new_password)

        # Update password and remove password_change_required flag
        user_repo.update_password(admin_user.id, hashed_password)
        user_repo.update_user(admin_user.id, password_change_required=False)

        print("✅ Admin password has been reset successfully!")
        print()
        print("📝 You can now login with:")
        print(f"   Username: {admin_user.username}")
        print(f"   Password: [the password you just set]")
        print()
        print("🔒 Security Reminder:")
        print("   • Keep this password secure and private")
        print("   • Consider changing it again from the web interface")
        print("   • Review user accounts and permissions")

    except Exception as e:
        print(f"❌ Failed to update password: {e}")
        print("   Please check database permissions and try again.")
        return


def main():
    """Main entry point."""
    try:
        reset_admin_password()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user. Exiting.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
