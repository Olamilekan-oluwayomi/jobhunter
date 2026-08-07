"""HTTP middleware: request logging, security headers, rate limiting."""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import get_settings
from utils.logger import get_logger

logger = get_logger("api.middleware")

REQUEST_ID_HEADER = "x-request-id"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("cf-connecting-ip")
    if forwarded:
        return forwarded.strip().split(",")[0]
    return request.client.host if request.client else "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status and duration."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - start) * 1000,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add sensible security headers to every response."""

    HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for header, value in self.HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter keyed by client IP.

    Suitable for single-instance deployments. Disable via
    ``RATE_LIMIT_ENABLED=false``; tune with ``RATE_LIMIT_REQUESTS`` and
    ``RATE_LIMIT_WINDOW_SECONDS``.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        settings = get_settings()
        self.enabled = settings.rate_limit_enabled
        self.max_requests = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window_seconds
        self._clients: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear recorded request history (used in tests)."""
        with self._lock:
            self._clients.clear()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        now = time.monotonic()
        key = _client_ip(request)

        with self._lock:
            bucket = self._clients[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                logger.warning("rate limit exceeded for %s", key)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                    headers={"Retry-After": str(self.window_seconds)},
                )

            bucket.append(now)

        return await call_next(request)
