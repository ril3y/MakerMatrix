import qrcode

from MakerMatrix.models.label_model import LabelData
from MakerMatrix.models import printer_config_model
from MakerMatrix.lib.printer import Printer


class PrinterService:
    printer = Printer()

    @staticmethod
    async def print_qr_code(label_data: LabelData):
        part_number = label_data.part_number
        part_name = label_data.part_name
        # Implement logic to generate and print QR code
        qr_img = qrcode.make(f'{{"name": "{part_name}", "number": "{part_number}"}}')
        return PrinterService.printer.print_qr_from_memory(qr_img)

    @staticmethod
    def configure_printer(config: printer_config_model.PrinterConfig):
        PrinterService.printer.set_backend(config.backend)
        PrinterService.printer.set_printer_identifier(config.printer_identifier)
        PrinterService.printer.save_config()

    @staticmethod
    def load_printer_config():
        PrinterService.printer.load_config()

    def get_current_configuration(self):
        # Return the current printer configuration
        return {
            "backend": self.backend,
            "printer_identifier": self.printer_identifier
        }
