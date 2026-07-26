"""Domain models shared across the API, workflow, and workers."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobStatus(StrEnum):
    """Lifecycle state for an analysis job."""

    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


class RatingLabel(StrEnum):
    """Explainable investment rating labels."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class AnalysisRequest(BaseModel):
    """Parameters accepted when starting an analysis."""

    company_name: str = Field(min_length=1, max_length=120)
    horizons: list[int] = Field(default_factory=lambda: [5, 20, 60])
    include_ai_narrative: bool = True

    @field_validator("company_name")
    @classmethod
    def normalize_company_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("company_name cannot be blank")
        return normalized

    @field_validator("horizons")
    @classmethod
    def validate_horizons(cls, value: list[int]) -> list[int]:
        unique = sorted(set(value))
        if not unique or len(unique) > 5:
            raise ValueError("provide between one and five unique horizons")
        if any(horizon < 1 or horizon > 252 for horizon in unique):
            raise ValueError("horizons must be between 1 and 252 trading days")
        return unique


class AnalysisAccepted(BaseModel):
    """Response returned after a job is accepted."""

    job_id: UUID
    status: JobStatus
    reused: bool = False


class CompanyIdentity(BaseModel):
    """Resolved market identity for a company search."""

    query: str
    symbol: str
    name: str
    exchange: str | None = None
    quote_type: str = "EQUITY"
    currency: str | None = None


class CompanyCandidate(BaseModel):
    """Candidate returned by the company search endpoint."""

    symbol: str
    name: str
    exchange: str | None = None
    quote_type: str | None = None
    score: float


class InvestmentNarrative(BaseModel):
    """Structured final output produced by CrewAI or the deterministic fallback."""

    executive_summary: str
    bull_case: list[str] = Field(default_factory=list, max_length=6)
    bear_case: list[str] = Field(default_factory=list, max_length=6)
    catalysts: list[str] = Field(default_factory=list, max_length=6)
    key_risks: list[str] = Field(default_factory=list, max_length=6)
    confidence_notes: str
    disclaimer: str


class AnalysisEventResponse(BaseModel):
    """Progress event emitted while a job runs."""

    sequence: int
    stage: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AnalysisJobResponse(BaseModel):
    """Complete representation of a persisted job."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str
    ticker: str | None
    status: JobStatus
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime
