from contextlib import asynccontextmanager
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.utils import get_openapi
import os

from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.routers import (
    parts_routes,
    locations_routes,
    categories_routes,
    project_routes,
    printer_routes,
    preview_routes,
    utility_routes,
    auth_routes,
    user_management_routes,
    ai_routes,
    import_routes,
    task_routes,
    websocket_routes,
    activity_routes,
    supplier_config_routes,
    supplier_routes,
    rate_limit_routes,
    label_template_routes,
    api_key_routes,
    part_allocation_routes,
    font_routes,
    tool_routes,
    tag_routes,
    backup_routes,
)
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.handlers.exception_handlers import register_exception_handlers
from MakerMatrix.auth.guards import secure_all_routes
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.services.system.task_service import task_service
from MakerMatrix.services.system.websocket_service import start_ping_task
from MakerMatrix.services.printer.printer_manager_service import initialize_default_printers


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

    # Initialize default supplier configurations
    print("Initializing default supplier configurations...")
    try:
        from MakerMatrix.services.system.supplier_config_service import SupplierConfigService

        config_service = SupplierConfigService()
        # Initialize default suppliers (will skip if they already exist)
        configs = config_service.initialize_default_suppliers()
        print(f"Initialized {len(configs)} supplier configurations")

        print("Default supplier initialization completed!")
    except Exception as e:
        print(f"Failed to initialize default suppliers: {e}")
        # Don't fail startup if supplier initialization fails

    # Auto-initialize suppliers with environment credentials
    print("Auto-initializing suppliers with environment credentials...")
    try:
        from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
        from MakerMatrix.utils.env_credentials import list_available_env_credentials
        from MakerMatrix.suppliers.registry import get_available_suppliers, get_supplier

        config_service = SupplierConfigService()
        available_creds = list_available_env_credentials()
        available_suppliers = get_available_suppliers()

        for supplier_name in available_suppliers:
            # Check if we have credentials for this supplier
            supplier_key = supplier_name.replace("-", "").replace("_", "").lower()
            cred_key = None
            for cred_supplier in available_creds.keys():
                if cred_supplier.replace("-", "").replace("_", "").lower() == supplier_key:
                    cred_key = cred_supplier
                    break

            if cred_key and available_creds[cred_key]:
                try:
                    # Check if supplier is already configured
                    existing_config = None
                    try:
                        existing_config = config_service.get_supplier_config(supplier_name)
                    except:
                        # Supplier not found, which is fine - we'll create it
                        pass

                    if not existing_config:
                        # Auto-create supplier configuration
                        supplier_info = get_supplier(supplier_name).get_supplier_info()
                        config_data = {
                            "supplier_name": supplier_name,
                            "display_name": supplier_info.display_name,
                            "description": supplier_info.description,
                            "api_type": "rest",
                            "base_url": getattr(supplier_info, "website_url", "https://api.example.com"),
                            "enabled": True,
                            "capabilities": [cap.value for cap in get_supplier(supplier_name).get_capabilities()],
                        }
                        config_service.create_supplier_config(config_data)
                        print(
                            f"Auto-configured supplier: {supplier_name} (found credentials: {list(available_creds[cred_key])})"
                        )
                    else:
                        print(f"Supplier {supplier_name} already configured")
                except Exception as supplier_error:
                    print(f"Failed to auto-configure supplier {supplier_name}: {supplier_error}")

        print("Supplier auto-initialization completed!")
    except Exception as e:
        print(f"Failed to auto-initialize suppliers: {e}")
        # Don't fail startup if supplier initialization fails

    # Initialize default CSV import configuration
    print("Initializing default CSV import configuration...")
    try:
        from MakerMatrix.models.csv_import_config_model import CSVImportConfigModel
        from MakerMatrix.models.models import engine
        from sqlmodel import Session, select

        session = Session(engine)
        try:
            existing_config = session.exec(
                select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
            ).first()
            if not existing_config:
                default_config = CSVImportConfigModel(
                    id="default",
                    download_datasheets=True,
                    download_images=True,
                    overwrite_existing_files=False,
                    download_timeout_seconds=30,
                    show_progress=True,
                    enable_enrichment=True,
                    auto_create_enrichment_tasks=True,
                    additional_settings={},
                )
                session.add(default_config)
                session.commit()
                print("Created default CSV import configuration!")
            else:
                print("Default CSV import configuration already exists")
        finally:
            session.close()
    except Exception as e:
        print(f"Failed to initialize CSV import config: {e}")
        # Don't fail startup if CSV config initialization fails

    # Start the task worker (after all setup is complete)
    print("Starting task worker...")
    asyncio.create_task(task_service.start_worker())
    print("Task worker started!")

    # Start WebSocket ping task
    print("Starting WebSocket ping task...")
    asyncio.create_task(start_ping_task())
    print("WebSocket service started!")

    # Start backup scheduler
    print("Starting backup scheduler...")
    try:
        from MakerMatrix.services.system.backup_scheduler import backup_scheduler

        await backup_scheduler.start()
        print("Backup scheduler started successfully!")
    except Exception as e:
        print(f"Failed to start backup scheduler: {e}")
        # Don't fail startup if backup scheduler fails

    # Restore printers from database
    print("Restoring printers from database...")
    try:
        from MakerMatrix.services.printer.printer_persistence_service import get_printer_persistence_service

        persistence_service = get_printer_persistence_service()
        restored_printers = await persistence_service.restore_printers_from_database()
        print(f"Restored {len(restored_printers)} printers from database: {restored_printers}")
    except Exception as e:
        print(f"Failed to restore printers from database: {e}")
        # Don't fail startup if printer restoration fails

    yield  # App continues running

    print("Shutting down...")

    # Stop backup scheduler on shutdown
    try:
        from MakerMatrix.services.system.backup_scheduler import backup_scheduler

        await backup_scheduler.stop()
        print("Backup scheduler stopped!")
    except Exception as e:
        print(f"Failed to stop backup scheduler: {e}")

    # Stop the task worker on shutdown
    await task_service.stop_worker()
    print("Task worker stopped!")


# Initialize the FastAPI app with lifespan
app = FastAPI(
    title="MakerMatrix",
    description="A comprehensive part inventory management system with label printing capabilities.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Enable API documentation
    redoc_url="/redoc",  # Enable ReDoc documentation
    # Temporarily disable OpenAPI generation for problematic schema
    generate_unique_id_function=lambda route: route.tags[0] + "-" + route.name if route.tags else route.name,
)

# Register exception handlers
register_exception_handlers(app)

# Configure CORS
# Get CORS origins from environment variable
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,*",
)
cors_origins_list = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add guest rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from MakerMatrix.middleware.guest_rate_limit import get_guest_identifier, guest_rate_limit_middleware

# Initialize slowapi limiter
limiter = Limiter(key_func=get_guest_identifier)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add the middleware to the app
app.middleware("http")(guest_rate_limit_middleware)

# Define permissions for specific routes
parts_permissions = {
    "/add_part": "parts:create",
    "/update_part/{part_id}": "parts:update",
    "/delete_part": "parts:delete",
    "/enrich-from-supplier": "parts:update",  # Enrichment requires update permission
    "/parts/{part_id}/enrichment-requirements/{supplier}": "parts:read",  # Read-only check
    "/enrichment-requirements/{supplier}": "parts:read",  # Read-only check
}

printer_permissions = {
    "/print/text": "parts:update",  # Printing requires update permission
    "/print/qr": "parts:update",
    "/print/image": "parts:update",
    "/print/template": "parts:update",
    "/print/advanced": "parts:update",
    "/printers": "parts:read",  # Reading printer list is read-only
    "/printers/{printer_id}": {"GET": "parts:read", "PUT": "printer:admin", "DELETE": "printer:admin"},
    "/printers/{printer_id}/status": "parts:read",
    "/printers/{printer_id}/test": "printer:admin",
}

locations_permissions = {
    "/add_location": "locations:create",
    "/update_location/{location_id}": "locations:update",
    "/delete_location/{location_id}": "locations:delete",
}

categories_permissions = {
    "/add_category/": "categories:create",
    "/update_category/{category_id}": "categories:update",
    "/remove_category": "categories:delete",
    "/delete_all_categories": "categories:delete_all",
}

import_permissions = {"/file": "parts:create", "/suppliers": "parts:read"}

task_permissions = {
    "/": {"POST": "tasks:create", "GET": "tasks:read"},
    "/my": "tasks:read",
    "/{task_id}": "tasks:read",
    "/{task_id}/cancel": "tasks:update",
    "/{task_id}/retry": "tasks:update",
    "/worker/start": "tasks:admin",
    "/worker/stop": "tasks:admin",
    "/worker/status": "tasks:read",
    "/stats/summary": "tasks:read",
    "/types/available": "tasks:read",
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
    "/security/validate": "tasks:create",
}


supplier_config_permissions = {
    "/suppliers": {
        # GET is public - only returns metadata (names, images, display info) needed for UI
        "POST": "supplier_config:create"
    },
    "/suppliers/{supplier_name}": {
        # GET is public - only returns configuration metadata without credentials
        "PUT": "supplier_config:update",
        "DELETE": "supplier_config:delete",
    },
    "/suppliers/{supplier_name}/test": "supplier_config:read",
    "/suppliers/{supplier_name}/capabilities": "supplier_config:read",
    "/suppliers/{supplier_name}/credential-fields": None,  # Public - no sensitive data
    "/suppliers/{supplier_name}/config-fields": None,  # Public - just field schemas
    "/credentials": "supplier_config:credentials",
    "/credentials/{supplier_name}": "supplier_config:credentials",
    "/import": "supplier_config:import",
    "/export": "supplier_config:export",
    "/initialize-defaults": "supplier_config:create",
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
    "/{supplier_name}/part/{part_number}/stock": "suppliers:use",
}

rate_limit_permissions = {
    "/suppliers": "rate_limits:read",
    "/suppliers/{supplier_name}": "rate_limits:read",
    "/suppliers/{supplier_name}/status": "rate_limits:read",
    "/summary": "rate_limits:read",
    "/initialize": "rate_limits:admin",
}

user_permissions = {
    "/register": "users:create",
    "/all": "users:read",
    "/{user_id}": "users:read",
    "/by-username/{username}": "users:read",
    "/{user_id}/roles": "users:update",
    "/{user_id}/status": "users:update",
    "/roles": "users:read",
    "/roles/add_role": "users:create",
    "/roles/by-name/{name}": "users:read",
    "/roles/{role_id}": {"GET": "users:read", "PUT": "users:update", "DELETE": "users:delete"},
}

api_key_permissions = {
    "/": {"POST": "api_keys:create", "GET": "api_keys:read"},
    "/{key_id}": {"GET": "api_keys:read", "PUT": "api_keys:update", "DELETE": "api_keys:delete"},
    "/{key_id}/revoke": "api_keys:delete",
    "/admin/all": "api_keys:admin",
}

tool_permissions = {
    "/": {"POST": "tools:create", "GET": "tools:read"},
    "/{tool_id}": {"GET": "tools:read", "PUT": "tools:update", "DELETE": "tools:delete"},
    "/search": "tools:read",
    "/{tool_id}/checkout": "tools:use",
    "/{tool_id}/return": "tools:use",
    "/{tool_id}/checkin": "tools:use",
    "/{tool_id}/maintenance": "tools:update",
    "/statistics": "tools:read",
    "/suggestions": "tools:read",
    "/check_name_exists": "tools:read",
}

tag_permissions = {
    "/": {"POST": "tags:create", "GET": "tags:read"},
    "/{tag_id}": {"GET": "tags:read", "PUT": "tags:update", "DELETE": "tags:delete"},
    "/name/{tag_name}": "tags:read",
    "/{tag_id}/parts/{part_id}": {"POST": "tags:assign", "DELETE": "tags:assign"},
    "/{tag_id}/tools/{tool_id}": {"POST": "tags:assign", "DELETE": "tags:assign"},
    "/parts/{part_id}/tags": "tags:read",
    "/tools/{tool_id}/tags": "tags:read",
    "/{tag_id}/parts": "tags:read",
    "/{tag_id}/tools": "tags:read",
    "/bulk": "tags:assign",
    "/merge": "tags:admin",
    "/cleanup": "tags:admin",
    "/statistics": "tags:read",
}

backup_permissions = {
    "/create": "admin",
    "/restore": "admin",
    "/list": "admin",
    "/download/{backup_filename}": "admin",
    "/delete/{backup_filename}": "admin",
    "/retention/run": "admin",
    "/config": "admin",
    "/status": "admin",
}

# Define paths that should be excluded from authentication
auth_exclude_paths = ["/login", "/refresh", "/logout"]

# Secure routers with authentication
secure_all_routes(parts_routes.router, permissions=parts_permissions)
secure_all_routes(
    locations_routes.router,
    permissions=locations_permissions,
    exclude_paths=["/get_all_locations", "/get_container_slots/{container_id}"],
)
secure_all_routes(categories_routes.router, permissions=categories_permissions)
secure_all_routes(tool_routes.router, permissions=tool_permissions)
secure_all_routes(tag_routes.router, permissions=tag_permissions)
secure_all_routes(printer_routes.router, permissions=printer_permissions, exclude_paths=["/preview/template"])
secure_all_routes(preview_routes.router)
secure_all_routes(
    utility_routes.router,
    exclude_paths=[
        "/get_counts",
        "/get_image/{image_id}",
        "/static/datasheets/{filename}",
        "/supplier_icon/{supplier_name}",
    ],
)
# Don't secure auth routes - they need to be accessible without authentication
# secure_all_routes(auth_routes.router, exclude_paths=auth_exclude_paths)
secure_all_routes(user_management_routes.router, permissions=user_permissions)
secure_all_routes(api_key_routes.router, permissions=api_key_permissions)
secure_all_routes(ai_routes.router)
secure_all_routes(import_routes.router, permissions=import_permissions)
secure_all_routes(task_routes.router, permissions=task_permissions)
secure_all_routes(supplier_config_routes.router, permissions=supplier_config_permissions)
secure_all_routes(
    supplier_routes.router,
    permissions=supplier_permissions,
    exclude_paths=["/{supplier_name}/oauth/callback"],  # OAuth callbacks must be public
)
secure_all_routes(rate_limit_routes.router, permissions=rate_limit_permissions)
secure_all_routes(activity_routes.router)
secure_all_routes(backup_routes.router, permissions=backup_permissions)

# Public routes that don't need authentication
public_paths = ["/", "/docs", "/redoc", "/openapi.json"]

# Include routers
app.include_router(parts_routes.router, prefix="/api/parts", tags=["parts"])
app.include_router(part_allocation_routes.router, prefix="/api", tags=["Part Allocations"])
app.include_router(tool_routes.router, prefix="/api/tools", tags=["tools"])
app.include_router(tag_routes.router, prefix="/api/tags", tags=["tags"])
app.include_router(locations_routes.router, prefix="/api/locations", tags=["locations"])
app.include_router(categories_routes.router, prefix="/api/categories", tags=["categories"])
app.include_router(project_routes.router, prefix="/api/projects", tags=["projects"])
app.include_router(printer_routes.router, prefix="/api/printer", tags=["printer"])
app.include_router(preview_routes.router, prefix="/api/preview", tags=["Label Preview"])
app.include_router(label_template_routes.router, prefix="/api/templates", tags=["Label Templates"])
app.include_router(font_routes.router, prefix="/api", tags=["Fonts"])
app.include_router(utility_routes.router, prefix="/api/utility", tags=["utility"])
app.include_router(auth_routes.router, prefix="/api", tags=["Authentication"])
app.include_router(user_management_routes.router, prefix="/api/users", tags=["Users"])
app.include_router(api_key_routes.router, prefix="/api/api-keys", tags=["API Keys"])
app.include_router(ai_routes.router, prefix="/api/ai", tags=["AI Configuration"])
app.include_router(import_routes.router, prefix="/api/import")
app.include_router(task_routes.router, prefix="/api/tasks")
app.include_router(supplier_config_routes.router, prefix="/api/suppliers/config", tags=["Supplier Configuration"])
app.include_router(supplier_routes.router, prefix="/api/suppliers", tags=["Suppliers"])
app.include_router(rate_limit_routes.router, prefix="/api/rate-limits", tags=["Rate Limiting"])
app.include_router(activity_routes.router, prefix="/api/activity", tags=["Activity"])
app.include_router(backup_routes.router, tags=["Backup Management"])
app.include_router(websocket_routes.router, tags=["WebSocket"])

# Include user management router also at /users for backward compatibility
app.include_router(user_management_routes.router, prefix="/users", tags=["Users Legacy"])


# Custom OpenAPI schema to handle Callable types
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    try:
        # Try to generate the full OpenAPI schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    except Exception as e:
        # Log the specific error for debugging
        print(f"OpenAPI generation error: {type(e).__name__}: {str(e)}")

        # Try to generate schema route by route to identify problematic routes
        try:
            from fastapi.openapi.utils import get_openapi
            from fastapi.routing import APIRoute

            # Get all non-problematic routes
            working_routes = []
            for route in app.routes:
                if isinstance(route, APIRoute):
                    try:
                        # Test if this specific route can be serialized
                        test_schema = get_openapi(title="Test", version="1.0.0", routes=[route])
                        working_routes.append(route)
                    except Exception as route_error:
                        print(f"Problematic route: {route.path} - {type(route_error).__name__}: {str(route_error)}")

            # Generate schema with working routes only
            if working_routes:
                openapi_schema = get_openapi(
                    title=app.title,
                    version=app.version,
                    description=app.description,
                    routes=working_routes,
                )
                app.openapi_schema = openapi_schema
                return app.openapi_schema

        except Exception as fallback_error:
            print(f"Fallback generation also failed: {type(fallback_error).__name__}: {str(fallback_error)}")

        # Final fallback - return minimal schema
        return {
            "openapi": "3.0.2",
            "info": {"title": app.title, "version": app.version},
            "paths": {
                "/api/utility/get_counts": {
                    "get": {"summary": "Get system counts", "responses": {"200": {"description": "Success"}}}
                }
            },
        }


app.openapi = custom_openapi

# Static file serving for React frontend
frontend_dist_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")

# Only serve static files if the dist directory exists (production build)
if os.path.exists(frontend_dist_path):
    # Mount the static assets (CSS, JS, etc.)
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")

    # Mount JS directory for PDF.js worker and other JS files
    js_path = os.path.join(frontend_dist_path, "js")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))

    # Catch-all route for React Router (SPA routing) - but exclude API routes entirely
    @app.get("/{full_path:path}")
    async def serve_frontend_routes(full_path: str):
        # Skip this route entirely for API paths - let FastAPI routing handle them
        if full_path.startswith(
            (
                "parts/",
                "locations/",
                "categories/",
                "printer/",
                "utility/",
                "auth/",
                "users/",
                "roles/",
                "ai/",
                "api/",
                "static/",
                "docs",
                "redoc",
                "openapi.json",
            )
        ):
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
    # HTTPS Configuration
    import ssl

    def run_with_https():
        """Run the application with HTTPS support"""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain("certs/cert.pem", "certs/key.pem")

        uvicorn.run(
            "MakerMatrix.main:app",
            host="0.0.0.0",
            port=8443,
            ssl_keyfile="certs/key.pem",
            ssl_certfile="certs/cert.pem",
            reload=False,  # Disable reload for HTTPS
        )

    import os

    if os.getenv("HTTPS_ENABLED", "false").lower() == "true":
        print(f"🔒 Starting MakerMatrix with HTTPS on port 8443")
        run_with_https()
    else:
        print("🌐 Starting MakerMatrix with HTTP on port 8080")
        uvicorn.run("MakerMatrix.main:app", host="0.0.0.0", port=8080, reload=True)
