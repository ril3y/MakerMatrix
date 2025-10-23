"""
Web scraping utilities for supplier data extraction.

This module provides fallback web scraping functionality for suppliers
when API access is not available or not configured.
"""

from .web_scraper import WebScraper

__all__ = ["WebScraper"]
