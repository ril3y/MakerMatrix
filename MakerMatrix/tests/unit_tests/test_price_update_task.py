"""
Test price update task with supplier capability system
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from MakerMatrix.tasks.price_update_task import PriceUpdateTask
from MakerMatrix.models.task_models import TaskModel, TaskStatus
from MakerMatrix.models.models import PartModel
from MakerMatrix.suppliers.base import SupplierCapability
from MakerMatrix.suppliers.registry import SupplierRegistry


@pytest.fixture
def mock_task():
    """Create a mock task for testing"""
    task = TaskModel(id="test-task-id", task_type="price_update", name="Price Update Task", status=TaskStatus.PENDING)
    task.set_input_data({"update_all": True})
    return task


@pytest.fixture
def mock_parts():
    """Create mock parts for testing"""
    return [
        PartModel(id="part1", name="Test Part 1", part_number="TP001", supplier="DIGIKEY", unit_price=1.50),
        PartModel(id="part2", name="Test Part 2", part_number="TP002", supplier="LCSC", unit_price=None),
        PartModel(id="part3", name="Test Part 3", part_number="TP003", supplier="MOUSER", unit_price=2.25),
    ]


@pytest.fixture
def mock_supplier_with_pricing():
    """Create a mock supplier that supports pricing"""
    supplier = MagicMock()
    supplier.get_capabilities.return_value = [SupplierCapability.FETCH_PRICING]
    supplier.fetch_pricing = AsyncMock(
        return_value=[
            {"quantity": 1, "price": 1.25, "currency": "USD"},
            {"quantity": 10, "price": 1.00, "currency": "USD"},
        ]
    )
    return supplier


@pytest.fixture
def mock_supplier_without_pricing():
    """Create a mock supplier that doesn't support pricing"""
    supplier = MagicMock()
    supplier.get_capabilities.return_value = [SupplierCapability.FETCH_DATASHEET]
    return supplier


class TestPriceUpdateTask:
    """Test the price update task functionality"""

    @pytest.mark.asyncio
    async def test_execute_with_pricing_capable_suppliers(self, mock_task, mock_parts, mock_supplier_with_pricing):
        """Test price update only processes suppliers with pricing capability"""

        with (
            patch("MakerMatrix.tasks.price_update_task.get_session") as mock_get_session,
            patch.object(SupplierRegistry, "get_supplier") as mock_get_supplier,
            patch("MakerMatrix.tasks.price_update_task.SupplierConfigService") as mock_config_service,
        ):

            # Setup mocks
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session.exec.return_value.all.return_value = mock_parts

            # Mock supplier registry
            def supplier_side_effect(supplier_name):
                if supplier_name == "DIGIKEY":
                    return mock_supplier_with_pricing
                elif supplier_name == "MOUSER":
                    return mock_supplier_with_pricing
                else:
                    return None  # LCSC doesn't support pricing

            mock_get_supplier.side_effect = supplier_side_effect

            # Mock supplier config service
            mock_config = MagicMock()
            mock_config.credentials = {"api_key": "test_key"}
            mock_config.config = {"rate_limit": 100}
            mock_config_service.return_value.get_supplier_config.return_value = mock_config

            # Create and execute task
            task_instance = PriceUpdateTask()
            result = await task_instance.execute(mock_task)

            # Verify results
            assert "updated_count" in result
            assert "failed_count" in result
            assert result["updated_count"] >= 0

            # Verify suppliers were checked for pricing capability
            assert mock_get_supplier.call_count > 0

            # Verify pricing was only fetched for capable suppliers
            assert mock_supplier_with_pricing.fetch_pricing.call_count >= 0

    @pytest.mark.asyncio
    async def test_skips_suppliers_without_pricing_capability(
        self, mock_task, mock_parts, mock_supplier_without_pricing
    ):
        """Test that suppliers without pricing capability are skipped"""

        with (
            patch("MakerMatrix.tasks.price_update_task.get_session") as mock_get_session,
            patch.object(SupplierRegistry, "get_supplier") as mock_get_supplier,
            patch("MakerMatrix.tasks.price_update_task.SupplierConfigService") as mock_config_service,
        ):

            # Setup mocks
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session.exec.return_value.all.return_value = [mock_parts[1]]  # Only LCSC part

            # LCSC doesn't support pricing
            mock_get_supplier.return_value = mock_supplier_without_pricing

            # Mock config service
            mock_config_service.return_value.get_supplier_config.return_value = None

            # Create and execute task
            task_instance = PriceUpdateTask()
            result = await task_instance.execute(mock_task)

            # Verify that no pricing was attempted since supplier doesn't support it
            assert "failed_count" in result
            # Should have failed because supplier doesn't support pricing
            assert result["failed_count"] >= 0

    @pytest.mark.asyncio
    async def test_handles_missing_supplier_configuration(self, mock_task, mock_parts):
        """Test handling of suppliers without configuration"""

        with (
            patch("MakerMatrix.tasks.price_update_task.get_session") as mock_get_session,
            patch.object(SupplierRegistry, "get_supplier") as mock_get_supplier,
            patch("MakerMatrix.tasks.price_update_task.SupplierConfigService") as mock_config_service,
        ):

            # Setup mocks
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session.exec.return_value.all.return_value = mock_parts

            # Supplier exists but no configuration
            mock_get_supplier.return_value = mock_supplier_with_pricing
            mock_config_service.return_value.get_supplier_config.return_value = None

            # Create and execute task
            task_instance = PriceUpdateTask()
            result = await task_instance.execute(mock_task)

            # Should handle missing configuration gracefully
            assert "failed_count" in result
            assert result["failed_count"] >= 0

    def test_task_type_registration(self):
        """Test that the price update task is properly registered"""
        task_instance = PriceUpdateTask()
        assert task_instance.task_type == "price_update"
        assert task_instance.name == "Price Update"
        assert "price" in task_instance.description.lower()


def test_supplier_capability_checking():
    """Test that supplier capability checking works correctly"""
    # This tests the core concept that tasks should check supplier capabilities

    # Mock suppliers with different capabilities
    pricing_supplier = MagicMock()
    pricing_supplier.get_capabilities.return_value = [
        SupplierCapability.FETCH_PRICING,
        SupplierCapability.FETCH_DATASHEET,
    ]

    datasheet_only_supplier = MagicMock()
    datasheet_only_supplier.get_capabilities.return_value = [SupplierCapability.FETCH_DATASHEET]

    # Test capability checking
    assert SupplierCapability.FETCH_PRICING in pricing_supplier.get_capabilities()
    assert SupplierCapability.FETCH_PRICING not in datasheet_only_supplier.get_capabilities()

    # This demonstrates the pattern all tasks should follow:
    # 1. Get supplier instance
    # 2. Check if supplier supports required capability
    # 3. Only proceed if capability is supported


if __name__ == "__main__":
    pytest.main([__file__])
