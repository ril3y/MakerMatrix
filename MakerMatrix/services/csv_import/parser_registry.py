"""
Dynamic CSV Parser Registry

Automatically discovers and registers all CSV parser classes in the csv_import directory.
No need to manually register or hardcode parser names - just drop a new parser
class into the directory and it becomes available.
"""

import os
import importlib
import inspect
from typing import Dict, Type, List, Optional, Any
from pathlib import Path
import logging

from .base_parser import BaseCSVParser

logger = logging.getLogger(__name__)


class CSVParserRegistry:
    """
    Dynamically discovers and manages CSV parser classes
    """
    
    def __init__(self):
        self._parsers: Dict[str, Type[BaseCSVParser]] = {}
        self._discover_parsers()
    
    def _discover_parsers(self):
        """
        Automatically discover all CSV parser classes in the csv_import directory
        """
        csv_import_dir = Path(__file__).parent
        
        # Find all Python files in the csv_import directory
        for file_path in csv_import_dir.glob("*.py"):
            if file_path.name.startswith("_") or file_path.name in ["base_parser.py", "parser_registry.py"]:
                continue
                
            module_name = file_path.stem
            try:
                # Import the module dynamically
                module = importlib.import_module(f".{module_name}", package=__package__)
                
                # Find all classes that inherit from BaseCSVParser
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseCSVParser) and 
                        obj != BaseCSVParser and 
                        not inspect.isabstract(obj)):
                        
                        # Create a temporary instance to get parser info
                        try:
                            # Try different initialization strategies for different parser types
                            temp_instance = self._create_temp_parser(obj)
                            if temp_instance:
                                parser_type = temp_instance.parser_type
                                self._parsers[parser_type] = obj
                                logger.info(f"Discovered CSV parser: {parser_type} -> {obj.__name__}")
                        except Exception as e:
                            logger.warning(f"Failed to initialize parser {obj.__name__}: {e}")
                        
            except Exception as e:
                logger.warning(f"Failed to import CSV parser module {module_name}: {e}")
    
    def _create_temp_parser(self, parser_class: Type[BaseCSVParser]) -> Optional[BaseCSVParser]:
        """
        Create a temporary parser instance for getting parser info
        
        Args:
            parser_class: Parser class to instantiate
            
        Returns:
            Temporary parser instance or None if creation fails
        """
        # Use the intelligent parser creation method
        return self._create_parser_instance(parser_class, download_config={'download_datasheets': False, 'download_images': False})
    
    def get_parser_class(self, parser_type: str) -> Optional[Type[BaseCSVParser]]:
        """
        Get a parser class by type
        
        Args:
            parser_type: Type of the parser (e.g., 'lcsc', 'digikey', 'mouser')
            
        Returns:
            Parser class or None if not found
        """
        return self._parsers.get(parser_type.lower())
    
    def get_available_parser_types(self) -> List[str]:
        """
        Get list of available parser types
        
        Returns:
            List of parser type names
        """
        return list(self._parsers.keys())
    
    def create_parser(self, parser_type: str, **kwargs) -> Optional[BaseCSVParser]:
        """
        Create an instance of a parser with intelligent parameter handling
        
        Args:
            parser_type: Type of the parser
            **kwargs: Arguments to pass to the parser constructor
            
        Returns:
            Parser instance or None if parser type not found
        """
        parser_class = self.get_parser_class(parser_type)
        if parser_class:
            # Use the same intelligent initialization as temp parser creation
            return self._create_parser_instance(parser_class, **kwargs)
        return None
    
    def _create_parser_instance(self, parser_class: Type[BaseCSVParser], **kwargs) -> Optional[BaseCSVParser]:
        """
        Create a parser instance with intelligent parameter handling
        
        Args:
            parser_class: Parser class to instantiate
            **kwargs: Keyword arguments to try passing
            
        Returns:
            Parser instance or None if creation fails
        """
        try:
            # Strategy 1: Try with provided kwargs
            if kwargs:
                try:
                    return parser_class(**kwargs)
                except TypeError:
                    # If kwargs failed, try other strategies
                    pass
            
            # Strategy 2: No parameters (most common)
            try:
                return parser_class()
            except TypeError:
                pass
            
            # Strategy 3: Try with download_config parameter (for parsers that support it)
            if 'download_config' in kwargs:
                try:
                    return parser_class(download_config=kwargs['download_config'])
                except TypeError:
                    pass
            
            # Strategy 4: Default construction
            return parser_class()
            
        except Exception as e:
            logger.debug(f"Failed to create parser instance of {parser_class.__name__}: {e}")
            return None
    
    def get_all_parsers(self, **kwargs) -> List[BaseCSVParser]:
        """
        Create instances of all available parsers
        
        Args:
            **kwargs: Arguments to pass to parser constructors
            
        Returns:
            List of parser instances
        """
        parsers = []
        for parser_type in self._parsers.keys():
            parser = self.create_parser(parser_type, **kwargs)
            if parser:
                parsers.append(parser)
        return parsers
    
    def get_parser_info(self, parser_type: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific parser
        
        Args:
            parser_type: Type of the parser
            
        Returns:
            Parser information dictionary or None if not found
        """
        parser = self.create_parser(parser_type)
        if parser:
            return parser.get_info()
        return None
    
    def get_all_parser_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all available parsers
        
        Returns:
            List of parser information dictionaries
        """
        info_list = []
        for parser_type in self._parsers.keys():
            info = self.get_parser_info(parser_type)
            if info:
                info_list.append(info)
        return info_list
    
    def reload_parsers(self):
        """
        Reload all parsers (useful for development)
        """
        self._parsers.clear()
        self._discover_parsers()


# Global registry instance
csv_parser_registry = CSVParserRegistry()


# Convenience functions
def get_parser_class(parser_type: str) -> Optional[Type[BaseCSVParser]]:
    """Get a parser class by type"""
    return csv_parser_registry.get_parser_class(parser_type)


def get_available_parser_types() -> List[str]:
    """Get list of available parser types"""
    return csv_parser_registry.get_available_parser_types()


def create_parser(parser_type: str, **kwargs) -> Optional[BaseCSVParser]:
    """Create a parser instance"""
    return csv_parser_registry.create_parser(parser_type, **kwargs)


def get_all_parsers(**kwargs) -> List[BaseCSVParser]:
    """Get instances of all available parsers"""
    return csv_parser_registry.get_all_parsers(**kwargs)


def get_parser_info(parser_type: str) -> Optional[Dict[str, Any]]:
    """Get information about a parser"""
    return csv_parser_registry.get_parser_info(parser_type)


def get_all_parser_info() -> List[Dict[str, Any]]:
    """Get information about all parsers"""
    return csv_parser_registry.get_all_parser_info()


def reload_parsers():
    """Reload all parsers"""
    csv_parser_registry.reload_parsers()