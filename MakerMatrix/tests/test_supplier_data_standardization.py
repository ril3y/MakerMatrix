"""
Test Supplier Data Standardization

Tests that supplier data is correctly mapped to standardized database fields
for consistent UI display across all suppliers.
"""

import pytest
import json
from datetime import datetime
from sqlmodel import Session, select

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.suppliers.base import PartSearchResult, SupplierCapability
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
from MakerMatrix.schemas.part_data_standards import ComponentType, MountingType, RoHSStatus


class TestSupplierDataStandardization:
    """Test standardization of supplier data to database format"""
    
    @pytest.fixture
    def cleanup_test_parts(self):
        """Clean up test parts after test"""
        test_part_numbers = ["TEST_STANDARD_R123", "TEST_STANDARD_C456", "TEST_STANDARD_IC789"]
        yield
        try:
            with Session(engine) as session:
                for part_number in test_part_numbers:
                    part = session.exec(
                        select(PartModel).where(PartModel.part_number == part_number)
                    ).first()
                    if part:
                        session.delete(part)
                        session.commit()
                        print(f"Cleaned up test part {part_number}")
        except Exception as e:
            print(f"Note: Could not clean up test parts: {e}")
    
    def test_part_model_standardized_fields(self):
        """Test that PartModel has all the standardized fields we added"""
        
        # Test that the model has the new standardized fields
        expected_fields = [
            'manufacturer', 'manufacturer_part_number', 'component_type', 'package',
            'mounting_type', 'rohs_status', 'lifecycle_status', 'stock_quantity',
            'last_stock_update', 'last_enrichment_date', 'enrichment_source',
            'data_quality_score'
        ]
        
        for field in expected_fields:
            assert hasattr(PartModel, field), f"PartModel should have field: {field}"
        
        print("✅ PartModel has all standardized fields")
    
    def test_part_model_ui_convenience_methods(self):
        """Test that PartModel has UI convenience methods"""
        
        expected_methods = [
            'get_display_name', 'get_standardized_additional_properties',
            'get_specifications_dict', 'get_supplier_data', 'has_datasheet',
            'has_complete_identification', 'needs_enrichment', 'update_data_quality_score',
            'get_enrichment_status'
        ]
        
        for method in expected_methods:
            assert hasattr(PartModel, method), f"PartModel should have method: {method}"
        
        print("✅ PartModel has all UI convenience methods")
    
    def test_supplier_data_mapper_lcsc(self):
        """Test mapping LCSC supplier data to standardized format"""
        
        # Create mock LCSC PartSearchResult
        lcsc_result = PartSearchResult(
            supplier_part_number="C2918489",
            manufacturer="Samwha Capacitor",
            manufacturer_part_number="CS2012X5R475K250NRE",
            description="4.7µF ±10% 25V Multilayer Ceramic Capacitors MLCC - SMD/SMT 1206",
            category="Capacitors",
            datasheet_url="https://item.szlcsc.com/373011.html",
            image_url="https://assets.lcsc.com/images/lcsc/900x900/20230121_Samwha-Capacitor-CS2012X5R475K250NRE_C2918489_front.jpg",
            specifications={
                "Value": "4.7µF",
                "Tolerance": "±10%",
                "Voltage": "25V",
                "Package": "1206",
                "Temperature": "-55°C~+125°C"
            },
            additional_data={
                "product_url": "https://lcsc.com/product-detail/C2918489.html",
                "easyeda_data_available": True,
                "is_smt": True
            }
        )
        
        # Map to standardized format
        mapper = SupplierDataMapper()
        mapped_data = mapper.map_supplier_result_to_part_data(
            lcsc_result, "LCSC", ["fetch_datasheet", "fetch_image", "fetch_specifications"]
        )
        
        # Verify core fields are correctly mapped
        assert mapped_data['part_number'] == "C2918489"
        assert mapped_data['manufacturer'] == "Samwha Capacitor"
        assert mapped_data['manufacturer_part_number'] == "CS2012X5R475K250NRE"
        assert mapped_data['component_type'] == ComponentType.CAPACITOR
        assert mapped_data['package'] == "1206"
        assert mapped_data['mounting_type'] == MountingType.SMT
        assert mapped_data['supplier'] == "LCSC"
        assert mapped_data['image_url'] == lcsc_result.image_url
        
        # Verify additional_properties structure
        additional_props = mapped_data['additional_properties']
        assert 'specifications' in additional_props
        assert 'supplier_data' in additional_props
        assert 'metadata' in additional_props
        
        # Check specifications
        specs = additional_props['specifications']
        assert specs['value'] == "4.7µF"
        assert specs['tolerance'] == "±10%"
        assert specs['voltage_rating'] == "25V"
        assert specs['package'] == "1206"
        
        # Check supplier data
        supplier_data = additional_props['supplier_data']['lcsc']
        assert supplier_data['supplier_part_number'] == "C2918489"
        assert supplier_data['supplier_category'] == "Capacitors"
        
        # Check metadata
        metadata = additional_props['metadata']
        assert metadata['enrichment_supplier'] == "LCSC"
        assert metadata['has_datasheet'] == True
        assert metadata['has_image'] == True
        assert metadata['needs_enrichment'] == False
        
        print("✅ LCSC data mapping works correctly")
    
    def test_supplier_data_mapper_mouser(self):
        """Test mapping Mouser supplier data to standardized format"""
        
        # Create mock Mouser PartSearchResult with pricing
        mouser_result = PartSearchResult(
            supplier_part_number="511-STM32F373CBT6",
            manufacturer="STMicroelectronics",
            manufacturer_part_number="STM32F373CBT6",
            description="ARM Microcontrollers - MCU 32-Bit ARM Cortex M4 72MHz 128kB MCU FPU",
            category="Microcontrollers",
            datasheet_url="https://www.st.com/resource/en/datasheet/stm32f373cb.pdf",
            image_url="https://eu.mouser.com/images/stmicroelectronics/images/STM32F373CBT6_SPL.jpg",
            stock_quantity=2540,
            pricing=[
                {"quantity": 1, "price": 3.45, "currency": "USD"},
                {"quantity": 10, "price": 3.21, "currency": "USD"},
                {"quantity": 100, "price": 2.89, "currency": "USD"}
            ],
            specifications={
                "Core": "ARM Cortex-M4",
                "Speed": "72MHz", 
                "Flash": "128kB",
                "RAM": "32kB",
                "Package": "LQFP-48",
                "Operating Temperature": "-40°C to +85°C"
            },
            additional_data={
                "product_detail_url": "https://eu.mouser.com/ProductDetail/511-STM32F373CBT6",
                "lead_time": "In Stock",
                "min_order_qty": 1,
                "rohs_status": "RoHS Compliant",
                "lifecycle_status": "Active"
            }
        )
        
        # Map to standardized format
        mapper = SupplierDataMapper()
        mapped_data = mapper.map_supplier_result_to_part_data(
            mouser_result, "Mouser", ["fetch_datasheet", "fetch_image", "fetch_pricing", "fetch_stock", "fetch_specifications"]
        )
        
        # Verify core fields
        assert mapped_data['manufacturer'] == "STMicroelectronics"
        assert mapped_data['manufacturer_part_number'] == "STM32F373CBT6"
        assert mapped_data['component_type'] == ComponentType.IC_MICROCONTROLLER
        assert mapped_data['package'] == "LQFP-48"
        assert mapped_data['rohs_status'] == RoHSStatus.COMPLIANT
        assert mapped_data['supplier'] == "MOUSER"
        
        # Verify pricing data
        assert mapped_data['unit_price'] == 3.45  # First tier price
        assert mapped_data['currency'] == "USD"
        assert 'pricing_data' in mapped_data
        assert mapped_data['pricing_data']['tier_count'] == 3
        
        # Verify stock data
        assert mapped_data['stock_quantity'] == 2540
        assert 'last_stock_update' in mapped_data
        
        # Verify additional properties
        additional_props = mapped_data['additional_properties']
        specs = additional_props['specifications']
        assert 'ARM Cortex-M4' in str(specs)  # Should contain core info
        
        supplier_data = additional_props['supplier_data']['mouser']
        assert supplier_data['supplier_part_number'] == "511-STM32F373CBT6"
        
        print("✅ Mouser data mapping works correctly")
    
    def test_create_part_with_standardized_data(self, cleanup_test_parts):
        """Test creating a part with standardized data and using UI methods"""
        
        with Session(engine) as session:
            # Create a part with standardized data
            part = PartModel(
                part_number="TEST_STANDARD_R123",
                part_name="Test Standardized Resistor",
                description="10kΩ ±1% 0.25W Thick Film Resistors - SMD 0603",
                quantity=100,
                supplier="LCSC",
                
                # Standardized core fields
                manufacturer="Vishay",
                manufacturer_part_number="CRCW060310K0FKEA",
                component_type=ComponentType.RESISTOR.value,
                package="0603",
                mounting_type=MountingType.SMT.value,
                rohs_status=RoHSStatus.COMPLIANT.value,
                
                # Pricing info
                unit_price=0.015,
                currency="USD",
                stock_quantity=50000,
                
                # Enrichment tracking
                last_enrichment_date=datetime.utcnow(),
                enrichment_source="LCSC"
            )
            
            # Set standardized additional_properties
            from MakerMatrix.schemas.part_data_standards import StandardizedAdditionalProperties
            std_props = StandardizedAdditionalProperties()
            std_props.specifications.value = "10kΩ"
            std_props.specifications.tolerance = "±1%"
            std_props.specifications.power_rating = "0.25W"
            std_props.specifications.package = "0603"
            std_props.specifications.mounting_type = MountingType.SMT
            
            part.additional_properties = std_props.to_dict()
            
            session.add(part)
            session.commit()
            session.refresh(part)
            
            # Test UI convenience methods
            assert part.get_display_name() == "Vishay CRCW060310K0FKEA"
            assert part.has_complete_identification() == True
            assert part.needs_enrichment() == False  # Has been enriched
            
            # Test specifications access
            specs = part.get_specifications_dict()
            assert specs['value'] == "10kΩ"
            assert specs['tolerance'] == "±1%"
            assert specs['power_rating'] == "0.25W"
            
            # Test enrichment status
            status = part.get_enrichment_status()
            assert status['has_complete_id'] == True
            assert status['has_pricing'] == True
            assert status['has_stock_info'] == True
            assert status['enrichment_source'] == "LCSC"
            
            # Update data quality score
            part.update_data_quality_score()
            assert part.data_quality_score > 0.8  # Should be high quality
            
            print("✅ Part creation with standardized data works correctly")
            print(f"  Display name: {part.get_display_name()}")
            print(f"  Data quality score: {part.data_quality_score:.2f}")
            print(f"  Component type: {part.component_type}")
            print(f"  Package: {part.package}")
            print(f"  Mounting type: {part.mounting_type}")
    
    def test_ui_data_consistency(self, cleanup_test_parts):
        """Test that UI can reliably access data regardless of supplier"""
        
        # Create parts from different "suppliers" with consistent data access
        suppliers_data = {
            "LCSC": {
                "part_number": "C25804",
                "manufacturer": "Vishay",
                "manufacturer_part_number": "RC0603FR-0710KL",
                "component_type": ComponentType.RESISTOR.value
            },
            "Mouser": {
                "part_number": "71-RC0603FR-0710KL",
                "manufacturer": "Vishay", 
                "manufacturer_part_number": "RC0603FR-0710KL",
                "component_type": ComponentType.RESISTOR.value
            },
            "DigiKey": {
                "part_number": "RC0603FR-0710KLCT-ND",
                "manufacturer": "Vishay",
                "manufacturer_part_number": "RC0603FR-0710KL", 
                "component_type": ComponentType.RESISTOR.value
            }
        }
        
        created_parts = []
        
        with Session(engine) as session:
            for supplier, data in suppliers_data.items():
                part = PartModel(
                    part_number=data["part_number"],
                    part_name=f"Test {supplier} Resistor",
                    supplier=supplier,
                    manufacturer=data["manufacturer"],
                    manufacturer_part_number=data["manufacturer_part_number"],
                    component_type=data["component_type"],
                    package="0603",
                    mounting_type=MountingType.SMT.value
                )
                session.add(part)
                created_parts.append(part)
            
            session.commit()
            
            # Test that UI can access consistent data from all parts
            for part in created_parts:
                # All parts should have consistent access methods
                assert part.get_display_name().startswith("Vishay RC0603FR-0710KL")
                assert part.has_complete_identification() == True
                assert part.component_type == ComponentType.RESISTOR.value
                assert part.package == "0603"
                assert part.mounting_type == MountingType.SMT.value
                
                # Supplier-specific data should be accessible but different
                supplier_data = part.get_supplier_data()
                # May be empty since we didn't set additional_properties, but method should work
                assert isinstance(supplier_data, dict)
                
                print(f"✅ {part.supplier}: {part.get_display_name()}")
            
            print("✅ UI can consistently access data from all suppliers")
    
    def test_component_type_detection(self):
        """Test automatic component type detection"""
        
        from MakerMatrix.schemas.part_data_standards import determine_component_type
        
        test_cases = [
            ("10K Resistor", "10kΩ ±1% resistor", ComponentType.RESISTOR),
            ("STM32F103", "ARM Microcontroller", ComponentType.IC_MICROCONTROLLER),
            ("4.7µF Capacitor", "Ceramic capacitor 25V", ComponentType.CAPACITOR),
            ("LED Red", "Red LED 5mm", ComponentType.DIODE),
            ("USB Connector", "USB Type-C connector", ComponentType.CONNECTOR),
        ]
        
        for part_name, description, expected_type in test_cases:
            detected_type = determine_component_type(part_name, description, {})
            assert detected_type == expected_type, f"Expected {expected_type} for '{part_name}', got {detected_type}"
        
        print("✅ Component type auto-detection works correctly")
    
    def test_data_quality_scoring(self):
        """Test data quality scoring calculation"""
        
        # Create part with minimal data (low quality)
        minimal_part = PartModel(
            part_name="Minimal Part",
            quantity=1
        )
        minimal_part.update_data_quality_score()
        assert minimal_part.data_quality_score < 0.3
        
        # Create part with complete data (high quality)
        complete_part = PartModel(
            part_name="Complete Part",
            manufacturer="Test Manufacturer",
            manufacturer_part_number="TEST123",
            component_type=ComponentType.RESISTOR.value,
            package="0603",
            description="Complete part with all data",
            image_url="https://example.com/image.jpg",
            unit_price=1.25
        )
        complete_part.update_data_quality_score()
        assert complete_part.data_quality_score >= 0.8
        
        print(f"✅ Data quality scoring: minimal={minimal_part.data_quality_score:.2f}, complete={complete_part.data_quality_score:.2f}")


if __name__ == "__main__":
    # Run basic tests
    test = TestSupplierDataStandardization()
    test.test_part_model_standardized_fields()
    test.test_part_model_ui_convenience_methods()
    test.test_component_type_detection()
    test.test_data_quality_scoring()
    print("✅ All basic standardization tests passed!")