from PIL import Image
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster
import json
from PIL import ImageOps


class Printer:
    model: str
    backend: str
    printer_identifier: str
    dpi: int
    qlr: BrotherQLRaster

    def __init__(self, model: str = None, backend: str = None, printer_identifier: str = None, dpi: int = 300):
        self.model = model
        self.backend = backend
        self.printer_identifier = printer_identifier
        self.dpi = dpi
        self.qlr = BrotherQLRaster(self.model) if model else None
        ##self.qlr.exception_on_warning = True  # Enable exceptions for warnings

    def set_backend(self, backend: str):
        self.backend = backend

    def set_printer_identifier(self, printer_identifier: str):
        self.printer_identifier = printer_identifier

    def set_dpi(self, dpi: int):
        """Set the DPI for printing."""
        if dpi not in [300, 600]:
            raise ValueError("DPI must be 300 or 600.")
        self.dpi = dpi

    def _resize_and_print(self, image: Image.Image, label: str = '12', rotate: str = '0'):
        """Common method to resize the image, convert it, and send to printer."""
        print("Resize and Print called.")

        dpi = self.dpi  # Use the instance's DPI value

        # Calculate the pixel size to match the label size
        label_size_mm = 15  # Label width in millimeters
        label_size_in = label_size_mm / 25.4  # Convert mm to inches
        pixel_size = int(label_size_in * dpi)  # Calculate the pixel dimensions

        # Make a copy of the image to avoid modifying the original
        image_copy = image.copy()

        # Ensure the image maintains its aspect ratio and fits within the label
        image_copy.thumbnail((pixel_size, pixel_size), Image.LANCZOS)

        # Create a new white background image of the target size (15mm x 15mm)
        background = Image.new("RGB", (pixel_size, pixel_size), "white")

        # Center the QR code image on the background
        image_copy = ImageOps.fit(image_copy, (pixel_size, pixel_size), Image.LANCZOS)

        # Convert the image to printer instructions
        self.qlr.data = b''  # Clear the last QR code data
        instructions = convert(
            qlr=self.qlr,
            images=[image_copy],
            label=label,  # Should be the width of the label in mm as a string
            rotate=rotate,  # Rotation angle: '0', '90', '180', '270', or 'auto'
            threshold=70.0,  # Black and white threshold
            dither=False,  # Dithering for grayscale images
            compress=False,  # Compress the image data
            red=False,  # Only True if using Red/Black 62 mm label tape
            dpi_600=(self.dpi == 600),  # Set to True if using 600 DPI
            hq=True,  # High-quality printing
            cut=True  # Auto-cut after printing
        )

        # Debugging: Print the size/length of the instructions before sending
        print(f"Instruction size: {len(instructions)}")

        try:
            # Attempt to send the data to the printer
            send(
                instructions=instructions,
                printer_identifier=self.printer_identifier,
                backend_identifier=self.backend,
                blocking=True
            )
            print("Print job sent successfully.")
            return True  # Return True on success
        except Exception as e:
            print(f"Error during printing: {str(e)}")
            return False  # Return False if there was an error

    def print_qr_from_memory(self, qr_image: Image.Image, label: str = '12', rotate: str = '0'):
        """Print a QR code from an in-memory image object."""
        return self._resize_and_print(qr_image, label, rotate)

    def print_qr(self, image_path: str, label: str = '12', rotate: str = '0'):
        """Print a QR code from an image file."""
        # Open the image from the file
        try:
            im = Image.open(image_path)
            return self._resize_and_print(im, label, rotate)
        except Exception as e:
            print(f"Error opening image file {image_path}: {str(e)}")
            return False  # Return False if the image file cannot be opened

    def save_config(self, config_path='printer_config.json'):
        config = {
            'model': self.model,
            'backend': self.backend,
            'printer_identifier': self.printer_identifier,
            'dpi': self.dpi
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

    def load_config(self, config_path='printer_config.json'):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.model = config.get('model')
                self.backend = config.get('backend')
                self.printer_identifier = config.get('printer_identifier')
                self.dpi = config.get('dpi', 300)  # Default to 300 if not set
                # Reinitialize the BrotherQLRaster with the new model
                self.qlr = BrotherQLRaster(self.model)
                self.qlr.exception_on_warning = True
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
