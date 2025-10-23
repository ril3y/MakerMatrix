"""
Unit tests for base_repository.py using real in-memory database.

These tests use an in-memory SQLite database for fast, reliable testing
without complex mocking of SQLAlchemy components.
"""

import pytest
import uuid
from sqlmodel import SQLModel, Field, create_engine, Session
from MakerMatrix.repositories.base_repository import BaseRepository
from MakerMatrix.tests.unit_tests.test_database import create_test_db
from typing import Optional


# Test model for BaseRepository testing
class SampleModel(SQLModel, table=True):
    """Sample model for BaseRepository testing."""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    value: Optional[int] = None


class TestBaseRepositoryNew:
    """Test cases for BaseRepository using real database."""

    def setup_method(self):
        """Set up test database for each test."""
        self.test_db = create_test_db()
        # Add our test table to the database
        SampleModel.metadata.create_all(self.test_db.engine)
        self.repo = BaseRepository(SampleModel)

    def teardown_method(self):
        """Clean up after each test."""
        self.test_db.close()

    def test_get_by_id_success(self):
        """Test successfully retrieving model by ID."""
        session = self.test_db.get_session()

        # Create test model
        test_model = SampleModel(id="test-id", name="Test Model", value=42)
        session.add(test_model)
        session.commit()

        # Test retrieval
        result = self.repo.get_by_id(session, "test-id")

        assert result is not None
        assert result.id == "test-id"
        assert result.name == "Test Model"
        assert result.value == 42

    def test_get_by_id_not_found(self):
        """Test get_by_id returns None when model not found."""
        session = self.test_db.get_session()

        result = self.repo.get_by_id(session, "nonexistent-id")

        assert result is None

    def test_get_all_success(self):
        """Test successfully retrieving all models."""
        session = self.test_db.get_session()

        # Create multiple test models
        models = []
        for i in range(3):
            model = SampleModel(id=f"id-{i}", name=f"Model {i}", value=i * 10)
            session.add(model)
            models.append(model)
        session.commit()

        # Test retrieval
        results = self.repo.get_all(session)

        assert len(results) == 3
        result_names = [r.name for r in results]
        assert "Model 0" in result_names
        assert "Model 2" in result_names

    def test_get_all_empty(self):
        """Test get_all returns empty list when no models exist."""
        session = self.test_db.get_session()

        result = self.repo.get_all(session)

        assert result == []

    def test_create_success(self):
        """Test successfully creating a model."""
        session = self.test_db.get_session()

        # Create new model
        new_model = SampleModel(id="create-test", name="Created Model", value=100)

        result = self.repo.create(session, new_model)

        assert result.id == "create-test"
        assert result.name == "Created Model"
        assert result.value == 100

        # Verify it's in database
        found_model = self.repo.get_by_id(session, "create-test")
        assert found_model is not None
        assert found_model.name == "Created Model"

    def test_create_with_auto_id(self):
        """Test creating model with auto-generated ID."""
        session = self.test_db.get_session()

        # Create model without explicit ID
        new_model = SampleModel(name="Auto ID Model", value=200)

        result = self.repo.create(session, new_model)

        assert result.id is not None  # Should be auto-generated
        assert result.name == "Auto ID Model"
        assert result.value == 200

    def test_update_success(self):
        """Test successfully updating a model."""
        session = self.test_db.get_session()

        # Create initial model
        model = SampleModel(id="update-test", name="Original Name", value=50)
        session.add(model)
        session.commit()

        # Update model
        model.name = "Updated Name"
        model.value = 75

        result = self.repo.update(session, model)

        assert result.name == "Updated Name"
        assert result.value == 75

        # Verify changes persisted
        found_model = self.repo.get_by_id(session, "update-test")
        assert found_model.name == "Updated Name"
        assert found_model.value == 75

    def test_delete_success(self):
        """Test successfully deleting a model."""
        session = self.test_db.get_session()

        # Create model to delete
        model = SampleModel(id="delete-test", name="Delete Me", value=999)
        session.add(model)
        session.commit()

        # Delete model
        result = self.repo.delete(session, "delete-test")

        assert result is True

        # Verify model is gone
        found_model = self.repo.get_by_id(session, "delete-test")
        assert found_model is None

    def test_delete_not_found(self):
        """Test delete returns False when model not found."""
        session = self.test_db.get_session()

        result = self.repo.delete(session, "nonexistent-id")

        assert result is False

    def test_repository_initialization(self):
        """Test that BaseRepository initializes correctly with model class."""
        repo = BaseRepository(SampleModel)

        assert repo.model_class == SampleModel

    def test_repository_with_different_model(self):
        """Test that BaseRepository works with different model classes."""

        class AnotherModel(SQLModel, table=True):
            id: Optional[str] = Field(default=None, primary_key=True)
            description: str

        repo = BaseRepository(AnotherModel)

        assert repo.model_class == AnotherModel

    def test_multiple_operations_sequence(self):
        """Test sequence of operations on same repository."""
        session = self.test_db.get_session()

        # Create
        model1 = SampleModel(id="seq-1", name="Sequence 1", value=10)
        created = self.repo.create(session, model1)
        assert created.name == "Sequence 1"

        # Read
        found = self.repo.get_by_id(session, "seq-1")
        assert found is not None
        assert found.name == "Sequence 1"

        # Update
        found.value = 20
        updated = self.repo.update(session, found)
        assert updated.value == 20

        # Verify update
        verified = self.repo.get_by_id(session, "seq-1")
        assert verified.value == 20

        # Delete
        deleted = self.repo.delete(session, "seq-1")
        assert deleted is True

        # Verify deletion
        gone = self.repo.get_by_id(session, "seq-1")
        assert gone is None

    def test_create_multiple_models(self):
        """Test creating multiple models and retrieving them."""
        session = self.test_db.get_session()

        # Create multiple models
        for i in range(5):
            model = SampleModel(id=f"multi-{i}", name=f"Multi Model {i}", value=i * 5)
            self.repo.create(session, model)

        # Retrieve all
        all_models = self.repo.get_all(session)
        assert len(all_models) == 5

        # Verify specific models
        model_2 = self.repo.get_by_id(session, "multi-2")
        assert model_2 is not None
        assert model_2.name == "Multi Model 2"
        assert model_2.value == 10

    def test_update_nonexistent_model(self):
        """Test updating a model that doesn't exist in database."""
        session = self.test_db.get_session()

        # Create model with ID that doesn't exist in database
        model = SampleModel(id="not-in-db", name="Not In DB", value=123)

        # This should still work - SQLModel/SQLAlchemy will treat it as an insert
        result = self.repo.update(session, model)

        assert result.name == "Not In DB"
        assert result.value == 123

        # Verify it's now in database
        found = self.repo.get_by_id(session, "not-in-db")
        assert found is not None

    def test_create_with_duplicate_id(self):
        """Test creating model with duplicate ID raises error."""
        session = self.test_db.get_session()

        # Create first model
        model1 = SampleModel(id="duplicate", name="First", value=1)
        self.repo.create(session, model1)

        # Try to create second model with same ID
        model2 = SampleModel(id="duplicate", name="Second", value=2)

        with pytest.raises(Exception):  # Should raise integrity error
            self.repo.create(session, model2)

    def test_model_with_none_values(self):
        """Test creating and working with models that have None values."""
        session = self.test_db.get_session()

        # Create model with None optional field
        model = SampleModel(id="none-test", name="Has None Value", value=None)

        result = self.repo.create(session, model)

        assert result.name == "Has None Value"
        assert result.value is None

        # Verify retrieval
        found = self.repo.get_by_id(session, "none-test")
        assert found.value is None
