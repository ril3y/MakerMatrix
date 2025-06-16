"""
Shared test database infrastructure for unit tests.
Uses in-memory SQLite for fast, isolated testing.
"""
import tempfile
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from MakerMatrix.models.user_models import UserModel, RoleModel, UserRoleLink
from MakerMatrix.models.models import PartModel, CategoryModel, LocationModel, PartCategoryLink
from MakerMatrix.repositories.user_repository import UserRepository
from passlib.hash import pbkdf2_sha256


class TestDatabase:
    """Test database manager for unit tests."""
    
    def __init__(self):
        # Create in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.session = None
        
    def create_tables(self):
        """Create all tables in the test database."""
        SQLModel.metadata.create_all(self.engine)
        
    def get_session(self) -> Session:
        """Get a database session for testing."""
        if self.session is None:
            self.session = Session(self.engine)
        return self.session
        
    def close(self):
        """Close the database session and engine."""
        if self.session:
            self.session.close()
        self.engine.dispose()
        
    def clear_all_tables(self):
        """Clear all data from all tables."""
        session = self.get_session()
        try:
            # Delete in proper order to avoid foreign key constraints
            session.query(UserRoleLink).delete()
            session.query(PartCategoryLink).delete()
            session.query(PartModel).delete()
            session.query(CategoryModel).delete()
            session.query(LocationModel).delete()
            session.query(UserModel).delete()
            session.query(RoleModel).delete()
            session.commit()
        except Exception:
            session.rollback()
            raise
    
    def setup_test_data(self):
        """Set up basic test data for most tests."""
        session = self.get_session()
        
        try:
            # Create test roles
            admin_role = RoleModel(
                name="admin",
                description="Admin role",
                permissions=["all"]
            )
            user_role = RoleModel(
                name="user", 
                description="User role",
                permissions=["read"]
            )
            session.add(admin_role)
            session.add(user_role)
            session.flush()  # Get IDs
            
            # Create test user
            test_user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password=pbkdf2_sha256.hash("testpass"),
                is_active=True,
                password_change_required=False
            )
            test_user.roles = [user_role]
            session.add(test_user)
            
            # Create test location
            test_location = LocationModel(
                name="Test Location",
                description="A test location"
            )
            session.add(test_location)
            session.flush()  # Get ID
            
            # Create test category
            test_category = CategoryModel(
                name="Test Category",
                description="A test category"
            )
            session.add(test_category)
            session.flush()  # Get ID
            
            # Create test part
            test_part = PartModel(
                part_name="Test Part",
                part_number="TEST-001",
                description="A test part",
                quantity=10,
                location_id=test_location.id
            )
            test_part.categories = [test_category]
            session.add(test_part)
            
            session.commit()
            
            # Store IDs for tests to use
            self.test_user_id = test_user.id
            self.test_location_id = test_location.id
            self.test_category_id = test_category.id
            self.test_part_id = test_part.id
            self.admin_role_id = admin_role.id
            self.user_role_id = user_role.id
            
        except Exception:
            session.rollback()
            raise


def create_test_db() -> TestDatabase:
    """Factory function to create a test database."""
    db = TestDatabase()
    db.create_tables()
    return db


def create_test_db_with_data() -> TestDatabase:
    """Factory function to create a test database with basic test data."""
    db = create_test_db()
    db.setup_test_data()
    return db