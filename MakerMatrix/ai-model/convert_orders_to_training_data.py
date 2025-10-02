#!/usr/bin/env python3
"""
Convert DigiKey and Mouser order files to training data format.

This script:
1. Reads DigiKey CSV and Mouser XLS order files
2. Extracts unique part descriptions
3. Uses LLM to extract specifications
4. Saves to JSONL format for review in the web UI
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

try:
    import xlrd
except ImportError:
    print("Warning: xlrd not installed. Mouser XLS support disabled.")
    print("Install with: pip install xlrd")
    xlrd = None

# Import the labeler from label_with_llm.py
sys.path.insert(0, str(Path(__file__).parent))
from label_with_llm import OllamaLabeler


def parse_digikey_csv(csv_path: Path) -> List[Dict]:
    """
    Parse DigiKey order CSV file.

    Returns:
        List of component dictionaries
    """
    components = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            description = row.get('Description', '').strip()
            mpn = row.get('Manufacturer Part Number', '').strip()
            manufacturer = row.get('Manufacturer', '').strip()

            if not description:
                continue

            # Create component dict in format similar to LCSC
            component = {
                'description': description,
                'mpn': mpn,
                'manufacturer': manufacturer,
                'supplier': 'DigiKey',
                'source_file': csv_path.name,
                'main_category': 'Unknown',  # DigiKey doesn't provide this
                'subcategory': 'Unknown',
                'package': 'Unknown',
                'attributes': {}
            }

            components.append(component)

    return components


def parse_mouser_xls(xls_path: Path) -> List[Dict]:
    """
    Parse Mouser order XLS file.

    Returns:
        List of component dictionaries
    """
    if xlrd is None:
        print(f"Skipping {xls_path.name} - xlrd not installed")
        return []

    components = []

    try:
        workbook = xlrd.open_workbook(xls_path)
        sheet = workbook.sheet_by_index(0)

        # Find header row (usually first row)
        headers = [str(sheet.cell_value(0, col)).strip() for col in range(sheet.ncols)]

        # Find column indices (Mouser uses "Desc.:" with colon)
        desc_col = next((i for i, h in enumerate(headers) if 'Desc' in h), None)
        mpn_col = next((i for i, h in enumerate(headers) if 'Mfr. #' in h or 'Part' in h), None)
        mfr_col = None  # Mouser doesn't have manufacturer name column

        if desc_col is None:
            print(f"Warning: Could not find Description column in {xls_path.name}")
            return []

        # Read data rows
        for row_idx in range(1, sheet.nrows):
            description = str(sheet.cell_value(row_idx, desc_col)).strip() if desc_col is not None else ''
            mpn = str(sheet.cell_value(row_idx, mpn_col)).strip() if mpn_col is not None else ''
            manufacturer = str(sheet.cell_value(row_idx, mfr_col)).strip() if mfr_col is not None else ''

            if not description or description == '':
                continue

            # Create component dict
            component = {
                'description': description,
                'mpn': mpn,
                'manufacturer': manufacturer,
                'supplier': 'Mouser',
                'source_file': xls_path.name,
                'main_category': 'Unknown',
                'subcategory': 'Unknown',
                'package': 'Unknown',
                'attributes': {}
            }

            components.append(component)

    except Exception as e:
        print(f"Error reading {xls_path.name}: {e}")
        return []

    return components


def deduplicate_components(components: List[Dict]) -> List[Dict]:
    """
    Remove duplicate components based on description.
    Keep the first occurrence of each unique description.
    """
    seen = set()
    unique_components = []

    for component in components:
        desc = component['description'].lower().strip()
        if desc not in seen and desc:
            seen.add(desc)
            unique_components.append(component)

    return unique_components


def main():
    parser = argparse.ArgumentParser(
        description='Convert order files to training data format'
    )
    parser.add_argument(
        '--orders-dir',
        type=Path,
        default=Path('orders'),
        help='Directory containing order files'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/oneshot-examples'),
        help='Output directory for training data'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of components to process'
    )
    parser.add_argument(
        '--digikey-only',
        action='store_true',
        help='Process only DigiKey files'
    )
    parser.add_argument(
        '--mouser-only',
        action='store_true',
        help='Process only Mouser files'
    )
    parser.add_argument(
        '--model',
        default='mistral:7b-instruct',
        help='Ollama model to use for extraction'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )

    args = parser.parse_args()

    orders_dir = args.orders_dir
    output_dir = args.output_dir

    if not orders_dir.exists():
        print(f"Error: Orders directory not found: {orders_dir}")
        return 1

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect all components
    all_components = []

    # Process DigiKey files
    if not args.mouser_only:
        print("\n" + "="*70)
        print("PROCESSING DIGIKEY FILES")
        print("="*70 + "\n")

        digikey_files = sorted(orders_dir.glob("DK_PRODUCTS_*.csv"))
        print(f"Found {len(digikey_files)} DigiKey files\n")

        for csv_file in digikey_files:
            print(f"Reading {csv_file.name}...")
            components = parse_digikey_csv(csv_file)
            all_components.extend(components)
            print(f"  → {len(components)} parts")

    # Process Mouser files
    if not args.digikey_only:
        print("\n" + "="*70)
        print("PROCESSING MOUSER FILES")
        print("="*70 + "\n")

        mouser_files = sorted(orders_dir.glob("*.xls"))
        print(f"Found {len(mouser_files)} Mouser files\n")

        for xls_file in mouser_files:
            print(f"Reading {xls_file.name}...")
            components = parse_mouser_xls(xls_file)
            all_components.extend(components)
            print(f"  → {len(components)} parts")

    # Deduplicate
    print("\n" + "="*70)
    print("DEDUPLICATION")
    print("="*70 + "\n")

    print(f"Total parts before deduplication: {len(all_components)}")
    unique_components = deduplicate_components(all_components)
    print(f"Unique parts after deduplication: {len(unique_components)}")
    print(f"Removed {len(all_components) - len(unique_components)} duplicates\n")

    # Apply limit
    if args.limit:
        unique_components = unique_components[:args.limit]
        print(f"Limited to {len(unique_components)} parts\n")

    # Show summary by supplier
    supplier_counts = defaultdict(int)
    for comp in unique_components:
        supplier_counts[comp['supplier']] += 1

    print("Parts by supplier:")
    for supplier, count in sorted(supplier_counts.items()):
        print(f"  {supplier}: {count}")

    if args.dry_run:
        print("\n[DRY RUN] Would process these components but not extracting specs")
        return 0

    # Extract specifications using LLM
    print("\n" + "="*70)
    print("LLM EXTRACTION")
    print("="*70 + "\n")

    print(f"Using model: {args.model}")
    print("Initializing labeler...")

    labeler = OllamaLabeler(model=args.model)

    # Process each component
    results = []
    skipped = 0

    for i, component in enumerate(unique_components, 1):
        print(f"\n[{i}/{len(unique_components)}] {component['description'][:60]}...")

        # Extract specs
        specs = labeler.extract_with_ollama(labeler.build_prompt(component))

        if specs:
            # Add to results in format compatible with review UI
            result = {
                'description': component['description'],
                'mpn': component['mpn'],
                'manufacturer': component['manufacturer'],
                'supplier': component['supplier'],
                'source_file': component['source_file'],
                'main_category': component['main_category'],
                'subcategory': component['subcategory'],
                'package': component['package'],
                'extracted_specs': specs,
                'labeled_at': datetime.now().timestamp(),
                'labeled_by': args.model,
                'review_status': 'pending'
            }
            results.append(result)
            print(f"  ✓ Extracted {len(specs)} fields")
        else:
            skipped += 1
            print(f"  ✗ Extraction failed")

    # Save results
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70 + "\n")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"orders_extracted_{timestamp}.jsonl"

    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f"✓ Saved {len(results)} components to {output_file}")
    print(f"✗ Skipped {skipped} components (extraction failed)")
    print(f"\nNext steps:")
    print(f"1. Run: python label_with_llm.py --mode web --model {args.model}")
    print(f"2. Review and correct the extractions in the web UI")
    print(f"3. Save corrections to create high-quality training data")

    return 0


if __name__ == '__main__':
    sys.exit(main())
