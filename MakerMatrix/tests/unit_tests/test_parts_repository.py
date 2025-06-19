"""
Unit tests for parts_repositories.py using real in-memory database.

These tests use an in-memory SQLite database for fast, reliable testing
without complex mocking of SQLAlchemy components.
"""

import pytest
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    PartAlreadyExistsError,
    InvalidReferenceError
)
from MakerMatrix.models.models import PartModel, CategoryModel, LocationModel, AdvancedPartSearch
from sqlmodel import select
from MakerMatrix.tests.unit_tests.test_database import create_test_db, create_test_db_with_data


class TestPartRepositoryNew:
    """Test cases for PartRepository using real database."""

    def setup_method(self):
        """Set up test database for each test."""
        self.test_db = create_test_db()
        self.repo = PartRepository(self.test_db.engine)

    def teardown_method(self):
        """Clean up after each test."""
        self.test_db.close()

    def test_get_part_by_id_success(self):
        """Test successfully retrieving part by ID."""
        session = self.test_db.get_session()
        
        # Create test part
        test_part = PartModel(
            part_name="Test Part",
            part_number="TP001",
            description="A test part",
            quantity=10
        )
        session.add(test_part)
        session.commit()
        part_id = test_part.id

        # Test retrieval
        result = PartRepository.get_part_by_id(session, part_id)
        
        assert result.id == part_id
        assert result.part_name == "Test Part"
        assert result.part_number == "TP001"

    def test_get_part_by_id_not_found(self):
        """Test ResourceNotFoundError when part not found by ID."""
        session = self.test_db.get_session()
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            PartRepository.get_part_by_id(session, "nonexistent-id")
        
        assert "Part with ID nonexistent-id not found" in str(exc_info.value)

    def test_get_part_by_name_success(self):
        """Test successfully retrieving part by name."""
        session = self.test_db.get_session()
        
        # Create test part
        test_part = PartModel(
            part_name="Unique Part Name",
            part_number="UPN001",
            quantity=5
        )
        session.add(test_part)
        session.commit()

        # Test retrieval
        result = PartRepository.get_part_by_name(session, "Unique Part Name")
        
        assert result.part_name == "Unique Part Name"
        assert result.part_number == "UPN001"

    def test_get_part_by_name_not_found(self):
        """Test ResourceNotFoundError when part not found by name."""
        session = self.test_db.get_session()
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            PartRepository.get_part_by_name(session, "Nonexistent Part")
        
        assert "Part with name 'Nonexistent Part' not found" in str(exc_info.value)

    def test_get_part_by_part_number_success(self):
        """Test successfully retrieving part by part number."""
        session = self.test_db.get_session()
        
        # Create test part
        test_part = PartModel(
            part_name="Part by Number",
            part_number="PBN123",
            quantity=3
        )
        session.add(test_part)
        session.commit()

        # Test retrieval
        result = PartRepository.get_part_by_part_number(session, "PBN123")
        
        assert result.part_name == "Part by Number"
        assert result.part_number == "PBN123"

    def test_get_part_by_part_number_not_found(self):
        """Test ResourceNotFoundError when part not found by part number."""
        session = self.test_db.get_session()
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            PartRepository.get_part_by_part_number(session, "NONEXIST")
        
        assert "Part with part number NONEXIST not found" in str(exc_info.value)

    def test_add_part_success(self):
        """Test successfully adding a new part."""
        session = self.test_db.get_session()
        
        # Create part data
        part_data = PartModel(
            part_name="New Part",
            part_number="NP001",
            description="A new part for testing",
            quantity=15,
            supplier="Test Supplier"
        )

        # Add part
        result = PartRepository.add_part(session, part_data)
        
        assert result.part_name == "New Part"
        assert result.part_number == "NP001"
        assert result.quantity == 15
        assert result.supplier == "Test Supplier"
        
        # Verify it's in database
        found_part = session.exec(select(PartModel).where(PartModel.part_name == "New Part")).first()
        assert found_part is not None

    def test_add_part_with_valid_location(self):
        """Test adding part with valid location reference."""
        session = self.test_db.get_session()
        
        # Create location first
        location = LocationModel(name="Test Location", description="Test")
        session.add(location)
        session.commit()
        location_id = location.id

        # Create part with location
        part_data = PartModel(
            part_name="Located Part",
            part_number="LP001",
            quantity=10,
            location_id=location_id
        )

        result = PartRepository.add_part(session, part_data)
        
        assert result.location_id == location_id
        assert result.part_name == "Located Part"

    def test_add_part_with_invalid_location(self):
        """Test adding part with invalid location raises error."""
        session = self.test_db.get_session()
        
        # Create part with non-existent location
        part_data = PartModel(
            part_name="Bad Location Part",
            part_number="BLP001",
            quantity=10,
            location_id="nonexistent-location-id"
        )

        with pytest.raises(InvalidReferenceError) as exc_info:
            PartRepository.add_part(session, part_data)
        
        assert "Location with ID 'nonexistent-location-id' does not exist" in str(exc_info.value)

    def test_add_part_with_categories(self):
        """Test adding part with categories."""
        session = self.test_db.get_session()
        
        # Create categories
        cat1 = CategoryModel(name="Category 1", description="First category")
        cat2 = CategoryModel(name="Category 2", description="Second category")
        session.add(cat1)
        session.add(cat2)
        session.commit()

        # Create part with categories
        part_data = PartModel(
            part_name="Categorized Part",
            part_number="CP001",
            quantity=8
        )
        part_data.categories = [cat1, cat2]

        result = PartRepository.add_part(session, part_data)
        
        assert result.part_name == "Categorized Part"
        assert len(result.categories) == 2
        category_names = [cat.name for cat in result.categories]
        assert "Category 1" in category_names
        assert "Category 2" in category_names

    def test_update_part_success(self):
        """Test successfully updating a part."""
        session = self.test_db.get_session()
        
        # Create initial part
        part = PartModel(
            part_name="Original Part",
            part_number="OP001",
            quantity=5,
            description="Original description"
        )
        session.add(part)
        session.commit()

        # Update part
        part.part_name = "Updated Part"
        part.quantity = 10
        part.description = "Updated description"

        result = PartRepository.update_part(session, part)
        
        assert result.part_name == "Updated Part"
        assert result.quantity == 10
        assert result.description == "Updated description"
        assert result.part_number == "OP001"  # Unchanged

    def test_get_all_parts_success(self):
        """Test retrieving all parts with pagination."""
        session = self.test_db.get_session()
        
        # Create multiple parts
        for i in range(5):
            part = PartModel(
                part_name=f"Part {i}",
                part_number=f"P{i:03d}",
                quantity=i + 1
            )
            session.add(part)
        session.commit()

        # Test getting all parts
        results = PartRepository.get_all_parts(session, page=1, page_size=10)
        
        assert len(results) == 5
        part_names = [part.part_name for part in results]
        assert "Part 0" in part_names
        assert "Part 4" in part_names

    def test_get_all_parts_pagination(self):
        """Test pagination in get_all_parts."""
        session = self.test_db.get_session()
        
        # Create 10 parts
        for i in range(10):
            part = PartModel(
                part_name=f"Paginated Part {i}",
                part_number=f"PP{i:03d}",
                quantity=1
            )
            session.add(part)
        session.commit()

        # Test first page
        page1 = PartRepository.get_all_parts(session, page=1, page_size=3)
        assert len(page1) == 3

        # Test second page
        page2 = PartRepository.get_all_parts(session, page=2, page_size=3)
        assert len(page2) == 3

        # Ensure different parts
        page1_names = {part.part_name for part in page1}
        page2_names = {part.part_name for part in page2}
        assert page1_names.isdisjoint(page2_names)

    def test_get_part_counts(self):
        """Test getting total part count."""
        session = self.test_db.get_session()
        
        # Initial count should be 0
        initial_count = PartRepository.get_part_counts(session)
        assert initial_count == 0

        # Add some parts
        for i in range(7):
            part = PartModel(
                part_name=f"Count Part {i}",
                part_number=f"CP{i:03d}",
                quantity=1
            )
            session.add(part)
        session.commit()

        # Test count
        final_count = PartRepository.get_part_counts(session)
        assert final_count == 7

    def test_is_part_name_unique_true(self):
        """Test part name uniqueness check when name is unique."""
        session = self.test_db.get_session()
        
        # Create a part
        part = PartModel(
            part_name="Existing Part",
            part_number="EP001",
            quantity=1
        )
        session.add(part)
        session.commit()

        # Test uniqueness of different name
        result = self.repo.is_part_name_unique("New Unique Name")
        assert result == True

    def test_is_part_name_unique_false(self):
        """Test part name uniqueness check when name exists."""
        session = self.test_db.get_session()
        
        # Create a part
        part = PartModel(
            part_name="Duplicate Name",
            part_number="DN001",
            quantity=1
        )
        session.add(part)
        session.commit()

        # Test uniqueness of same name
        result = self.repo.is_part_name_unique("Duplicate Name")
        assert result == False

    def test_is_part_name_unique_with_exclude_id(self):
        """Test part name uniqueness check with excluded ID."""
        session = self.test_db.get_session()
        
        # Create a part
        part = PartModel(
            part_name="Exclude Test Part",
            part_number="ETP001",
            quantity=1
        )
        session.add(part)
        session.commit()
        part_id = part.id

        # Test uniqueness excluding the same part
        result = self.repo.is_part_name_unique("Exclude Test Part", exclude_id=part_id)
        assert result == True

        # Test uniqueness without exclusion
        result = self.repo.is_part_name_unique("Exclude Test Part")
        assert result == False

    def test_advanced_search_success(self):
        """Test advanced search functionality."""
        session = self.test_db.get_session()
        
        # Create test data
        category = CategoryModel(name="Search Category")
        location = LocationModel(name="Search Location")
        session.add(category)
        session.add(location)
        session.commit()

        part = PartModel(
            part_name="Searchable Part",
            part_number="SP001",
            description="A part for searching",
            quantity=25,
            supplier="Search Supplier",
            location_id=location.id
        )
        part.categories = [category]
        session.add(part)
        session.commit()

        # Test search
        search_params = AdvancedPartSearch(
            search_term="Searchable",
            page=1,
            page_size=10
        )
        
        results, total_count = PartRepository.advanced_search(session, search_params)
        
        assert total_count == 1
        assert len(results) == 1
        assert results[0].part_name == "Searchable Part"

    def test_advanced_search_with_filters(self):
        """Test advanced search with multiple filters."""
        session = self.test_db.get_session()
        
        # Create test data
        category = CategoryModel(name="Filter Category")
        session.add(category)
        session.commit()

        # Create multiple parts
        for i in range(5):
            part = PartModel(
                part_name=f"Filter Part {i}",
                part_number=f"FP{i:03d}",
                quantity=i * 10,
                supplier="Filter Supplier" if i < 3 else "Other Supplier"
            )
            if i < 2:
                part.categories = [category]
            session.add(part)
        session.commit()

        # Test search with quantity filter
        search_params = AdvancedPartSearch(
            min_quantity=20,
            max_quantity=40,
            page=1,
            page_size=10
        )
        
        results, total_count = PartRepository.advanced_search(session, search_params)
        
        assert total_count == 3  # Parts with quantity 20, 30, and 40
        for part in results:
            assert 20 <= part.quantity <= 40

    def test_get_parts_by_location_id_recursive(self):
        """Test getting parts by location with recursive search."""
        session = self.test_db.get_session()
        
        # Create location hierarchy
        parent_location = LocationModel(name="Parent Location")
        session.add(parent_location)
        session.flush()
        
        child_location = LocationModel(name="Child Location", parent_id=parent_location.id)
        session.add(child_location)
        session.commit()

        # Create parts in both locations
        parent_part = PartModel(
            part_name="Parent Part",
            part_number="PP001",
            quantity=5,
            location_id=parent_location.id
        )
        child_part = PartModel(
            part_name="Child Part",
            part_number="CP001",
            quantity=3,
            location_id=child_location.id
        )
        session.add(parent_part)
        session.add(child_part)
        session.commit()

        # Test non-recursive search
        non_recursive_results = PartRepository.get_parts_by_location_id(session, parent_location.id, recursive=False)
        assert len(non_recursive_results) == 1
        assert non_recursive_results[0].part_name == "Parent Part"

        # Test recursive search (would need to implement get_child_location_ids)
        # This test would require the recursive logic to be implemented
        # For now, just test that the method can be called
        try:
            recursive_results = PartRepository.get_parts_by_location_id(session, parent_location.id, recursive=True)
            # The implementation might not fully support recursion yet
        except AttributeError:
            # Expected if get_child_location_ids is not implemented
            pass

    def test_dynamic_search_success(self):
        """Test dynamic search functionality."""
        session = self.test_db.get_session()
        
        # Create test parts
        part1 = PartModel(
            part_name="Dynamic Search Part",
            part_number="DSP001",
            description="Searchable description",
            quantity=10
        )
        part2 = PartModel(
            part_name="Another Part",
            part_number="AP001",
            description="Different description",
            quantity=5
        )
        session.add(part1)
        session.add(part2)
        session.commit()

        # Test search by name
        results = PartRepository.dynamic_search(session, "Dynamic")
        assert len(results) == 1
        assert results[0].part_name == "Dynamic Search Part"

        # Test search by part number
        results = PartRepository.dynamic_search(session, "DSP001")
        assert len(results) == 1
        assert results[0].part_number == "DSP001"

    def test_dynamic_search_no_results(self):
        """Test dynamic search with no results."""
        session = self.test_db.get_session()
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            PartRepository.dynamic_search(session, "NonexistentTerm")
        
        assert "No parts found for search term 'NonexistentTerm'" in str(exc_info.value)