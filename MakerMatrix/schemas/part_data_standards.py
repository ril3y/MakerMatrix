"""
Part Data Standardization Schema

Defines the standardized structure for part data across all suppliers,
ensuring consistent UI display regardless of data source.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class ComponentType(str, Enum):
    """Standardized component types across all suppliers"""

    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    TRANSISTOR = "transistor"
    IC_MICROCONTROLLER = "ic_microcontroller"
    IC_MEMORY = "ic_memory"
    IC_ANALOG = "ic_analog"
    IC_DIGITAL = "ic_digital"
    IC_POWER = "ic_power"
    CONNECTOR = "connector"
    SWITCH = "switch"
    RELAY = "relay"
    TRANSFORMER = "transformer"
    CRYSTAL = "crystal"
    SENSOR = "sensor"
    MECHANICAL = "mechanical"
    CABLE = "cable"
    TOOL = "tool"
    UNKNOWN = "unknown"


class MountingType(str, Enum):
    """Standardized mounting types"""

    SMT = "smt"
    THROUGH_HOLE = "through_hole"
    PANEL_MOUNT = "panel_mount"
    CHASSIS_MOUNT = "chassis_mount"
    UNKNOWN = "unknown"


class RoHSStatus(str, Enum):
    """Standardized RoHS compliance status"""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    EXEMPT = "exempt"
    UNKNOWN = "unknown"


class LifecycleStatus(str, Enum):
    """Standardized part lifecycle status"""

    ACTIVE = "active"
    OBSOLETE = "obsolete"
    NRND = "nrnd"  # Not Recommended for New Designs
    PREVIEW = "preview"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"


@dataclass
class StandardizedSpecifications:
    """Standardized technical specifications structure"""

    # Universal specs (applicable to most components)
    value: Optional[str] = None  # "10K", "4.7µF", "STM32F103"
    tolerance: Optional[str] = None  # "±1%", "±10%"
    voltage_rating: Optional[str] = None  # "50V", "3.3V"
    current_rating: Optional[str] = None  # "1A", "100mA"
    power_rating: Optional[str] = None  # "0.25W", "1W"
    temperature_rating: Optional[str] = None  # "-40°C to +85°C"
    frequency_rating: Optional[str] = None  # "1MHz", "16MHz"

    # Physical specs
    package: Optional[str] = None  # "0603", "SOIC-8", "TO-220"
    mounting_type: Optional[MountingType] = None
    dimensions: Optional[str] = None  # "3.2x1.6x0.6mm"
    pin_count: Optional[int] = None

    # Material specs
    material: Optional[str] = None  # "Ceramic", "Aluminum", "Tantalum"
    finish: Optional[str] = None  # "Tin", "Gold", "HASL"

    # Additional technical properties
    additional_specs: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        result = {}
        for field, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, Enum):
                    result[field] = value.value
                else:
                    result[field] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardizedSpecifications":
        """Create from dictionary loaded from JSON"""
        # Handle enum fields
        if "mounting_type" in data and isinstance(data["mounting_type"], str):
            try:
                data["mounting_type"] = MountingType(data["mounting_type"])
            except ValueError:
                data["mounting_type"] = MountingType.UNKNOWN

        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class StandardizedSupplierData:
    """Standardized supplier-specific data structure"""

    supplier_name: str
    supplier_part_number: str
    product_url: Optional[str] = None
    datasheet_url: Optional[str] = None
    supplier_category: Optional[str] = None
    lead_time: Optional[str] = None
    minimum_order_quantity: Optional[int] = None
    packaging: Optional[str] = None  # "Tape & Reel", "Cut Tape", "Bulk"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class StandardizedMetadata:
    """Standardized enrichment and import metadata"""

    import_source: Optional[str] = None  # "LCSC CSV", "Manual Entry", "API"
    import_date: Optional[datetime] = None
    last_enrichment: Optional[datetime] = None
    enrichment_supplier: Optional[str] = None
    enrichment_capabilities: Optional[List[str]] = None
    has_datasheet: bool = False
    has_image: bool = False
    needs_enrichment: bool = False
    quality_score: Optional[float] = None  # 0.0-1.0 data completeness score

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for k, v in self.__dict__.items():
            if v is not None:
                if isinstance(v, datetime):
                    result[k] = v.isoformat()
                else:
                    result[k] = v
        return result


@dataclass
class StandardizedOrderData:
    """Standardized order history data from CSV imports"""

    last_order_date: Optional[datetime] = None
    last_unit_price: Optional[float] = None
    last_order_quantity: Optional[int] = None
    last_extended_price: Optional[float] = None
    customer_reference: Optional[str] = None
    order_number: Optional[str] = None
    currency: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for k, v in self.__dict__.items():
            if v is not None:
                if isinstance(v, datetime):
                    result[k] = v.isoformat()
                else:
                    result[k] = v
        return result


class StandardizedAdditionalProperties:
    """Complete standardized structure for additional_properties field"""

    def __init__(self):
        self.specifications = StandardizedSpecifications()
        self.supplier_data: Dict[str, StandardizedSupplierData] = {}
        self.metadata = StandardizedMetadata()
        self.order_data = StandardizedOrderData()
        self.custom_fields: Dict[str, Any] = {}

    def add_supplier_data(self, supplier_name: str, data: StandardizedSupplierData):
        """Add supplier-specific data"""
        self.supplier_data[supplier_name.lower()] = data

    def get_supplier_data(self, supplier_name: str) -> Optional[StandardizedSupplierData]:
        """Get supplier-specific data"""
        return self.supplier_data.get(supplier_name.lower())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage in database"""
        return {
            "specifications": self.specifications.to_dict(),
            "supplier_data": {k: v.to_dict() for k, v in self.supplier_data.items()},
            "metadata": self.metadata.to_dict(),
            "order_data": self.order_data.to_dict(),
            "custom_fields": self.custom_fields,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardizedAdditionalProperties":
        """Create from dictionary loaded from database JSON"""
        instance = cls()

        if "specifications" in data:
            instance.specifications = StandardizedSpecifications.from_dict(data["specifications"])

        if "supplier_data" in data:
            for supplier, supplier_data in data["supplier_data"].items():
                instance.supplier_data[supplier] = StandardizedSupplierData(**supplier_data)

        if "metadata" in data:
            metadata_dict = data["metadata"].copy()
            # Convert datetime strings back to datetime objects
            for field in ["import_date", "last_enrichment"]:
                if field in metadata_dict and isinstance(metadata_dict[field], str):
                    try:
                        metadata_dict[field] = datetime.fromisoformat(metadata_dict[field])
                    except ValueError:
                        metadata_dict[field] = None
            instance.metadata = StandardizedMetadata(**metadata_dict)

        if "order_data" in data:
            order_dict = data["order_data"].copy()
            # Convert datetime strings back to datetime objects
            if "last_order_date" in order_dict and isinstance(order_dict["last_order_date"], str):
                try:
                    order_dict["last_order_date"] = datetime.fromisoformat(order_dict["last_order_date"])
                except ValueError:
                    order_dict["last_order_date"] = None
            instance.order_data = StandardizedOrderData(**order_dict)

        if "custom_fields" in data:
            instance.custom_fields = data["custom_fields"]

        return instance


def determine_component_type(part_name: str, description: str, specifications: Dict[str, Any]) -> ComponentType:
    """Automatically determine component type from part data"""

    # Combine text for analysis
    text = f"{part_name} {description}".lower()

    # Check specifications for clues
    if specifications:
        spec_text = " ".join(str(v).lower() for v in specifications.values())
        text += f" {spec_text}"

    # Component type detection rules (order matters - more specific first)
    if any(keyword in text for keyword in ["microcontroller", "mcu", "stm32", "atmega", "pic"]):
        return ComponentType.IC_MICROCONTROLLER
    elif any(keyword in text for keyword in ["resistor", "ohm", "kohm", "mohm"]):
        return ComponentType.RESISTOR
    elif any(keyword in text for keyword in ["capacitor", "cap", "farad", "pf", "nf", "uf", "µf"]):
        return ComponentType.CAPACITOR
    elif any(keyword in text for keyword in ["inductor", "henry", "uh", "mh"]):
        return ComponentType.INDUCTOR
    elif any(keyword in text for keyword in ["diode", "led", "zener", "schottky"]):
        return ComponentType.DIODE
    elif any(keyword in text for keyword in ["transistor", "mosfet", "bjt", "fet", "npn", "pnp"]):
        return ComponentType.TRANSISTOR
    elif any(keyword in text for keyword in ["memory", "ram", "rom", "flash", "eeprom", "sram"]):
        return ComponentType.IC_MEMORY
    elif any(keyword in text for keyword in ["connector", "header", "socket", "plug"]):
        return ComponentType.CONNECTOR
    elif any(keyword in text for keyword in ["switch", "button", "tactile"]):
        return ComponentType.SWITCH
    elif any(keyword in text for keyword in ["relay", "contactor"]):
        return ComponentType.RELAY
    elif any(keyword in text for keyword in ["crystal", "oscillator", "xtal", "mhz", "khz"]):
        return ComponentType.CRYSTAL
    elif any(keyword in text for keyword in ["sensor", "temperature", "pressure", "accelerometer"]):
        return ComponentType.SENSOR
    elif any(keyword in text for keyword in ["ic", "chip", "integrated"]):
        return ComponentType.IC_ANALOG  # Default IC type

    return ComponentType.UNKNOWN


def extract_package_from_specs(specifications: Dict[str, Any]) -> Optional[str]:
    """Extract package information from specifications"""

    # Common package field names
    package_fields = ["package", "footprint", "case", "mounting", "enclosure"]

    for field, value in specifications.items():
        if any(pkg_field in field.lower() for pkg_field in package_fields):
            return str(value)

    # Look for package patterns in values
    for value in specifications.values():
        if isinstance(value, str):
            value_lower = value.lower()
            # Common package patterns
            if any(pkg in value_lower for pkg in ["0603", "0805", "1206", "sot-23", "soic", "qfp", "bga"]):
                return value

    return None


def determine_mounting_type(package: str, specifications: Dict[str, Any]) -> MountingType:
    """Determine mounting type from package and specifications"""

    if not package:
        return MountingType.UNKNOWN

    package_lower = package.lower()

    # SMT packages
    smt_indicators = ["0603", "0805", "1206", "2512", "sot", "soic", "qfp", "bga", "qfn", "smd", "smt"]
    if any(indicator in package_lower for indicator in smt_indicators):
        return MountingType.SMT

    # Through-hole packages
    th_indicators = ["dip", "to-220", "to-92", "through", "hole", "radial", "axial"]
    if any(indicator in package_lower for indicator in th_indicators):
        return MountingType.THROUGH_HOLE

    # Check specifications for mounting type
    specs_text = " ".join(str(v).lower() for v in specifications.values())
    if "smt" in specs_text or "surface mount" in specs_text:
        return MountingType.SMT
    elif "through hole" in specs_text or "dip" in specs_text:
        return MountingType.THROUGH_HOLE

    return MountingType.UNKNOWN
