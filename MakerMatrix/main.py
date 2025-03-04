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
from MakerMatrix.dependencies.auth import secure_router, get_current_active_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    create_db_and_tables()  # Run the database setup
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

# Secure routers with authentication
secure_router(parts_routes.router)
secure_router(locations_routes.router)
secure_router(categories_routes.router)
secure_router(printer_routes.router)
secure_router(utility_routes.router)
secure_router(user_routes.router)
secure_router(role_routes.router)

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
