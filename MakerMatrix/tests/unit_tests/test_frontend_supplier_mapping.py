"""
Test frontend supplier field mapping to ensure it works with backend API response format
"""
import pytest


def test_supplier_name_field_mapping():
    """Test that frontend code can handle different supplier field names from API"""
    
    # Mock API response format (what the backend actually returns)
    mock_api_response = {
        "status": "success",
        "data": [
            {
                "id": "digikey", 
                "name": "DigiKey Electronics",
                "configured": True,
                "enabled": True
            },
            {
                "id": "lcsc",
                "name": "LCSC Electronics", 
                "configured": False,
                "enabled": False
            }
        ]
    }
    
    # Simulate the frontend logic
    def extract_supplier_names(response_data):
        """Extract supplier names using the same logic as frontend"""
        return set(response_data.get('data', []) and [
            (s.get('name') or s.get('supplier_name') or s.get('id') or '').upper()
            for s in response_data['data']
        ] or [])
    
    configured_names = extract_supplier_names(mock_api_response)
    
    # Test that supplier names are correctly extracted
    assert "DIGIKEY ELECTRONICS" in configured_names or "DIGIKEY" in configured_names
    assert "LCSC ELECTRONICS" in configured_names or "LCSC" in configured_names
    
    # Test that parts with these suppliers would be correctly identified
    part_suppliers = ["DIGIKEY", "LCSC", "MOUSER"]
    
    # Check for unconfigured suppliers (using the logic from frontend)
    unconfigured_suppliers = []
    for supplier in part_suppliers:
        found = False
        for configured in configured_names:
            if supplier.upper() in configured or configured in supplier.upper():
                found = True
                break
        if not found:
            unconfigured_suppliers.append(supplier)
    
    # MOUSER should be unconfigured, DIGIKEY and LCSC should be configured
    assert "MOUSER" in unconfigured_suppliers
    assert "DIGIKEY" not in unconfigured_suppliers  # Should be found via name matching
    assert "LCSC" not in unconfigured_suppliers     # Should be found via name matching


def test_supplier_mapping_edge_cases():
    """Test edge cases in supplier name mapping"""
    
    # Test with empty response
    empty_response = {"status": "success", "data": []}
    
    def extract_supplier_names(response_data):
        return set(response_data.get('data', []) and [
            (s.get('name') or s.get('supplier_name') or s.get('id') or '').upper()
            for s in response_data['data']
        ] or [])
    
    names = extract_supplier_names(empty_response)
    assert len(names) == 0
    
    # Test with missing fields
    partial_response = {
        "status": "success", 
        "data": [
            {"id": "test_supplier"},  # Only ID field
            {"name": "Another Supplier"},  # Only name field
            {}  # Empty supplier object
        ]
    }
    
    names = extract_supplier_names(partial_response)
    assert "TEST_SUPPLIER" in names
    assert "ANOTHER SUPPLIER" in names
    assert "" in names  # Empty string from empty object


if __name__ == "__main__":
    pytest.main([__file__, "-v"])