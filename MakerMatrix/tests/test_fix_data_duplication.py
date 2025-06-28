#!/usr/bin/env python3
"""
Test to demonstrate and fix the data duplication issue in enrichment results.
"""

import pytest
import json
from unittest.mock import Mock, patch

from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.models.models import engine


class TestFixDataDuplication:
    """Test fixes for data duplication in enrichment results"""

    def test_current_duplication_issue(self):
        """Demonstrate the current duplication problem"""
        
        # Mock part similar to the user's example
        part = Mock()
        part.additional_properties = {}
        
        # Mock enrichment results that would cause duplication
        enrichment_results = {
            'fetch_pricing': {
                'success': True,
                'unit_price': 2.039545,
                'currency': 'USD',
                'price_breaks': [{'quantity': 1, 'unit_price': 2.039545}]
            },
            'fetch_specifications': {
                'success': True,
                'specifications': [
                    {'name': 'package', 'value': 'QFN-20'},
                    {'name': 'manufacturer', 'value': 'Microchip'}
                ]
            }
        }
        
        # Simulate current behavior
        part.additional_properties['enrichment_results'] = enrichment_results
        
        # Then the _update_part_from_enrichment_results also stores separately
        if 'fetch_pricing' in enrichment_results:
            part.additional_properties['pricing_info'] = enrichment_results['fetch_pricing']
        
        if 'fetch_specifications' in enrichment_results:
            part.additional_properties['specifications_info'] = enrichment_results['fetch_specifications']
        
        # Show the duplication
        print("\n=== Current Duplication Issue ===")
        print("Pricing stored in:")
        print(f"  1. enrichment_results.fetch_pricing: {bool(part.additional_properties['enrichment_results']['fetch_pricing'])}")
        print(f"  2. pricing_info: {bool(part.additional_properties['pricing_info'])}")
        
        print("Specifications stored in:")
        print(f"  1. enrichment_results.fetch_specifications: {bool(part.additional_properties['enrichment_results']['fetch_specifications'])}")
        print(f"  2. specifications_info: {bool(part.additional_properties['specifications_info'])}")
        
        # Calculate data size (rough estimate)
        json_str = json.dumps(part.additional_properties)
        print(f"Total JSON size: {len(json_str)} characters")
        
        # This test shows the problem exists
        assert 'enrichment_results' in part.additional_properties
        assert 'pricing_info' in part.additional_properties
        assert 'specifications_info' in part.additional_properties

    def test_proposed_fix_single_storage(self):
        """Demonstrate a cleaner approach with single storage"""
        
        part = Mock()
        part.additional_properties = {}
        
        # Store enrichment results in a single location
        enrichment_results = {
            'fetch_pricing': {
                'success': True,
                'unit_price': 2.039545,
                'currency': 'USD',
                'price_breaks': [{'quantity': 1, 'unit_price': 2.039545}]
            },
            'fetch_specifications': {
                'success': True,
                'specifications': [
                    {'name': 'package', 'value': 'QFN-20'},
                    {'name': 'manufacturer', 'value': 'Microchip'}
                ]
            }
        }
        
        # Store only in enrichment_results (no duplication)
        part.additional_properties['enrichment_results'] = enrichment_results
        
        # Store only essential fields at top level for quick access
        part.additional_properties['unit_price'] = enrichment_results['fetch_pricing']['unit_price']
        part.additional_properties['last_enrichment'] = '2025-06-18T10:00:00Z'
        
        print("\n=== Proposed Fix - Single Storage ===")
        print("Pricing stored in:")
        print(f"  1. enrichment_results.fetch_pricing: {bool(part.additional_properties['enrichment_results']['fetch_pricing'])}")
        print(f"  2. unit_price (quick access): {part.additional_properties['unit_price']}")
        
        # Calculate data size
        json_str = json.dumps(part.additional_properties)
        print(f"Total JSON size: {len(json_str)} characters")
        
        # Verify no duplication
        assert 'enrichment_results' in part.additional_properties
        assert 'pricing_info' not in part.additional_properties  # No duplication
        assert 'specifications_info' not in part.additional_properties  # No duplication
        assert part.additional_properties['unit_price'] == 2.039545  # Quick access preserved

    def test_optimized_storage_structure(self):
        """Test an optimized storage structure that reduces redundancy"""
        
        part = Mock()
        part.additional_properties = {}
        
        # Optimized structure - store only what's needed
        optimized_data = {
            'enrichment': {
                'last_updated': '2025-06-18T10:00:00Z',
                'supplier': 'LCSC',
                'capabilities_used': ['fetch_pricing', 'fetch_specifications', 'fetch_datasheet'],
                'results': {
                    'pricing': {
                        'unit_price': 2.039545,
                        'currency': 'USD',
                        'min_order_qty': 1
                    },
                    'specifications': [
                        {'name': 'package', 'value': 'QFN-20'},
                        {'name': 'manufacturer', 'value': 'Microchip'}
                    ],
                    'files': {
                        'datasheet_url': 'https://example.com/datasheet.pdf',
                        'datasheet_local': '/static/datasheets/uuid.pdf',
                        'image_url': 'https://example.com/image.jpg', 
                        'image_local': '/static/images/part_image.jpg'
                    }
                }
            },
            # Quick access fields (no duplication of source data)
            'unit_price': 2.039545,
            'package': 'QFN-20'
        }
        
        part.additional_properties = optimized_data
        
        print("\n=== Optimized Storage Structure ===")
        json_str = json.dumps(part.additional_properties)
        print(f"Optimized JSON size: {len(json_str)} characters")
        print("Data access patterns:")
        print(f"  Quick price access: {part.additional_properties['unit_price']}")
        print(f"  Full pricing data: {part.additional_properties['enrichment']['results']['pricing']}")
        print(f"  File locations: {list(part.additional_properties['enrichment']['results']['files'].keys())}")
        
        # Verify structure is clean
        assert 'enrichment' in part.additional_properties
        assert len(part.additional_properties['enrichment']['results']) == 3  # pricing, specs, files
        assert 'unit_price' in part.additional_properties  # Quick access
        
        # Verify no source/metadata duplication
        enrichment_str = json.dumps(part.additional_properties['enrichment'])
        assert enrichment_str.count('"supplier": "LCSC"') == 1  # Only stored once
        assert enrichment_str.count('"api_endpoint"') == 0  # Source metadata removed

    @pytest.mark.asyncio
    async def test_fix_implementation_suggestion(self):
        """Test a suggested fix for the enrichment handler"""
        
        part_repo = PartRepository(engine)
        part_service = PartService()
        handler = EnrichmentTaskHandlers(part_repo, part_service)
        
        # Mock part
        part = Mock()
        part.additional_properties = {}
        part.image_url = None
        part.description = None
        
        # Mock enrichment results with typical duplication
        enrichment_results = {
            'fetch_pricing': {
                'success': True,
                'unit_price': 2.039545,
                'currency': 'USD',
                'source': {
                    'supplier': 'LCSC',
                    'api_endpoint': 'https://api.lcsc.com',
                    'enriched_at': '2025-06-18T10:00:00Z'
                }
            },
            'fetch_datasheet': {
                'success': True,
                'datasheet_url': 'https://example.com/datasheet.pdf',
                'source': {
                    'supplier': 'LCSC', 
                    'api_endpoint': 'https://api.lcsc.com',
                    'enriched_at': '2025-06-18T10:00:00Z'
                }
            }
        }
        
        print("\n=== Testing Improved Handler Logic ===")
        
        # Simulate improved logic that removes duplication
        with patch.object(handler, '_update_part_from_enrichment_results') as mock_update:
            
            async def improved_update_logic(part_obj, results):
                """Improved logic that doesn't duplicate data"""
                
                # Store clean enrichment results (remove redundant source metadata)
                clean_results = {}
                for capability, result in results.items():
                    if isinstance(result, dict):
                        # Keep only essential data, remove verbose source metadata
                        clean_result = {k: v for k, v in result.items() if k != 'source'}
                        clean_results[capability] = clean_result
                
                # Store in single location
                if not part_obj.additional_properties:
                    part_obj.additional_properties = {}
                
                part_obj.additional_properties['enrichment_results'] = clean_results
                part_obj.additional_properties['last_enrichment'] = '2025-06-18T10:00:00Z'
                
                # Extract only essential fields for quick access (no full duplication)
                if 'fetch_pricing' in clean_results and clean_results['fetch_pricing'].get('success'):
                    part_obj.additional_properties['unit_price'] = clean_results['fetch_pricing']['unit_price']
                
                if 'fetch_datasheet' in clean_results and clean_results['fetch_datasheet'].get('success'):
                    part_obj.additional_properties['datasheet_url'] = clean_results['fetch_datasheet']['datasheet_url']
                
                # Set image_url on part object (not duplicated in additional_properties)
                if 'fetch_image' in clean_results and clean_results['fetch_image'].get('success'):
                    part_obj.image_url = clean_results['fetch_image'].get('primary_image_url')
            
            # Set the improved function
            mock_update.side_effect = improved_update_logic
            
            # Test the improved logic
            await handler._update_part_from_enrichment_results(part, enrichment_results)
            
            # Verify improved results
            print("Before improvement - would have:")
            print("  enrichment_results + pricing_info + datasheet duplicate data")
            
            print("After improvement - has:")
            print(f"  enrichment_results: {bool(part.additional_properties.get('enrichment_results'))}")
            print(f"  unit_price (quick access): {part.additional_properties.get('unit_price')}")
            print(f"  datasheet_url (quick access): {part.additional_properties.get('datasheet_url')}")
            print(f"  No pricing_info duplication: {'pricing_info' not in part.additional_properties}")
            
            # Verify no source metadata duplication
            json_str = json.dumps(part.additional_properties)
            source_count = json_str.count('"api_endpoint"')
            print(f"  Source metadata eliminated: {source_count == 0}")
            
            assert 'enrichment_results' in part.additional_properties
            assert 'unit_price' in part.additional_properties
            assert 'pricing_info' not in part.additional_properties  # No duplication
            assert source_count == 0  # Source metadata removed

    def test_calculate_storage_savings(self):
        """Calculate potential storage savings from fixing duplication"""
        
        # Simulate current approach (with duplication)
        current_data = {
            'enrichment_results': {
                'fetch_pricing': {
                    'success': True,
                    'unit_price': 2.039545,
                    'currency': 'USD',
                    'source': {'supplier': 'LCSC', 'api_endpoint': 'https://api.lcsc.com/long/endpoint/path'}
                },
                'fetch_specifications': {
                    'success': True,
                    'specifications': [{'name': 'package', 'value': 'QFN-20'}] * 10,  # Simulate multiple specs
                    'source': {'supplier': 'LCSC', 'api_endpoint': 'https://api.lcsc.com/long/endpoint/path'}
                }
            },
            'pricing_info': {  # DUPLICATE
                'success': True,
                'unit_price': 2.039545,
                'currency': 'USD',
                'source': {'supplier': 'LCSC', 'api_endpoint': 'https://api.lcsc.com/long/endpoint/path'}
            },
            'specifications_info': {  # DUPLICATE
                'success': True,
                'specifications': [{'name': 'package', 'value': 'QFN-20'}] * 10,
                'source': {'supplier': 'LCSC', 'api_endpoint': 'https://api.lcsc.com/long/endpoint/path'}
            }
        }
        
        # Optimized approach (no duplication)
        optimized_data = {
            'enrichment_results': {
                'fetch_pricing': {
                    'success': True,
                    'unit_price': 2.039545,
                    'currency': 'USD'
                },
                'fetch_specifications': {
                    'success': True,
                    'specifications': [{'name': 'package', 'value': 'QFN-20'}] * 10
                }
            },
            'last_enrichment': '2025-06-18T10:00:00Z',
            'unit_price': 2.039545  # Quick access only
        }
        
        current_size = len(json.dumps(current_data))
        optimized_size = len(json.dumps(optimized_data))
        savings = current_size - optimized_size
        savings_percent = (savings / current_size) * 100
        
        print(f"\n=== Storage Savings Analysis ===")
        print(f"Current approach: {current_size} characters")
        print(f"Optimized approach: {optimized_size} characters") 
        print(f"Savings: {savings} characters ({savings_percent:.1f}%)")
        print(f"For 1000 parts: {savings * 1000:,} characters saved")
        
        assert savings > 0, "Optimized approach should save storage"
        assert savings_percent > 20, "Should save at least 20% storage"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])