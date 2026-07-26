"""End-to-end LangGraph workflow test using an in-memory fake provider."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from app.config import Settings
from app.domain import AnalysisRequest, CompanyIdentity
from app.market import MarketBundle
from app.workflow import AnalysisWorkflow


class FakeProvider:
    """Deterministic provider used to test orchestration without network access."""

    def __init__(self, bundle: MarketBundle) -> None:
        self.bundle = bundle

    async def resolve(self, query: str) -> CompanyIdentity:
        return self.bundle.identity

    async def fetch_bundle(self, identity: CompanyIdentity, period: str) -> MarketBundle:
        return self.bundle


@pytest.mark.asyncio
async def test_workflow_produces_complete_report(
    synthetic_history: pd.DataFrame,
) -> None:
    identity = CompanyIdentity(
        query="Example",
        symbol="EXM",
        name="Example Corp",
        exchange="TEST",
        currency="USD",
    )
    bundle = MarketBundle(
        identity=identity,
        info={
            "sector": "Technology",
            "industry": "Software",
            "marketCap": 10_000_000_000,
            "profitMargins": 0.18,
            "returnOnEquity": 0.22,
            "revenueGrowth": 0.12,
            "earningsGrowth": 0.16,
            "debtToEquity": 55,
            "currentRatio": 1.5,
            "forwardPE": 27,
            "freeCashflow": 900_000_000,
        },
        history=synthetic_history,
        benchmark_history=synthetic_history.copy(),
        news=[
            {
                "title": "Example beats estimates with strong growth",
                "published_at": "2026-07-01T10:00:00+00:00",
            }
        ],
        analyst_targets={"mean": float(synthetic_history["close"].iloc[-1] * 1.1)},
        recommendations=[],
    )
    events: list[tuple[str, str, dict[str, Any]]] = []

    async def capture(stage: str, message: str, data: dict[str, Any]) -> None:
        events.append((stage, message, data))

    settings = Settings(
        _env_file=None,
        enable_crewai_default=False,
        openai_api_key=None,
        market_data_period="5y",
        benchmark_ticker="SPY",
    )
    workflow = AnalysisWorkflow(
        provider=FakeProvider(bundle),
        settings=settings,
        on_event=capture,
    )
    state = await workflow.run(
        AnalysisRequest(
            company_name="Example",
            horizons=[5, 20, 60],
            include_ai_narrative=False,
        )
    )

    report = state["output"]
    assert report["company"]["symbol"] == "EXM"
    assert len(report["ratings"]) == 3
    assert report["narrative"]["executive_summary"]
    assert any(stage == "complete" for stage, _, _ in events)
