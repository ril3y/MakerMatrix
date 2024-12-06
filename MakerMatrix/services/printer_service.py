import qrcode
from PIL import Image, ImageDraw, ImageFont
from MakerMatrix.models.label_model import LabelData
from MakerMatrix.models import printer_config_model
from MakerMatrix.lib.printer import Printer
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster

class PrinterService:
    printer = Printer()  # Initialize with default Printer instance

    def __init__(self):
        self.printer_identifier = None
        self.backend = None

    @staticmethod
    async def print_qr_code_with_name(label_data: LabelData):
        try:
            qr_img = qrcode.make(f'{{"name": "{label_data.part_name}", "number": "{label_data.part_number}"}}')
            qr_img = qr_img.resize((400, 400))

            combined_img = Image.new('RGB', (800, 400), 'white')
            combined_img.paste(qr_img, (0, 0))

            font = ImageFont.truetype("arial.ttf", 72)
            text_img = Image.new('RGB', (400, 100), 'white')
            text_draw = ImageDraw.Draw(text_img)
            text_draw.text((0, 0), label_data.part_name, font=font, fill='black')
            rotated_text = text_img.rotate(90, expand=True)
            combined_img.paste(rotated_text, (450, 50))

            result = PrinterService.printer.print_qr_from_memory(combined_img)
            return result

        except Exception as e:
            print(f"Error printing combined QR code and text: {str(e)}")
            return False

    @staticmethod
    async def print_part_name(label_data: LabelData, label_len):
        try:
            text_label = label_data.part_name
            result = PrinterService.printer.print_text_label(text=text_label, label_len=label_len)
            return result
        except Exception as e:
            print(f"Error printing part name: {str(e)}")
            return False

    @staticmethod
    def load_printer_config():
        PrinterService.printer.load_config()

    def get_current_configuration(self):
        return {
            "backend": self.backend,
            "printer_identifier": self.printer_identifier
        }

    @staticmethod
    def configure_printer(config: printer_config_model.PrinterConfig):
        PrinterService.printer.set_backend(config.backend)
        PrinterService.printer.set_printer_identifier(config.printer_identifier)
        PrinterService.printer.set_dpi(config.dpi)
        PrinterService.printer.set_model(config.model)
        PrinterService.printer.save_config()
