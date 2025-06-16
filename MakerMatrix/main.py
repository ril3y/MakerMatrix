from contextlib import asynccontextmanager
import asyncio

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.routers import (
    parts_routes, locations_routes, categories_routes, printer_routes, modern_printer_routes, preview_routes,
    utility_routes, auth_routes, user_routes, role_routes, ai_routes, csv_routes, static_routes, task_routes, websocket_routes, analytics_routes
)
from MakerMatrix.services.printer_service import PrinterService
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.handlers.exception_handlers import register_exception_handlers
from MakerMatrix.dependencies.auth import secure_all_routes
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.services.task_service import task_service
from MakerMatrix.services.websocket_service import start_ping_task
from MakerMatrix.services.printer_manager_service import initialize_default_printers


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # Run the database setup
    create_db_and_tables()
    
    # Set up default roles and admin user
    print("Setting up default roles and admin user...")
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    print("Setup complete!")
    
    # Start the task worker
    print("Starting task worker...")
    asyncio.create_task(task_service.start_worker())
    print("Task worker started!")
    
    # Start WebSocket ping task
    print("Starting WebSocket ping task...")
    asyncio.create_task(start_ping_task())
    print("WebSocket service started!")
    
    # Initialize default printers
    print("Initializing default printers...")
    await initialize_default_printers()
    print("Default printers initialized!")
    
    # Restore printers from database
    print("Restoring printers from database...")
    try:
        from MakerMatrix.services.printer_persistence_service import get_printer_persistence_service
        persistence_service = get_printer_persistence_service()
        restored_printers = await persistence_service.restore_printers_from_database()
        print(f"Restored {len(restored_printers)} printers from database: {restored_printers}")
    except Exception as e:
        print(f"Failed to restore printers from database: {e}")
        # Don't fail startup if printer restoration fails
    
    yield  # App continues running
    
    print("Shutting down...")
    # Stop the task worker on shutdown
    await task_service.stop_worker()
    print("Task worker stopped!")


# Initialize the FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Register exception handlers
register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define permissions for specific routes
parts_permissions = {
    "/add_part": "parts:create",
    "/update_part/{part_id}": "parts:update",
    "/delete_part": "parts:delete"
}

locations_permissions = {
    "/add_location": "locations:create",
    "/update_location/{location_id}": "locations:update",
    "/delete_location/{location_id}": "locations:delete"
}

categories_permissions = {
    "/add_category/": "categories:create",
    "/update_category/{category_id}": "categories:update",
    "/remove_category": "categories:delete",
    "/delete_all_categories": "categories:delete_all"
}

csv_permissions = {
    "/import": "parts:create",
    "/preview": "parts:read",
    "/extract-filename-info": "parts:read",
    "/supported-types": "parts:read",
    "/parse": "parts:read"
}

task_permissions = {
    "/": {
        "POST": "tasks:create",
        "GET": "tasks:read"
    },
    "/my": "tasks:read",
    "/{task_id}": "tasks:read",
    "/{task_id}/cancel": "tasks:update",
    "/{task_id}/retry": "tasks:update",
    "/worker/start": "tasks:admin",
    "/worker/stop": "tasks:admin",
    "/worker/status": "tasks:read",
    "/stats/summary": "tasks:read",
    "/types/available": "tasks:read",
    "/quick/csv_enrichment": "tasks:create",
    "/quick/price_update": "tasks:create", 
    "/quick/database_cleanup": "tasks:create",
    "/quick/part_enrichment": "tasks:create",
    "/quick/datasheet_fetch": "tasks:create",
    "/quick/image_fetch": "tasks:create",
    "/quick/bulk_enrichment": "tasks:create",
    "/capabilities/suppliers": "tasks:read",
    "/capabilities/suppliers/{supplier_name}": "tasks:read",
    "/capabilities/find/{capability_type}": "tasks:read",
    "/security/permissions": "tasks:create",
    "/security/limits": "tasks:create",
    "/security/validate": "tasks:create"
}

# Define paths that should be excluded from authentication
auth_exclude_paths = [
    "/login",
    "/refresh",
    "/logout"
]

# Secure routers with authentication
secure_all_routes(parts_routes.router, permissions=parts_permissions)
secure_all_routes(locations_routes.router, permissions=locations_permissions, exclude_paths=["/get_all_locations"])
secure_all_routes(categories_routes.router, permissions=categories_permissions)
secure_all_routes(printer_routes.router)
secure_all_routes(modern_printer_routes.router)
secure_all_routes(preview_routes.router)
secure_all_routes(utility_routes.router, exclude_paths=["/get_counts"])
# Don't secure auth routes - they need to be accessible without authentication
# secure_all_routes(auth_routes.router, exclude_paths=auth_exclude_paths)
secure_all_routes(user_routes.router)
secure_all_routes(role_routes.router)
secure_all_routes(ai_routes.router)
secure_all_routes(csv_routes.router, permissions=csv_permissions)
secure_all_routes(task_routes.router, permissions=task_permissions)
secure_all_routes(analytics_routes.router)

# Public routes that don't need authentication
public_paths = ["/", "/docs", "/redoc", "/openapi.json"]

# Include routers
app.include_router(parts_routes.router, prefix="/parts", tags=["parts"])
app.include_router(locations_routes.router, prefix="/locations", tags=["locations"])
app.include_router(categories_routes.router, prefix="/categories", tags=["categories"])
app.include_router(printer_routes.router, prefix="/printer", tags=["printer"])
app.include_router(modern_printer_routes.router, prefix="/printer", tags=["printer"])
app.include_router(preview_routes.router, tags=["Label Preview"])
app.include_router(utility_routes.router, prefix="/utility", tags=["utility"])
app.include_router(auth_routes.router, tags=["Authentication"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(role_routes.router, prefix="/roles", tags=["Roles"])
app.include_router(ai_routes.router, prefix="/ai", tags=["AI Configuration"])
app.include_router(csv_routes.router, prefix="/api/csv", tags=["CSV Import"])
app.include_router(task_routes.router, prefix="/api/tasks", tags=["Background Tasks"])
app.include_router(analytics_routes.router, tags=["Analytics"])
app.include_router(websocket_routes.router, tags=["WebSocket"])
app.include_router(static_routes.router, tags=["Static Files"])

# Static file serving for React frontend
frontend_dist_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")

# Only serve static files if the dist directory exists (production build)
if os.path.exists(frontend_dist_path):
    # Mount the static assets (CSS, JS, etc.)
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))
    
    # Catch-all route for React Router (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend_routes(full_path: str):
        # Don't serve frontend for API routes
        if full_path.startswith(("parts/", "locations/", "categories/", "printer/", "utility/", "auth/", "users/", "roles/", "ai/", "api/", "static/", "docs", "redoc", "openapi.json")):
            return {"error": "Not found"}
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Welcome to MakerMatrix API - Frontend not built yet"}

if __name__ == "__main__":
    # Load printer config at startup
    try:
        printer_service = PrinterService(PrinterRepository())
        printer_service.load_printer_config()
        print("Printer configuration loaded on startup.")
    except FileNotFoundError:
        print("No config file found. Using default printer configuration.")
    except Exception as e:
        print(f"Error loading configuration: {e}")

    # Start the FastAPI server
    uvicorn.run(app, host='0.0.0.0', port=57891)
