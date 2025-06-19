"""
Unit tests for Bolt Depot Supplier

Tests the web scraping functionality for BoltDepot.com including
product details extraction, pricing parsing, and image URL handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from bs4 import BeautifulSoup

from MakerMatrix.suppliers.bolt_depot import BoltDepotSupplier
from MakerMatrix.suppliers.base import SupplierCapability


class TestBoltDepotSupplier:
    """Test cases for Bolt Depot supplier implementation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.supplier = BoltDepotSupplier()
        self.supplier.configure({}, {
            'base_url': 'https://boltdepot.com',
            'request_delay_seconds': 0.1,  # Fast for testing
            'timeout_seconds': 30,
            'user_agent': 'MakerMatrix/Test',
            'enable_caching': False
        })
    
    def test_supplier_info(self):
        """Test supplier information"""
        info = self.supplier.get_supplier_info()
        assert info.name == "bolt-depot"
        assert info.display_name == "Bolt Depot"
        assert "fastener" in info.description.lower()
        assert info.website_url == "https://boltdepot.com"
        assert not info.supports_oauth
    
    def test_capabilities(self):
        """Test supplier capabilities"""
        caps = self.supplier.get_capabilities()
        expected_caps = [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_PRICING,
            SupplierCapability.FETCH_IMAGE,
            SupplierCapability.FETCH_SPECIFICATIONS
        ]
        assert set(caps) == set(expected_caps)
    
    def test_credential_schema(self):
        """Test credential schema (should be empty for public scraping)"""
        schema = self.supplier.get_credential_schema()
        assert len(schema) == 0
    
    def test_configuration_schema(self):
        """Test configuration schema"""
        schema = self.supplier.get_configuration_schema()
        field_names = [field.name for field in schema]
        
        expected_fields = [
            'base_url',
            'request_delay_seconds',
            'timeout_seconds',
            'user_agent',
            'enable_caching'
        ]
        
        assert set(field_names) == set(expected_fields)
    
    @pytest.mark.asyncio
    async def test_authentication(self):
        """Test authentication (should always succeed for public scraping)"""
        result = await self.supplier.authenticate()
        assert result is True
    
    def test_extract_product_details(self):
        """Test product details extraction from HTML"""
        html = '''
        <table class="product-details-table">
            <tbody>
                <tr><th colspan="2">Product details</th></tr>
                <tr>
                    <td class="property-name">Bolt Depot product#</td>
                    <td class="property-value">8981</td>
                </tr>
                <tr>
                    <td class="property-name">Material</td>
                    <td class="property-value">
                        Stainless steel
                        <div class="value-message">Description here</div>
                    </td>
                </tr>
                <tr>
                    <td class="property-name">Diameter</td>
                    <td class="property-value">5/16"</td>
                </tr>
            </tbody>
        </table>
        '''
        
        soup = BeautifulSoup(html, 'html.parser')
        details = self.supplier._extract_product_details(soup)
        
        assert details['Bolt Depot product#'] == '8981'
        assert details['Material'] == 'Stainless steel'
        assert details['Diameter'] == '5/16"'
    
    def test_extract_pricing(self):
        """Test pricing extraction from HTML"""
        html = '''
        <table id="product-list-table">
            <tbody>
                <tr id="p8981" class="product-table-row">
                    <td class="cell-price cell-price-multiple">
                        <span class="price-break">
                            $0.25 <span class="perQty">/ ea</span>
                        </span>
                    </td>
                    <td class="cell-price cell-price-multiple">
                        <span class="price-break">
                            $19.13 <span class="perQty">/ 100</span>
                        </span>
                    </td>
                    <td class="cell-price cell-price-multiple">
                        <span class="price-break">
                            $168.00 <span class="perQty">/ 1,000</span>
                        </span>
                    </td>
                </tr>
            </tbody>
        </table>
        '''
        
        soup = BeautifulSoup(html, 'html.parser')
        pricing = self.supplier._extract_pricing(soup, '8981')
        
        assert pricing is not None
        assert len(pricing) == 3
        
        # Check individual price breaks
        assert pricing[0]['quantity'] == 1
        assert pricing[0]['price'] == 0.25
        assert pricing[0]['currency'] == 'USD'
        
        assert pricing[1]['quantity'] == 100
        assert pricing[1]['price'] == 19.13
        
        assert pricing[2]['quantity'] == 1000
        assert pricing[2]['price'] == 168.00
    
    def test_extract_image_url(self):
        """Test image URL extraction"""
        html = '''
        <div>
            <img src="images/bdlogo-normal.png" alt="Logo">
            <img src="images/catalog/hex-bolt-full-thread.png" alt="Full thread hex bolt">
            <img src="other-image.jpg" alt="Other">
        </div>
        '''
        
        soup = BeautifulSoup(html, 'html.parser')
        image_url = self.supplier._extract_image_url(soup)
        
        assert image_url == "https://boltdepot.com/images/catalog/hex-bolt-full-thread.png"
    
    def test_build_description(self):
        """Test description building from product details"""
        details = {
            'Category': 'Hex bolts',
            'Subcategory': 'Hex bolts',
            'Material': 'Stainless steel',
            'Diameter': '5/16"',
            'Length': '3/8"',
            'Thread count': '18'
        }
        
        description = self.supplier._build_description(details)
        
        assert 'Hex bolts' in description
        assert 'Stainless steel' in description
        assert '5/16" x 3/8"' in description
        assert '18 TPI' in description
    
    def test_build_description_minimal(self):
        """Test description building with minimal details"""
        details = {
            'Category': 'Fasteners'
        }
        
        description = self.supplier._build_description(details)
        assert description == 'Fasteners'
    
    def test_build_description_empty(self):
        """Test description building with no details"""
        details = {}
        
        description = self.supplier._build_description(details)
        assert description == 'Fastener'
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_get_part_details_success(self, mock_get):
        """Test successful part details retrieval"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='''
        <html>
            <table class="product-details-table">
                <tbody>
                    <tr><td class="property-name">Category</td><td class="property-value">Hex bolts</td></tr>
                    <tr><td class="property-name">Material</td><td class="property-value">Steel</td></tr>
                </tbody>
            </table>
            <table id="product-list-table">
                <tbody>
                    <tr id="p8981">
                        <td class="cell-price">
                            <span class="price-break">$0.25 <span class="perQty">/ ea</span></span>
                        </td>
                    </tr>
                </tbody>
            </table>
            <img src="images/catalog/test-image.png" alt="Test bolt">
        </html>
        ''')
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.supplier.get_part_details('8981')
        
        assert result is not None
        assert result.supplier_part_number == '8981'
        assert result.category == 'Hex bolts'
        assert result.manufacturer == 'Bolt Depot'
        assert 'Steel' in result.description
        assert result.pricing is not None
        assert len(result.pricing) == 1
        assert result.pricing[0]['price'] == 0.25
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_get_part_details_not_found(self, mock_get):
        """Test part details retrieval for non-existent part"""
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.supplier.get_part_details('99999')
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_test_connection_success(self, mock_get):
        """Test successful connection test"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='<html><title>Bolt Depot - Fasteners</title></html>')
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.supplier.test_connection()
        
        assert result['success'] is True
        assert 'Connection successful' in result['message']
        assert result['details']['status_code'] == 200
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_test_connection_failure(self, mock_get):
        """Test connection test failure"""
        mock_response = AsyncMock()
        mock_response.status = 500
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.supplier.test_connection()
        
        assert result['success'] is False
        assert 'HTTP error: 500' in result['message']
    
    @pytest.mark.asyncio
    async def test_search_parts_numeric_query(self):
        """Test search with numeric query (should try part lookup)"""
        with patch.object(self.supplier, 'get_part_details') as mock_get_details:
            mock_part = Mock()
            mock_get_details.return_value = mock_part
            
            result = await self.supplier.search_parts('8981')
            
            mock_get_details.assert_called_once_with('8981')
            assert result == [mock_part]
    
    @pytest.mark.asyncio
    async def test_search_parts_non_numeric_query(self):
        """Test search with non-numeric query (should return empty)"""
        result = await self.supplier.search_parts('hex bolt')
        assert result == []
    
    def test_get_rate_limit_delay(self):
        """Test rate limit delay configuration"""
        delay = self.supplier.get_rate_limit_delay()
        assert delay == 0.1  # As configured in setup_method
    
    @pytest.mark.asyncio
    async def test_invalid_part_number(self):
        """Test handling of invalid part numbers"""
        result = await self.supplier.get_part_details('invalid')
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])