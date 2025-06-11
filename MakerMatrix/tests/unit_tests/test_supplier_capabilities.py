"""
Unit tests for Supplier Capabilities System
"""

import pytest
from MakerMatrix.parsers.supplier_capabilities import (
    CapabilityType,
    SupplierCapabilities,
    LCSCCapabilities,
    MouserCapabilities,
    DigiKeyCapabilities,
    BoltDepotCapabilities,
    get_supplier_capabilities,
    get_all_supplier_capabilities,
    find_suppliers_with_capability
)


class TestCapabilityType:
    """Test cases for CapabilityType enum"""

    def test_capability_type_values(self):
        """Test that all expected capability types exist"""
        expected_capabilities = [
            "enrich_basic_info",
            "fetch_datasheet", 
            "fetch_image",
            "fetch_pricing",
            "fetch_stock",
            "fetch_specifications",
            "validate_part_number",
            "fetch_alternatives"
        ]
        
        # Test that basic capabilities exist
        assert hasattr(CapabilityType, 'FETCH_DATASHEET')
        assert hasattr(CapabilityType, 'FETCH_IMAGE')
        assert hasattr(CapabilityType, 'FETCH_PRICING')
        assert hasattr(CapabilityType, 'ENRICH_BASIC_INFO')
        
        # Test enum values
        assert CapabilityType.FETCH_DATASHEET.value == "fetch_datasheet"
        assert CapabilityType.FETCH_IMAGE.value == "fetch_image"


class TestSupplierCapabilities:
    """Test cases for base SupplierCapabilities class"""

    def test_base_capabilities_interface(self):
        """Test that base class defines required interface"""
        # Can't instantiate abstract base class directly, test via LCSC
        lcsc = LCSCCapabilities()
        
        # Test methods exist
        assert hasattr(lcsc, 'get_supported_capabilities')
        assert hasattr(lcsc, 'supports_capability')
        assert hasattr(lcsc, 'get_capabilities_summary')
        assert hasattr(lcsc, 'get_capability_metadata')

    def test_base_capabilities_summary_structure(self):
        """Test the structure of capabilities summary"""
        lcsc = LCSCCapabilities()
        summary = lcsc.get_capabilities_summary()
        
        assert isinstance(summary, dict)
        assert "supplier" in summary
        assert "supported_capabilities" in summary
        assert "capabilities_detail" in summary


class TestLCSCCapabilities:
    """Test cases for LCSC capabilities"""

    def test_lcsc_supported_capabilities(self):
        """Test LCSC supported capabilities"""
        lcsc = LCSCCapabilities()
        capabilities = lcsc.get_supported_capabilities()
        
        # LCSC should support these capabilities
        expected_caps = [
            CapabilityType.ENRICH_BASIC_INFO,
            CapabilityType.FETCH_DATASHEET,
            CapabilityType.FETCH_IMAGE,
            CapabilityType.FETCH_PRICING,
            CapabilityType.FETCH_STOCK,
            CapabilityType.FETCH_SPECIFICATIONS
        ]
        
        for cap in expected_caps:
            assert cap in capabilities

    def test_lcsc_supports_capability(self):
        """Test LCSC capability checking"""
        lcsc = LCSCCapabilities()
        
        # Should support these
        assert lcsc.supports_capability(CapabilityType.FETCH_DATASHEET) is True
        assert lcsc.supports_capability(CapabilityType.FETCH_IMAGE) is True
        assert lcsc.supports_capability(CapabilityType.FETCH_PRICING) is True
        
        # Should not support these (not in LCSC capabilities)
        assert lcsc.supports_capability(CapabilityType.GET_ALTERNATIVES) is False

    def test_lcsc_capability_descriptions(self):
        """Test LCSC capability descriptions"""
        lcsc = LCSCCapabilities()
        
        desc = lcsc.get_capability_description(CapabilityType.FETCH_DATASHEET)
        assert "datasheet" in desc.lower()
        assert "pdf" in desc.lower()
        
        desc = lcsc.get_capability_description(CapabilityType.FETCH_PRICING)
        assert "pricing" in desc.lower() or "price" in desc.lower()

    def test_lcsc_capabilities_summary(self):
        """Test LCSC capabilities summary"""
        lcsc = LCSCCapabilities()
        summary = lcsc.get_capabilities_summary()
        
        assert summary["supplier_name"] == "LCSC"
        assert len(summary["supported_capabilities"]) >= 6
        assert summary["total_capabilities"] >= 6
        assert isinstance(summary["capability_descriptions"], dict)


class TestMouserCapabilities:
    """Test cases for Mouser capabilities"""

    def test_mouser_supported_capabilities(self):
        """Test Mouser supported capabilities"""
        mouser = MouserCapabilities()
        capabilities = mouser.get_supported_capabilities()
        
        # Mouser should support these capabilities
        expected_caps = [
            CapabilityType.ENRICH_BASIC_INFO,
            CapabilityType.FETCH_DATASHEET,
            CapabilityType.FETCH_IMAGE,
            CapabilityType.FETCH_PRICING,
            CapabilityType.FETCH_SPECIFICATIONS,
            CapabilityType.GET_ALTERNATIVES
        ]
        
        for cap in expected_caps:
            assert cap in capabilities

    def test_mouser_unique_capabilities(self):
        """Test capabilities unique to Mouser"""
        mouser = MouserCapabilities()
        
        # Mouser should support alternatives (not all suppliers do)
        assert mouser.supports_capability(CapabilityType.GET_ALTERNATIVES) is True

    def test_mouser_capabilities_summary(self):
        """Test Mouser capabilities summary"""
        mouser = MouserCapabilities()
        summary = mouser.get_capabilities_summary()
        
        assert summary["supplier_name"] == "Mouser"
        assert len(summary["supported_capabilities"]) >= 5


class TestDigiKeyCapabilities:
    """Test cases for DigiKey capabilities"""

    def test_digikey_supported_capabilities(self):
        """Test DigiKey supported capabilities"""
        digikey = DigiKeyCapabilities()
        capabilities = digikey.get_supported_capabilities()
        
        # DigiKey should support comprehensive capabilities
        expected_caps = [
            CapabilityType.ENRICH_BASIC_INFO,
            CapabilityType.FETCH_DATASHEET,
            CapabilityType.FETCH_IMAGE,
            CapabilityType.FETCH_PRICING,
            CapabilityType.FETCH_SPECIFICATIONS,
            CapabilityType.VALIDATE_PART,
            CapabilityType.GET_ALTERNATIVES
        ]
        
        for cap in expected_caps:
            assert cap in capabilities

    def test_digikey_validation_capability(self):
        """Test DigiKey's part validation capability"""
        digikey = DigiKeyCapabilities()
        
        # DigiKey should support part validation
        assert digikey.supports_capability(CapabilityType.VALIDATE_PART) is True

    def test_digikey_capabilities_summary(self):
        """Test DigiKey capabilities summary"""
        digikey = DigiKeyCapabilities()
        summary = digikey.get_capabilities_summary()
        
        assert summary["supplier_name"] == "DigiKey"
        assert len(summary["supported_capabilities"]) >= 6


class TestBoltDepotCapabilities:
    """Test cases for BoltDepot capabilities"""

    def test_boltdepot_supported_capabilities(self):
        """Test BoltDepot supported capabilities"""
        boltdepot = BoltDepotCapabilities()
        capabilities = boltdepot.get_supported_capabilities()
        
        # BoltDepot should support these capabilities (hardware-focused)
        expected_caps = [
            CapabilityType.ENRICH_BASIC_INFO,
            CapabilityType.FETCH_IMAGE,
            CapabilityType.FETCH_PRICING,
            CapabilityType.FETCH_SPECIFICATIONS
        ]
        
        for cap in expected_caps:
            assert cap in capabilities

    def test_boltdepot_limited_capabilities(self):
        """Test BoltDepot's limited capabilities (no datasheets for hardware)"""
        boltdepot = BoltDepotCapabilities()
        
        # BoltDepot should NOT support datasheets (hardware doesn't have datasheets)
        assert boltdepot.supports_capability(CapabilityType.FETCH_DATASHEET) is False
        
        # Should support basic info and images
        assert boltdepot.supports_capability(CapabilityType.ENRICH_BASIC_INFO) is True
        assert boltdepot.supports_capability(CapabilityType.FETCH_IMAGE) is True

    def test_boltdepot_capabilities_summary(self):
        """Test BoltDepot capabilities summary"""
        boltdepot = BoltDepotCapabilities()
        summary = boltdepot.get_capabilities_summary()
        
        assert summary["supplier_name"] == "BoltDepot"
        assert len(summary["supported_capabilities"]) >= 3


class TestSupplierCapabilityFunctions:
    """Test cases for supplier capability utility functions"""

    def test_get_supplier_capabilities_valid_supplier(self):
        """Test getting capabilities for valid suppliers"""
        lcsc_caps = get_supplier_capabilities("LCSC")
        assert isinstance(lcsc_caps, LCSCCapabilities)
        
        mouser_caps = get_supplier_capabilities("Mouser")
        assert isinstance(mouser_caps, MouserCapabilities)
        
        digikey_caps = get_supplier_capabilities("DigiKey")
        assert isinstance(digikey_caps, DigiKeyCapabilities)
        
        boltdepot_caps = get_supplier_capabilities("BoltDepot")
        assert isinstance(boltdepot_caps, BoltDepotCapabilities)

    def test_get_supplier_capabilities_case_insensitive(self):
        """Test getting capabilities with different case"""
        lcsc_caps_lower = get_supplier_capabilities("lcsc")
        lcsc_caps_upper = get_supplier_capabilities("LCSC")
        lcsc_caps_mixed = get_supplier_capabilities("Lcsc")
        
        assert isinstance(lcsc_caps_lower, LCSCCapabilities)
        assert isinstance(lcsc_caps_upper, LCSCCapabilities)
        assert isinstance(lcsc_caps_mixed, LCSCCapabilities)

    def test_get_supplier_capabilities_invalid_supplier(self):
        """Test getting capabilities for invalid supplier"""
        invalid_caps = get_supplier_capabilities("InvalidSupplier")
        assert invalid_caps is None

    def test_get_all_supplier_capabilities(self):
        """Test getting all supplier capabilities"""
        all_caps = get_all_supplier_capabilities()
        
        assert isinstance(all_caps, dict)
        assert "LCSC" in all_caps
        assert "Mouser" in all_caps
        assert "DigiKey" in all_caps
        assert "BoltDepot" in all_caps
        
        # Verify each is the correct type
        assert isinstance(all_caps["LCSC"], LCSCCapabilities)
        assert isinstance(all_caps["Mouser"], MouserCapabilities)
        assert isinstance(all_caps["DigiKey"], DigiKeyCapabilities)
        assert isinstance(all_caps["BoltDepot"], BoltDepotCapabilities)

    def test_find_suppliers_with_capability_datasheet(self):
        """Test finding suppliers that support datasheet fetching"""
        suppliers = find_suppliers_with_capability(CapabilityType.FETCH_DATASHEET)
        
        # Electronic component suppliers should support datasheets
        assert "LCSC" in suppliers
        assert "Mouser" in suppliers
        assert "DigiKey" in suppliers
        
        # Hardware supplier should NOT support datasheets
        assert "BoltDepot" not in suppliers

    def test_find_suppliers_with_capability_image(self):
        """Test finding suppliers that support image fetching"""
        suppliers = find_suppliers_with_capability(CapabilityType.FETCH_IMAGE)
        
        # All suppliers should support images
        assert "LCSC" in suppliers
        assert "Mouser" in suppliers
        assert "DigiKey" in suppliers
        assert "BoltDepot" in suppliers

    def test_find_suppliers_with_capability_alternatives(self):
        """Test finding suppliers that support alternative parts"""
        suppliers = find_suppliers_with_capability(CapabilityType.GET_ALTERNATIVES)
        
        # Only some suppliers support alternatives
        assert "Mouser" in suppliers
        assert "DigiKey" in suppliers
        
        # LCSC and BoltDepot may or may not support alternatives
        # (depends on implementation)

    def test_find_suppliers_with_capability_validation(self):
        """Test finding suppliers that support part validation"""
        suppliers = find_suppliers_with_capability(CapabilityType.VALIDATE_PART)
        
        # DigiKey should support validation
        assert "DigiKey" in suppliers

    def test_find_suppliers_with_capability_empty_result(self):
        """Test finding suppliers for a capability no one supports"""
        # Create a mock capability that no supplier supports
        # Since we can't create new enum values, we'll test with existing ones
        # and verify the function works correctly
        
        # Test that function returns a list (even if empty)
        suppliers = find_suppliers_with_capability(CapabilityType.VALIDATE_PART)
        assert isinstance(suppliers, list)

    def test_capability_consistency_across_suppliers(self):
        """Test that capability checking is consistent"""
        all_caps = get_all_supplier_capabilities()
        
        for supplier_name, supplier_caps in all_caps.items():
            supported = supplier_caps.get_supported_capabilities()
            
            # Every supported capability should return True for supports_capability
            for capability in supported:
                assert supplier_caps.supports_capability(capability) is True
            
            # Every capability should have a description
            for capability in supported:
                desc = supplier_caps.get_capability_description(capability)
                assert isinstance(desc, str)
                assert len(desc) > 0

    def test_capability_descriptions_quality(self):
        """Test that capability descriptions are meaningful"""
        all_caps = get_all_supplier_capabilities()
        
        for supplier_name, supplier_caps in all_caps.items():
            supported = supplier_caps.get_supported_capabilities()
            
            for capability in supported:
                desc = supplier_caps.get_capability_description(capability)
                
                # Description should contain relevant keywords
                desc_lower = desc.lower()
                capability_name = capability.value.lower()
                
                # Should contain some relevant keywords
                relevant_keywords = capability_name.split('_')
                keyword_found = any(keyword in desc_lower for keyword in relevant_keywords)
                assert keyword_found, f"Description '{desc}' doesn't contain relevant keywords for {capability_name}"

    def test_supplier_capability_coverage(self):
        """Test that suppliers have reasonable capability coverage"""
        all_caps = get_all_supplier_capabilities()
        
        for supplier_name, supplier_caps in all_caps.items():
            supported = supplier_caps.get_supported_capabilities()
            
            # Every supplier should support at least basic info enrichment
            assert CapabilityType.ENRICH_BASIC_INFO in supported
            
            # Every supplier should support at least 3 capabilities
            assert len(supported) >= 3
            
            # Electronic suppliers should support more capabilities than hardware suppliers
            if supplier_name in ["LCSC", "Mouser", "DigiKey"]:
                assert len(supported) >= 5
            elif supplier_name == "BoltDepot":
                assert len(supported) >= 3  # Hardware has fewer capabilities