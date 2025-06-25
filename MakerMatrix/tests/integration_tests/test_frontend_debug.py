"""
Debug test to simulate exactly what the frontend is doing when checking supplier configurations
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()
    
    # Set up default roles and admin
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # Clean up
    SQLModel.metadata.drop_all(engine)


def test_frontend_debug_exact_simulation():
    """Debug what exact API calls the frontend is making"""
    
    # Step 1: Login (exactly like frontend)
    print("=== STEP 1: LOGIN ===")
    login_response = client.post("/auth/login", data={
        "username": "admin",
        "password": "Admin123!"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    print(f"✅ Login successful, got token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Check current supplier configurations
    print("\n=== STEP 2: CHECK CONFIGURED SUPPLIERS (before creating any) ===")
    response = client.get("/api/suppliers/configured", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Configured suppliers count: {len(data.get('data', []))}")
    
    # Step 3: Create a supplier configuration (like user would do via UI)
    print("\n=== STEP 3: CREATE SUPPLIER CONFIG ===")
    supplier_config = {
        "supplier_name": "LCSC",
        "display_name": "LCSC Electronics",
        "base_url": "https://api.lcsc.com",
        "enabled": True,
        "credentials": {
            "api_key": "test_key_123"
        },
        "config": {
            "rate_limit": 100,
            "timeout": 30
        }
    }
    
    config_response = client.post(
        "/api/config/suppliers",
        json=supplier_config,
        headers=headers
    )
    print(f"Config creation status: {config_response.status_code}")
    print(f"Config creation response: {config_response.text}")
    
    # Step 4: Now check configured suppliers again
    print("\n=== STEP 4: CHECK CONFIGURED SUPPLIERS (after creating LCSC) ===")
    response = client.get("/api/suppliers/configured", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        suppliers = data.get('data', [])
        print(f"Configured suppliers count: {len(suppliers)}")
        
        for supplier in suppliers:
            print(f"  - ID: {supplier.get('id')}")
            print(f"  - Name: {supplier.get('name')}")
            print(f"  - Supplier Name: {supplier.get('supplier_name')}")
            print(f"  - Configured: {supplier.get('configured')}")
            print(f"  - Enabled: {supplier.get('enabled')}")
            print("  ---")
    
    # Step 5: Simulate frontend field mapping logic
    print("\n=== STEP 5: SIMULATE FRONTEND FIELD MAPPING ===")
    if response.status_code == 200:
        configuredSuppliers = response.json()
        
        # OLD (broken) logic
        try:
            old_logic_names = set(configuredSuppliers.get('data', []) and [
                s.get('supplier_name', '').upper() for s in configuredSuppliers['data']
            ] or [])
            print(f"OLD logic would find: {old_logic_names}")
        except Exception as e:
            print(f"OLD logic error: {e}")
        
        # NEW (fixed) logic
        try:
            new_logic_names = set(configuredSuppliers.get('data', []) and [
                (s.get('name') or s.get('supplier_name') or s.get('id') or '').upper()
                for s in configuredSuppliers['data']
            ] or [])
            print(f"NEW logic finds: {new_logic_names}")
        except Exception as e:
            print(f"NEW logic error: {e}")
        
        # Test with LCSC part
        part_suppliers = ["LCSC"]
        print(f"\nChecking if parts with suppliers {part_suppliers} would be flagged as unconfigured:")
        
        unconfigured_with_old = [s for s in part_suppliers if s.upper() not in old_logic_names]
        unconfigured_with_new = []
        for supplier in part_suppliers:
            found = False
            for configured in new_logic_names:
                if supplier.upper() in configured or configured in supplier.upper():
                    found = True
                    break
            if not found:
                unconfigured_with_new.append(supplier)
        
        print(f"OLD logic: unconfigured = {unconfigured_with_old}")
        print(f"NEW logic: unconfigured = {unconfigured_with_new}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])