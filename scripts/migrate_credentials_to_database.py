#!/usr/bin/env python3
"""
Migrate Supplier Credentials from .env to Database

This script migrates existing supplier API credentials from environment
variables (.env file) to database storage (plain text, protected by
password-encrypted backup ZIPs).

Usage:
    python scripts/migrate_credentials_to_database.py [--dry-run]

Options:
    --dry-run    Show what would be migrated without making changes
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import MakerMatrix modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlmodel import Session

from MakerMatrix.database.db import engine
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.repositories.supplier_config_repository import SupplierConfigRepository
from MakerMatrix.repositories.supplier_credentials_repository import SupplierCredentialsRepository


def load_env_credentials():
    """
    Load supplier credentials from environment variables

    Returns:
        Dictionary mapping supplier names to credential dictionaries
    """
    # Load .env file
    load_dotenv()

    credentials = {}

    # DigiKey
    digikey_client_id = os.getenv("DIGIKEY_CLIENT_ID")
    digikey_client_secret = os.getenv("DIGIKEY_CLIENT_SECRET")

    if digikey_client_id or digikey_client_secret:
        credentials["DIGIKEY"] = {}
        if digikey_client_id:
            credentials["DIGIKEY"]["client_id"] = digikey_client_id
        if digikey_client_secret:
            credentials["DIGIKEY"]["client_secret"] = digikey_client_secret

    # Mouser
    mouser_api_key = os.getenv("MOUSER_API_KEY")

    if mouser_api_key:
        credentials["MOUSER"] = {"api_key": mouser_api_key}

    # LCSC
    lcsc_api_key = os.getenv("LCSC_API_KEY")

    if lcsc_api_key:
        credentials["LCSC"] = {"api_key": lcsc_api_key}

    # McMaster-Carr
    mcmaster_username = os.getenv("MCMASTER_CARR_USERNAME")
    mcmaster_password = os.getenv("MCMASTER_CARR_PASSWORD")
    mcmaster_cert_path = os.getenv("MCMASTER_CARR_CLIENT_CERT_PATH")
    mcmaster_cert_password = os.getenv("MCMASTER_CARR_CLIENT_CERT_PASSWORD")

    if any([mcmaster_username, mcmaster_password, mcmaster_cert_path, mcmaster_cert_password]):
        credentials["MCMASTER"] = {}
        if mcmaster_username:
            credentials["MCMASTER"]["username"] = mcmaster_username
        if mcmaster_password:
            credentials["MCMASTER"]["password"] = mcmaster_password
        if mcmaster_cert_path:
            credentials["MCMASTER"]["cert_path"] = mcmaster_cert_path
        if mcmaster_cert_password:
            credentials["MCMASTER"]["cert_password"] = mcmaster_cert_password

    return credentials


def migrate_credentials(dry_run=False):
    """
    Migrate credentials from environment to database

    Args:
        dry_run: If True, only show what would be migrated without making changes
    """
    print("=" * 70)
    print("Supplier Credentials Migration - .env to Database (Plain Text)")
    print("=" * 70)
    print()

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    # Load credentials from environment
    print("Loading credentials from .env file...")
    env_credentials = load_env_credentials()

    if not env_credentials:
        print("✓ No credentials found in .env file")
        print()
        return

    print(f"Found credentials for {len(env_credentials)} suppliers:")
    for supplier_name, creds in env_credentials.items():
        print(f"  • {supplier_name}: {len(creds)} credential fields")
    print()

    if dry_run:
        print("Would migrate the following credentials:")
        for supplier_name, creds in env_credentials.items():
            print(f"\n  {supplier_name}:")
            for field in creds.keys():
                print(f"    - {field}: ****** (hidden)")
        print()
        print("Run without --dry-run to perform migration")
        return

    # Initialize services
    supplier_config_service = SupplierConfigService()
    credentials_repo = SupplierCredentialsRepository()

    # Migrate each supplier's credentials
    migrated = []
    skipped = []
    failed = []

    for supplier_name, creds in env_credentials.items():
        try:
            print(f"Migrating {supplier_name}...", end=" ")

            with Session(engine) as session:
                # Check if supplier configuration exists
                config_repo = SupplierConfigRepository()
                try:
                    config = config_repo.get_by_supplier_name_required(session, supplier_name)
                except Exception:
                    print(f"❌ SKIPPED - Supplier configuration not found in database")
                    skipped.append(supplier_name)
                    continue

                # Check if credentials already exist
                existing_creds = credentials_repo.get_credentials(session, config.id)

                if existing_creds:
                    print(f"⚠️  SKIPPED - Credentials already exist in database")
                    skipped.append(supplier_name)
                    continue

            # Store credentials using service (use None for user_id to avoid foreign key issues)
            result = supplier_config_service.set_supplier_credentials(supplier_name, creds, user_id=None)

            if result.get("status") == "database_stored":
                print(f"✓ MIGRATED")
                migrated.append(supplier_name)
            else:
                print(f"❌ FAILED - {result.get('message', 'Unknown error')}")
                failed.append(supplier_name)

        except Exception as e:
            print(f"❌ FAILED - {str(e)}")
            failed.append(supplier_name)

    # Summary
    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"✓ Migrated: {len(migrated)}")
    print(f"⚠️  Skipped:  {len(skipped)}")
    print(f"❌ Failed:   {len(failed)}")
    print()

    if migrated:
        print("Successfully migrated:")
        for supplier in migrated:
            print(f"  • {supplier}")
        print()

    if skipped:
        print("Skipped (already in database or not configured):")
        for supplier in skipped:
            print(f"  • {supplier}")
        print()

    if failed:
        print("Failed to migrate:")
        for supplier in failed:
            print(f"  • {supplier}")
        print()

    print("=" * 70)
    print()

    if migrated:
        print("✓ Migration complete!")
        print()
        print("SECURITY MODEL:")
        print("  • Credentials stored as plain text in database")
        print("  • Protected by OS file permissions")
        print("  • Backup ZIPs are password-encrypted")
        print("  • .env fallback remains for backward compatibility")
        print()
        print("IMPORTANT: Backup your database with a strong password!")
        print()


def main():
    parser = argparse.ArgumentParser(description="Migrate supplier credentials from .env to database storage")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")

    args = parser.parse_args()

    try:
        migrate_credentials(dry_run=args.dry_run)
    except Exception as e:
        print(f"❌ Migration failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
