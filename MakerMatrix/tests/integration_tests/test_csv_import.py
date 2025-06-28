import pytest
import tempfile
import os
from datetime import datetime
from sqlmodel import Session, select
from MakerMatrix.database.db import get_session
from MakerMatrix.services.csv_import_service import csv_import_service
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.models.models import PartModel, PartOrderSummary
from MakerMatrix.models.order_models import OrderModel, OrderItemModel


class TestCSVImport:
    """Integration tests for CSV import functionality"""

    @pytest.fixture
    def sample_lcsc_csv(self):
        """Sample LCSC CSV content for testing"""
        return """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C1525,STM32F405RGT6,STMicroelectronics,STM32F405RGT6,LQFP-64_10x10x05P,ARM Microcontrollers - MCU,Yes,1,1,5.2300,5.23
C52923,C3216X7S2A335KT000N,TDK,C3216X7S2A335KT000N,1206,Multilayer Ceramic Capacitors MLCC - SMD/SMT,Yes,10,1,0.0648,0.65
C25804,JSM6207,JoulWatt,JSM6207,SOT-23-6,MOSFET,Yes,5,1,0.1234,0.62"""

    @pytest.fixture
    def sample_digikey_csv(self):
        """Sample DigiKey CSV content for testing"""
        return """Index,DigiKey Part #,Manufacturer Part Number,Description,Customer Reference,Quantity,Backorder,Unit Price,Extended Price
1,STM32F405RGT6CT-ND,STM32F405RGT6,"IC MCU 32BIT 1MB FLASH 64LQFP",REF001,2,0,6.45000,12.90
2,1276-1000-1-ND,C3216X7S2A335KT000N,"CAP CER 3.3UF 100V X7S 1206",REF002,20,0,0.08900,1.78"""

    def test_lcsc_filename_extraction(self):
        """Test LCSC filename pattern extraction"""
        # Test valid LCSC filename
        order_info = csv_import_service.extract_order_info_from_filename("LCSC_Exported__20241222_232705.csv")
        assert order_info is not None
        assert order_info['order_date'] == "2024-12-22"
        assert order_info['order_number'] == "232705"
        assert order_info['supplier'] == "LCSC"

        # Test invalid filename
        order_info = csv_import_service.extract_order_info_from_filename("random_file.csv")
        assert order_info is None

    def test_lcsc_csv_detection(self, sample_lcsc_csv):
        """Test LCSC CSV auto-detection"""
        detected_type = csv_import_service.detect_csv_type(sample_lcsc_csv)
        assert detected_type == "lcsc"

    def test_digikey_csv_detection(self, sample_digikey_csv):
        """Test DigiKey CSV auto-detection"""
        detected_type = csv_import_service.detect_csv_type(sample_digikey_csv)
        assert detected_type == "digikey"

    def test_lcsc_csv_preview(self, sample_lcsc_csv):
        """Test LCSC CSV preview functionality"""
        preview = csv_import_service.preview_csv(sample_lcsc_csv)
        
        assert preview['detected_type'] == "lcsc"
        assert preview['type_info'] == "LCSC"
        assert preview['is_supported'] is True
        assert preview['total_rows'] == 3
        assert len(preview['headers']) > 0
        assert "LCSC Part Number" in preview['headers']
        assert len(preview['preview_rows']) == 3
        assert len(preview['parsed_preview']) == 3

    def test_lcsc_csv_parsing(self, sample_lcsc_csv):
        """Test LCSC CSV parsing to parts data"""
        parts_data, errors = csv_import_service.parse_csv_to_parts(sample_lcsc_csv, "lcsc")
        
        assert len(errors) == 0
        assert len(parts_data) == 3
        
        # Check first part (STM32F405RGT6)
        part = parts_data[0]
        assert part['part_name'] == "STM32F405RGT6"
        assert part['part_number'] == "STM32F405RGT6"
        assert part['quantity'] == 1
        assert part['supplier'] == "LCSC"
        assert part['properties']['lcsc_part_number'] == "C1525"
        assert part['properties']['manufacturer'] == "STMicroelectronics"
        assert part['properties']['unit_price'] == 5.23
        assert part['properties']['package'] == "LQFP-64_10x10x05P"

    @pytest.mark.asyncio
    async def test_csv_import_with_order_tracking(self, sample_lcsc_csv):
        """Test complete CSV import with order tracking"""
        session = next(get_session())
        try:
            # Parse CSV
            parts_data, errors = csv_import_service.parse_csv_to_parts(sample_lcsc_csv, "lcsc")
            assert len(errors) == 0
            assert len(parts_data) == 3

            # Import with order info
            part_service = PartService()
            order_info = {
                'order_number': '232705',
                'order_date': datetime(2024, 12, 22),
                'supplier': 'LCSC',
                'notes': 'Test import'
            }

            success_parts, failed_parts = await csv_import_service.import_parts_with_order(
                parts_data, part_service, order_info
            )

            # Check results
            assert len(failed_parts) == 0
            assert len(success_parts) == 3

            # Verify parts were created
            parts = session.exec(select(PartModel)).all()
            part_names = [p.part_name for p in parts]
            assert "STM32F405RGT6" in part_names
            assert "C3216X7S2A335KT000N" in part_names
            assert "JSM6207" in part_names

            # Verify order was created
            orders = session.exec(select(OrderModel)).all()
            assert len(orders) == 1
            order = orders[0]
            assert order.supplier == "LCSC"
            assert order.order_number == "232705"

            # Verify order items were created
            order_items = session.exec(select(OrderItemModel)).all()
            assert len(order_items) == 3

            # Verify PartOrderSummary records were created
            summaries = session.exec(select(PartOrderSummary)).all()
            assert len(summaries) == 3

            # Check specific PartOrderSummary data
            stm32_part = session.exec(select(PartModel).where(PartModel.part_name == "STM32F405RGT6")).first()
            assert stm32_part is not None
            
            summary = session.exec(select(PartOrderSummary).where(PartOrderSummary.part_id == stm32_part.id)).first()
            assert summary is not None
            assert float(summary.last_ordered_price) == 5.23
            assert summary.total_orders == 1
            assert float(summary.lowest_price) == 5.23
            assert float(summary.highest_price) == 5.23
            assert float(summary.average_price) == 5.23
            assert summary.last_order_number == "232705"

        finally:
            # Cleanup
            for summary in session.exec(select(PartOrderSummary)).all():
                session.delete(summary)
            for item in session.exec(select(OrderItemModel)).all():
                session.delete(item)
            for order in session.exec(select(OrderModel)).all():
                session.delete(order)
            for part in session.exec(select(PartModel)).all():
                session.delete(part)
            session.commit()
            session.close()

    @pytest.mark.asyncio
    async def test_duplicate_import_updates_existing_parts(self, sample_lcsc_csv):
        """Test that importing the same CSV twice updates existing parts correctly"""
        session = next(get_session())
        try:
            # First import
            parts_data, _ = csv_import_service.parse_csv_to_parts(sample_lcsc_csv, "lcsc")
            part_service = PartService()
            order_info = {
                'order_number': '232705',
                'order_date': datetime(2024, 12, 22),
                'supplier': 'LCSC'
            }

            success_parts, failed_parts = await csv_import_service.import_parts_with_order(
                parts_data, part_service, order_info
            )
            assert len(failed_parts) == 0

            # Check initial quantities
            stm32_part = session.exec(select(PartModel).where(PartModel.part_name == "STM32F405RGT6")).first()
            initial_quantity = stm32_part.quantity
            assert initial_quantity == 1

            # Second import with different order number
            order_info2 = {
                'order_number': '232706',
                'order_date': datetime(2024, 12, 23),
                'supplier': 'LCSC'
            }

            success_parts2, failed_parts2 = await csv_import_service.import_parts_with_order(
                parts_data, part_service, order_info2
            )
            assert len(failed_parts2) == 0

            # Verify quantities were updated
            session.refresh(stm32_part)
            assert stm32_part.quantity == 2  # 1 + 1

            # Verify PartOrderSummary was updated
            summary = session.exec(select(PartOrderSummary).where(PartOrderSummary.part_id == stm32_part.id)).first()
            assert summary.total_orders == 2
            assert summary.last_order_number == "232706"

            # Verify we have 2 orders but still 3 unique parts
            orders = session.exec(select(OrderModel)).all()
            assert len(orders) == 2
            
            parts = session.exec(select(PartModel)).all()
            assert len(parts) == 3

        finally:
            # Cleanup
            for summary in session.exec(select(PartOrderSummary)).all():
                session.delete(summary)
            for item in session.exec(select(OrderItemModel)).all():
                session.delete(item)
            for order in session.exec(select(OrderModel)).all():
                session.delete(order)
            for part in session.exec(select(PartModel)).all():
                session.delete(part)
            session.commit()
            session.close()

    @pytest.mark.asyncio
    async def test_pricing_statistics_tracking(self, sample_lcsc_csv):
        """Test that pricing statistics are tracked correctly over multiple orders"""
        session = next(get_session())
        try:
            # Modify CSV to have different prices for same part
            modified_csv = sample_lcsc_csv.replace("5.2300,5.23", "4.0000,4.00")  # Lower price
            
            # First import
            parts_data, _ = csv_import_service.parse_csv_to_parts(sample_lcsc_csv, "lcsc")
            part_service = PartService()
            
            await csv_import_service.import_parts_with_order(
                parts_data, part_service, {
                    'order_number': '001',
                    'order_date': datetime(2024, 12, 22),
                    'supplier': 'LCSC'
                }
            )

            # Second import with modified prices
            parts_data2, _ = csv_import_service.parse_csv_to_parts(modified_csv, "lcsc")
            await csv_import_service.import_parts_with_order(
                parts_data2, part_service, {
                    'order_number': '002', 
                    'order_date': datetime(2024, 12, 23),
                    'supplier': 'LCSC'
                }
            )

            # Check pricing statistics
            stm32_part = session.exec(select(PartModel).where(PartModel.part_name == "STM32F405RGT6")).first()
            summary = session.exec(select(PartOrderSummary).where(PartOrderSummary.part_id == stm32_part.id)).first()
            
            assert float(summary.lowest_price) == 4.00
            assert float(summary.highest_price) == 5.23
            assert summary.total_orders == 2
            # Average should be between the two prices
            assert 4.0 <= float(summary.average_price) <= 5.23

        finally:
            # Cleanup
            for summary in session.exec(select(PartOrderSummary)).all():
                session.delete(summary)
            for item in session.exec(select(OrderItemModel)).all():
                session.delete(item)
            for order in session.exec(select(OrderModel)).all():
                session.delete(order)
            for part in session.exec(select(PartModel)).all():
                session.delete(part)
            session.commit()
            session.close()

    def test_supported_parsers_endpoint(self):
        """Test the supported parsers API endpoint"""
        supported_types = csv_import_service.get_supported_types()
        
        assert len(supported_types) >= 3  # LCSC, DigiKey, Mouser
        
        parser_types = [p['type'] for p in supported_types]
        assert 'lcsc' in parser_types
        assert 'digikey' in parser_types
        assert 'mouser' in parser_types

        # Check LCSC parser details
        lcsc_parser = next(p for p in supported_types if p['type'] == 'lcsc')
        assert lcsc_parser['name'] == 'LCSC'
        assert 'LCSC Part Number' in lcsc_parser['required_columns']
        assert 'Manufacture Part Number' in lcsc_parser['required_columns']

    def test_invalid_csv_handling(self):
        """Test handling of invalid CSV content"""
        invalid_csv = "This is not a valid CSV\nwith proper headers"
        
        detected_type = csv_import_service.detect_csv_type(invalid_csv)
        assert detected_type is None

        preview = csv_import_service.preview_csv(invalid_csv)
        assert preview['is_supported'] is False
        # Either has validation errors or an error field
        assert len(preview['validation_errors']) > 0 or preview.get('error') is not None

    def test_empty_csv_handling(self):
        """Test handling of empty CSV content"""
        empty_csv = ""
        
        detected_type = csv_import_service.detect_csv_type(empty_csv)
        assert detected_type is None

        preview = csv_import_service.preview_csv(empty_csv)
        assert preview['is_supported'] is False