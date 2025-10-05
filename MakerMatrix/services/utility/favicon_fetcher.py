"""
Favicon Fetcher Service

Automatically fetches and stores favicons from supplier websites.
"""

import logging
import aiohttp
import uuid
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

logger = logging.getLogger(__name__)


class FaviconFetcherService:
    """Service for fetching and storing supplier favicons"""

    def __init__(self, static_images_dir: str = "MakerMatrix/services/static/images"):
        self.static_images_dir = Path(static_images_dir)
        self.static_images_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_and_store_favicon(self, website_url: str, supplier_name: str) -> Optional[str]:
        """
        Fetch favicon from website and store locally.

        Args:
            website_url: The supplier's website URL
            supplier_name: Name of the supplier (for filename)

        Returns:
            Local image URL path or None if failed
        """
        if not website_url:
            return None

        try:
            # Parse URL to get domain
            parsed = urlparse(website_url if website_url.startswith('http') else f'https://{website_url}')
            domain = parsed.netloc or parsed.path
            base_url = f"{parsed.scheme}://{domain}" if parsed.scheme else f"https://{domain}"

            logger.info(f"Fetching favicon for {supplier_name} from {domain}")

            # Try multiple favicon locations in order of preference
            favicon_urls = [
                f"https://www.google.com/s2/favicons?domain={domain}&sz=64",  # Try Google first - most reliable
                f"{base_url}/favicon.ico",
                f"{base_url}/favicon.png",
                f"{base_url}/apple-touch-icon.png",
                f"https://favicon.im/{domain}?larger=true",  # Alternative favicon service
            ]

            async with aiohttp.ClientSession() as session:
                for favicon_url in favicon_urls:
                    try:
                        logger.debug(f"Trying favicon URL: {favicon_url}")
                        async with session.get(favicon_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status == 200:
                                content = await response.read()

                                # Validate content (at least 100 bytes for a valid icon)
                                if len(content) < 100:
                                    logger.debug(f"Content too small ({len(content)} bytes), skipping")
                                    continue

                                # Determine file extension from content-type or URL
                                content_type = response.headers.get('content-type', '')
                                if 'png' in content_type or favicon_url.endswith('.png'):
                                    ext = 'png'
                                elif 'svg' in content_type or favicon_url.endswith('.svg'):
                                    ext = 'svg'
                                elif 'jpeg' in content_type or 'jpg' in content_type:
                                    ext = 'jpg'
                                else:
                                    ext = 'ico'

                                # Generate filename with UUID only (no supplier prefix)
                                file_id = str(uuid.uuid4())
                                filename = f"{file_id}.{ext}"
                                filepath = self.static_images_dir / filename

                                # Save file
                                with open(filepath, 'wb') as f:
                                    f.write(content)

                                logger.info(f"Successfully saved favicon for {supplier_name} to {filename}")

                                # Return the URL path that will be served by the utility endpoint
                                return f"/api/utility/get_image/{filename}"

                    except Exception as e:
                        logger.debug(f"Failed to fetch from {favicon_url}: {e}")
                        continue

            logger.warning(f"Could not fetch favicon for {supplier_name} from any source")
            return None

        except Exception as e:
            logger.error(f"Error fetching favicon for {supplier_name}: {e}")
            return None
