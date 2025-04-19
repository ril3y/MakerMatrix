from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.printer_repository import PrinterRepository


class PrinterService:
    """
    This service is called by your routes. It calls into the repository, which in turn
    creates/configures the correct printer driver.
    """

    def __init__(self, printer_repo: PrinterRepository):
        self.printer_repo = printer_repo
        self.printer = self.printer_repo.get_printer()

    async def print_part_name(self, part: PartModel, print_settings: PrintSettings):
        printer = self.printer_repo.get_printer()
        try:
            # Now, we pass the PrintConfig to the printer's print_text_label method.
            return printer.print_text_label(part.part_name, print_settings)
        except Exception as e:
            raise RuntimeError(f"Error printing part name: {e}")

    async def print_text_label(self, text: str, print_settings: PrintSettings):
        printer = self.printer_repo.get_printer()
        try:
            # Now, we pass the PrintConfig to the printer's print_text_label method.
            return printer.print_text_label(text, print_settings)
        except Exception as e:
            raise RuntimeError(f"Error printing text: {e}")

    # async def print_qr_code_with_name(self, label_data: LabelData):
    #     printer = self.printer_repo.get_printer()
    #     try:
    #         # Create a temporary PartModel using LabelData.
    #         part = PartModel(part_number=label_data.part_number, part_name=label_data.part_name)
    #         qr_image = self._generate_qr_code(part)
    #         return printer.print_qr_from_memory(qr_image)
    #     except Exception as e:
    #         raise RuntimeError(f"Error printing QR code with name: {e}")

    async def print_qr_and_text(self, part: PartModel, print_settings: PrintSettings, text: str = None):
        printer = self.printer_repo.get_printer()

        if text:
            if text == "name":
                text = part['data']['part_name']
            elif text == "number":
                text = part['data']['part_number']

        try:

            return printer.print_qr_and_text(
                text=text,
                part=part,
                print_settings=print_settings)

        except Exception as e:
            raise RuntimeError(f"Error printing QR code + text: {e}")

    def load_printer_config(self):
        """
        Reloads the printer configuration and re-imports the driver.
        Useful if the config file is changed at runtime.
        """
        self.printer_repo.load_config()
        self.printer_repo._import_driver()
