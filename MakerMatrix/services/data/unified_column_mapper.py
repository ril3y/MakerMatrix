"""
Unified Column Mapping Service

Provides standardized column mapping across all suppliers for consistent
data extraction from CSV, XLS, and other file formats.
"""

from typing import Dict, List, Optional, Any
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class UnifiedColumnMapper:
    """Standardized column mapping utility for all suppliers"""

    # Common field mappings across suppliers (case-insensitive)
    STANDARD_MAPPINGS = {
        "part_number": [
            "part #",
            "part number",
            "supplier part",
            "supplier part number",
            "lcsc part number",
            "mouser #:",
            "mouser part #",
            "mouser part number",
            "mouser p/n",
            "digikey part number",
            "digi-key part number",
        ],
        "manufacturer": ["manufacturer", "mfr", "mfg", "brand", "manufacture"],
        "manufacturer_part_number": [
            "mfr part #",
            "manufacturer part number",
            "mpn",
            "mfr. #:",
            "mfg part #",
            "customer #",
            "manufacture part number",
        ],
        "description": ["description", "desc", "product description", "desc.:"],
        "quantity": ["quantity", "qty", "order qty", "order qty.", "order quantity"],
        "unit_price": ["unit price", "price", "unit cost", "price (usd)", "unit price($)"],
        "order_price": ["order price", "total price", "line total", "ext. (usd)", "extended price", "order price($)"],
        "package": ["package", "packaging", "case", "footprint", "case/package"],
        "rohs": ["rohs", "rohs status", "rohs compliant", "rohs compliance"],
        "customer_reference": ["customer no.", "customer #", "customer reference", "customer part number"],
        "min_order_qty": ["min order qty", "minimum order", "min qty", "min\\mult order qty."],
    }

    def __init__(self):
        """Initialize the column mapper"""
        pass

    def map_columns(self, df_columns: List[str], supplier_mappings: Optional[Dict] = None) -> Dict[str, str]:
        """
        Find actual column names using flexible mapping

        Args:
            df_columns: List of actual column names from the dataframe
            supplier_mappings: Optional supplier-specific additional mappings

        Returns:
            Dict mapping standard field names to actual column names
        """
        mapped_columns = {}

        # Combine standard mappings with supplier-specific ones
        all_mappings = self.STANDARD_MAPPINGS.copy()
        if supplier_mappings:
            for field, variations in supplier_mappings.items():
                if field in all_mappings:
                    all_mappings[field].extend(variations)
                else:
                    all_mappings[field] = variations

        # Convert column names to lowercase for case-insensitive matching
        lower_columns = {col.lower(): col for col in df_columns}

        # Find matches for each field
        for field, possible_names in all_mappings.items():
            for possible_name in possible_names:
                # Check for exact match (case-insensitive)
                if possible_name.lower() in lower_columns:
                    mapped_columns[field] = lower_columns[possible_name.lower()]
                    break

                # Check for partial match (case-insensitive)
                matching_cols = [
                    original_col
                    for lower_col, original_col in lower_columns.items()
                    if possible_name.lower() in lower_col
                ]
                if matching_cols:
                    mapped_columns[field] = matching_cols[0]
                    break

        logger.debug(f"Mapped columns: {mapped_columns}")
        return mapped_columns

    def validate_required_columns(self, mapped_columns: Dict[str, str], required: List[str]) -> bool:
        """
        Validate required columns are present

        Args:
            mapped_columns: Result from map_columns()
            required: List of required field names

        Returns:
            True if all required columns are found
        """
        missing = [field for field in required if field not in mapped_columns]
        if missing:
            logger.warning(f"Missing required columns: {missing}")
            return False
        return True

    def extract_row_data(self, row: pd.Series, mapped_columns: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract data from a pandas row using mapped column names

        Args:
            row: Pandas Series representing a data row
            mapped_columns: Column mapping from map_columns()

        Returns:
            Dict with extracted data using standard field names
        """
        extracted_data = {}

        for field, column_name in mapped_columns.items():
            if column_name in row.index:
                value = row[column_name]
                # Clean up the value
                if pd.isna(value):
                    extracted_data[field] = None
                elif isinstance(value, str):
                    extracted_data[field] = value.strip()
                else:
                    extracted_data[field] = value
            else:
                extracted_data[field] = None

        return extracted_data

    def get_supplier_specific_mappings(self, supplier_name: str) -> Dict[str, List[str]]:
        """
        Get supplier-specific column mapping variations

        Args:
            supplier_name: Name of the supplier (lcsc, mouser, digikey)

        Returns:
            Dict with supplier-specific column name variations
        """
        supplier_mappings = {
            "lcsc": {
                "part_number": ["lcsc part number"],
                "manufacturer_part_number": ["manufacture part number"],
                "customer_reference": ["customer no."],
                "min_order_qty": ["min\\mult order qty."],
                "unit_price": ["unit price($)"],
                "order_price": ["order price($)"],
            },
            "mouser": {
                "part_number": ["mouser #:", "mouser part #", "mouser part number", "mouser p/n"],
                "manufacturer_part_number": ["mfr. #:", "mfr part #"],
                "description": ["desc.:"],
                "quantity": ["order qty."],
                "unit_price": ["price (usd)"],
                "order_price": ["ext. (usd)"],
            },
            "digikey": {
                "part_number": ["digikey part number", "digi-key part number"],
                "manufacturer_part_number": ["manufacturer part number"],
                "customer_reference": ["customer reference"],
                "backorder_qty": ["backorder qty", "backorder quantity"],
            },
        }

        return supplier_mappings.get(supplier_name.lower(), {})

    def create_smart_part_name(self, extracted_data: Dict[str, Any]) -> str:
        """
        Create an intelligent part name from available data

        Args:
            extracted_data: Data extracted from extract_row_data()

        Returns:
            Smart part name using best available information
        """
        # Priority order for part naming
        name_candidates = [
            extracted_data.get("manufacturer_part_number"),
            extracted_data.get("description"),
            extracted_data.get("part_number"),
        ]

        # Use first non-empty candidate
        for candidate in name_candidates:
            if candidate and str(candidate).strip():
                return str(candidate).strip()

        # Fallback to part number
        return str(extracted_data.get("part_number", "Unknown Part")).strip()
