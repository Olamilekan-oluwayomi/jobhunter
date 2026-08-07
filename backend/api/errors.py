"""Global exception handlers with consistent, production-friendly responses.

Every error the API returns follows the same shape:

    {"detail": "message"}                     # simple errors
    {"detail": [{"loc": [], "msg": "", "type": ""}]}  # validation errors
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils.logger import get_logger

logger = get_logger("api.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom error handlers to the given app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Log 5xx as errors; 4xx are client mistakes and need no stack trace.
        if exc.status_code >= 500:
            logger.exception("unhandled HTTP %s at %s", exc.status_code, request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled exception at %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."},
        )
