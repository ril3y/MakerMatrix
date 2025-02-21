import json
from abc import ABC, abstractmethod

from PIL import Image

from MakerMatrix.lib.print_settings import PrintSettings


class AbstractPrinter(ABC):
    """Abstract base class for printers."""

    def __init__(self, dpi: int = 300, scaling_factor: float = 1.0,
                 name: str = "Generic Printer", version: str = "1.0",
                 additional_settings: dict = None):
        self.dpi = dpi
        self.scaling_factor = scaling_factor
        self.name = name
        self.version = version
        self.additional_settings = additional_settings or {}

    @abstractmethod
    def print_text_label(self, label: str, print_config: PrintSettings) -> int:
        pass

    @abstractmethod
    def print_image(self, image: Image, label: str = "") -> None:
        pass

    @abstractmethod
    def configure_printer(self, config: dict) -> None:
        pass

    @abstractmethod
    def get_status(self) -> str:
        pass

    @abstractmethod
    def cancel_print(self) -> None:
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        """Check if the printer is available.

        Returns:
            bool: True if the printer is available, False otherwise.
        """
        pass

    def save_config(self, config_path: str) -> None:
        config = {
            'dpi': self.dpi,
            'scaling_factor': self.scaling_factor,
            'name': self.name,
            'version': self.version,
            'additional_settings': self.additional_settings,
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

    def load_config(self, config_path: str) -> None:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.additional_settings = config.get("additional_settings", {})
                self.configure_printer(config)
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
