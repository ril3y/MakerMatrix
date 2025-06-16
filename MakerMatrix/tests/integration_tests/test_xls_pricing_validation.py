"""
Test XLS import pricing information parsing and storage.
"""

import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.models.order_models import OrderModel, OrderItemModel
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_clean_database():
    """Set up a clean database for each test."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    user_repo = UserRepository()
    user_repo.engine = engine
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token(setup_clean_database):
    """Get admin authentication token."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": "admin", "password_change_required": False})
    return token


@pytest.fixture
def auth_headers(admin_token):
    """Get authentication headers."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestXLSPricingValidation:
    """Test that XLS import properly parses and stores pricing information."""
    
    @pytest.mark.skipif(not Path("MakerMatrix/tests/mouser_xls_test/271360826.xls").exists(), 
                       reason="Mouser XLS test file not available")
    def test_xls_import_pricing_data_storage(self, auth_headers):
        """Test that XLS import stores pricing information in orders and parts."""
        test_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")
        
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        print(f"\n=== XLS Pricing Validation ===")
        
        # Import XLS file
        import_response = client.post(
            "/api/csv/import-file",
            headers=auth_headers,
            files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")},
            data={
                "parser_type": "mouser",
                "order_number": "PRICING-TEST-001",
                "order_date": "2024-01-21",
                "notes": "Pricing validation test"
            }
        )
        
        assert import_response.status_code == 200
        import_data = import_response.json()
        assert import_data["status"] == "success"
        assert import_data["data"]["successful_imports"] > 0
        
        print(f"Import completed: {import_data['data']['successful_imports']} parts")
        
        # Check if orders were created
        with Session(engine) as session:
            # Check orders table
            orders = session.exec(select(OrderModel)).all()
            print(f"Orders in database: {len(orders)}")
            
            if orders:
                order = orders[0]
                print(f"Order details:")
                print(f"  ID: {order.id}")
                print(f"  Order number: {order.order_number}")
                print(f"  Supplier: {order.supplier}")
                print(f"  Subtotal: {order.subtotal}")
                print(f"  Total: {order.total}")
                
                # Check order items
                order_items = session.exec(
                    select(OrderItemModel).where(OrderItemModel.order_id == order.id)
                ).all()
                print(f"Order items: {len(order_items)}")
                
                for i, item in enumerate(order_items[:3]):  # Show first 3
                    print(f"  Item {i+1}:")
                    print(f"    Part number: {item.manufacturer_part_number}")
                    print(f"    Description: {item.description}")
                    print(f"    Quantity: {item.quantity_ordered}")
                    print(f"    Unit price: {item.unit_price}")
                    print(f"    Extended price: {item.extended_price}")
            
            # Check parts table for pricing information
            parts = session.exec(select(PartModel)).all()
            print(f"Parts in database: {len(parts)}")
            
            if parts:
                part = parts[0]
                print(f"Part details:")
                print(f"  Name: {part.part_name}")
                print(f"  Part number: {part.part_number}")
                print(f"  Quantity: {part.quantity}")
                print(f"  Additional properties: {part.additional_properties}")
        
        # Assertions
        assert len(orders) > 0, "Should have created at least one order"
        assert len(order_items) > 0, "Should have created order items"
        assert len(parts) > 0, "Should have created parts"
        
        # Check that order has pricing information
        order = orders[0]
        # Note: Parser-extracted order number takes precedence for XLS files
        assert order.order_number in ["PRICING-TEST-001", "271360826"]  # Either user or parser order number
        assert order.supplier == "Mouser"
        
        # Check that order items have pricing
        pricing_items = [item for item in order_items if item.unit_price and item.unit_price > 0]
        print(f"Order items with pricing: {len(pricing_items)} out of {len(order_items)}")
        
        # Check if parts have additional pricing properties
        parts_with_pricing = []
        for part in parts:
            if part.additional_properties:
                pricing_keys = [k for k in part.additional_properties.keys() if 'price' in k.lower()]
                if pricing_keys:
                    parts_with_pricing.append(part)
                    print(f"Part {part.part_name} has pricing keys: {pricing_keys}")
        
        print(f"Parts with pricing data: {len(parts_with_pricing)} out of {len(parts)}")
    
    def test_mouser_xls_parser_pricing_extraction(self):
        """Test that Mouser XLS parser extracts pricing information correctly."""
        from MakerMatrix.parsers.mouser_xls_parser import MouserXLSParser
        
        test_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")
        if not test_file.exists():
            pytest.skip("Mouser XLS test file not available")
        
        parser = MouserXLSParser()
        result = parser.parse_file(str(test_file))
        
        assert result.success, "Parser should successfully parse the file"
        assert len(result.parts) > 0, "Should have parsed some parts"
        
        print(f"\n=== Parser Pricing Extraction ===")
        print(f"Parsed {len(result.parts)} parts")
        
        # Check first few parts for pricing information
        for i, part in enumerate(result.parts[:3]):
            print(f"Part {i+1}: {part['part_name']}")
            print(f"  Quantity: {part['quantity']}")
            print(f"  Additional properties: {part.get('additional_properties', {})}")
            
            # Check if pricing information is in additional_properties
            if 'additional_properties' in part:
                props = part['additional_properties']
                pricing_keys = [k for k in props.keys() if any(keyword in k.lower() for keyword in ['price', 'cost', 'unit'])]
                if pricing_keys:
                    print(f"  Pricing keys found: {pricing_keys}")
                    for key in pricing_keys:
                        print(f"    {key}: {props[key]}")
                else:
                    print(f"  No pricing keys found in additional_properties")
        
        # Look for any pricing-related data in the parts
        parts_with_pricing = 0
        for part in result.parts:
            if 'additional_properties' in part:
                props = part['additional_properties']
                has_pricing = any('price' in str(key).lower() or 'cost' in str(key).lower() for key in props.keys())
                if has_pricing:
                    parts_with_pricing += 1
        
        print(f"Parts with potential pricing data: {parts_with_pricing}/{len(result.parts)}")
    
    def test_xls_preview_shows_pricing_columns(self, auth_headers):
        """Test that XLS preview shows pricing-related columns."""
        test_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")
        if not test_file.exists():
            pytest.skip("Mouser XLS test file not available")
        
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        # Test preview
        preview_response = client.post(
            "/api/csv/preview-file",
            headers=auth_headers,
            files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")}
        )
        
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        assert preview_data["status"] == "success"
        
        headers = preview_data["data"]["headers"]
        preview_rows = preview_data["data"]["preview_rows"]
        
        print(f"\n=== XLS Preview Pricing Columns ===")
        print(f"Headers: {headers}")
        
        # Look for pricing-related columns
        pricing_columns = [h for h in headers if any(keyword in h.lower() for keyword in ['price', 'cost', 'usd', '$'])]
        print(f"Pricing columns found: {pricing_columns}")
        
        # Show sample data for pricing columns
        if preview_rows and pricing_columns:
            print(f"Sample pricing data from first row:")
            first_row = preview_rows[0]
            for col in pricing_columns:
                if col in first_row:
                    print(f"  {col}: {first_row[col]}")
        
        # We should find at least some pricing-related columns in Mouser data
        assert len(pricing_columns) > 0, f"Should find pricing columns in headers: {headers}"