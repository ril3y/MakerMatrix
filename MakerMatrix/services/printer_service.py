import qrcode
from PIL import Image

from MakerMatrix.lib.print_config import PrintJobConfig
from MakerMatrix.models.label_model import LabelData
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.printer_repository import PrinterRepository


# Assume PrintConfig is imported or defined above

class PrinterService:
    """
    This service is called by your routes. It calls into the repository, which in turn
    creates/configures the correct printer driver.
    """

    def __init__(self, printer_repo: PrinterRepository):
        self.printer_repo = printer_repo

    def _generate_qr_code(self, part: PartModel) -> Image.Image:
        data = {"name": part.part_name, "number": part.part_number}
        return qrcode.make(str(data))

    async def print_part_name(self, part: PartModel, print_config: PrintJobConfig):
        printer = self.printer_repo.get_printer()
        try:
            # Now, we pass the PrintConfig to the printer's print_text_label method.
            return printer.print_text_label(part.part_name, print_config)
        except Exception as e:
            print(f"Error printing part name: {e}")
            return False

    async def print_qr_code_with_name(self, label_data: LabelData):
        printer = self.printer_repo.get_printer()
        try:
            # Create a temporary PartModel using LabelData.
            part = PartModel(part_number=label_data.part_number, part_name=label_data.part_name)
            qr_image = self._generate_qr_code(part)
            return printer.print_qr_from_memory(qr_image)
        except Exception as e:
            print(f"Error printing QR code with name: {e}")
            return False

    async def print_qr_and_text(self, part: PartModel, print_config: PrintJobConfig, text: str):
        printer = self.printer_repo.get_printer()
        try:
            qr_image = self._generate_qr_code(part)
            return printer.print_qr_and_text(qr_image, text, print_config)
        except Exception as e:
            print(f"Error printing QR code + text: {e}")
            return False

    def load_printer_config(self):
        """
        Reloads the printer configuration and re-imports the driver.
        Useful if the config file is changed at runtime.
        """
        self.printer_repo.load_config()
        self.printer_repo._import_driver()
