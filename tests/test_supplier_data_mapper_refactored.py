"""
Test Refactored SupplierDataMapper - Supplier-agnostic data mapping

This test suite verifies that the refactored SupplierDataMapper:
1. Has NO hardcoded supplier-specific mapping methods
2. Delegates all supplier-specific mapping to supplier's map_to_standard_format()
3. Works with ANY supplier dynamically through the registry
4. Maintains backward compatibility with existing data structures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
from datetime import datetime

from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
from MakerMatrix.suppliers.base import PartSearchResult


class MockSupplierForMapping:
    """Mock supplier that implements map_to_standard_format()"""

    def __init__(self, supplier_name: str, custom_mapping: Dict[str, Any] = None):
        self.supplier_name = supplier_name
        self.custom_mapping = custom_mapping or {}

    def get_supplier_info(self):
        return Mock(
            name=self.supplier_name,
            display_name=f"{self.supplier_name.title()} Supplier"
        )

    def map_to_standard_format(self, supplier_data):
        """
        Simulate supplier-specific mapping.
        This method would contain supplier-specific logic in real suppliers.
        """
        if isinstance(supplier_data, PartSearchResult):
            # Base mapping
            mapped = {
                'supplier_part_number': supplier_data.supplier_part_number,
                'part_name': supplier_data.part_name,
                'manufacturer': supplier_data.manufacturer,
                'description': supplier_data.description,
            }

            # Add supplier-specific custom fields
            if self.custom_mapping:
                mapped.update(self.custom_mapping)

            # Add supplier-specific prefix to demonstrate custom behavior
            mapped[f'{self.supplier_name}_custom_field'] = f'custom_value_for_{self.supplier_name}'

            return mapped

        return {}


class TestRefactoredSupplierDataMapper:
    """Test the refactored, supplier-agnostic SupplierDataMapper"""

    def test_mapper_has_no_hardcoded_supplier_methods(self):
        """Verify that SupplierDataMapper has NO hardcoded supplier-specific methods"""
        import inspect
        from MakerMatrix.services.data import supplier_data_mapper

        # Get all methods from the SupplierDataMapper class
        mapper_source = inspect.getsource(supplier_data_mapper.SupplierDataMapper)

        # These method names should NOT exist anymore
        forbidden_methods = [
            '_map_lcsc_data',
            '_map_mouser_data',
            '_map_digikey_data',
            '_map_mcmaster_data',
            '_map_bolt_depot_data',
            '_map_seeedstudio_data',
            '_map_adafruit_data',
        ]

        for method_name in forbidden_methods:
            assert method_name not in mapper_source, \
                f"Found forbidden hardcoded method '{method_name}' in SupplierDataMapper"

    def test_mapper_delegates_to_supplier_mapping(self):
        """Test that mapper delegates supplier-specific logic to supplier.map_to_standard_format()"""
        mapper = SupplierDataMapper()

        # Create a mock supplier with custom mapping
        mock_supplier = MockSupplierForMapping(
            supplier_name='test-supplier',
            custom_mapping={'test_field': 'test_value'}
        )

        # Create test data
        test_result = PartSearchResult(
            supplier_part_number='TEST-123',
            part_name='Test Part',
            manufacturer='Test Mfg',
            description='Test description'
        )

        # Patch get_supplier to return our mock
        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=mock_supplier):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=test_result,
                supplier_name='test-supplier'
            )

        # Verify supplier-specific mapping was applied
        assert 'test-supplier_custom_field' in mapped_data['additional_properties']
        assert mapped_data['additional_properties']['test-supplier_custom_field'] == 'custom_value_for_test-supplier'

    def test_mapper_works_with_any_supplier_dynamically(self):
        """Test that mapper works with ANY supplier without hardcoding"""
        mapper = SupplierDataMapper()

        # Test with multiple different supplier names
        test_suppliers = [
            'mcmaster-carr',
            'digikey',
            'new-supplier-2025',
            'custom-supplier-xyz',
            'future-supplier'
        ]

        for supplier_name in test_suppliers:
            mock_supplier = MockSupplierForMapping(supplier_name)

            test_result = PartSearchResult(
                supplier_part_number=f'{supplier_name.upper()}-123',
                part_name=f'Part from {supplier_name}',
                manufacturer='Test Mfg'
            )

            with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=mock_supplier):
                mapped_data = mapper.map_supplier_result_to_part_data(
                    supplier_result=test_result,
                    supplier_name=supplier_name
                )

            # Verify mapping succeeded
            assert mapped_data['supplier_part_number'] == f'{supplier_name.upper()}-123'
            assert mapped_data['part_name'] == f'Part from {supplier_name}'

            # Verify supplier-specific custom field was applied
            assert f'{supplier_name}_custom_field' in mapped_data['additional_properties']

    def test_mapper_handles_supplier_not_in_registry(self):
        """Test that mapper handles gracefully when supplier not found in registry"""
        mapper = SupplierDataMapper()

        test_result = PartSearchResult(
            supplier_part_number='TEST-123',
            part_name='Test Part'
        )

        # Patch get_supplier to return None (supplier not found)
        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=None):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=test_result,
                supplier_name='unknown-supplier'
            )

        # Should still return mapped data with core fields
        assert mapped_data['supplier_part_number'] == 'TEST-123'
        assert mapped_data['part_name'] == 'Test Part'

    def test_mapper_separates_core_and_custom_fields(self):
        """Test that mapper properly separates core model fields from custom fields"""
        mapper = SupplierDataMapper()

        # Create supplier that returns both core and custom fields
        mock_supplier = MockSupplierForMapping('test')

        # Mock the map_to_standard_format to return mixed fields
        def custom_mapping(supplier_data):
            return {
                # Core fields (should go to model)
                'supplier_part_number': 'CORE-123',
                'manufacturer': 'Core Mfg',
                'description': 'Core desc',

                # Custom fields (should go to additional_properties)
                'voltage_rating': '3.3V',
                'package_type': 'SOT-23',
                'custom_field': 'custom_value'
            }

        mock_supplier.map_to_standard_format = custom_mapping

        test_result = PartSearchResult(supplier_part_number='TEST')

        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=mock_supplier):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=test_result,
                supplier_name='test'
            )

        # Core fields should be at top level
        assert mapped_data['supplier_part_number'] == 'CORE-123'
        assert mapped_data['manufacturer'] == 'Core Mfg'
        assert mapped_data['description'] == 'Core desc'

        # Custom fields should be in additional_properties
        assert 'voltage_rating' in mapped_data['additional_properties']
        assert 'package_type' in mapped_data['additional_properties']
        assert 'custom_field' in mapped_data['additional_properties']

    def test_mapper_adds_enrichment_metadata(self):
        """Test that mapper adds enrichment metadata to results"""
        mapper = SupplierDataMapper()
        mock_supplier = MockSupplierForMapping('test')

        test_result = PartSearchResult(supplier_part_number='TEST-123')

        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=mock_supplier):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=test_result,
                supplier_name='test'
            )

        # Should have enrichment metadata
        assert 'last_enrichment_date' in mapped_data
        assert 'enrichment_source' in mapped_data
        assert mapped_data['enrichment_source'] == 'test'

        # Should also be in additional_properties
        assert 'last_enrichment_date' in mapped_data['additional_properties']
        assert 'enrichment_source' in mapped_data['additional_properties']

    def test_mapper_calculates_data_quality_score(self):
        """Test that mapper calculates data quality score"""
        mapper = SupplierDataMapper()
        mock_supplier = MockSupplierForMapping('test')

        # Rich data should have higher quality score
        rich_result = PartSearchResult(
            supplier_part_number='TEST-123',
            part_name='Rich Part',
            manufacturer='Test Mfg',
            manufacturer_part_number='MFG-456',
            description='Complete description',
            image_url='https://example.com/image.jpg',
            pricing=[{'quantity': 1, 'price': 1.23}],
            stock_quantity=100
        )

        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=mock_supplier):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=rich_result,
                supplier_name='test'
            )

        # Should have quality score
        assert 'data_quality_score' in mapped_data
        assert isinstance(mapped_data['data_quality_score'], float)
        assert 0.0 <= mapped_data['data_quality_score'] <= 1.0


class TestBackwardCompatibility:
    """Test that refactored mapper maintains backward compatibility"""

    def test_mapper_output_structure_unchanged(self):
        """Test that output structure matches what existing code expects"""
        mapper = SupplierDataMapper()
        mock_supplier = MockSupplierForMapping('test')

        test_result = PartSearchResult(
            supplier_part_number='TEST-123',
            part_name='Test Part',
            manufacturer='Test Mfg',
            description='Test description',
            pricing=[{'quantity': 1, 'price': 1.50}]
        )

        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=mock_supplier):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=test_result,
                supplier_name='test'
            )

        # Expected structure keys
        expected_keys = {
            'part_name',
            'supplier_part_number',
            'manufacturer',
            'description',
            'additional_properties',
            'last_enrichment_date',
            'enrichment_source',
            'data_quality_score'
        }

        assert all(key in mapped_data for key in expected_keys)
        assert isinstance(mapped_data['additional_properties'], dict)

    def test_pricing_data_normalization_still_works(self):
        """Test that pricing normalization still works after refactoring"""
        mapper = SupplierDataMapper()
        mock_supplier = MockSupplierForMapping('test')

        test_result = PartSearchResult(
            supplier_part_number='TEST-123',
            pricing=[
                {'quantity': 1, 'price': 1.50},
                {'quantity': 10, 'price': 1.25},
                {'quantity': 100, 'price': 1.00}
            ]
        )

        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=mock_supplier):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=test_result,
                supplier_name='test'
            )

        # Should have pricing tiers for history
        assert 'pricing_tiers_for_history' in mapped_data
        assert 'tiers' in mapped_data['pricing_tiers_for_history']
        assert len(mapped_data['pricing_tiers_for_history']['tiers']) == 3


class TestNoHardcodingVerification:
    """Verify that NO supplier names are hardcoded anywhere in the mapper"""

    def test_no_supplier_names_in_mapper_init(self):
        """Test that __init__ has no hardcoded supplier mappings"""
        import inspect
        from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper

        init_source = inspect.getsource(SupplierDataMapper.__init__)

        # Should NOT have supplier_specific_mappers dictionary anymore
        assert 'supplier_specific_mappers' not in init_source
        assert "'lcsc':" not in init_source.lower()
        assert "'digikey':" not in init_source.lower()
        assert "'mcmaster-carr':" not in init_source.lower()

    def test_mapping_is_purely_dynamic(self):
        """Test that all mapping is purely dynamic through get_supplier()"""
        mapper = SupplierDataMapper()

        # The mapper should work with a supplier name that was NEVER hardcoded
        future_supplier = MockSupplierForMapping('future-supplier-2030')
        test_result = PartSearchResult(supplier_part_number='FUTURE-123')

        with patch('MakerMatrix.services.data.supplier_data_mapper.get_supplier', return_value=future_supplier):
            mapped_data = mapper.map_supplier_result_to_part_data(
                supplier_result=test_result,
                supplier_name='future-supplier-2030'
            )

        # Should work perfectly without any prior knowledge of this supplier
        assert mapped_data['supplier_part_number'] == 'FUTURE-123'
        assert 'future-supplier-2030_custom_field' in mapped_data['additional_properties']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
