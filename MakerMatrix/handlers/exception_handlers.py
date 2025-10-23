from fastapi import Request
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_409_CONFLICT

from MakerMatrix.exceptions import (
    MakerMatrixException,
    PartAlreadyExistsError,
    ResourceNotFoundError,
    CategoryAlreadyExistsError,
    LocationAlreadyExistsError,
    UserAlreadyExistsError,
    InvalidReferenceError,
    get_http_status_code,
    log_exception,
)
from MakerMatrix.schemas.response import ResponseSchema


def register_exception_handlers(app):
    """Register all exception handlers for the FastAPI app."""

    @app.exception_handler(MakerMatrixException)
    async def maker_matrix_exception_handler(request: Request, exc: MakerMatrixException):
        """
        Centralized handler for all MakerMatrix exceptions.

        This consolidates exception handling and eliminates the duplication
        that was present in the original individual handlers.
        """
        # Log the exception with request context
        log_exception(exc, context=f"{request.method} {request.url.path}")

        # Get appropriate HTTP status code
        status_code = get_http_status_code(exc)

        return JSONResponse(
            status_code=status_code,
            content=ResponseSchema(
                status="error", message=exc.message, data=exc.details if exc.details else None
            ).model_dump(),
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
            content=ResponseSchema(status="error", message="Validation error", data=messages).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # For all HTTP exceptions, use the ResponseSchema format
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseSchema(
                status="error", message=exc.detail if isinstance(exc.detail, str) else str(exc.detail), data=None
            ).model_dump(),
        )

    # Note: Individual exception handlers removed in favor of centralized
    # MakerMatrixException handler above. This eliminates the duplication
    # that was present in the original code while maintaining all functionality.
