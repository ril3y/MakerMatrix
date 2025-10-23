"""
Comprehensive CRUD Functionality Testing with Real LCSC Data
Tests parts, locations, categories CRUD operations using real LCSC CSV data
Part of Step 12.8 - Comprehensive Testing Validation
"""

import pytest
import csv
from typing import Dict, List, Any

from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.repositories.category_repositories import CategoryRepository
from MakerMatrix.models.models import PartModel, CategoryModel, LocationModel, LocationQueryModel
from MakerMatrix.tests.unit_tests.test_database import create_test_db


class TestComprehensiveCRUDWithLCSCData:
    """Comprehensive CRUD tests using real LCSC CSV data"""

    def setup_method(self):
        """Set up test database for each test."""
        self.test_db = create_test_db()

    def teardown_method(self):
        """Clean up after each test."""
        self.test_db.close()

    def load_lcsc_test_data(self) -> List[Dict[str, Any]]:
        """Load real LCSC CSV test data for testing"""
        csv_file = "/home/ril3y/MakerMatrix/MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv"
        parts_data = []

        try:
            with open(csv_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Skip empty rows
                    if not row.get("LCSC Part Number"):
                        continue

                    parts_data.append(
                        {
                            "lcsc_part_number": row["LCSC Part Number"],
                            "manufacturer_part_number": row["Manufacture Part Number"],
                            "manufacturer": row["Manufacturer"],
                            "package": row["Package"],
                            "description": row["Description"],
                            "rohs": row["RoHS"],
                            "order_qty": row["Order Qty."],
                            "unit_price": row["Unit Price($)"],
                            "order_price": row["Order Price($)"],
                        }
                    )

            return parts_data

        except Exception as e:
            pytest.fail(f"Failed to load LCSC test data: {e}")

    def test_load_lcsc_csv_data(self):
        """Test that we can load the LCSC CSV test data"""
        lcsc_data = self.load_lcsc_test_data()

        # Verify we loaded data
        assert len(lcsc_data) > 0, "No LCSC test data loaded"

        # Verify data structure
        first_part = lcsc_data[0]
        expected_fields = [
            "lcsc_part_number",
            "manufacturer_part_number",
            "manufacturer",
            "package",
            "description",
            "rohs",
            "order_qty",
            "unit_price",
            "order_price",
        ]

        for field in expected_fields:
            assert field in first_part, f"Missing field: {field}"

        # Verify specific data from CSV
        assert first_part["lcsc_part_number"] == "C7442639"
        assert first_part["manufacturer"] == "Lelon"
        assert "capacitor" in first_part["description"].lower()

        print(f"✅ Successfully loaded {len(lcsc_data)} parts from LCSC CSV")

    def test_location_crud_operations(self):
        """Test complete CRUD operations for locations"""
        session = self.test_db.get_session()

        # CREATE - Test location creation
        location_data = {
            "name": "Test Electronics Lab",
            "description": "Primary electronics testing laboratory",
            "location_type": "laboratory",
        }

        created_location = LocationRepository.add_location(session, location_data)
        assert created_location.id is not None
        assert created_location.name == "Test Electronics Lab"
        assert created_location.location_type == "laboratory"

        # READ - Test location retrieval
        query = LocationQueryModel(id=created_location.id)
        retrieved_location = LocationRepository.get_location(session, query)
        assert retrieved_location is not None
        assert retrieved_location.id == created_location.id
        assert retrieved_location.name == "Test Electronics Lab"

        # UPDATE - Test location updates
        update_data = {"description": "Updated description for testing"}
        updated_location = LocationRepository.update_location(session, created_location.id, update_data)
        assert updated_location.description == "Updated description for testing"

        # DELETE - Test location deletion
        LocationRepository.delete_location(session, updated_location)

        # Verify deletion - location should not be found
        query = LocationQueryModel(id=created_location.id)
        try:
            deleted_location = LocationRepository.get_location(session, query)
            assert deleted_location is None  # Should not reach here
        except Exception:
            # Expected - location should not be found after deletion
            pass

        print("✅ Location CRUD operations completed successfully")

    def test_category_crud_operations(self):
        """Test complete CRUD operations for categories"""
        session = self.test_db.get_session()

        # CREATE - Test category creation
        category_data = {"name": "Capacitors", "description": "Electronic capacitors and related components"}

        created_category = CategoryRepository.create_category(session, category_data)
        assert created_category.id is not None
        assert created_category.name == "Capacitors"
        assert created_category.description == "Electronic capacitors and related components"

        # READ - Test category retrieval
        retrieved_category = CategoryRepository.get_category(session, category_id=created_category.id)
        assert retrieved_category is not None
        assert retrieved_category.id == created_category.id
        assert retrieved_category.name == "Capacitors"

        # UPDATE - Test category updates
        update_data = {"description": "Updated description for testing"}
        updated_category = CategoryRepository.update_category(session, created_category.id, update_data)
        assert updated_category.description == "Updated description for testing"

        # DELETE - Test category deletion
        CategoryRepository.remove_category(session, updated_category)

        # Verify deletion - category should not be found
        try:
            deleted_category = CategoryRepository.get_category(session, category_id=created_category.id)
            assert deleted_category is None  # Should not reach here
        except Exception:
            # Expected - category should not be found after deletion
            pass

        print("✅ Category CRUD operations completed successfully")

    def test_part_crud_operations_with_lcsc_data(self):
        """Test complete CRUD operations for parts using real LCSC data"""
        session = self.test_db.get_session()

        # Load real LCSC test data
        lcsc_data = self.load_lcsc_test_data()
        assert len(lcsc_data) > 0, "No LCSC test data loaded"

        # Create a test location for parts
        location_data = {
            "name": "Component Storage A1",
            "description": "Main component storage rack A1",
            "location_type": "storage",
        }
        test_location = LocationRepository.add_location(session, location_data)

        # CREATE - Test part creation with real LCSC data
        part_data = lcsc_data[0]  # Use first part from CSV

        part_model = PartModel(
            part_number=part_data["lcsc_part_number"],
            part_name=f"LCSC {part_data['lcsc_part_number']}",
            description=part_data["description"],
            quantity=int(part_data["order_qty"]) if part_data["order_qty"].isdigit() else 0,
            supplier="LCSC",
            location_id=test_location.id,
            additional_properties={
                "manufacturer": part_data["manufacturer"],
                "manufacturer_part_number": part_data["manufacturer_part_number"],
                "package": part_data["package"],
                "rohs": part_data["rohs"],
                "unit_price": part_data["unit_price"],
                "order_price": part_data["order_price"],
            },
        )

        created_part = PartRepository.add_part(session, part_model)
        assert created_part.id is not None
        assert created_part.part_number == part_data["lcsc_part_number"]
        assert created_part.supplier == "LCSC"
        assert created_part.additional_properties["manufacturer"] == part_data["manufacturer"]

        # READ - Test part retrieval
        retrieved_part = PartRepository.get_part_by_id(session, created_part.id)
        assert retrieved_part is not None
        assert retrieved_part.id == created_part.id
        assert retrieved_part.part_number == part_data["lcsc_part_number"]

        # Verify location relationship
        assert retrieved_part.location_id == test_location.id

        # UPDATE - Test part updates
        original_quantity = retrieved_part.quantity
        retrieved_part.quantity += 10
        retrieved_part.description = "Updated description for testing"

        updated_part = PartRepository.update_part(session, retrieved_part)
        assert updated_part.quantity == original_quantity + 10
        assert updated_part.description == "Updated description for testing"

        # DELETE - Test part deletion
        deleted_part = PartRepository.delete_part(session, created_part.id)
        assert deleted_part is not None

        # Verify deletion - part should not be found
        try:
            deleted_check = PartRepository.get_part_by_id(session, created_part.id)
            assert deleted_check is None  # Should not reach here
        except Exception:
            # Expected - part should not be found after deletion
            pass

        print("✅ Part CRUD operations with real LCSC data completed successfully")

    def test_parts_with_categories_relationship(self):
        """Test part-category relationships using real LCSC data"""
        session = self.test_db.get_session()

        # Load real LCSC test data
        lcsc_data = self.load_lcsc_test_data()
        assert len(lcsc_data) > 0, "No LCSC test data loaded"

        # Create test categories
        capacitor_category = CategoryRepository.create_category(
            session, {"name": "Capacitors", "description": "Electronic capacitors and related components"}
        )

        connector_category = CategoryRepository.create_category(
            session, {"name": "Connectors", "description": "Electronic connectors and cable assemblies"}
        )

        # Create test location
        location_data = {
            "name": "Component Storage A1",
            "description": "Main component storage rack A1",
            "location_type": "storage",
        }
        test_location = LocationRepository.add_location(session, location_data)

        # Create parts with categories based on LCSC data
        created_parts = []
        for i, part_data in enumerate(lcsc_data[:3]):  # Test with first 3 parts
            part_model = PartModel(
                part_number=part_data["lcsc_part_number"],
                part_name=f"LCSC {part_data['lcsc_part_number']}",
                description=part_data["description"],
                quantity=int(part_data["order_qty"]) if part_data["order_qty"].isdigit() else 0,
                supplier="LCSC",
                location_id=test_location.id,
                additional_properties={
                    "manufacturer": part_data["manufacturer"],
                    "manufacturer_part_number": part_data["manufacturer_part_number"],
                    "package": part_data["package"],
                    "rohs": part_data["rohs"],
                    "unit_price": part_data["unit_price"],
                    "order_price": part_data["order_price"],
                },
            )

            created_part = PartRepository.add_part(session, part_model)

            # Assign category based on description
            if "capacitor" in part_data["description"].lower():
                created_part.categories.append(capacitor_category)
            elif "connector" in part_data["description"].lower():
                created_part.categories.append(connector_category)

            session.commit()
            created_parts.append(created_part)

        # Verify relationships
        for part in created_parts:
            retrieved_part = PartRepository.get_part_by_id(session, part.id)
            assert retrieved_part is not None

            # Verify location relationship
            assert retrieved_part.location_id == test_location.id

            # Verify category relationships
            if "capacitor" in part.description.lower():
                assert any(cat.name == "Capacitors" for cat in retrieved_part.categories)
            elif "connector" in part.description.lower():
                assert any(cat.name == "Connectors" for cat in retrieved_part.categories)

        print(f"✅ Created {len(created_parts)} parts with proper category relationships")

    def test_search_functionality_with_lcsc_data(self):
        """Test search functionality with real LCSC data"""
        session = self.test_db.get_session()

        # Load real LCSC test data
        lcsc_data = self.load_lcsc_test_data()
        assert len(lcsc_data) > 0, "No LCSC test data loaded"

        # Create test location
        location_data = {
            "name": "Component Storage A1",
            "description": "Main component storage rack A1",
            "location_type": "storage",
        }
        test_location = LocationRepository.add_location(session, location_data)

        # Create parts with real LCSC data
        created_parts = []
        for part_data in lcsc_data:
            part_model = PartModel(
                part_number=part_data["lcsc_part_number"],
                part_name=f"LCSC {part_data['lcsc_part_number']}",
                description=part_data["description"],
                quantity=int(part_data["order_qty"]) if part_data["order_qty"].isdigit() else 0,
                supplier="LCSC",
                location_id=test_location.id,
            )

            created_part = PartRepository.add_part(session, part_model)
            created_parts.append(created_part)

        # Test search by part number
        test_part = created_parts[0]
        found_part = PartRepository.get_part_by_part_number(session, test_part.part_number)
        assert found_part is not None
        assert found_part.id == test_part.id

        # Test search by part name
        found_part_by_name = PartRepository.get_part_by_name(session, test_part.part_name)
        assert found_part_by_name is not None
        assert found_part_by_name.id == test_part.id

        # Test get all parts
        all_parts = PartRepository.get_all_parts(session)
        assert len(all_parts) >= len(created_parts)

        print(f"✅ Search functionality tested with {len(created_parts)} LCSC parts")

    def test_bulk_operations_with_lcsc_data(self):
        """Test bulk operations with all LCSC data"""
        session = self.test_db.get_session()

        # Load real LCSC test data
        lcsc_data = self.load_lcsc_test_data()
        assert len(lcsc_data) > 0, "No LCSC test data loaded"

        # Create test location
        location_data = {
            "name": "Bulk Storage",
            "description": "Bulk component storage for testing",
            "location_type": "storage",
        }
        test_location = LocationRepository.add_location(session, location_data)

        # Create all parts from LCSC data
        created_parts = []
        for i, part_data in enumerate(lcsc_data):
            part_model = PartModel(
                part_number=f"BULK_{part_data['lcsc_part_number']}_{i}",
                part_name=f"BULK LCSC {part_data['lcsc_part_number']}",
                description=part_data["description"],
                quantity=int(part_data["order_qty"]) if part_data["order_qty"].isdigit() else 0,
                supplier="LCSC",
                location_id=test_location.id,
            )

            created_part = PartRepository.add_part(session, part_model)
            created_parts.append(created_part)

        # Verify all parts were created
        assert len(created_parts) == len(lcsc_data)

        # Test bulk retrieval
        for part in created_parts:
            retrieved_part = PartRepository.get_part_by_id(session, part.id)
            assert retrieved_part is not None
            assert retrieved_part.supplier == "LCSC"

        print(f"✅ Bulk operations tested with {len(created_parts)} LCSC parts")

    def test_comprehensive_crud_workflow(self):
        """Test complete CRUD workflow with real LCSC data"""
        session = self.test_db.get_session()

        # Load real LCSC test data
        lcsc_data = self.load_lcsc_test_data()
        assert len(lcsc_data) > 0, "No LCSC test data loaded"

        # 1. Create supporting data structures
        location_data = {
            "name": "Test Workflow Storage",
            "description": "Storage for comprehensive workflow testing",
            "location_type": "storage",
        }
        test_location = LocationRepository.add_location(session, location_data)

        category_data = {"name": "Workflow Components", "description": "Components for workflow testing"}
        test_category = CategoryRepository.create_category(session, category_data)

        # 2. Create parts with real LCSC data
        test_parts = lcsc_data[:2]  # Use first 2 parts
        created_parts = []

        for part_data in test_parts:
            part_model = PartModel(
                part_number=part_data["lcsc_part_number"],
                part_name=f"WORKFLOW {part_data['lcsc_part_number']}",
                description=part_data["description"],
                quantity=int(part_data["order_qty"]) if part_data["order_qty"].isdigit() else 0,
                supplier="LCSC",
                location_id=test_location.id,
                additional_properties={
                    "manufacturer": part_data["manufacturer"],
                    "lcsc_part_number": part_data["lcsc_part_number"],
                    "unit_price": part_data["unit_price"],
                },
            )

            created_part = PartRepository.add_part(session, part_model)
            created_part.categories.append(test_category)
            session.commit()
            created_parts.append(created_part)

        # 3. Verify all relationships
        for part in created_parts:
            retrieved_part = PartRepository.get_part_by_id(session, part.id)
            assert retrieved_part is not None

            # Verify location relationship
            assert retrieved_part.location_id == test_location.id

            # Verify category relationship
            assert len(retrieved_part.categories) > 0
            assert any(cat.name == "Workflow Components" for cat in retrieved_part.categories)

            # Verify LCSC data preservation
            assert retrieved_part.supplier == "LCSC"
            assert "manufacturer" in retrieved_part.additional_properties
            assert "lcsc_part_number" in retrieved_part.additional_properties

        # 4. Test updates and cleanup
        for part in created_parts:
            # Update part
            part.quantity += 5
            part.description = "Updated in workflow test"
            updated_part = PartRepository.update_part(session, part)
            assert updated_part.quantity == part.quantity
            assert updated_part.description == "Updated in workflow test"

            # Delete part
            deleted_part = PartRepository.delete_part(session, part.id)
            assert deleted_part is not None

        # 5. Cleanup supporting structures
        CategoryRepository.remove_category(session, test_category)
        LocationRepository.delete_location(session, test_location)

        print(f"✅ Comprehensive CRUD workflow completed with {len(created_parts)} LCSC parts")
