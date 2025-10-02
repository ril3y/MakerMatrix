#!/usr/bin/env python3
"""
Lightweight API for querying the LCSC component database.

Loads the database into memory for fast queries.

Usage:
    python lcsc_api.py

API will be available at http://localhost:8766
"""

import json
import sqlite3
from typing import Dict, List, Optional
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS


app = FastAPI(
    title="LCSC Component Database API",
    description="Fast API for querying 7M electronic components",
    version="1.0.0"
)

# Enable CORS for the review tool
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        self.conn = sqlite3.connect(':memory:')

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

    def sample_diverse(self, count: int = 100, categories: Optional[List[str]] = None) -> List[Dict]:
        """Sample diverse components across categories."""
        if not categories:
            categories = [
                'Resistors', 'Capacitors', 'Integrated Circuits (ICs)',
                'Diodes', 'Transistors', 'Inductors', 'Connectors',
                'Optoelectronics'
            ]

        per_category = max(1, count // len(categories))
        results = []

        for cat in categories:
            samples = self.sample_random(per_category, cat)
            results.extend(samples)

            if len(results) >= count:
                break

        return results[:count]

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Search components by title or part number."""
        cursor = self.conn.cursor()

        sql = """
        SELECT * FROM components
        WHERE (mfr LIKE ? OR extra LIKE ?)
        AND extra IS NOT NULL
        LIMIT ?
        """

        search_term = f"%{query}%"
        cursor.execute(sql, (search_term, search_term, limit))

        results = []
        for row in cursor.fetchall():
            component = self.parse_component(row)
            if component:
                results.append(component)

        return results

    def get_categories(self) -> List[Dict]:
        """Get all categories with counts."""
        cursor = self.conn.cursor()

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

        cursor.execute(query)

        return [
            {
                'main_category': row[0],
                'subcategory': row[1],
                'count': row[2]
            }
            for row in cursor.fetchall()
        ]


@app.on_event("startup")
async def startup_event():
    """Load database on startup."""
    global db_conn

    db_path = Path(__file__).parent / "data" / "lcsc_raw" / "cache.sqlite3"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("   Run: python download_lcsc_database.py")
        return

    db_conn = ComponentDatabase(str(db_path))


@app.get("/")
async def root():
    """API information."""
    if not db_conn:
        raise HTTPException(status_code=503, detail="Database not loaded")

    return {
        "service": "LCSC Component Database API",
        "version": "1.0.0",
        "total_components": db_conn.total_components,
        "total_categories": db_conn.total_categories,
        "endpoints": {
            "GET /sample/random": "Sample random components",
            "GET /sample/diverse": "Sample diverse components across categories",
            "GET /search": "Search components",
            "GET /categories": "List all categories",
            "GET /stats": "Database statistics"
        }
    }


@app.get("/stats")
async def get_stats():
    """Get database statistics."""
    if not db_conn:
        raise HTTPException(status_code=503, detail="Database not loaded")

    return {
        "total_components": db_conn.total_components,
        "total_categories": db_conn.total_categories,
        "database_size": "6.7 GB",
        "loaded_in_memory": True
    }


@app.get("/categories")
async def get_categories(limit: int = Query(50, ge=1, le=500)):
    """Get all categories with component counts."""
    if not db_conn:
        raise HTTPException(status_code=503, detail="Database not loaded")

    categories = db_conn.get_categories()
    return {
        "total": len(categories),
        "categories": categories[:limit]
    }


@app.get("/sample/random")
async def sample_random(
    count: int = Query(100, ge=1, le=1000, description="Number of samples"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Sample random components."""
    if not db_conn:
        raise HTTPException(status_code=503, detail="Database not loaded")

    try:
        samples = db_conn.sample_random(count, category)

        return {
            "count": len(samples),
            "requested": count,
            "category": category,
            "components": samples
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sample/diverse")
async def sample_diverse(
    count: int = Query(100, ge=1, le=1000, description="Number of samples"),
    categories: Optional[str] = Query(None, description="Comma-separated category list")
):
    """Sample diverse components across multiple categories."""
    if not db_conn:
        raise HTTPException(status_code=503, detail="Database not loaded")

    try:
        category_list = categories.split(',') if categories else None
        samples = db_conn.sample_diverse(count, category_list)

        return {
            "count": len(samples),
            "requested": count,
            "categories_used": category_list,
            "components": samples
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_components(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=500)
):
    """Search components by title or part number."""
    if not db_conn:
        raise HTTPException(status_code=503, detail="Database not loaded")

    try:
        results = db_conn.search(q, limit)

        return {
            "query": q,
            "count": len(results),
            "limit": limit,
            "components": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the API server."""
    print("="*60)
    print("LCSC Component Database API")
    print("="*60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8766,
        log_level="info"
    )


if __name__ == "__main__":
    main()
