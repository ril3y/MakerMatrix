"""
Test decimal to float conversion in order models.
"""

import pytest
from decimal import Decimal
from MakerMatrix.models.order_models import OrderModel, OrderItemModel


class TestDecimalConversion:
    """Test that Decimal values are properly converted to floats during serialization."""
    
    def test_order_model_serialization_no_warnings(self):
        """Test that order model serialization doesn't produce Decimal warnings."""
        order = OrderModel(
            order_number="TEST-002",
            supplier="Test Supplier 2",
            subtotal=Decimal('99.99'),
            tax=Decimal('8.00'),
            shipping=Decimal('0.00'),
            total=Decimal('107.99')
        )
        
        # This should not produce any Pydantic warnings about Decimals
        serialized = order.model_dump()
        
        # All price fields should be floats in the serialized output
        assert isinstance(serialized['subtotal'], float)
        assert isinstance(serialized['tax'], float)
        assert isinstance(serialized['shipping'], float)
        assert isinstance(serialized['total'], float)
    
    def test_order_item_serialization_no_warnings(self):
        """Test that order item serialization doesn't produce Decimal warnings."""
        order_item = OrderItemModel(
            order_id="test-order-id-2",
            supplier_part_number="TEST-PART-002",
            quantity_ordered=5,
            unit_price=Decimal('4.75'),
            extended_price=Decimal('23.75')
        )
        
        # This should not produce any Pydantic warnings about Decimals
        serialized = order_item.model_dump()
        
        # Price fields should be floats in the serialized output
        assert isinstance(serialized['unit_price'], float)
        assert isinstance(serialized['extended_price'], float)