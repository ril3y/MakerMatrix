"""
Path Traversal Middleware
=========================

Rejects requests whose RAW URL path contains traversal sequences before
Starlette has a chance to normalize them away.

Why this exists
---------------
Starlette's routing layer URL-normalizes ``..`` segments **before** the route
handler runs. Without this middleware, a request to
``/api/utility/get_image/..`` either:

  * has the ``..`` stripped (so the handler never sees it and the
    per-handler regex validator misses the attack), or
  * returns 401 from an unrelated auth gate by accident, rather than the
    400 we actually want to convey.

This middleware inspects the raw path before any other middleware runs and
short-circuits with a JSON 400 response on any of:

  * a path segment whose value is exactly ``.`` or ``..``;
  * a NUL byte (``\\x00``) anywhere in the path;
  * a backslash (``\\``) anywhere in the path — these are not legal in
    URL paths but some clients send Windows-style separators that some
    intermediaries translate to ``/`` later in the stack.

URL-encoded forms (``%2e%2e``, ``%2f``) are caught because we examine the
already-decoded ``request.url.path``. The raw ASGI ``raw_path`` is also
checked as a defence-in-depth measure for traversal sequences that some
middleware might un-encode later.

Filenames that merely **contain** ``..`` as a substring (e.g. ``foo..bar.png``)
are NOT rejected, since they are technically valid filename components. Only
segments that are **exactly** ``.`` or ``..`` are blocked.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable
from urllib.parse import unquote

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# Single segments that indicate a traversal attempt.
_BAD_SEGMENTS = {".", ".."}


def _path_is_traversal(path: str) -> bool:
    """Return True if ``path`` contains a traversal segment or null/backslash.

    ``path`` is expected to be the URL path (already %-decoded by Starlette).
    """
    if not path:
        return False
    if "\x00" in path or "\\" in path:
        return True
    # Split on / and reject if any segment is exactly . or ..
    for segment in path.split("/"):
        if segment in _BAD_SEGMENTS:
            return True
    return False


class PathTraversalMiddleware(BaseHTTPMiddleware):
    """Reject path-traversal sequences before routing/auth/CORS run."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
        # Check the parsed URL path (already %-decoded by Starlette).
        if _path_is_traversal(request.url.path):
            logger.warning("Blocked path-traversal request: path=%s", request.url.path)
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Invalid request path", "data": None},
            )

        # Defence in depth: also inspect the raw ASGI path. Some proxies or
        # middleware may un-percent-encode segments later, so we additionally
        # decode the raw bytes once and re-check. If the raw path is missing
        # or identical to url.path, the check above already covered it.
        raw_path = request.scope.get("raw_path")
        if raw_path:
            try:
                decoded = unquote(raw_path.decode("latin-1"))
            except (UnicodeDecodeError, AttributeError):
                decoded = ""
            if decoded and _path_is_traversal(decoded):
                logger.warning(
                    "Blocked path-traversal request (raw): raw_path=%r", raw_path
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Invalid request path",
                        "data": None,
                    },
                )

        return await call_next(request)


async def path_traversal_middleware(request: Request, call_next):
    """Functional form for ``app.middleware("http")(...)`` registration.

    Kept here for callers that prefer the function-style registration that
    matches the existing ``guest_rate_limit_middleware`` pattern.
    """
    if _path_is_traversal(request.url.path):
        logger.warning("Blocked path-traversal request: path=%s", request.url.path)
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid request path", "data": None},
        )

    raw_path = request.scope.get("raw_path")
    if raw_path:
        try:
            decoded = unquote(raw_path.decode("latin-1"))
        except (UnicodeDecodeError, AttributeError):
            decoded = ""
        if decoded and _path_is_traversal(decoded):
            logger.warning(
                "Blocked path-traversal request (raw): raw_path=%r", raw_path
            )
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Invalid request path", "data": None},
            )

    return await call_next(request)


__all__ = ["PathTraversalMiddleware", "path_traversal_middleware", "_path_is_traversal"]
