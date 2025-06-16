"""
Mouser XLS File Parser

Handles parsing of Mouser Electronics order XLS files.
Mouser provides order data in XLS format with specific column structure.
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from MakerMatrix.models.models import PartModel
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ParsingResult:
    """Simple result class for XLS parsing"""
    def __init__(self, success: bool, error_message: str = None, total_rows: int = 0, 
                 successful_rows: int = 0, failed_rows: int = 0, parts: List[Dict] = None, 
                 errors: List[str] = None, order_info: Dict = None):
        self.success = success
        self.error_message = error_message
        self.total_rows = total_rows
        self.successful_rows = successful_rows
        self.failed_rows = failed_rows
        self.parts = parts or []
        self.errors = errors or []
        self.order_info = order_info or {}


class MouserXLSParser:
    """Parser for Mouser XLS order files."""
    
    def __init__(self):
        self.parser_type = "mouser"
        self.supplier_name = "Mouser"
        self.required_columns = [
            "Mouser #:",
            "Mfr. #:",
            "Desc.:",
            "Order Qty."
        ]
        self.optional_columns = [
            "Sales Order #:",
            "Web Order #:",
            "Order Date:",
            "Price (USD)"
        ]
    
    def can_parse(self, file_content: bytes = None, file_path: str = None, filename: str = None, **kwargs) -> bool:
        """Check if this parser can handle the given file."""
        # First check if filename suggests XLS format
        filename_to_check = filename or file_path
        if filename_to_check and not filename_to_check.lower().endswith(('.xls', '.xlsx')):
            return False
            
        try:
            if file_content:
                # Parse content from bytes
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file.flush()
                    
                    try:
                        df = pd.read_excel(tmp_file.name)
                    finally:
                        os.unlink(tmp_file.name)
            elif file_path:
                df = pd.read_excel(file_path)
            else:
                return False
                
            # Check for Mouser-specific columns
            mouser_columns = ["Mouser #:", "Mfr. #:", "Desc.:"]
            return all(col in df.columns for col in mouser_columns)
        except Exception as e:
            logger.warning(f"Failed to read XLS file: {e}")
            return False
    
    def parse_file(self, file_path: str, **kwargs) -> ParsingResult:
        """Parse a Mouser XLS file and return structured data."""
        try:
            df = pd.read_excel(file_path)
            return self._parse_dataframe(df, **kwargs)
        except Exception as e:
            logger.error(f"Failed to parse Mouser XLS file {file_path}: {e}")
            return ParsingResult(
                success=False,
                error_message=f"Failed to parse XLS file: {str(e)}",
                total_rows=0,
                successful_rows=0,
                failed_rows=0,
                parts=[],
                errors=[]
            )
    
    def parse_content(self, content: bytes, **kwargs) -> ParsingResult:
        """Parse Mouser XLS content from bytes."""
        try:
            # Write content to temp file and parse
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                try:
                    result = self.parse_file(tmp_file.name, **kwargs)
                finally:
                    os.unlink(tmp_file.name)
                
                return result
        except Exception as e:
            logger.error(f"Failed to parse Mouser XLS content: {e}")
            return ParsingResult(
                success=False,
                error_message=f"Failed to parse XLS content: {str(e)}",
                total_rows=0,
                successful_rows=0,
                failed_rows=0,
                parts=[],
                errors=[]
            )
    
    def _parse_dataframe(self, df: pd.DataFrame, **kwargs) -> ParsingResult:
        """Parse the pandas DataFrame containing Mouser data."""
        parts = []
        errors = []
        successful_rows = 0
        
        # Clean column names and data
        df = df.dropna(how='all')  # Remove completely empty rows
        
        # Extract order information from first row
        order_info = self._extract_order_info(df)
        
        for index, row in df.iterrows():
            try:
                part_data = self._parse_row(row, order_info)
                if part_data:
                    parts.append(part_data)
                    successful_rows += 1
            except Exception as e:
                error_msg = f"Row {index + 1}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        return ParsingResult(
            success=successful_rows > 0,
            error_message=None if successful_rows > 0 else "No valid parts found",
            total_rows=len(df),
            successful_rows=successful_rows,
            failed_rows=len(df) - successful_rows,
            parts=parts,
            errors=errors,
            order_info=order_info
        )
    
    def _extract_order_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract order information from the dataframe."""
        order_info = {
            "supplier": self.supplier_name,
            "order_date": None,
            "order_number": None,
            "order_status": None
        }
        
        if not df.empty:
            first_row = df.iloc[0]
            
            # Extract order number (try Sales Order # or Web Order #)
            if "Sales Order #:" in df.columns and pd.notna(first_row.get("Sales Order #:")):
                order_info["order_number"] = str(first_row["Sales Order #:"])
            elif "Web Order #:" in df.columns and pd.notna(first_row.get("Web Order #:")):
                order_info["order_number"] = str(first_row["Web Order #:"])
            
            # Extract order date
            if "Order Date:" in df.columns and pd.notna(first_row.get("Order Date:")):
                try:
                    order_date = pd.to_datetime(first_row["Order Date:"])
                    order_info["order_date"] = order_date.strftime("%Y-%m-%d")
                except:
                    pass
            
            # Extract order status
            if "Order Status:" in df.columns and pd.notna(first_row.get("Order Status:")):
                order_info["order_status"] = str(first_row["Order Status:"])
        
        return order_info
    
    def _parse_row(self, row: pd.Series, order_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single row into part data."""
        # Skip rows with missing essential data
        if pd.isna(row.get("Mouser #:")) or pd.isna(row.get("Mfr. #:")):
            return None
        
        # Extract basic part information
        mouser_part_number = str(row["Mouser #:"]).strip()
        mfr_part_number = str(row["Mfr. #:"]).strip()
        description = str(row.get("Desc.:", "")).strip()
        
        # Parse quantity
        quantity = 0
        if pd.notna(row.get("Order Qty.")):
            try:
                quantity = int(row["Order Qty."])
            except (ValueError, TypeError):
                quantity = 0
        
        # Parse price
        unit_price = 0.0
        if pd.notna(row.get("Price (USD)")):
            price_str = str(row["Price (USD)"]).strip()
            # Remove currency symbols and parse
            price_str = re.sub(r'[$,]', '', price_str)
            try:
                unit_price = float(price_str)
            except (ValueError, TypeError):
                unit_price = 0.0
        
        # Parse extended price
        extended_price = 0.0
        if pd.notna(row.get("Ext. (USD)")):
            ext_price_str = str(row["Ext. (USD)"]).strip()
            # Remove currency symbols and parse
            ext_price_str = re.sub(r'[$,]', '', ext_price_str)
            try:
                extended_price = float(ext_price_str)
            except (ValueError, TypeError):
                extended_price = 0.0
        
        # Create unique part name using manufacturer part number
        part_name = mfr_part_number
        
        # Build part data with pricing information
        part_data = {
            "part_name": part_name,
            "part_number": mouser_part_number,  # Use Mouser part number as primary
            "description": description,
            "quantity": quantity,
            "supplier": self.supplier_name,
            "additional_properties": {
                "manufacturer_part_number": mfr_part_number,
                "description": description,
                "unit_price": unit_price,
                "extended_price": extended_price,
                "supplier_part_number": mouser_part_number
            }
        }
        
        return part_data
    
    def get_preview_data(self, file_path: str = None, file_content: bytes = None, limit: int = 5) -> Dict[str, Any]:
        """Get preview data for the XLS file."""
        try:
            if file_path:
                df = pd.read_excel(file_path)
            elif file_content:
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file.flush()
                    
                    try:
                        df = pd.read_excel(tmp_file.name)
                    finally:
                        os.unlink(tmp_file.name)
            else:
                raise ValueError("Either file_path or file_content must be provided")
            
            # Clean and prepare preview data
            df = df.dropna(how='all')
            preview_rows = df.head(limit).fillna('').to_dict('records')
            
            # Get parsed preview
            parsing_result = self._parse_dataframe(df.head(limit))
            parsed_preview = []
            for part in parsing_result.parts:
                parsed_preview.append({
                    "name": part["part_name"],
                    "part_number": part["part_number"],
                    "quantity": part["quantity"],
                    "supplier": part["supplier"],
                    "additional_properties": part["additional_properties"]
                })
            
            return {
                "detected_parser": self.supplier_name.lower(),
                "type_info": f"{self.supplier_name} XLS Order File",
                "headers": df.columns.tolist(),
                "preview_rows": preview_rows,
                "parsed_preview": parsed_preview,
                "total_rows": len(df),
                "is_supported": True,
                "validation_errors": [],
                "file_format": "xls"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate preview for Mouser XLS: {e}")
            return {
                "detected_parser": None,
                "type_info": "Unknown",
                "headers": [],
                "preview_rows": [],
                "parsed_preview": [],
                "total_rows": 0,
                "is_supported": False,
                "validation_errors": [f"Failed to read XLS file: {str(e)}"],
                "file_format": "xls",
                "error": str(e)
            }