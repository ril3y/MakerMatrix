#!/usr/bin/env python3
"""
Lightweight API for querying the LCSC component database using Flask.

Loads the database into memory for fast queries.

Usage:
    python lcsc_api_flask.py

API will be available at http://localhost:8766
"""

import json
import sqlite3
from typing import Dict, List, Optional
from pathlib import Path
from flask import Flask, jsonify, request

app = Flask(__name__)

# Global database connection (loaded into memory)
db_conn = None


class ComponentDatabase:
    """In-memory SQLite database wrapper."""

    def __init__(self, db_path: str):
        """Load database into memory."""
        print(f"Loading database from {db_path}...")

        # Load from disk
        disk_conn = sqlite3.connect(db_path)

        # Create in-memory database
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)

        # Copy to memory
        disk_conn.backup(self.conn)
        disk_conn.close()

        print("✓ Database loaded into memory")

        # Get row counts
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        self.total_components = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM categories")
        self.total_categories = cursor.fetchone()[0]

        print(f"  Components: {self.total_components:,}")
        print(f"  Categories: {self.total_categories:,}")

    def parse_component(self, row: tuple) -> Optional[Dict]:
        """Parse a component row into a dictionary."""
        (lcsc_id, category_id, mfr, package, joints, manufacturer_id,
         basic, description, datasheet, stock, price, last_update,
         extra, flag, last_on_stock, preferred) = row

        try:
            extra_data = json.loads(extra) if extra else {}

            title = extra_data.get('title', mfr)
            category = extra_data.get('category', {})
            manufacturer = extra_data.get('manufacturer', {})

            return {
                'lcsc_number': extra_data.get('number'),
                'title': title,
                'mpn': mfr,
                'package': package,
                'stock': stock,
                'main_category': category.get('name1'),
                'subcategory': category.get('name2'),
                'manufacturer': manufacturer.get('name'),
                'datasheet_url': extra_data.get('datasheet', {}).get('pdf') if isinstance(extra_data.get('datasheet'), dict) else None,
            }
        except (json.JSONDecodeError, AttributeError):
            return None

    def sample_random(self, count: int = 100, category: Optional[str] = None) -> List[Dict]:
        """Sample random components."""
        cursor = self.conn.cursor()

        if category:
            query = """
            SELECT c.*
            FROM components c
            LEFT JOIN categories cat ON c.category_id = cat.id
            WHERE cat.category = ?
            AND c.extra IS NOT NULL
            AND c.stock > 0
            ORDER BY RANDOM()
            LIMIT ?
            """
            cursor.execute(query, (category, count))
        else:
            query = """
            SELECT * FROM components
            WHERE extra IS NOT NULL
            AND stock > 0
            ORDER BY RANDOM()
            LIMIT ?
            """
            cursor.execute(query, (count,))

        results = []
        for row in cursor.fetchall():
            component = self.parse_component(row)
            if component and component['main_category']:
                results.append(component)

        return results


@app.route("/")
def root():
    """API information."""
    if not db_conn:
        return jsonify({"error": "Database not loaded"}), 503

    return jsonify({
        "service": "LCSC Component Database API",
        "version": "1.0.0",
        "total_components": db_conn.total_components,
        "total_categories": db_conn.total_categories,
        "endpoints": {
            "GET /sample/random": "Sample random components",
            "GET /stats": "Database statistics"
        }
    })


@app.route("/stats")
def get_stats():
    """Get database statistics."""
    if not db_conn:
        return jsonify({"error": "Database not loaded"}), 503

    return jsonify({
        "total_components": db_conn.total_components,
        "total_categories": db_conn.total_categories,
        "database_size": "6.7 GB",
        "loaded_in_memory": True
    })


@app.route("/sample/random")
def sample_random():
    """Sample random components."""
    if not db_conn:
        return jsonify({"error": "Database not loaded"}), 503

    count = int(request.args.get('count', 100))
    category = request.args.get('category')

    count = max(1, min(count, 1000))  # Limit between 1-1000

    try:
        samples = db_conn.sample_random(count, category)

        return jsonify({
            "count": len(samples),
            "requested": count,
            "category": category,
            "components": samples
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    """Run the API server."""
    global db_conn

    print("="*60)
    print("LCSC Component Database API")
    print("="*60)
    print()

    db_path = Path(__file__).parent / "data" / "lcsc_raw" / "cache.sqlite3"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("   Run: python download_lcsc_database.py")
        return

    db_conn = ComponentDatabase(str(db_path))

    print()
    print("="*60)
    print("API ready at http://localhost:8766")
    print("="*60)
    print()
    print("Try:")
    print("  curl http://localhost:8766/")
    print("  curl http://localhost:8766/sample/random?count=10")
    print()

    app.run(host="0.0.0.0", port=8766, debug=False)


if __name__ == "__main__":
    main()
