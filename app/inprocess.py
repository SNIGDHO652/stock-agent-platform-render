"""In-process job execution for Render free-tier deployments."""

from __future__ import annotations

import asyncio
import os
from typing import Any
from uuid import UUID

import structlog

from app.config import get_settings
from app.db import SessionFactory
from app.domain import AnalysisRequest, JobStatus
from app.market import CompanyNotFoundError, MarketDataError, YahooFinanceProvider
from app.repository import JobRepository
from app.workflow import AnalysisWorkflow

logger = structlog.get_logger(__name__)
settings = get_settings()
_job_semaphore = asyncio.Semaphore(1)


async def run_analysis_in_process(job_id: UUID | str, cache: Any) -> dict[str, Any]:
    """Execute a persisted analysis job inside the FastAPI web process.

    The semaphore intentionally keeps memory and CPU usage predictable on Render
    free web services.
    """
    job_uuid = UUID(str(job_id))
    owner = f"in-process-{os.getpid()}"

    async with _job_semaphore:
        try:
            return await _execute(job_uuid, owner, cache)
        except CompanyNotFoundError as exc:
            await _mark_failed(job_uuid, str(exc))
            return {"job_id": str(job_uuid), "status": JobStatus.FAILED.value, "error": str(exc)}
        except MarketDataError as exc:
            await _mark_failed(job_uuid, str(exc))
            return {"job_id": str(job_uuid), "status": JobStatus.FAILED.value, "error": str(exc)}
        except Exception as exc:
            logger.exception("in_process_analysis_failed", job_id=str(job_uuid))
            await _mark_failed(job_uuid, str(exc))
            return {"job_id": str(job_uuid), "status": JobStatus.FAILED.value, "error": str(exc)}


async def _execute(job_id: UUID, owner: str, cache: Any) -> dict[str, Any]:
    async with SessionFactory() as session:
        repository = JobRepository(session)
        job = await repository.claim(job_id, owner, settings.job_lease_seconds)
        if job is None:
            existing = await repository.get(job_id)
            return {
                "job_id": str(job_id),
                "status": existing.status if existing else "missing",
                "claimed": False,
            }
        request = AnalysisRequest.model_validate(job.request_payload)
        await repository.append_event(job_id, "runner", "Web process claimed the analysis job")
        await session.commit()

    async def emit(stage: str, message: str, data: dict[str, Any]) -> None:
        async with SessionFactory() as event_session:
            event_repository = JobRepository(event_session)
            await event_repository.append_event(job_id, stage, message, data)
            await event_session.commit()

    provider = YahooFinanceProvider(
        cache=cache,
        cache_ttl_seconds=settings.analysis_cache_ttl_seconds,
        benchmark_ticker=settings.benchmark_ticker,
    )
    workflow = AnalysisWorkflow(provider=provider, settings=settings, on_event=emit)
    state = await workflow.run(request)
    identity = state["identity"]
    result = state["output"]

    async with SessionFactory() as session:
        repository = JobRepository(session)
        await repository.complete(job_id, identity.symbol, result)
        await repository.append_event(
            job_id,
            "complete",
            "Job persisted successfully",
            {"ticker": identity.symbol},
        )
        await session.commit()

    return {
        "job_id": str(job_id),
        "status": JobStatus.COMPLETED.value,
        "ticker": identity.symbol,
        "claimed": True,
    }


async def _mark_failed(job_id: UUID, error: str) -> None:
    async with SessionFactory() as session:
        repository = JobRepository(session)
        await repository.fail(job_id, error)
        await repository.append_event(
            job_id,
            "failed",
            "Analysis failed",
            {"error": error[:500]},
        )
        await session.commit()
