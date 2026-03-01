"""
Generic web scraping utility for extracting data from supplier websites.

This module provides a robust web scraping framework with:
- BeautifulSoup for HTML parsing
- Playwright for JavaScript-rendered content
- Rate limiting and caching
- Error handling and retries
"""

import re
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import hashlib
import json

import aiohttp
from bs4 import BeautifulSoup
from functools import lru_cache

logger = logging.getLogger(__name__)

# Simple in-memory cache for scraped data
SCRAPE_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_MINUTES = 15


class WebScraper:
    """
    Generic web scraping utility with rate limiting and caching.

    Supports both simple HTML parsing and JavaScript-rendered content.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._playwright_browser = None
        self._last_request_time: Dict[str, datetime] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if not self._session or self._session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session

    async def _apply_rate_limit(self, domain: str, delay_seconds: float = 1.0):
        """Apply rate limiting per domain."""
        if domain in self._last_request_time:
            time_since_last = (datetime.now() - self._last_request_time[domain]).total_seconds()
            if time_since_last < delay_seconds:
                await asyncio.sleep(delay_seconds - time_since_last)
        self._last_request_time[domain] = datetime.now()

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key for a URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cached_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached data if available and not expired."""
        cache_key = self._get_cache_key(url)
        if cache_key in SCRAPE_CACHE:
            cached = SCRAPE_CACHE[cache_key]
            if datetime.now() - cached["timestamp"] < timedelta(minutes=CACHE_TTL_MINUTES):
                logger.info(f"Using cached data for {url}")
                return cached["data"]
        return None

    def _set_cached_data(self, url: str, data: Dict[str, Any]):
        """Store data in cache."""
        cache_key = self._get_cache_key(url)
        SCRAPE_CACHE[cache_key] = {"data": data, "timestamp": datetime.now()}

    async def scrape_simple(self, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Simple HTML scraping using BeautifulSoup.

        Args:
            url: URL to scrape
            selectors: Dictionary mapping field names to CSS selectors

        Returns:
            Dictionary with extracted data
        """
        # Check cache first
        cached = self._get_cached_data(url)
        if cached:
            return cached

        # Apply rate limiting
        domain = urlparse(url).netloc
        await self._apply_rate_limit(domain)

        session = None
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch {url}: Status {response.status}")
                    return {}

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Log the page title to see if we got actual content
                title = soup.find("title")
                if title:
                    logger.info(f"Page title: {title.get_text()[:100]}")
                else:
                    logger.warning("No title found in HTML - might be blocked or empty page")

                result = {}
                for field, selector in selectors.items():
                    try:
                        if selector.startswith("//"):
                            # XPath selector - BeautifulSoup doesn't support XPath natively
                            logger.warning(f"XPath selectors not supported in simple mode: {selector}")
                            continue

                        element = soup.select_one(selector)
                        if element:
                            # Extract text content
                            text = element.get_text(strip=True)
                            result[field] = self.clean_text(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract {field} with selector {selector}: {e}")

                # Cache the result
                self._set_cached_data(url, result)
                return result

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {}
        finally:
            # Don't close the session here as it's reused
            # It will be closed in the close() method
            pass

    async def scrape_with_playwright(
        self,
        url: str,
        selectors: Dict[str, str],
        wait_for_selector: str = None,
        force_refresh: bool = False,
        interaction_callback=None,
        headless: bool = True,
    ) -> Dict[str, Any]:
        """
        Scrape JavaScript-rendered content using Playwright.

        Args:
            url: URL to scrape
            selectors: Dictionary mapping field names to CSS selectors
            wait_for_selector: Optional selector to wait for before extracting data
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with extracted data
        """
        # Check cache first (unless force_refresh is True)
        if not force_refresh:
            cached = self._get_cached_data(url)
            if cached:
                logger.info(f"Returning cached data for {url}")
                return cached
        else:
            logger.info(f"Force refresh enabled, bypassing cache for {url}")

        # Apply rate limiting
        domain = urlparse(url).netloc
        await self._apply_rate_limit(domain, delay_seconds=2.0)  # Longer delay for JS rendering

        try:
            # Import playwright here to avoid dependency if not needed
            from playwright.async_api import async_playwright

            result = {}
            async with async_playwright() as p:
                # Launch browser with args to make it less detectable
                browser = await p.chromium.launch(
                    headless=headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--exclude-switches=enable-automation",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                    ],
                )

                # Create context with viewport and other settings
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                page = await context.new_page()

                # Add anti-detection script
                await page.add_init_script(
                    """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });

                    // Mock chrome object
                    window.chrome = {
                        runtime: {},
                        app: {isInstalled: false}
                    };
                """
                )

                # Set a realistic user agent and headers to appear more like a real browser
                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )

                # Navigate to page with better wait strategy
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as e:
                    logger.warning(f"Navigation timeout or error: {e}")

                # Execute custom interaction if provided (e.g., search or verify landing)
                if interaction_callback:
                    print(f"DEBUG: Executing custom interaction callback for {url}")
                    logger.info("Executing custom interaction callback")
                    await interaction_callback(page)
                else:
                    print(f"DEBUG: No interaction callback provided for {url}")

                # Wait for specific element if provided
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=10000)
                    except:
                        logger.warning(f"Timeout waiting for selector: {wait_for_selector}")

                # Add small delay to allow any lazy-loaded content to appear
                await page.wait_for_timeout(2000)

                # Extract data using selectors
                for field, selector in selectors.items():
                    try:
                        # Special handling for spec tables - extract all rows
                        if field == "spec_table" and (
                            "table" in selector.lower()
                            or "spec" in selector.lower()
                            or "tbody" in selector.lower()
                            or "tr" in selector.lower()
                        ):
                            # Try to extract table data from rows directly
                            rows = await page.query_selector_all(selector)
                            if rows:
                                table_data = {}
                                for row in rows:
                                    # Look for cells within each row
                                    cells = await row.query_selector_all("td")
                                    if len(cells) >= 2:
                                        label = await cells[0].text_content()
                                        value = await cells[1].text_content()
                                        if label and value:
                                            key = self._normalize_key(self.clean_text(label))
                                            table_data[key] = self.clean_text(value)
                                if table_data:
                                    result[field] = table_data
                                    logger.info(f"Extracted {len(table_data)} specifications from table")
                        # Special handling for images - extract src attribute
                        elif field == "image" and ("img" in selector.lower()):
                            element = await page.query_selector(selector)
                            if element:
                                # Try to get src attribute
                                src = await element.get_attribute("src")
                                if src:
                                    result[field] = src
                                    logger.info(f"Extracted image URL: {src}")
                        # Special handling for links - extract href attribute
                        elif selector.startswith("a[") or selector.startswith("a:"):
                            logger.debug(f"Attempting to extract link for field '{field}' with selector: {selector}")
                            element = await page.query_selector(selector)
                            if element:
                                # Try to get href attribute
                                href = await element.get_attribute("href")
                                if href:
                                    result[field] = href
                                    logger.info(f"Extracted {field} link URL: {href}")
                                else:
                                    logger.warning(f"Found element for {field} but no href attribute")
                            else:
                                logger.warning(f"No element found for {field} with selector: {selector}")
                        else:
                            # Normal text extraction
                            element = await page.query_selector(selector)
                            if element:
                                text = await element.text_content()
                                if text:
                                    result[field] = self.clean_text(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract {field} with selector {selector}: {e}")

                await context.close()
                await browser.close()

            # Cache the result
            self._set_cached_data(url, result)
            return result

        except ImportError:
            logger.error(
                "Playwright not installed. Install with: pip install playwright && playwright install chromium"
            )
            # Fall back to simple scraping
            return await self.scrape_simple(url, selectors)
        except Exception as e:
            error_msg = str(e)
            # Check if it's a browser not installed error
            if "Executable doesn't exist" in error_msg or "browser executable" in error_msg.lower():
                logger.warning(f"Browser not installed, falling back to simple scraping: {error_msg}")
                result = await self.scrape_simple(url, selectors)
                logger.info(f"Simple scraping result: {result}")
                return result
            logger.error(f"Error scraping {url} with Playwright: {e}")
            return {}

    async def _extract_table_playwright(self, page, table_selector: str) -> Dict[str, str]:
        """Extract data from a table using Playwright."""
        try:
            # Get all rows in the table
            rows = await page.query_selector_all(f"{table_selector} tr")

            table_data = {}
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) >= 2:
                    # Assume first cell is label, second is value
                    label = await cells[0].text_content()
                    value = await cells[1].text_content()
                    if label and value:
                        key = self._normalize_key(self.clean_text(label))
                        table_data[key] = self.clean_text(value)

            return table_data
        except Exception as e:
            logger.error(f"Error extracting table: {e}")
            return {}

    def extract_table_data(self, html: str, table_selector: str) -> Dict[str, str]:
        """
        Extract structured data from an HTML table.

        Args:
            html: HTML content containing the table
            table_selector: CSS selector for the table

        Returns:
            Dictionary with table data (label -> value)
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one(table_selector)

        if not table:
            return {}

        data = {}
        rows = table.find_all("tr")

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                # Assume first cell is label, second is value
                label = self.clean_text(cells[0].get_text())
                value = self.clean_text(cells[1].get_text())
                if label and value:
                    key = self._normalize_key(label)
                    data[key] = value

        return data

    def clean_text(self, text: str) -> str:
        """Clean and normalize scraped text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove leading/trailing whitespace
        text = text.strip()
        # Remove zero-width spaces and other invisible characters
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

        return text

    def _normalize_key(self, text: str) -> str:
        """Normalize a text string to be used as a dictionary key."""
        # Convert to lowercase
        key = text.lower()
        # Replace spaces and special characters with underscores
        key = re.sub(r"[^a-z0-9]+", "_", key)
        # Remove leading/trailing underscores
        key = key.strip("_")
        return key

    def parse_price(self, price_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse price information from text.

        Args:
            price_text: Text containing price information (e.g., "$19.04 per pack of 100")

        Returns:
            Dictionary with price, currency, and quantity information
        """
        if not price_text:
            return None

        # Common price patterns
        patterns = [
            r"\$?([\d,]+\.?\d*)\s*(?:per\s+)?(?:pack\s+of\s+)?(\d+)?",
            r"([\d,]+\.?\d*)\s*([A-Z]{3})",  # e.g., "19.04 USD"
        ]

        for pattern in patterns:
            match = re.search(pattern, price_text, re.IGNORECASE)
            if match:
                price = float(match.group(1).replace(",", ""))
                quantity = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 1

                return {
                    "price": price,
                    "currency": "USD",  # Default to USD
                    "quantity": quantity,
                    "unit_price": price / quantity,
                    "original_text": price_text,
                }

        return {"original_text": price_text}

    async def close(self):
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()

        if self._playwright_browser:
            await self._playwright_browser.close()
