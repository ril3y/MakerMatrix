"""
Unit tests for category_repositories.py using real in-memory database.

These tests use an in-memory SQLite database for fast, reliable testing
without complex mocking of SQLAlchemy components.
"""

import pytest
from MakerMatrix.repositories.category_repositories import CategoryRepository
from MakerMatrix.exceptions import ResourceNotFoundError, CategoryAlreadyExistsError, InvalidReferenceError
from MakerMatrix.models.models import CategoryModel, PartModel
from MakerMatrix.tests.unit_tests.test_database import create_test_db
from sqlmodel import select


class TestCategoryRepositoryNew:
    """Test cases for CategoryRepository using real database."""

    def setup_method(self):
        """Set up test database for each test."""
        self.test_db = create_test_db()
        self.repo = CategoryRepository(self.test_db.engine)

    def teardown_method(self):
        """Clean up after each test."""
        self.test_db.close()

    def test_get_category_by_id_success(self):
        """Test successfully retrieving category by ID."""
        session = self.test_db.get_session()

        # Create test category
        category = CategoryModel(name="Test Category", description="A test category")
        session.add(category)
        session.commit()
        category_id = category.id

        # Test retrieval
        result = CategoryRepository.get_category(session, category_id=category_id)

        assert result.id == category_id
        assert result.name == "Test Category"
        assert result.description == "A test category"

    def test_get_category_by_name_success(self):
        """Test successfully retrieving category by name."""
        session = self.test_db.get_session()

        # Create test category
        category = CategoryModel(name="Find By Name", description="Test category")
        session.add(category)
        session.commit()

        # Test retrieval
        result = CategoryRepository.get_category(session, name="Find By Name")

        assert result.name == "Find By Name"
        assert result.description == "Test category"

    def test_get_category_by_id_not_found(self):
        """Test ResourceNotFoundError when category not found by ID."""
        session = self.test_db.get_session()

        with pytest.raises(ResourceNotFoundError) as exc_info:
            CategoryRepository.get_category(session, category_id="nonexistent-id")

        assert "Category with ID 'nonexistent-id' not found" in str(exc_info.value)

    def test_get_category_by_name_not_found(self):
        """Test ResourceNotFoundError when category not found by name."""
        session = self.test_db.get_session()

        with pytest.raises(ResourceNotFoundError) as exc_info:
            CategoryRepository.get_category(session, name="Nonexistent Category")

        assert "Category with name 'Nonexistent Category' not found" in str(exc_info.value)

    def test_get_category_no_criteria(self):
        """Test InvalidReferenceError when neither ID nor name provided."""
        session = self.test_db.get_session()

        with pytest.raises(InvalidReferenceError) as exc_info:
            CategoryRepository.get_category(session)

        assert "Either 'category_id' or 'name' must be provided for category lookup" in str(exc_info.value)

    def test_create_category_success(self):
        """Test successfully creating a new category."""
        session = self.test_db.get_session()

        category_data = {"name": "New Category", "description": "A new category for testing"}

        result = CategoryRepository.create_category(session, category_data)

        assert result.name == "New Category"
        assert result.description == "A new category for testing"

        # Verify it's in database
        found_category = session.exec(select(CategoryModel).where(CategoryModel.name == "New Category")).first()
        assert found_category is not None

    def test_create_category_duplicate_name(self):
        """Test CategoryAlreadyExistsError when category name already exists."""
        session = self.test_db.get_session()

        # Create first category
        first_category = CategoryModel(name="Duplicate Name", description="First")
        session.add(first_category)
        session.commit()

        # Try to create second category with same name
        category_data = {"name": "Duplicate Name", "description": "Second"}

        with pytest.raises(CategoryAlreadyExistsError) as exc_info:
            CategoryRepository.create_category(session, category_data)

        assert "Category with name 'Duplicate Name' already exists" in str(exc_info.value)
        assert exc_info.value.data["existing_category_id"] == first_category.id

    def test_create_category_no_name(self):
        """Test creating category without name raises error."""
        session = self.test_db.get_session()

        category_data = {"description": "Category without name"}

        with pytest.raises(RuntimeError) as exc_info:
            CategoryRepository.create_category(session, category_data)

        assert "Failed to create category" in str(exc_info.value)
        assert "NOT NULL constraint failed: categorymodel.name" in str(exc_info.value)

    def test_get_all_categories_success(self):
        """Test retrieving all categories."""
        session = self.test_db.get_session()

        # Create multiple categories
        for i in range(3):
            category = CategoryModel(name=f"Category {i}", description=f"Description {i}")
            session.add(category)
        session.commit()

        # Retrieve all categories
        results = CategoryRepository.get_all_categories(session)

        assert len(results) == 3
        category_names = [cat.name for cat in results]
        assert "Category 0" in category_names
        assert "Category 2" in category_names

    def test_get_all_categories_empty(self):
        """Test get_all_categories returns empty list when no categories."""
        session = self.test_db.get_session()

        result = CategoryRepository.get_all_categories(session)

        assert result == []

    def test_update_category_success(self):
        """Test successfully updating a category."""
        session = self.test_db.get_session()

        # Create initial category
        category = CategoryModel(name="Original Category", description="Original description")
        session.add(category)
        session.commit()
        category_id = category.id

        # Update category
        update_data = {"name": "Updated Category", "description": "Updated description"}

        result = CategoryRepository.update_category(session, category_id, update_data)

        assert result.name == "Updated Category"
        assert result.description == "Updated description"

    def test_update_category_not_found(self):
        """Test updating non-existent category raises error."""
        session = self.test_db.get_session()

        update_data = {"name": "Updated Name"}

        with pytest.raises(ResourceNotFoundError) as exc_info:
            CategoryRepository.update_category(session, "nonexistent-id", update_data)

        assert "Category with ID nonexistent-id not found" in str(exc_info.value)

    def test_update_category_partial_update(self):
        """Test updating only some fields of a category."""
        session = self.test_db.get_session()

        # Create initial category
        category = CategoryModel(name="Original Name", description="Original description")
        session.add(category)
        session.commit()
        category_id = category.id

        # Update only description
        update_data = {"description": "New description only"}

        result = CategoryRepository.update_category(session, category_id, update_data)

        assert result.name == "Original Name"  # Unchanged
        assert result.description == "New description only"

    def test_remove_category_success(self):
        """Test successfully removing a category."""
        session = self.test_db.get_session()

        # Create category
        category = CategoryModel(name="Remove Me", description="To be removed")
        session.add(category)
        session.commit()

        # Remove category
        result = CategoryRepository.remove_category(session, category)

        assert result.name == "Remove Me"

        # Verify category is gone
        found_category = session.exec(select(CategoryModel).where(CategoryModel.id == category.id)).first()
        assert found_category is None

    def test_remove_category_with_parts(self):
        """Test removing category that has associated parts."""
        session = self.test_db.get_session()

        # Create category
        category = CategoryModel(name="Category with Parts")
        session.add(category)
        session.flush()

        # Create parts with this category
        part1 = PartModel(part_name="Part 1", part_number="P001", quantity=5)
        part2 = PartModel(part_name="Part 2", part_number="P002", quantity=3)
        part1.categories = [category]
        part2.categories = [category]

        session.add(part1)
        session.add(part2)
        session.commit()

        # Remove category
        result = CategoryRepository.remove_category(session, category)

        assert result.name == "Category with Parts"

        # Verify category is gone
        found_category = session.exec(select(CategoryModel).where(CategoryModel.id == category.id)).first()
        assert found_category is None

        # Verify parts no longer have this category
        session.refresh(part1)
        session.refresh(part2)
        assert len(part1.categories) == 0
        assert len(part2.categories) == 0

    def test_remove_category_with_multiple_categories_on_parts(self):
        """Test removing category when parts have multiple categories."""
        session = self.test_db.get_session()

        # Create categories
        category_remove = CategoryModel(name="Remove This")
        category_keep = CategoryModel(name="Keep This")
        session.add(category_remove)
        session.add(category_keep)
        session.flush()

        # Create part with both categories
        part = PartModel(part_name="Multi-Category Part", part_number="MCP001", quantity=1)
        part.categories = [category_remove, category_keep]
        session.add(part)
        session.commit()

        # Remove one category
        result = CategoryRepository.remove_category(session, category_remove)

        assert result.name == "Remove This"

        # Verify target category is gone
        found_category = session.exec(select(CategoryModel).where(CategoryModel.id == category_remove.id)).first()
        assert found_category is None

        # Verify part still has the other category
        session.refresh(part)
        assert len(part.categories) == 1
        assert part.categories[0].name == "Keep This"

    def test_delete_all_categories_success(self):
        """Test successfully deleting all categories."""
        session = self.test_db.get_session()

        # Create multiple categories
        for i in range(5):
            category = CategoryModel(name=f"Category {i}")
            session.add(category)
        session.commit()

        # Delete all categories
        result = CategoryRepository.delete_all_categories(session)

        assert result == 5

        # Verify all categories are gone
        remaining_categories = CategoryRepository.get_all_categories(session)
        assert len(remaining_categories) == 0

    def test_delete_all_categories_empty_database(self):
        """Test delete_all_categories when database is empty."""
        session = self.test_db.get_session()

        result = CategoryRepository.delete_all_categories(session)

        assert result == 0

    def test_create_category_with_minimal_data(self):
        """Test category creation with minimal required data."""
        session = self.test_db.get_session()

        category_data = {"name": "Minimal Category"}

        result = CategoryRepository.create_category(session, category_data)

        assert result.name == "Minimal Category"
        assert result.description is None

    def test_category_case_sensitivity(self):
        """Test that category lookup by name is case-sensitive."""
        session = self.test_db.get_session()

        # Create category with specific case
        category = CategoryModel(name="CaseSensitive")
        session.add(category)
        session.commit()

        # Test exact match works
        result = CategoryRepository.get_category(session, name="CaseSensitive")
        assert result.name == "CaseSensitive"

        # Test different case fails
        with pytest.raises(ResourceNotFoundError):
            CategoryRepository.get_category(session, name="casesensitive")

    def test_create_category_empty_name(self):
        """Test creating category with empty string name."""
        session = self.test_db.get_session()

        category_data = {"name": "", "description": "Empty name category"}

        result = CategoryRepository.create_category(session, category_data)

        assert result.name == ""
        assert result.description == "Empty name category"
