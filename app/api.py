"""HTTP API routes."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID, uuid4

import orjson
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionFactory, check_database, get_session
from app.domain import (
    AnalysisAccepted,
    AnalysisEventResponse,
    AnalysisJobResponse,
    AnalysisRequest,
    CompanyCandidate,
    JobStatus,
)
from app.inprocess import run_analysis_in_process
from app.market import YahooFinanceProvider
from app.repository import JobRepository

settings = get_settings()

public_router = APIRouter()


async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Require an API key only when one is configured."""
    if settings.api_key and (
        x_api_key is None or not hmac.compare_digest(x_api_key, settings.api_key)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")


protected_router = APIRouter(prefix="/v1", dependencies=[Depends(verify_api_key)])


@public_router.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    """Process liveness probe."""
    return {"status": "ok"}


@public_router.get("/health/ready", tags=["health"])
async def ready(request: Request) -> Response:
    """Dependency readiness probe."""
    database_ok = await check_database()
    cache_ok = await request.app.state.cache.ping()
    payload = {"database": database_ok, "cache": cache_ok, "runner": "in_process"}
    status_code = status.HTTP_200_OK if all(payload.values()) else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(
        content=orjson.dumps(payload),
        status_code=status_code,
        media_type="application/json",
    )


@public_router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@protected_router.get(
    "/companies/search",
    response_model=list[CompanyCandidate],
    tags=["companies"],
)
async def search_companies(
    request: Request,
    query: Annotated[str, Query(min_length=1, max_length=120, alias="q")],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> list[CompanyCandidate]:
    """Resolve a company name or ticker into ranked listed-equity candidates."""
    provider = _provider(request.app.state.cache)
    return await provider.search(query, limit=limit)


@protected_router.post(
    "/analyses",
    response_model=AnalysisAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["analyses"],
)
async def create_analysis(
    payload: AnalysisRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key_header: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=128)
    ] = None,
) -> AnalysisAccepted:
    """Create an idempotent asynchronous stock-analysis job."""
    canonical = orjson.dumps(payload.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS)
    request_hash = hashlib.sha256(canonical).hexdigest()
    idempotency_key = idempotency_key_header or f"generated-{uuid4().hex}"

    repository = JobRepository(session)
    existing = await repository.get_by_idempotency_key(idempotency_key)
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="idempotency key was already used with a different request",
            )
        return AnalysisAccepted(
            job_id=existing.id,
            status=JobStatus(existing.status),
            reused=True,
        )

    try:
        job = await repository.create(payload, idempotency_key, request_hash)
        await repository.append_event(
            job.id,
            "queued",
            "Analysis job accepted",
            {"company_name": payload.company_name, "horizons": payload.horizons},
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await repository.get_by_idempotency_key(idempotency_key)
        if existing is None:
            raise
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="idempotency key was already used with a different request",
            )
        return AnalysisAccepted(
            job_id=existing.id,
            status=JobStatus(existing.status),
            reused=True,
        )

    background_tasks.add_task(run_analysis_in_process, job.id, request.app.state.cache)

    return AnalysisAccepted(job_id=job.id, status=JobStatus.QUEUED, reused=False)


@protected_router.get(
    "/analyses/{job_id}",
    response_model=AnalysisJobResponse,
    tags=["analyses"],
)
async def get_analysis(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisJobResponse:
    """Return job status and the report when completed."""
    job = await JobRepository(session).get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return AnalysisJobResponse(
        id=job.id,
        company_name=job.company_name,
        ticker=job.ticker,
        status=JobStatus(job.status),
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@protected_router.get(
    "/analyses/{job_id}/events",
    response_model=list[AnalysisEventResponse],
    tags=["analyses"],
)
async def get_analysis_events(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    after: Annotated[int, Query(ge=0)] = 0,
) -> list[AnalysisEventResponse]:
    """Return durable progress events after a sequence number."""
    repository = JobRepository(session)
    if await repository.get(job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    events = await repository.list_events(job_id, after=after)
    return [
        AnalysisEventResponse(
            sequence=event.sequence,
            stage=event.stage,
            message=event.message,
            data=event.data,
            created_at=event.created_at,
        )
        for event in events
    ]


@protected_router.get(
    "/analyses/{job_id}/stream",
    response_class=StreamingResponse,
    tags=["analyses"],
)
async def stream_analysis(job_id: UUID, request: Request) -> StreamingResponse:
    """Stream job progress with server-sent events."""
    async with SessionFactory() as session:
        if await JobRepository(session).get(job_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    async def event_source() -> AsyncIterator[str]:
        sequence = 0
        terminal_sent = False
        while not await request.is_disconnected():
            async with SessionFactory() as session:
                repository = JobRepository(session)
                events = await repository.list_events(job_id, after=sequence)
                job = await repository.get(job_id)

            for event in events:
                sequence = event.sequence
                payload = {
                    "sequence": event.sequence,
                    "stage": event.stage,
                    "message": event.message,
                    "data": event.data,
                    "created_at": event.created_at.isoformat(),
                }
                yield f"event: progress\ndata: {orjson.dumps(payload).decode()}\n\n"

            if job and job.status in {JobStatus.COMPLETED.value, JobStatus.FAILED.value}:
                if not terminal_sent:
                    terminal_sent = True
                    payload = {"status": job.status, "job_id": str(job_id)}
                    yield f"event: terminal\ndata: {orjson.dumps(payload).decode()}\n\n"
                return

            if not events:
                yield ": keep-alive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _provider(cache: object) -> YahooFinanceProvider:
    return YahooFinanceProvider(
        cache=cache,
        cache_ttl_seconds=settings.analysis_cache_ttl_seconds,
        benchmark_ticker=settings.benchmark_ticker,
    )

