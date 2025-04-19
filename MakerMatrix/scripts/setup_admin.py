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
            "permissions": ["all"]
        },
        {
            "name": "manager",
            "description": "Manager with write access",
            "permissions": ["read", "write", "update"]
        },
        {
            "name": "user",
            "description": "Regular user with read access",
            "permissions": ["read"]
        }
    ]

    for role_data in roles:
        try:
            existing_role = user_repo.get_role_by_name(role_data["name"])
            if not existing_role:
                user_repo.create_role(**role_data)
                print(f"Created role: {role_data['name']}")
            else:
                print(f"Role already exists: {role_data['name']}")
        except Exception as e:
            print(f"Error creating role {role_data['name']}: {str(e)}")


def setup_default_admin(user_repo: UserRepository):
    """Set up default admin user if it doesn't exist."""
    try:
        existing_admin = user_repo.get_user_by_username(DEFAULT_ADMIN_USERNAME)
        if existing_admin:
            print("Admin user already exists")
            return

        # Hash the default password
        hashed_password = pbkdf2_sha256.hash(DEFAULT_ADMIN_PASSWORD)
        
        # Create admin user with password change required
        admin_user = user_repo.create_user(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=hashed_password,
            roles=["admin"]
        )
        
        # Set password change required
        user_repo.update_user(
            user_id=admin_user.id,
            password_change_required=True
        )
        
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