#!/usr/bin/env python3
"""
Test script to list all available routes in the FastAPI application
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from MakerMatrix.main import app

def list_all_routes():
    print("🔍 Listing all registered routes in FastAPI app:")
    print("=" * 60)
    
    routes = []
    for route in app.router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                routes.append(f"{method:<8} {route.path}")
        elif hasattr(route, 'path'):
            routes.append(f"{'WS':<8} {route.path}")
    
    # Sort routes for easier reading
    routes.sort()
    
    for route in routes:
        print(route)
    
    print("\n" + "=" * 60)
    print(f"Total routes: {len(routes)}")
    
    # Check specifically for our route
    target_route = "/api/suppliers/configured"
    found_routes = [r for r in routes if target_route in r]
    
    if found_routes:
        print(f"\n✅ Found target route: {target_route}")
        for route in found_routes:
            print(f"  {route}")
    else:
        print(f"\n❌ Target route NOT found: {target_route}")
        
        # Look for similar routes
        supplier_routes = [r for r in routes if "supplier" in r.lower()]
        if supplier_routes:
            print("\n🔍 Found similar supplier routes:")
            for route in supplier_routes:
                print(f"  {route}")

if __name__ == "__main__":
    list_all_routes()