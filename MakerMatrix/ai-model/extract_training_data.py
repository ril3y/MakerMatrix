#!/usr/bin/env python3
"""
Extract training data samples from the LCSC database.

This script intelligently samples component descriptions from the LCSC database,
focusing on diverse component types with good data quality.

Usage:
    python extract_training_data.py --sample-size 10000 --output data/training/samples.jsonl
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
import sys


class TrainingDataExtractor:
    """Extracts and samples component data from LCSC database for ML training."""

    def __init__(self, db_path: str):
        """
        Initialize the extractor.

        Args:
            db_path: Path to the LCSC SQLite database
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def get_category_distribution(self) -> List[Dict]:
        """Get distribution of parts across categories."""
        query = """
        SELECT
            cat.category as main_category,
            cat.subcategory,
            COUNT(*) as count
        FROM components c
        LEFT JOIN categories cat ON c.category_id = cat.id
        WHERE cat.category IS NOT NULL
        GROUP BY cat.category, cat.subcategory
        ORDER BY count DESC
        """

        self.cursor.execute(query)
        results = []

        for main_cat, subcat, count in self.cursor.fetchall():
            results.append({
                'main_category': main_cat,
                'subcategory': subcat,
                'count': count
            })

        return results

    def extract_component_data(self, row: tuple) -> Optional[Dict]:
        """
        Extract and parse component data from a database row.

        Args:
            row: Database row containing (extra_json, mfr, package, stock)

        Returns:
            Parsed component data or None if parsing fails
        """
        extra_json, mfr, package, stock = row

        try:
            extra = json.loads(extra_json) if extra_json else {}

            # Extract core fields
            title = extra.get('title', mfr)  # Fallback to MPN if no title
            category = extra.get('category', {})
            manufacturer = extra.get('manufacturer', {})

            # Build structured data
            data = {
                'title': title,
                'mpn': mfr,
                'package': package,
                'stock': stock,
                'main_category': category.get('name1'),
                'subcategory': category.get('name2'),
                'manufacturer': manufacturer.get('name'),
                'lcsc_number': extra.get('number'),
                'datasheet_url': extra.get('datasheet', {}).get('pdf') if isinstance(extra.get('datasheet'), dict) else None,
            }

            # Only return if we have meaningful data
            if data['title'] and data['main_category']:
                return data

            return None

        except (json.JSONDecodeError, AttributeError, TypeError):
            return None

    def sample_by_category(self,
                          category: str,
                          subcategory: Optional[str] = None,
                          sample_size: int = 100) -> List[Dict]:
        """
        Sample components from a specific category.

        Args:
            category: Main category name
            subcategory: Subcategory name (optional)
            sample_size: Number of samples to extract

        Returns:
            List of component data dictionaries
        """
        if subcategory:
            query = """
            SELECT c.extra, c.mfr, c.package, c.stock
            FROM components c
            LEFT JOIN categories cat ON c.category_id = cat.id
            WHERE cat.category = ? AND cat.subcategory = ?
            AND c.extra IS NOT NULL
            AND c.stock > 0
            ORDER BY RANDOM()
            LIMIT ?
            """
            self.cursor.execute(query, (category, subcategory, sample_size))
        else:
            query = """
            SELECT c.extra, c.mfr, c.package, c.stock
            FROM components c
            LEFT JOIN categories cat ON c.category_id = cat.id
            WHERE cat.category = ?
            AND c.extra IS NOT NULL
            AND c.stock > 0
            ORDER BY RANDOM()
            LIMIT ?
            """
            self.cursor.execute(query, (category, sample_size))

        samples = []
        for row in self.cursor.fetchall():
            data = self.extract_component_data(row)
            if data:
                samples.append(data)

        return samples

    def sample_diverse_components(self,
                                  total_samples: int = 10000,
                                  min_per_category: int = 50) -> List[Dict]:
        """
        Sample diverse components across all categories.

        This ensures good representation of different component types.

        Args:
            total_samples: Target total number of samples
            min_per_category: Minimum samples per category

        Returns:
            List of sampled component data
        """
        print(f"Analyzing category distribution...")
        categories = self.get_category_distribution()

        print(f"Found {len(categories)} category/subcategory combinations")
        print(f"Total parts in database: {sum(c['count'] for c in categories):,}")

        # Focus on major categories with good data
        target_categories = [
            'Resistors',
            'Capacitors',
            'Integrated Circuits (ICs)',
            'Diodes',
            'Transistors',
            'Inductors',
            'Connectors',
            'Optoelectronics',
            'Filters',
            'Power Management',
            'Interface',
            'Logic',
            'Memory',
            'Sensors',
            'RF Devices',
        ]

        all_samples = []

        # Calculate samples per category
        major_categories = [c for c in categories if c['main_category'] in target_categories]

        if not major_categories:
            print("⚠ Warning: No target categories found, sampling from all categories")
            major_categories = categories[:20]  # Top 20 categories

        samples_per_category = max(min_per_category, total_samples // len(major_categories))

        print(f"\nSampling {samples_per_category} parts from each of {len(major_categories)} categories...")

        for cat_info in major_categories:
            main_cat = cat_info['main_category']
            sub_cat = cat_info['subcategory']
            count = cat_info['count']

            print(f"  📦 {main_cat}/{sub_cat} ({count:,} parts)...", end=' ')

            samples = self.sample_by_category(
                category=main_cat,
                subcategory=sub_cat,
                sample_size=samples_per_category
            )

            all_samples.extend(samples)
            print(f"✓ {len(samples)} samples")

            # Stop if we have enough
            if len(all_samples) >= total_samples:
                break

        # Trim to exact size if over
        if len(all_samples) > total_samples:
            all_samples = all_samples[:total_samples]

        print(f"\n✓ Extracted {len(all_samples)} total samples")
        return all_samples

    def save_samples(self, samples: List[Dict], output_path: str, format: str = 'jsonl'):
        """
        Save samples to file.

        Args:
            samples: List of component data
            output_path: Output file path
            format: Output format ('jsonl', 'json', or 'csv')
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == 'jsonl':
            # JSONL format - one JSON object per line
            with open(output_file, 'w') as f:
                for sample in samples:
                    f.write(json.dumps(sample) + '\n')
            print(f"✓ Saved {len(samples)} samples to {output_file} (JSONL)")

        elif format == 'json':
            # Standard JSON array
            with open(output_file, 'w') as f:
                json.dump(samples, f, indent=2)
            print(f"✓ Saved {len(samples)} samples to {output_file} (JSON)")

        elif format == 'csv':
            # CSV format
            import csv
            with open(output_file, 'w', newline='') as f:
                if samples:
                    writer = csv.DictWriter(f, fieldnames=samples[0].keys())
                    writer.writeheader()
                    writer.writerows(samples)
            print(f"✓ Saved {len(samples)} samples to {output_file} (CSV)")

        else:
            raise ValueError(f"Unsupported format: {format}")

    def print_statistics(self, samples: List[Dict]):
        """Print statistics about extracted samples."""
        print("\n" + "="*60)
        print("EXTRACTION STATISTICS")
        print("="*60)

        # Count by main category
        category_counts = {}
        for sample in samples:
            cat = sample.get('main_category', 'Unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        print(f"\nSamples by category:")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat}: {count}")

        # Count by package
        package_counts = {}
        for sample in samples:
            pkg = sample.get('package', 'Unknown')
            package_counts[pkg] = package_counts.get(pkg, 0) + 1

        print(f"\nTop packages:")
        for pkg, count in sorted(package_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {pkg}: {count}")

        # Sample titles
        print(f"\nSample titles:")
        for i, sample in enumerate(samples[:5], 1):
            print(f"  {i}. {sample['title']}")
            print(f"     Category: {sample['main_category']}/{sample['subcategory']}")
            print(f"     Package: {sample['package']}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract training data from LCSC database'
    )
    parser.add_argument(
        '--db-path',
        default='data/lcsc_raw/cache.sqlite3',
        help='Path to LCSC database (default: data/lcsc_raw/cache.sqlite3)'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=10000,
        help='Number of samples to extract (default: 10000)'
    )
    parser.add_argument(
        '--output',
        default='data/training/samples.jsonl',
        help='Output file path (default: data/training/samples.jsonl)'
    )
    parser.add_argument(
        '--format',
        choices=['jsonl', 'json', 'csv'],
        default='jsonl',
        help='Output format (default: jsonl)'
    )
    parser.add_argument(
        '--min-per-category',
        type=int,
        default=50,
        help='Minimum samples per category (default: 50)'
    )

    args = parser.parse_args()

    print("="*60)
    print("LCSC Training Data Extraction")
    print("="*60)

    try:
        # Initialize extractor
        extractor = TrainingDataExtractor(args.db_path)

        # Extract samples
        samples = extractor.sample_diverse_components(
            total_samples=args.sample_size,
            min_per_category=args.min_per_category
        )

        # Print statistics
        extractor.print_statistics(samples)

        # Save to file
        extractor.save_samples(samples, args.output, args.format)

        # Close connection
        extractor.close()

        print("\n✅ Extraction complete!")
        print(f"\nNext step:")
        print(f"  python label_with_llm.py --input {args.output}")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
