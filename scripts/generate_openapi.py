#!/usr/bin/env python3
"""
Generate a fresh openapi.json from the FastAPI application.

Usage:
    JWT_SECRET_KEY=test python scripts/generate_openapi.py          # write openapi.json
    JWT_SECRET_KEY=test python scripts/generate_openapi.py --check  # CI: exit 1 if stale

Requires JWT_SECRET_KEY to be set (any value is fine for generation).
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so MakerMatrix can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_FILE = PROJECT_ROOT / "openapi.json"


def generate() -> dict:
    """Import the app and return its OpenAPI schema."""
    # JWT_SECRET_KEY is required by auth modules at import time.
    if not os.environ.get("JWT_SECRET_KEY"):
        print("Error: JWT_SECRET_KEY environment variable must be set.", file=sys.stderr)
        print("Hint:  JWT_SECRET_KEY=test python scripts/generate_openapi.py", file=sys.stderr)
        sys.exit(1)

    from MakerMatrix.main import app  # noqa: E402

    # Force fresh generation (clear any cached schema).
    app.openapi_schema = None
    return app.openapi()


def main():
    parser = argparse.ArgumentParser(description="Generate openapi.json from the FastAPI app")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare with existing openapi.json and exit non-zero if stale",
    )
    args = parser.parse_args()

    schema = generate()
    new_content = json.dumps(schema, indent=2) + "\n"

    if args.check:
        if not OUTPUT_FILE.exists():
            print(f"FAIL: {OUTPUT_FILE} does not exist. Run without --check to create it.")
            sys.exit(1)

        existing_content = OUTPUT_FILE.read_text(encoding="utf-8")
        if existing_content == new_content:
            print(f"OK: {OUTPUT_FILE} is up to date.")
            sys.exit(0)
        else:
            print(f"FAIL: {OUTPUT_FILE} is stale. Re-run: python scripts/generate_openapi.py")
            sys.exit(1)

    OUTPUT_FILE.write_text(new_content, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
