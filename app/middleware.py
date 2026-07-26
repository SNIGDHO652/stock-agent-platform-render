"""Request correlation, rate limiting, and Prometheus instrumentation."""

from __future__ import annotations

import time
from uuid import uuid4

import structlog
from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

REQUESTS = Counter(
    "stock_agent_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "stock_agent_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a stable correlation ID to logs and responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window in-process rate limiter with fail-open degradation."""

    def __init__(self, app: ASGIApp, limit_per_minute: int) -> None:
        super().__init__(app)
        self._limit = limit_per_minute

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith(("/health", "/metrics")):
            return await call_next(request)

        cache = getattr(request.app.state, "cache", None)
        if cache is None:
            return await call_next(request)

        identity = request.headers.get("X-API-Key") or (
            request.client.host if request.client else "unknown"
        )
        window = int(time.time() // 60)
        key = f"rate-limit:v1:{identity}:{window}"
        try:
            count = await cache.incr(key)
            if count == 1:
                await cache.expire(key, 65)
            if count > self._limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
        except Exception:
            pass
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record route-level request counts and latency."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            status = str(response.status_code if response is not None else 500)
            REQUESTS.labels(request.method, path, status).inc()
            LATENCY.labels(request.method, path).observe(time.perf_counter() - started)
