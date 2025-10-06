#!/usr/bin/env python3
"""
Download favicons for built-in suppliers with proper names.
This script downloads and saves supplier favicons to the static images directory.
"""

import asyncio
import aiohttp
from pathlib import Path

# Built-in suppliers with their website URLs
BUILTIN_SUPPLIERS = {
    'lcsc': 'https://www.lcsc.com',
    'digikey': 'https://www.digikey.com',
    'mouser': 'https://www.mouser.com',
    'mcmaster-carr': 'https://www.mcmaster.com',
    'bolt-depot': 'https://www.boltdepot.com',
    'adafruit': 'https://www.adafruit.com',
    'alibaba': 'https://www.alibaba.com',
    'homedepot': 'https://www.homedepot.com',
    'temu': 'https://www.temu.com',
}


async def download_favicon(session, supplier_name: str, website_url: str, output_dir: Path):
    """Download favicon for a supplier"""
    from urllib.parse import urlparse

    parsed = urlparse(website_url if website_url.startswith('http') else f'https://{website_url}')
    domain = parsed.netloc or parsed.path
    base_url = f"{parsed.scheme}://{domain}" if parsed.scheme else f"https://{domain}"

    print(f"Fetching favicon for {supplier_name} from {domain}...")

    # Try multiple favicon locations
    favicon_urls = [
        f"{base_url}/favicon.ico",
        f"{base_url}/favicon.png",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=64",
    ]

    for favicon_url in favicon_urls:
        try:
            print(f"  Trying: {favicon_url}")
            async with session.get(favicon_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.read()

                    # Validate content
                    if len(content) < 100:
                        print(f"  Content too small ({len(content)} bytes), skipping")
                        continue

                    # Determine file extension
                    content_type = response.headers.get('content-type', '')
                    if 'png' in content_type or favicon_url.endswith('.png'):
                        ext = 'png'
                    elif 'svg' in content_type or favicon_url.endswith('.svg'):
                        ext = 'svg'
                    elif 'jpeg' in content_type or 'jpg' in content_type:
                        ext = 'jpg'
                    else:
                        ext = 'ico'

                    # Save with supplier name
                    filename = f"{supplier_name}.{ext}"
                    filepath = output_dir / filename

                    with open(filepath, 'wb') as f:
                        f.write(content)

                    print(f"  ✓ Saved to {filename} ({len(content)} bytes)")
                    return filename

        except Exception as e:
            print(f"  Failed: {e}")
            continue

    print(f"  ✗ Could not fetch favicon for {supplier_name}")
    return None


async def main():
    """Download all supplier favicons"""
    # Output directory
    output_dir = Path(__file__).parent.parent / "MakerMatrix" / "services" / "static" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}\n")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for supplier_name, website_url in BUILTIN_SUPPLIERS.items():
            tasks.append(download_favicon(session, supplier_name, website_url, output_dir))

        results = await asyncio.gather(*tasks)

    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    for supplier_name, filename in zip(BUILTIN_SUPPLIERS.keys(), results):
        status = f"✓ {filename}" if filename else "✗ Failed"
        print(f"{supplier_name:20s} {status}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
