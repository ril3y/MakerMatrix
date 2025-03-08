from fastapi import Request
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_409_CONFLICT

from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.schemas.response import ResponseSchema


def register_exception_handlers(app):
    """Register all exception handlers for the FastAPI app."""
    
    @app.exception_handler(PartAlreadyExistsError)
    async def part_already_exists_handler(request: Request, exc: PartAlreadyExistsError):
        return JSONResponse(
            status_code=HTTP_409_CONFLICT,
            content=ResponseSchema(
                status="error",
                message=exc.message,
                data=None
            ).model_dump()
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
                status="error",
                message="Validation error",
                data=messages
            ).model_dump()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # For all HTTP exceptions, use the ResponseSchema format
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseSchema(
                status="error",
                message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                data=None
            ).model_dump()
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