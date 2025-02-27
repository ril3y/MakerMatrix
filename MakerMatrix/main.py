from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_409_CONFLICT

from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.routers import parts_routes, locations_routes, categories_routes, printer_routes, utility_routes
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.printer_service import PrinterService
from MakerMatrix.database.db import create_db_and_tables

# Initialize the FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    create_db_and_tables()  # Run the database setup
    yield  # App continues running
    print("Shutting down...")  # If you need cleanup, add it here


@app.exception_handler(PartAlreadyExistsError)
async def part_already_exists_handler(request: Request, exc: PartAlreadyExistsError):
    return JSONResponse(
        status_code=409,
        content=ResponseSchema(
            status="conflict",
            message=str(exc),
            data=exc.part_data
        ).dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extract validation error details
    errors = exc.errors()

    messages = []
    for error in errors:
        loc = error.get("loc")
        msg = error.get("msg")
        typ = error.get("type")
        messages.append(f"Error in {loc}: {msg} ({typ})")

    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseSchema(
            status = "error",
            message = "Validation error",
            data = messages
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == HTTP_409_CONFLICT:
        # Extract details from the HTTPException
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseSchema(
                status="conflict",
                message=exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", "Conflict occurred"),
                data=exc.detail.get("data", None) if isinstance(exc.detail, dict) else None,
            ).model_dump()
        )

    # If it's not 409, fallback to the default handler
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
    return JSONResponse(
        status_code=404,
        content=ResponseSchema(
            status="error",
            message=str(exc),
            data=None
        ).model_dump()
    )


# Include routers
app.include_router(parts_routes.router, prefix="/parts", tags=["parts"])
app.include_router(locations_routes.router, prefix="/locations", tags=["locations"])
app.include_router(categories_routes.router, prefix="/categories", tags=["categories"])
app.include_router(printer_routes.router, prefix="/printer", tags=["printer"])
app.include_router(utility_routes.router, prefix="/utility", tags=["utility"])

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
