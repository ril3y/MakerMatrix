#!/usr/bin/env python3
"""
Version Bumping Script for MakerMatrix

Automatically increments version numbers in:
- MakerMatrix/__init__.py (Python app version)
- MakerMatrix/frontend/package.json (Frontend version)

Usage:
    python scripts/bump_version.py [major|minor|patch]

Default: patch
"""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_version(version_string):
    """Parse a semantic version string into (major, minor, patch)."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_string)
    if not match:
        raise ValueError(f"Invalid version format: {version_string}")
    return tuple(map(int, match.groups()))


def format_version(major, minor, patch):
    """Format version tuple as string."""
    return f"{major}.{minor}.{patch}"


def bump_version(version_string, bump_type="patch"):
    """Bump version based on type (major, minor, or patch)."""
    major, minor, patch = parse_version(version_string)

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Must be 'major', 'minor', or 'patch'")

    return format_version(major, minor, patch)


def update_python_version(file_path, new_version):
    """Update version in Python __init__.py file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Update __version__
    content = re.sub(r'__version__\s*=\s*["\']([^"\']+)["\']', f'__version__ = "{new_version}"', content)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"✅ Updated {file_path}: {new_version}")


def update_package_json_version(file_path, new_version):
    """Update version in package.json file."""
    with open(file_path, "r") as f:
        package_data = json.load(f)

    package_data["version"] = new_version

    with open(file_path, "w") as f:
        json.dump(package_data, f, indent=2)
        f.write("\n")  # Add trailing newline

    print(f"✅ Updated {file_path}: {new_version}")


def get_current_version(python_init_path):
    """Get current version from Python __init__.py."""
    with open(python_init_path, "r") as f:
        content = f.read()

    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError(f"Could not find __version__ in {python_init_path}")

    return match.group(1)


def main():
    parser = argparse.ArgumentParser(
        description="Bump MakerMatrix version numbers", epilog="Example: python scripts/bump_version.py minor"
    )
    parser.add_argument(
        "bump_type",
        nargs="?",
        default="patch",
        choices=["major", "minor", "patch"],
        help="Version component to bump (default: patch)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed without actually changing files"
    )

    args = parser.parse_args()

    # Define file paths
    project_root = Path(__file__).parent.parent
    python_init = project_root / "MakerMatrix" / "__init__.py"
    frontend_package = project_root / "MakerMatrix" / "frontend" / "package.json"

    # Verify files exist
    if not python_init.exists():
        print(f"❌ Error: {python_init} not found", file=sys.stderr)
        sys.exit(1)

    if not frontend_package.exists():
        print(f"❌ Error: {frontend_package} not found", file=sys.stderr)
        sys.exit(1)

    # Get current version and calculate new version
    current_version = get_current_version(python_init)
    new_version = bump_version(current_version, args.bump_type)

    print(f"🔄 Bumping version: {current_version} → {new_version} ({args.bump_type})")

    if args.dry_run:
        print("🔍 DRY RUN - No files will be modified")
        print(f"   Would update: {python_init}")
        print(f"   Would update: {frontend_package}")
        return

    # Update version files
    update_python_version(python_init, new_version)
    update_package_json_version(frontend_package, new_version)

    print(f"\n✨ Version bumped successfully: {current_version} → {new_version}")
    print("\n📝 Next steps:")
    print(f"   1. Review changes: git diff")
    print(f"   2. Commit changes: git add -A && git commit -m 'chore: bump version to {new_version}'")
    print(f"   3. Tag release: git tag v{new_version}")
    print(f"   4. Push changes: git push && git push --tags")


if __name__ == "__main__":
    main()
