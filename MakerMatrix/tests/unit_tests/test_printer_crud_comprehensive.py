"""
Comprehensive Printer Management CRUD Testing Suite
Tests all printer management operations including configuration, discovery, and settings
Part of extended testing validation following Phase 2 Backend Cleanup
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image

from MakerMatrix.services.printer.modern_printer_service import ModernPrinterService
from MakerMatrix.printers.base import (
    BasePrinter,
    PrinterInfo,
    PrinterCapability,
    PrinterStatus,
    PrintJobResult,
    PrinterNotFoundError,
    PrinterError,
)
from MakerMatrix.printers.drivers.mock import MockPrinter
from MakerMatrix.models.models import PartModel
from MakerMatrix.tests.unit_tests.test_database import create_test_db


class TestPrinterCRUDOperations:
    """Test comprehensive CRUD operations for printer management"""

    def setup_method(self):
        """Set up test database and services for each test"""
        self.test_db = create_test_db()
        self.printer_service = ModernPrinterService()

    def teardown_method(self):
        """Clean up after each test"""
        self.test_db.close()

    def test_printer_creation_and_registration(self):
        """Test creating and registering new printers"""
        # Create test printer
        test_printer = MockPrinter(
            printer_id="test_printer_001", name="Test Printer 001", model="Brother QL-800", connection_type="USB"
        )

        # Test printer registration
        printer_id = self.printer_service.add_printer(test_printer)
        assert printer_id == "test_printer_001"

        # Verify printer was registered
        registered_printers = self.printer_service.list_printers()
        assert "test_printer_001" in registered_printers

        # Test retrieving registered printer
        retrieved_printer = self.printer_service.get_printer("test_printer_001")
        assert retrieved_printer == test_printer

        print("✅ Printer creation and registration validated")

    def test_printer_configuration_management(self):
        """Test printer configuration CRUD operations"""
        # Create printer with configuration
        printer_config = {
            "dpi": 300,
            "scaling_factor": 1.2,
            "default_label_size": "29x90",
            "print_quality": "high",
            "paper_type": "continuous",
            "cut_mode": "auto",
            "darkness": 5,
            "speed": 3,
        }

        test_printer = MockPrinter(
            printer_id="config_test_printer",
            name="Config Test Printer",
            model="Brother QL-820NWB",
            connection_type="Network",
            config=printer_config,
        )

        # Test configuration creation
        self.printer_service.add_printer(test_printer)

        # Test configuration reading
        retrieved_printer = self.printer_service.get_printer("config_test_printer")
        assert retrieved_printer.get_config() == printer_config

        # Test configuration update
        updated_config = printer_config.copy()
        updated_config["dpi"] = 600
        updated_config["scaling_factor"] = 1.5

        retrieved_printer.update_config(updated_config)
        assert retrieved_printer.get_config()["dpi"] == 600
        assert retrieved_printer.get_config()["scaling_factor"] == 1.5

        # Test configuration validation
        invalid_config = {"dpi": "invalid", "scaling_factor": -1}
        with pytest.raises(ValueError):
            retrieved_printer.update_config(invalid_config)

        print("✅ Printer configuration management validated")

    def test_printer_discovery_and_detection(self):
        """Test printer discovery and auto-detection"""
        # Mock printer discovery
        discovered_printers = [
            {
                "printer_id": "discovered_printer_1",
                "name": "Network Printer 1",
                "model": "Brother QL-800",
                "connection_type": "Network",
                "ip_address": "192.168.1.71",
                "port": 9100,
                "status": "online",
            },
            {
                "printer_id": "discovered_printer_2",
                "name": "USB Printer 2",
                "model": "Brother QL-820NWB",
                "connection_type": "USB",
                "device_path": "/dev/usb/lp0",
                "status": "online",
            },
        ]

        # Test discovery functionality
        for printer_info in discovered_printers:
            discovered_printer = MockPrinter(
                printer_id=printer_info["printer_id"],
                name=printer_info["name"],
                model=printer_info["model"],
                connection_type=printer_info["connection_type"],
            )

            # Test auto-registration of discovered printers
            self.printer_service.add_printer(discovered_printer)

            # Verify printer was discovered and registered
            printers = self.printer_service.list_printers()
            assert printer_info["printer_id"] in printers

        # Test printer detection with specific IP
        network_printer = MockPrinter(
            printer_id="network_printer_ip",
            name="Network Printer IP",
            model="Brother QL-800",
            connection_type="Network",
            ip_address="192.168.1.71",
            port=9100,
        )

        self.printer_service.add_printer(network_printer)
        retrieved = self.printer_service.get_printer("network_printer_ip")
        assert retrieved.ip_address == "192.168.1.71"
        assert retrieved.port == 9100

        print("✅ Printer discovery and detection validated")

    def test_printer_status_management(self):
        """Test printer status monitoring and management"""
        # Create printer for status testing
        status_printer = MockPrinter(
            printer_id="status_test_printer", name="Status Test Printer", model="Brother QL-800"
        )

        self.printer_service.add_printer(status_printer)

        # Test status retrieval
        status = status_printer.get_status()
        assert isinstance(status, PrinterStatus)
        assert status.printer_id == "status_test_printer"

        # Test status updates
        status_printer.set_status("online")
        assert status_printer.get_status().status == "online"

        status_printer.set_status("offline")
        assert status_printer.get_status().status == "offline"

        # Test error status
        status_printer.set_status("error")
        assert status_printer.get_status().status == "error"

        # Test status with error details
        status_printer.set_error("Paper jam detected")
        status = status_printer.get_status()
        assert status.error_message == "Paper jam detected"

        print("✅ Printer status management validated")

    def test_printer_capability_management(self):
        """Test printer capability detection and management"""
        # Create printer with specific capabilities
        capable_printer = MockPrinter(
            printer_id="capable_printer",
            name="Capable Printer",
            model="Brother QL-820NWB",
            capabilities=[
                PrinterCapability.TEXT_PRINTING,
                PrinterCapability.QR_CODE_PRINTING,
                PrinterCapability.BARCODE_PRINTING,
                PrinterCapability.IMAGE_PRINTING,
                PrinterCapability.MULTI_SIZE_LABELS,
            ],
        )

        self.printer_service.add_printer(capable_printer)

        # Test capability querying
        capabilities = capable_printer.get_capabilities()
        assert PrinterCapability.TEXT_PRINTING in capabilities
        assert PrinterCapability.QR_CODE_PRINTING in capabilities
        assert PrinterCapability.BARCODE_PRINTING in capabilities
        assert PrinterCapability.IMAGE_PRINTING in capabilities
        assert PrinterCapability.MULTI_SIZE_LABELS in capabilities

        # Test capability checking
        assert capable_printer.has_capability(PrinterCapability.TEXT_PRINTING)
        assert capable_printer.has_capability(PrinterCapability.QR_CODE_PRINTING)
        assert not capable_printer.has_capability(PrinterCapability.BLUETOOTH_CONNECTIVITY)

        # Test supported label sizes
        supported_sizes = capable_printer.get_supported_label_sizes()
        assert isinstance(supported_sizes, list)
        assert len(supported_sizes) > 0

        print("✅ Printer capability management validated")

    def test_printer_queue_management(self):
        """Test printer job queue management"""
        # Create printer for queue testing
        queue_printer = MockPrinter(printer_id="queue_test_printer", name="Queue Test Printer", model="Brother QL-800")

        self.printer_service.add_printer(queue_printer)

        # Test queue operations
        queue = queue_printer.get_print_queue()
        assert isinstance(queue, list)
        initial_queue_size = len(queue)

        # Test adding jobs to queue (simulated)
        test_jobs = [
            {"job_id": "job_001", "type": "text", "content": "Test Label 1"},
            {"job_id": "job_002", "type": "qr", "content": "QR Test Data"},
            {"job_id": "job_003", "type": "text", "content": "Test Label 2"},
        ]

        for job in test_jobs:
            queue_printer.add_print_job(job)

        # Verify jobs were added
        updated_queue = queue_printer.get_print_queue()
        assert len(updated_queue) == initial_queue_size + 3

        # Test queue processing
        processed_jobs = queue_printer.process_print_queue()
        assert len(processed_jobs) == 3

        # Test queue clearing
        queue_printer.clear_print_queue()
        cleared_queue = queue_printer.get_print_queue()
        assert len(cleared_queue) == 0

        print("✅ Printer queue management validated")

    def test_printer_settings_persistence(self):
        """Test printer settings persistence and recovery"""
        # Create printer with settings
        settings_printer = MockPrinter(
            printer_id="settings_test_printer", name="Settings Test Printer", model="Brother QL-800"
        )

        # Test settings creation
        printer_settings = {
            "default_label_size": "62x29",
            "print_quality": "high",
            "auto_cut": True,
            "darkness": 7,
            "speed": 2,
            "orientation": "landscape",
        }

        settings_printer.save_settings(printer_settings)
        self.printer_service.add_printer(settings_printer)

        # Test settings retrieval
        retrieved_settings = settings_printer.get_settings()
        assert retrieved_settings["default_label_size"] == "62x29"
        assert retrieved_settings["print_quality"] == "high"
        assert retrieved_settings["auto_cut"] == True
        assert retrieved_settings["darkness"] == 7

        # Test settings update
        updated_settings = retrieved_settings.copy()
        updated_settings["darkness"] = 5
        updated_settings["speed"] = 4

        settings_printer.update_settings(updated_settings)

        # Verify settings were updated
        final_settings = settings_printer.get_settings()
        assert final_settings["darkness"] == 5
        assert final_settings["speed"] == 4

        # Test settings reset
        settings_printer.reset_settings()
        reset_settings = settings_printer.get_settings()
        assert reset_settings != final_settings  # Should be different after reset

        print("✅ Printer settings persistence validated")

    def test_printer_removal_and_cleanup(self):
        """Test printer removal and cleanup operations"""
        # Create multiple printers for removal testing
        printers_to_remove = [
            MockPrinter(printer_id="remove_test_1", name="Remove Test 1"),
            MockPrinter(printer_id="remove_test_2", name="Remove Test 2"),
            MockPrinter(printer_id="remove_test_3", name="Remove Test 3"),
        ]

        # Add printers to service
        for printer in printers_to_remove:
            self.printer_service.add_printer(printer)

        # Verify printers were added
        initial_count = len(self.printer_service.list_printers())
        assert initial_count >= 3

        # Test individual printer removal
        success = self.printer_service.remove_printer("remove_test_1")
        assert success == True

        # Verify printer was removed
        remaining_printers = self.printer_service.list_printers()
        assert "remove_test_1" not in remaining_printers
        assert len(remaining_printers) == initial_count - 1

        # Test removal of non-existent printer
        success = self.printer_service.remove_printer("nonexistent_printer")
        assert success == False

        # Test bulk removal
        bulk_remove_ids = ["remove_test_2", "remove_test_3"]
        for printer_id in bulk_remove_ids:
            success = self.printer_service.remove_printer(printer_id)
            assert success == True

        # Verify bulk removal
        final_printers = self.printer_service.list_printers()
        for printer_id in bulk_remove_ids:
            assert printer_id not in final_printers

        print("✅ Printer removal and cleanup validated")

    def test_printer_error_handling(self):
        """Test printer error handling and recovery"""
        # Create error-prone printer
        error_printer = MockPrinter(printer_id="error_test_printer", name="Error Test Printer", simulate_errors=True)

        self.printer_service.add_printer(error_printer)

        # Test error detection
        error_printer.simulate_paper_out()
        status = error_printer.get_status()
        assert status.status == "error"
        assert "paper" in status.error_message.lower()

        # Test error recovery
        error_printer.clear_error()
        status = error_printer.get_status()
        assert status.status != "error"

        # Test different error types
        error_types = ["paper_jam", "low_ink", "cover_open", "hardware_error"]
        for error_type in error_types:
            error_printer.simulate_error(error_type)
            status = error_printer.get_status()
            assert status.status == "error"
            assert error_type.replace("_", " ") in status.error_message.lower()

            # Clear error for next test
            error_printer.clear_error()

        print("✅ Printer error handling validated")

    def test_printer_connection_management(self):
        """Test printer connection management"""
        # Test different connection types
        connection_types = [
            {"type": "USB", "config": {"device_path": "/dev/usb/lp0", "baud_rate": 9600}},
            {"type": "Network", "config": {"ip_address": "192.168.1.71", "port": 9100}},
            {"type": "Bluetooth", "config": {"mac_address": "00:11:22:33:44:55", "channel": 1}},
        ]

        for i, connection in enumerate(connection_types):
            # Create printer with specific connection type
            connection_printer = MockPrinter(
                printer_id=f"connection_test_{i}",
                name=f"Connection Test {i}",
                connection_type=connection["type"],
                **connection["config"],
            )

            self.printer_service.add_printer(connection_printer)

            # Test connection establishment
            connection_result = connection_printer.establish_connection()
            assert connection_result["success"] == True

            # Test connection status
            is_connected = connection_printer.is_connected()
            assert is_connected == True

            # Test connection termination
            disconnect_result = connection_printer.disconnect()
            assert disconnect_result["success"] == True

            # Verify disconnection
            is_connected = connection_printer.is_connected()
            assert is_connected == False

        print("✅ Printer connection management validated")

    def test_printer_performance_metrics(self):
        """Test printer performance monitoring"""
        # Create printer for performance testing
        perf_printer = MockPrinter(
            printer_id="performance_test_printer", name="Performance Test Printer", model="Brother QL-800"
        )

        self.printer_service.add_printer(perf_printer)

        # Test performance metrics collection
        metrics = perf_printer.get_performance_metrics()
        assert isinstance(metrics, dict)

        # Expected metrics
        expected_metrics = ["jobs_printed", "print_time_average", "success_rate", "error_count", "uptime_hours"]

        for metric in expected_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))

        # Test performance tracking
        initial_jobs = metrics["jobs_printed"]

        # Simulate printing jobs
        for i in range(5):
            perf_printer.simulate_print_job(f"test_job_{i}")

        # Check updated metrics
        updated_metrics = perf_printer.get_performance_metrics()
        assert updated_metrics["jobs_printed"] == initial_jobs + 5

        # Test metric reset
        perf_printer.reset_performance_metrics()
        reset_metrics = perf_printer.get_performance_metrics()
        assert reset_metrics["jobs_printed"] == 0

        print("✅ Printer performance metrics validated")

    def test_printer_bulk_operations(self):
        """Test bulk printer operations"""
        # Create multiple printers for bulk testing
        bulk_printers = []
        for i in range(10):
            printer = MockPrinter(
                printer_id=f"bulk_printer_{i:02d}", name=f"Bulk Printer {i:02d}", model="Brother QL-800"
            )
            bulk_printers.append(printer)
            self.printer_service.add_printer(printer)

        # Test bulk status check
        all_printers = self.printer_service.list_printers()
        bulk_printer_ids = [p_id for p_id in all_printers if p_id.startswith("bulk_printer_")]
        assert len(bulk_printer_ids) == 10

        # Test bulk configuration update
        bulk_config = {"dpi": 300, "scaling_factor": 1.0, "default_label_size": "29x90"}

        for printer_id in bulk_printer_ids:
            printer = self.printer_service.get_printer(printer_id)
            printer.update_config(bulk_config)

            # Verify config was updated
            updated_config = printer.get_config()
            assert updated_config["dpi"] == 300
            assert updated_config["scaling_factor"] == 1.0

        # Test bulk removal
        removed_count = 0
        for printer_id in bulk_printer_ids:
            success = self.printer_service.remove_printer(printer_id)
            if success:
                removed_count += 1

        assert removed_count == 10

        # Verify all bulk printers were removed
        final_printers = self.printer_service.list_printers()
        for printer_id in bulk_printer_ids:
            assert printer_id not in final_printers

        print("✅ Printer bulk operations validated")


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
