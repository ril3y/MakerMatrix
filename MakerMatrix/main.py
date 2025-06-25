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
    parts_routes, locations_routes, categories_routes, printer_routes, preview_routes,
    utility_routes, auth_routes, user_routes, role_routes, ai_routes, import_routes, static_routes, task_routes, 
    websocket_routes, analytics_routes, activity_routes, supplier_config_routes, supplier_routes, rate_limit_routes,
    enrichment_routes
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
    
    # Initialize rate limiting system
    print("Initializing rate limiting system...")
    try:
        from MakerMatrix.services.rate_limit_service import RateLimitService
        from MakerMatrix.models.models import engine
        rate_limit_service = RateLimitService(engine)
        await rate_limit_service.initialize_default_limits()
        print("Rate limiting system initialized!")
    except Exception as e:
        print(f"Failed to initialize rate limiting: {e}")
        # Don't fail startup if rate limiting initialization fails
    
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "*"  # Fallback for all origins
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
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

import_permissions = {
    "/file": "parts:create",
    "/suppliers": "parts:read"
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
    "/security/permissions": "tasks:create",
    "/security/limits": "tasks:create",
    "/security/validate": "tasks:create"
}

enrichment_permissions = {
    "/capabilities": "enrichment:read",
    "/capabilities/{supplier_name}": "enrichment:read",
    "/capabilities/find/{capability_type}": "enrichment:read",
    "/tasks/part": "enrichment:create",
    "/tasks/bulk": "enrichment:create",
    "/queue/status": "enrichment:read",
    "/queue/cancel/{task_id}": "enrichment:update",
    "/queue/cancel-all": "enrichment:update"
}

supplier_config_permissions = {
    "/suppliers": {
        "GET": "supplier_config:read",
        "POST": "supplier_config:create"
    },
    "/suppliers/{supplier_name}": {
        "GET": "supplier_config:read",
        "PUT": "supplier_config:update",
        "DELETE": "supplier_config:delete"
    },
    "/suppliers/{supplier_name}/test": "supplier_config:read",
    "/suppliers/{supplier_name}/capabilities": "supplier_config:read",
    "/credentials": "supplier_config:credentials",
    "/credentials/{supplier_name}": "supplier_config:credentials",
    "/import": "supplier_config:import",
    "/export": "supplier_config:export",
    "/initialize-defaults": "supplier_config:create"
}

supplier_permissions = {
    "/": "suppliers:read",
    "/info": "suppliers:read",
    "/{supplier_name}/info": "suppliers:read",
    "/{supplier_name}/credentials-schema": "suppliers:read",
    "/{supplier_name}/config-schema": "suppliers:read",
    "/{supplier_name}/capabilities": "suppliers:read",
    "/{supplier_name}/env-defaults": "suppliers:read",
    "/{supplier_name}/test": "suppliers:use",
    "/{supplier_name}/oauth/authorization-url": "suppliers:use",
    "/{supplier_name}/oauth/exchange": "suppliers:use",
    "/{supplier_name}/search": "suppliers:use",
    "/{supplier_name}/bulk-search": "suppliers:use",
    "/{supplier_name}/part/{part_number}": "suppliers:use",
    "/{supplier_name}/part/{part_number}/datasheet": "suppliers:use",
    "/{supplier_name}/part/{part_number}/pricing": "suppliers:use",
    "/{supplier_name}/part/{part_number}/stock": "suppliers:use"
}

rate_limit_permissions = {
    "/suppliers": "rate_limits:read",
    "/suppliers/{supplier_name}": "rate_limits:read",
    "/suppliers/{supplier_name}/status": "rate_limits:read",
    "/summary": "rate_limits:read",
    "/initialize": "rate_limits:admin"
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
secure_all_routes(preview_routes.router)
secure_all_routes(utility_routes.router, exclude_paths=["/get_counts"])
# Don't secure auth routes - they need to be accessible without authentication
# secure_all_routes(auth_routes.router, exclude_paths=auth_exclude_paths)
secure_all_routes(user_routes.router)
secure_all_routes(role_routes.router)
secure_all_routes(ai_routes.router)
secure_all_routes(import_routes.router, permissions=import_permissions)
secure_all_routes(task_routes.router, permissions=task_permissions)
secure_all_routes(supplier_config_routes.router, permissions=supplier_config_permissions)
secure_all_routes(supplier_routes.router, permissions=supplier_permissions)
secure_all_routes(rate_limit_routes.router, permissions=rate_limit_permissions)
secure_all_routes(analytics_routes.router)
secure_all_routes(activity_routes.router)
secure_all_routes(enrichment_routes.router, permissions=enrichment_permissions)

# Public routes that don't need authentication
public_paths = ["/", "/docs", "/redoc", "/openapi.json"]

# Include routers
app.include_router(parts_routes.router, prefix="/api/parts", tags=["parts"])
app.include_router(locations_routes.router, prefix="/locations", tags=["locations"])
app.include_router(categories_routes.router, prefix="/categories", tags=["categories"])
app.include_router(printer_routes.router, prefix="/printer", tags=["printer"])
app.include_router(preview_routes.router, tags=["Label Preview"])
app.include_router(utility_routes.router, prefix="/utility", tags=["utility"])
app.include_router(auth_routes.router, tags=["Authentication"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(role_routes.router, prefix="/roles", tags=["Roles"])
app.include_router(ai_routes.router, prefix="/ai", tags=["AI Configuration"])
app.include_router(import_routes.router, prefix="/api/import")
app.include_router(task_routes.router, prefix="/api/tasks")
app.include_router(supplier_config_routes.router, tags=["Supplier Configuration"])
app.include_router(supplier_routes.router, tags=["Suppliers"])
app.include_router(rate_limit_routes.router, prefix="/api/rate-limits", tags=["Rate Limiting"])
app.include_router(analytics_routes.router, tags=["Analytics"])
app.include_router(activity_routes.router, prefix="/api/activity", tags=["Activity"])
app.include_router(enrichment_routes.router, prefix="/api/enrichment")
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
    
    # Catch-all route for React Router (SPA routing) - but exclude API routes entirely
    @app.get("/{full_path:path}")
    async def serve_frontend_routes(full_path: str):
        # Skip this route entirely for API paths - let FastAPI routing handle them
        if full_path.startswith(("parts/", "locations/", "categories/", "printer/", "utility/", "auth/", "users/", "roles/", "ai/", "api/", "static/", "docs", "redoc", "openapi.json")):
            # Special case: if it's an API route without trailing slash, try redirecting
            if full_path == "api/tasks":
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/api/tasks/", status_code=307)
            
            # This will never actually be reached for properly mounted API routes
            # but provides a fallback for unmounted API-like paths
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API endpoint not found")
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
    uvicorn.run(app, host='0.0.0.0', port=8080)
