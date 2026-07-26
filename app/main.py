"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import protected_router, public_router
from app.cache import LocalTTLCache
from app.config import get_settings
from app.db import create_schema, engine
from app.logging_config import configure_logging
from app.middleware import CorrelationIdMiddleware, MetricsMiddleware, RateLimitMiddleware
from app.web import router as web_router
from app.web_api import router as web_api_router

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and close process-scoped resources."""
    if settings.auto_create_schema:
        await create_schema()

    cache = LocalTTLCache()
    app.state.cache = cache
    logger.info("local_cache_ready")

    yield

    await cache.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Agentic stock-research backend using LangGraph, CrewAI, FastAPI, and PostgreSQL. "
        "Outputs are educational and are not personalized investment advice."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key", "X-Correlation-ID"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(web_router)
app.include_router(web_api_router)
app.include_router(public_router)
app.include_router(protected_router)
