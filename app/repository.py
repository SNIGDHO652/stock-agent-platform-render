"""Persistence operations for jobs and progress events."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import AnalysisRequest, JobStatus
from app.models import AnalysisEvent, AnalysisJob


class JobRepository:
    """Encapsulate database access for analysis jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, job_id: UUID) -> AnalysisJob | None:
        return await self._session.get(AnalysisJob, job_id)

    async def get_by_idempotency_key(self, key: str) -> AnalysisJob | None:
        statement = select(AnalysisJob).where(AnalysisJob.idempotency_key == key)
        return await self._session.scalar(statement)

    async def create(
        self,
        request: AnalysisRequest,
        idempotency_key: str,
        request_hash: str,
    ) -> AnalysisJob:
        job = AnalysisJob(
            company_name=request.company_name,
            status=JobStatus.QUEUED.value,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            request_payload=request.model_dump(mode="json"),
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def claim(self, job_id: UUID, owner: str, lease_seconds: int) -> AnalysisJob | None:
        now = datetime.now(UTC)
        statement = (
            update(AnalysisJob)
            .where(
                AnalysisJob.id == job_id,
                AnalysisJob.status != JobStatus.COMPLETED.value,
                or_(
                    AnalysisJob.lease_expires_at.is_(None),
                    AnalysisJob.lease_expires_at < now,
                    AnalysisJob.lease_owner == owner,
                ),
            )
            .values(
                status=JobStatus.RUNNING.value,
                lease_owner=owner,
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                error=None,
                updated_at=now,
            )
            .returning(AnalysisJob)
        )
        return await self._session.scalar(statement)

    async def mark_retrying(self, job_id: UUID, error: str) -> None:
        await self._session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == job_id)
            .values(
                status=JobStatus.RETRYING.value,
                error=error[:4000],
                lease_owner=None,
                lease_expires_at=None,
                updated_at=datetime.now(UTC),
            )
        )

    async def complete(self, job_id: UUID, ticker: str, result: dict[str, Any]) -> None:
        await self._session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == job_id)
            .values(
                ticker=ticker,
                status=JobStatus.COMPLETED.value,
                result=result,
                error=None,
                lease_owner=None,
                lease_expires_at=None,
                updated_at=datetime.now(UTC),
            )
        )

    async def fail(self, job_id: UUID, error: str) -> None:
        await self._session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == job_id)
            .values(
                status=JobStatus.FAILED.value,
                error=error[:4000],
                lease_owner=None,
                lease_expires_at=None,
                updated_at=datetime.now(UTC),
            )
        )

    async def append_event(
        self,
        job_id: UUID,
        stage: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> AnalysisEvent:
        await self._session.execute(
            select(AnalysisJob.id)
            .where(AnalysisJob.id == job_id)
            .with_for_update()
        )
        maximum = await self._session.scalar(
            select(func.max(AnalysisEvent.sequence)).where(AnalysisEvent.job_id == job_id)
        )
        event = AnalysisEvent(
            job_id=job_id,
            sequence=(maximum or 0) + 1,
            stage=stage,
            message=message,
            data=data or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_events(self, job_id: UUID, after: int = 0) -> list[AnalysisEvent]:
        statement = (
            select(AnalysisEvent)
            .where(AnalysisEvent.job_id == job_id, AnalysisEvent.sequence > after)
            .order_by(AnalysisEvent.sequence)
        )
        return list((await self._session.scalars(statement)).all())
