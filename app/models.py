"""SQLAlchemy persistence models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.domain import JobStatus

JsonType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Base declarative model."""


class AnalysisJob(Base):
    """Persisted asynchronous analysis job."""

    __tablename__ = "analysis_jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    company_name: Mapped[str] = mapped_column(String(120), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), default=JobStatus.QUEUED.value, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    error: Mapped[str | None] = mapped_column(Text)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    events: Mapped[list[AnalysisEvent]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="AnalysisEvent.sequence",
    )

    __table_args__ = (
        Index("ix_analysis_jobs_company_created", "company_name", "created_at"),
    )


class AnalysisEvent(Base):
    """Durable progress event for polling and server-sent events."""

    __tablename__ = "analysis_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(300), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    job: Mapped[AnalysisJob] = relationship(back_populates="events")

    __table_args__ = (
        UniqueConstraint("job_id", "sequence", name="uq_analysis_event_job_sequence"),
    )
