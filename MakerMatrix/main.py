from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.routers import (
    parts_routes, locations_routes, categories_routes, printer_routes,
    utility_routes, auth_routes, user_routes, role_routes
)
from MakerMatrix.services.printer_service import PrinterService
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.handlers.exception_handlers import register_exception_handlers
from MakerMatrix.dependencies.auth import secure_all_routes
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository


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
    
    yield  # App continues running
    print("Shutting down...")  # If you need cleanup, add it here


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

# Define paths that should be excluded from authentication
auth_exclude_paths = [
    "/login",
    "/refresh",
    "/logout"
]

# Secure routers with authentication
secure_all_routes(parts_routes.router, permissions=parts_permissions)
secure_all_routes(locations_routes.router, permissions=locations_permissions)
secure_all_routes(categories_routes.router, permissions=categories_permissions)
secure_all_routes(printer_routes.router)
secure_all_routes(utility_routes.router)
# Don't secure auth routes - they need to be accessible without authentication
# secure_all_routes(auth_routes.router, exclude_paths=auth_exclude_paths)
secure_all_routes(user_routes.router)
secure_all_routes(role_routes.router)

# Public routes that don't need authentication
public_paths = ["/", "/docs", "/redoc", "/openapi.json"]

# Include routers
app.include_router(parts_routes.router, prefix="/parts", tags=["parts"])
app.include_router(locations_routes.router, prefix="/locations", tags=["locations"])
app.include_router(categories_routes.router, prefix="/categories", tags=["categories"])
app.include_router(printer_routes.router, prefix="/printer", tags=["printer"])
app.include_router(utility_routes.router, prefix="/utility", tags=["utility"])
app.include_router(auth_routes.router, tags=["Authentication"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(role_routes.router, prefix="/roles", tags=["Roles"])

@app.get("/")
async def root():
    return {"message": "Welcome to MakerMatrix API"}

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
