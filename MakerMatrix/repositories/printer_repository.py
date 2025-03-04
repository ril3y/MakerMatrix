import importlib
import json
from typing import Optional

from MakerMatrix.models.printer_config_model import PrinterConfig

# Map config driver names to the actual class names.
DRIVER_CLASS_MAP = {
    "brother_ql": "BrotherQL"
}


class PrinterRepository:
    """
    Loads the printer configuration from a JSON file, dynamically imports the correct driver,
    and instantiates the printer driver.
    """

    def __init__(self, config_path: str = "printer_config.json"):
        self.config_path = config_path
        self._printer = None
        self._printer_config: Optional[PrinterConfig] = None
        self._driver_cls = None

        self.load_config()
        self._import_driver()

    def load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        self._printer_config = PrinterConfig(
            backend=config_data["backend"],
            driver=config_data["driver"],
            printer_identifier=config_data["printer_identifier"],
            dpi=config_data["dpi"],
            model=config_data["model"],
            scaling_factor=config_data.get("scaling_factor", 1.0),
            additional_settings=config_data.get("additional_settings", {})
        )
        # Reset any existing printer/driver so that changes take effect.
        self._printer = None
        self._driver_cls = None

    def _import_driver(self) -> None:
        if not self._printer_config:
            raise ValueError("Printer configuration is missing.")

        module_name = "MakerMatrix.printers." + self._printer_config.driver
        try:
            driver_module = importlib.import_module(module_name)
        except ImportError as e:
            raise ValueError(f"Could not import printer driver for '{module_name}'") from e

        driver_class_name = DRIVER_CLASS_MAP.get(self._printer_config.driver)
        if not driver_class_name:
            # Fallback: convert snake_case to CamelCase.
            driver_class_name = ''.join(word.capitalize() for word in self._printer_config.driver.split('_'))

        self._driver_cls = getattr(driver_module, driver_class_name, None)
        if not self._driver_cls:
            raise ValueError(f"No valid class '{driver_class_name}' found in {module_name}")

    def get_printer(self):
        if not self._printer:
            if not self._printer_config:
                raise ValueError("Printer configuration is missing.")
            if not self._driver_cls:
                self._import_driver()
            # Instantiate the driver by passing configuration parameters including additional_settings.
            self._printer = self._driver_cls(
                model=self._printer_config.model,
                backend=self._printer_config.backend,
                printer_identifier=self._printer_config.printer_identifier,
                dpi=self._printer_config.dpi,
                scaling_factor=self._printer_config.scaling_factor,
                additional_settings=self._printer_config.additional_settings
            )
        return self._printer

    def configure_printer(self, config: PrinterConfig, save: bool = True) -> None:
        self._printer_config = config
        self._printer = None
        self._driver_cls = None
        if save:
            self.save_config()

    def save_config(self) -> None:
        if not self._printer_config:
            raise ValueError("Printer config is not set.")
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({
                "backend": self._printer_config.backend,
                "driver": self._printer_config.driver,
                "printer_identifier": self._printer_config.printer_identifier,
                "dpi": self._printer_config.dpi,
                "model": self._printer_config.model,
                "scaling_factor": self._printer_config.scaling_factor,
                "additional_settings": self._printer_config.additional_settings
            },
                f,
                indent=4
            )

    def get_configuration(self) -> dict:
        if not self._printer_config:
            return {}
        return {
            "backend": self._printer_config.backend,
            "driver": self._printer_config.driver,
            "printer_identifier": self._printer_config.printer_identifier,
            "dpi": self._printer_config.dpi,
            "model": self._printer_config.model,
            "scaling_factor": self._printer_config.scaling_factor,
            "additional_settings": self._printer_config.additional_settings
        }
