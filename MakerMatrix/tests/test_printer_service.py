import pytest
from fastapi.testclient import TestClient
from MakerMatrix.services.printer_service import PrinterService
from MakerMatrix.models.label_model import LabelData
from MakerMatrix.models.printer_config_model import PrinterConfig

@pytest.fixture
def printer_service():
    return PrinterService()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_code_with_name(printer_service):
    # Set up printer config
    config = PrinterConfig(
        model="QL-800",
        backend="network",
        printer_identifier="tcp://192.168.1.71",
        dpi=300
    )

    # Load and configure printer
    printer_service.load_printer_config()
    #printer_service.configure_printer(config)

    # Create test label data
    label_data = LabelData(
        part_number="TEST-456",
        part_name="N123931"
    )

    # Test the new combined print function
    result = await printer_service.print_qr_code_with_name(label_data)
    assert result is not None

@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_part_name(printer_service):
    # Set up printer config
    config = PrinterConfig(
        model="QL-800",
        backend="network",
        printer_identifier="tcp://192.168.1.71",
        dpi=300,
        scaling_factor=1.1
    )

    # Load and configure printer
    printer_service.load_printer_config()
    #printer_service.configure_printer(config)

    # Create test label data with a long part name to test text sizing
    label_data = LabelData(
        part_number="TEST-789",
        part_name="#6 1/2\" Tap Screw"
    )

    # Test the new part name print function
    result = await printer_service.print_part_name(label_data, 1.6)
    assert result is not None
