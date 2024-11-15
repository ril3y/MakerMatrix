import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_409_CONFLICT

from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.routers import parts_routes, locations_routes, categories_routes, printer_routes, utility_routes
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.printer_service import PrinterService

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
        if error["type"] == "missing":
            # Handle missing required fields
            messages.append(f"Field '{error['loc'][-1]}' is required but missing.")
        elif error["type"] == "string_type":
            # Handle incorrect data type (e.g., int where string is expected)
            loc_path = " -> ".join(str(loc) for loc in error["loc"])
            messages.append(f"Invalid type for field '{loc_path}': Expected a valid string but got '{error['input']}'.")
        else:
            # General message for other validation errors
            loc_path = " -> ".join(str(loc) for loc in error["loc"])
            messages.append(f"Validation error in field '{loc_path}': {error['msg']}")

    # Create a ResponseSchema for the validation error
    response_data = ResponseSchema(
        status="error",
        message="Validation failed for the input data.",
        data={"errors": messages}
    )

    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data.dict()
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
            ).dict()
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
            status=exc.status,
            message=exc.message[0],
            data=exc.data
        ).dict()
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
        printer_service = PrinterService()
        printer_service.load_printer_config()
        print("Printer configuration loaded on startup.")
    except FileNotFoundError:
        print("No config file found. Using default printer configuration.")
    except Exception as e:
        print(f"Error loading configuration: {e}")

    # Start the FastAPI server
    uvicorn.run(app, host='0.0.0.0', port=57891)
