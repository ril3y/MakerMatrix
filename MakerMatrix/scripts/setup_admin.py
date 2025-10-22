from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.models import engine
from sqlmodel import SQLModel
from MakerMatrix.database.db import create_db_and_tables
from passlib.hash import pbkdf2_sha256

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@makermatrix.local"
DEFAULT_ADMIN_PASSWORD = "Admin123!"  # This should be changed on first login


def setup_default_roles(user_repo: UserRepository):
    """Set up default roles if they don't exist."""
    roles = [
        {
            "name": "admin",
            "description": "Administrator with full access",
            "permissions": [
                "all",
                "parts:read",
                "parts:create",
                "parts:update",
                "parts:delete",
                "locations:read",
                "locations:create",
                "locations:update",
                "locations:delete",
                "categories:read",
                "categories:create",
                "categories:update",
                "categories:delete",
                "users:read",
                "users:create",
                "users:update",
                "users:delete",
                "api_keys:read",
                "api_keys:create",
                "api_keys:update",
                "api_keys:delete",
                "api_keys:admin",
                "tasks:read",
                "tasks:create",
                "tasks:update",
                "tasks:admin",
                "tools:read",
                "tools:create",
                "tools:update",
                "tools:delete",
                "tools:use",
                "backup:create",
                "backup:restore",
                "backup:manage",
            ],
        },
        {
            "name": "manager",
            "description": "Manager with write access",
            "permissions": [
                "parts:read",
                "parts:create",
                "parts:update",
                "parts:delete",
                "locations:read",
                "locations:create",
                "locations:update",
                "locations:delete",
                "categories:read",
                "categories:create",
                "categories:update",
                "categories:delete",
                "tasks:read",
                "tasks:create",
                "tasks:update",
                "tools:read",
                "tools:create",
                "tools:update",
                "tools:delete",
                "tools:use",
                "tags:read",
                "tags:update",
                "tags:create",
                "tags:delete",
                "suppliers:read",
                "projects:read",
                "projects:create",
                "projects:update",
                "projects:delete",
            ],
        },
        {
            "name": "user",
            "description": "Regular user with read access",
            "permissions": ["parts:read", "locations:read", "categories:read", "tasks:read", "tools:read", "tools:use"],
        },
        {
            "name": "viewer",
            "description": "Read-only viewer with comprehensive read access",
            "permissions": [
                "parts:read",
                "tools:read",
                "dashboard:view",
                "tags:read",
                "projects:read",
                "suppliers:read",
                "locations:read",
                "categories:read",
            ],
        },
    ]

    for role_data in roles:
        try:
            # Try to get the role - will raise exception if not found
            existing_role = user_repo.get_role_by_name(role_data["name"])
            print(f"Role already exists: {role_data['name']}")
        except Exception:
            # Role doesn't exist, create it
            try:
                user_repo.create_role(**role_data)
                print(f"Created role: {role_data['name']}")
            except Exception as e:
                print(f"Error creating role {role_data['name']}: {str(e)}")


def setup_default_admin(user_repo: UserRepository):
    """Set up default admin user if it doesn't exist."""
    try:
        # Check if default credentials have been removed for security
        if DEFAULT_ADMIN_USERNAME is None or DEFAULT_ADMIN_PASSWORD is None:
            print("⚠️  Default admin credentials have been removed for security.")
            print("    This happens automatically after changing the admin password.")
            print("    To create a new admin user, use the API or manually restore credentials.")
            return

        # Check if admin user already exists
        try:
            existing_admin = user_repo.get_user_by_username(DEFAULT_ADMIN_USERNAME)
            print("Admin user already exists")
            return
        except Exception:
            # User doesn't exist, continue with creation
            pass

        # Hash the default password
        hashed_password = user_repo.get_password_hash(DEFAULT_ADMIN_PASSWORD)

        # Create admin user with password change required
        admin_user = user_repo.create_user(
            username=DEFAULT_ADMIN_USERNAME, email=DEFAULT_ADMIN_EMAIL, hashed_password=hashed_password, roles=["admin"]
        )

        # Set password change required
        user_repo.update_user(user_id=admin_user.id, password_change_required=True)

        print(f"Created default admin user: {DEFAULT_ADMIN_USERNAME}")
        print("Please change the password on first login!")

    except Exception as e:
        print(f"Error creating admin user: {str(e)}")


def main():
    """Main setup function."""
    print("Setting up MakerMatrix admin user and roles...")

    # Create tables if they don't exist
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Initialize repository
    user_repo = UserRepository()

    # Set up roles and admin user
    print("\nSetting up default roles...")
    setup_default_roles(user_repo)

    print("\nSetting up default admin user...")
    setup_default_admin(user_repo)

    print("\nSetup complete!")


if __name__ == "__main__":
    main()
