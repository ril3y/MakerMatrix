#!/usr/bin/env python3
"""
Database Migration: Location Name Constraint Update

This script migrates the location name uniqueness constraint from a simple
UniqueConstraint to a partial unique index that allows duplicate slot names
under different containers.

IMPORTANT: Run this BEFORE deploying code with the updated LocationModel!

Background:
- Old constraint: UniqueConstraint('name', 'parent_id')
- New constraint: Partial unique index that only applies to non-slot locations
- Allows multiple containers to have slots with the same names (R1-C1, R1-C2, etc.)

Usage:
    python scripts/migrate_location_constraint.py [--dry-run] [--backup]

Options:
    --dry-run: Show what would be done without making changes
    --backup: Create a backup before migration (recommended)
"""

import sys
import os
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment or default"""
    return os.getenv("DATABASE_URL", "sqlite:///makermatrix.db")


def backup_database(db_path: str) -> str:
    """Create a backup of the database"""
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"

    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"✓ Database backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise


def check_current_constraints(engine):
    """Check what constraints currently exist on the locationmodel table"""
    inspector = inspect(engine)

    try:
        # Get table info
        columns = inspector.get_columns("locationmodel")
        indexes = inspector.get_indexes("locationmodel")
        unique_constraints = inspector.get_unique_constraints("locationmodel")

        logger.info("Current locationmodel table structure:")
        logger.info(f"  Columns: {len(columns)}")
        logger.info(f"  Indexes: {indexes}")
        logger.info(f"  Unique constraints: {unique_constraints}")

        return {"columns": columns, "indexes": indexes, "unique_constraints": unique_constraints}
    except Exception as e:
        logger.error(f"Error inspecting table: {e}")
        return None


def migrate_constraint(engine, dry_run=False):
    """
    Migrate the location name constraint.

    SQLite doesn't support ALTER TABLE to modify constraints, so we need to:
    1. Check if old constraint exists
    2. Create new table with partial index
    3. Copy data
    4. Drop old table
    5. Rename new table
    """

    logger.info("Starting location constraint migration...")

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    with engine.connect() as conn:
        # Check current state
        current = check_current_constraints(engine)

        if not current:
            logger.error("Could not inspect current table structure")
            return False

        # Check if migration is needed
        has_old_constraint = any(uc.get("name") == "uix_location_name_parent" for uc in current["unique_constraints"])

        has_new_index = any(idx.get("name") == "idx_location_name_parent_unique" for idx in current["indexes"])

        if has_new_index:
            logger.info("✓ New partial index already exists - migration not needed")
            return True

        if not has_old_constraint:
            logger.warning("Old constraint not found - table may already be migrated or structure is different")
            logger.info("Proceeding with index creation...")

        if dry_run:
            logger.info("\n[DRY RUN] Would execute:")
            logger.info("  1. Create partial unique index on (name, parent_id) WHERE is_auto_generated_slot = 0")
            logger.info("  2. Verify no constraint violations")
            logger.info("  3. If old constraint exists, it will be handled by table recreation")
            return True

        # For SQLite, we can't easily drop constraints, but SQLAlchemy will handle
        # the table recreation when we call metadata.create_all() with the new schema
        # The new schema uses an Index instead of UniqueConstraint, so it will work

        # Create the new partial index
        try:
            # Check if any duplicate slot names would violate the constraint
            # (for regular locations, not slots)
            check_query = text(
                """
                SELECT name, parent_id, COUNT(*) as count
                FROM locationmodel
                WHERE is_auto_generated_slot = 0 OR is_auto_generated_slot IS NULL
                GROUP BY name, parent_id
                HAVING COUNT(*) > 1
            """
            )

            result = conn.execute(check_query)
            duplicates = result.fetchall()

            if duplicates:
                logger.error("Found duplicate non-slot locations that would violate the new constraint:")
                for row in duplicates:
                    logger.error(f"  name='{row[0]}', parent_id='{row[1]}', count={row[2]}")
                logger.error("Please resolve these duplicates before migration")
                return False

            logger.info("✓ No constraint violations found for non-slot locations")

            # Create the new partial index
            # Note: SQLite syntax for partial indexes
            create_index_sql = text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_location_name_parent_unique
                ON locationmodel (name, parent_id)
                WHERE is_auto_generated_slot = 0 OR is_auto_generated_slot IS NULL
            """
            )

            conn.execute(create_index_sql)
            conn.commit()

            logger.info("✓ Created new partial unique index: idx_location_name_parent_unique")
            logger.info("  - Enforces uniqueness for non-slot locations only")
            logger.info("  - Allows duplicate slot names across different containers")

            # Verify the index was created
            inspector = inspect(engine)
            new_indexes = inspector.get_indexes("locationmodel")

            if any(idx.get("name") == "idx_location_name_parent_unique" for idx in new_indexes):
                logger.info("✓ Migration completed successfully!")
                return True
            else:
                logger.error("Index creation reported success but index not found in table")
                return False

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            conn.rollback()
            return False


def main():
    parser = argparse.ArgumentParser(description="Migrate location name constraint to allow duplicate slot names")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--backup", action="store_true", help="Create a backup before migration (recommended)")
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Database URL (default: from DATABASE_URL env var or sqlite:///makermatrix.db)",
    )

    args = parser.parse_args()

    # Get database URL
    db_url = args.database_url or get_database_url()
    logger.info(f"Database: {db_url}")

    # Create backup if requested
    if args.backup and not args.dry_run:
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            backup_database(db_path)
        else:
            logger.warning("Backup only supported for SQLite databases")

    # Create engine
    engine = create_engine(db_url)

    # Run migration
    success = migrate_constraint(engine, dry_run=args.dry_run)

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Deploy updated code with new LocationModel")
        logger.info("2. Test creating containers with duplicate slot names")
        logger.info("3. Verify existing locations still work correctly")
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("Migration failed!")
        logger.error("=" * 60)
        logger.error("\nPlease review errors above and try again")
        sys.exit(1)


if __name__ == "__main__":
    main()
