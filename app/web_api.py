"""Browser-facing API routes that never expose the backend API key."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID, uuid4

import orjson
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionFactory, get_session
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
router = APIRouter(prefix="/web", tags=["browser-ui"], include_in_schema=False)


@router.get("/companies/search", response_model=list[CompanyCandidate])
async def web_search_companies(
    request: Request,
    query: Annotated[str, Query(min_length=1, max_length=120, alias="q")],
    limit: Annotated[int, Query(ge=1, le=6)] = 5,
) -> list[CompanyCandidate]:
    """Search companies for the browser UI without requiring browser secrets."""
    provider = _provider(request.app.state.cache)
    return await provider.search(query, limit=limit)


@router.post(
    "/analyses",
    response_model=AnalysisAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def web_create_analysis(
    payload: AnalysisRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisAccepted:
    """Create a UI analysis job without exposing API_KEY to browser JavaScript.

    This endpoint is same-origin and public for the hosted demo UI. Abuse is
    controlled by the app's rate-limit middleware; production apps should add
    login, CAPTCHA, or per-user quotas.
    """
    canonical = orjson.dumps(payload.model_dump(mode="json"), option=orjson.OPT_SORT_KEYS)
    request_hash = hashlib.sha256(canonical).hexdigest()
    idempotency_key = f"web-{uuid4().hex}"

    repository = JobRepository(session)
    try:
        job = await repository.create(payload, idempotency_key, request_hash)
        await repository.append_event(
            job.id,
            "queued",
            "Analysis job accepted from browser UI",
            {
                "company_name": payload.company_name,
                "horizons": payload.horizons,
                "source": "web-ui",
            },
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="unable to create a unique analysis job; please retry",
        ) from None

    background_tasks.add_task(run_analysis_in_process, job.id, request.app.state.cache)
    return AnalysisAccepted(job_id=job.id, status=JobStatus.QUEUED, reused=False)


@router.get("/analyses/{job_id}", response_model=AnalysisJobResponse)
async def web_get_analysis(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisJobResponse:
    """Return job status and report for the browser UI."""
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


@router.get("/analyses/{job_id}/events", response_model=list[AnalysisEventResponse])
async def web_get_analysis_events(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    after: Annotated[int, Query(ge=0)] = 0,
) -> list[AnalysisEventResponse]:
    """Return durable progress events for the browser UI."""
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


@router.get("/analyses/{job_id}/stream", response_class=StreamingResponse)
async def web_stream_analysis(job_id: UUID, request: Request) -> StreamingResponse:
    """Stream browser UI progress without API-key headers."""
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
