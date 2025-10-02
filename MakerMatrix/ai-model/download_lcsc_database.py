#!/usr/bin/env python3
"""
Download and extract the LCSC parts database from jlcparts.

This script downloads the complete LCSC component database which contains
hundreds of thousands of component descriptions perfect for training ML models.

Usage:
    python download_lcsc_database.py
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


class LCSCDatabaseDownloader:
    """Downloads and extracts the LCSC parts database from jlcparts."""

    BASE_URL = "https://yaqwsx.github.io/jlcparts/data"
    CACHE_FILES = ["cache.zip"] + [f"cache.z{i:02d}" for i in range(1, 20)]  # Try up to z19

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to download files to. Defaults to ./data/lcsc_raw
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "data" / "lcsc_raw"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def check_dependencies(self) -> bool:
        """Check if required tools are installed."""
        print("Checking dependencies...")

        # Check for wget
        try:
            subprocess.run(["wget", "--version"],
                          capture_output=True, check=True)
            print("  ✓ wget is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  ✗ wget is not installed")
            print("    Install with: sudo apt install wget  (Ubuntu/Debian)")
            print("                  brew install wget      (macOS)")
            return False

        # Check for 7z
        try:
            subprocess.run(["7z"],
                          capture_output=True, check=False)
            print("  ✓ 7z is installed")
        except FileNotFoundError:
            print("  ✗ 7z is not installed")
            print("    Install with: sudo apt install p7zip-full  (Ubuntu/Debian)")
            print("                  brew install p7zip           (macOS)")
            return False

        return True

    def download_files(self) -> bool:
        """Download all cache files from jlcparts."""
        print(f"\nDownloading files to: {self.output_dir}")

        for filename in self.CACHE_FILES:
            url = f"{self.BASE_URL}/{filename}"
            output_path = self.output_dir / filename

            # Skip if already downloaded
            if output_path.exists():
                print(f"  ↷ {filename} already exists, skipping")
                continue

            print(f"  ⬇ Downloading {filename}...")

            try:
                result = subprocess.run(
                    ["wget", "-q", "--show-progress", "-O", str(output_path), url],
                    check=True
                )
                print(f"    ✓ Downloaded {filename}")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Failed to download {filename}: {e}")
                return False

        return True

    def extract_database(self) -> bool:
        """Extract the SQLite database from the downloaded files."""
        print("\nExtracting database...")

        cache_zip = self.output_dir / "cache.zip"

        if not cache_zip.exists():
            print(f"  ✗ cache.zip not found at {cache_zip}")
            return False

        try:
            # Extract using 7z
            result = subprocess.run(
                ["7z", "x", "-y", str(cache_zip), f"-o{self.output_dir}"],
                capture_output=True,
                check=True,
                cwd=str(self.output_dir)
            )
            print("  ✓ Extraction complete")

            # Check for SQLite database
            db_path = self.output_dir / "cache.sqlite3"
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ Database found: cache.sqlite3 ({size_mb:.1f} MB)")
                return True
            else:
                print("  ⚠ Warning: cache.sqlite3 not found after extraction")
                print("    Checking for alternative database files...")

                # List all .sqlite* files
                sqlite_files = list(self.output_dir.glob("*.sqlite*"))
                if sqlite_files:
                    for f in sqlite_files:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        print(f"    Found: {f.name} ({size_mb:.1f} MB)")
                    return True
                else:
                    print("    ✗ No SQLite database files found")
                    return False

        except subprocess.CalledProcessError as e:
            print(f"  ✗ Extraction failed: {e}")
            print(f"    stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
            return False

    def inspect_database(self) -> None:
        """Inspect the downloaded database to see what's inside."""
        import sqlite3

        db_path = self.output_dir / "cache.sqlite3"

        if not db_path.exists():
            print(f"\n⚠ Database not found at {db_path}")
            return

        print("\n" + "="*60)
        print("DATABASE INSPECTION")
        print("="*60)

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            print(f"\nTables found: {len(tables)}")
            for table in tables:
                table_name = table[0]
                print(f"\n  📊 Table: {table_name}")

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"     Rows: {count:,}")

                # Get column info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"     Columns: {len(columns)}")
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    print(f"       - {col_name} ({col_type})")

                # Sample 3 rows
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                if rows:
                    print(f"\n     Sample data:")
                    for i, row in enumerate(rows, 1):
                        print(f"       Row {i}: {row[:5]}...")  # First 5 fields

            conn.close()

            print("\n" + "="*60)
            print(f"✓ Database ready for use at: {db_path}")
            print("="*60)

        except Exception as e:
            print(f"\n✗ Failed to inspect database: {e}")

    def cleanup_download_files(self) -> None:
        """Remove the downloaded zip files to save space."""
        print("\nCleaning up download files...")

        removed_size = 0
        for filename in self.CACHE_FILES:
            file_path = self.output_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                file_path.unlink()
                removed_size += size
                print(f"  ✓ Removed {filename}")

        if removed_size > 0:
            print(f"  Freed {removed_size / (1024 * 1024):.1f} MB")

    def run(self, cleanup: bool = True) -> bool:
        """
        Run the complete download and extraction process.

        Args:
            cleanup: Whether to remove download files after extraction

        Returns:
            True if successful, False otherwise
        """
        print("="*60)
        print("LCSC Database Downloader")
        print("="*60)

        # Check dependencies
        if not self.check_dependencies():
            return False

        # Download files
        if not self.download_files():
            return False

        # Extract database
        if not self.extract_database():
            return False

        # Inspect what we got
        try:
            self.inspect_database()
        except ImportError:
            print("\n⚠ sqlite3 module not available for inspection")
            print("  (Database downloaded successfully but can't inspect)")

        # Optional cleanup
        if cleanup:
            self.cleanup_download_files()

        print("\n✅ LCSC database download complete!")
        return True


def main():
    """Main entry point."""
    downloader = LCSCDatabaseDownloader()

    success = downloader.run(cleanup=True)

    if success:
        print("\nNext steps:")
        print("  1. Run: python extract_training_data.py")
        print("  2. Run: python label_with_llm.py")
        print("  3. Run: python train_model.py")
        sys.exit(0)
    else:
        print("\n✗ Download failed. Please check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
