"""LangGraph orchestration for the complete stock-analysis workflow."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.analytics import (
    forecast_prices,
    fundamental_analysis,
    risk_analysis,
    sentiment_analysis,
    technical_analysis,
)
from app.config import Settings
from app.crew import build_ai_narrative, build_fallback_narrative
from app.domain import AnalysisRequest, CompanyIdentity
from app.market import MarketBundle, MarketDataProvider
from app.ratings import build_ratings

EventCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class WorkflowState(TypedDict):
    """State passed between LangGraph nodes."""

    request: dict[str, Any]
    identity: NotRequired[CompanyIdentity]
    bundle: NotRequired[MarketBundle]
    technical: NotRequired[dict[str, Any]]
    fundamentals: NotRequired[dict[str, Any]]
    forecasts: NotRequired[dict[str, Any]]
    sentiment: NotRequired[dict[str, Any]]
    risk: NotRequired[dict[str, Any]]
    ratings: NotRequired[list[dict[str, Any]]]
    narrative: NotRequired[dict[str, Any]]
    output: NotRequired[dict[str, Any]]


class AnalysisWorkflow:
    """Build and execute the stateful analysis graph."""

    def __init__(
        self,
        provider: MarketDataProvider,
        settings: Settings,
        on_event: EventCallback,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._on_event = on_event
        self._graph = self._build_graph()

    async def run(self, request: AnalysisRequest) -> WorkflowState:
        """Execute the graph and return its final state."""
        return await self._graph.ainvoke({"request": request.model_dump(mode="json")})

    def _build_graph(self) -> Any:
        builder = StateGraph(WorkflowState)
        builder.add_node("resolve_company", self._resolve_company)
        builder.add_node("fetch_market_data", self._fetch_market_data)
        builder.add_node("run_analytics", self._run_analytics)
        builder.add_node("build_ratings", self._build_ratings)
        builder.add_node("crewai_committee", self._crewai_committee)
        builder.add_node("fallback_narrative", self._fallback_narrative)
        builder.add_node("finalize", self._finalize)

        builder.add_edge(START, "resolve_company")
        builder.add_edge("resolve_company", "fetch_market_data")
        builder.add_edge("fetch_market_data", "run_analytics")
        builder.add_edge("run_analytics", "build_ratings")
        builder.add_conditional_edges(
            "build_ratings",
            self._narrative_route,
            {
                "crewai": "crewai_committee",
                "fallback": "fallback_narrative",
            },
        )
        builder.add_edge("crewai_committee", "finalize")
        builder.add_edge("fallback_narrative", "finalize")
        builder.add_edge("finalize", END)
        return builder.compile()

    async def _resolve_company(self, state: WorkflowState) -> dict[str, Any]:
        request = AnalysisRequest.model_validate(state["request"])
        await self._emit("resolve", f"Resolving listed company for '{request.company_name}'")
        identity = await self._provider.resolve(request.company_name)
        await self._emit(
            "resolve",
            f"Resolved {identity.name} to {identity.symbol}",
            {"symbol": identity.symbol, "exchange": identity.exchange},
        )
        return {"identity": identity}

    async def _fetch_market_data(self, state: WorkflowState) -> dict[str, Any]:
        identity = state["identity"]
        await self._emit("market_data", f"Fetching market data for {identity.symbol}")
        bundle = await self._provider.fetch_bundle(
            identity,
            period=self._settings.market_data_period,
        )
        await self._emit(
            "market_data",
            "Market data normalized and cached",
            {
                "price_rows": len(bundle.history),
                "news_articles": len(bundle.news),
                "benchmark": self._settings.benchmark_ticker,
            },
        )
        return {"bundle": bundle}

    async def _run_analytics(self, state: WorkflowState) -> dict[str, Any]:
        request = AnalysisRequest.model_validate(state["request"])
        bundle = state["bundle"]
        await self._emit(
            "analytics",
            "Running technical, fundamental, forecast, sentiment, and risk analyses",
        )

        technical, fundamentals, forecasts, sentiment, risk = await asyncio.gather(
            asyncio.to_thread(technical_analysis, bundle.history),
            asyncio.to_thread(fundamental_analysis, bundle.info),
            asyncio.to_thread(forecast_prices, bundle.history, request.horizons),
            asyncio.to_thread(sentiment_analysis, bundle.news),
            asyncio.to_thread(risk_analysis, bundle.history, bundle.benchmark_history),
        )
        await self._emit(
            "analytics",
            "Quantitative analyses completed",
            {
                "technical_regime": technical.get("regime"),
                "risk_level": risk.get("risk_level"),
                "forecast_model": forecasts.get("model"),
            },
        )
        return {
            "technical": technical,
            "fundamentals": fundamentals,
            "forecasts": forecasts,
            "sentiment": sentiment,
            "risk": risk,
        }

    async def _build_ratings(self, state: WorkflowState) -> dict[str, Any]:
        await self._emit("ratings", "Building explainable horizon-specific ratings")
        ratings = build_ratings(
            forecasts=state["forecasts"],
            technical=state["technical"],
            fundamentals=state["fundamentals"],
            sentiment=state["sentiment"],
            risk=state["risk"],
            analyst_targets=state["bundle"].analyst_targets,
        )
        await self._emit(
            "ratings",
            "Ratings completed",
            {
                "ratings": [
                    {
                        "horizon_days": item["horizon_days"],
                        "label": item["label"],
                        "confidence": item["confidence"],
                    }
                    for item in ratings
                ]
            },
        )
        return {"ratings": ratings}

    def _narrative_route(self, state: WorkflowState) -> str:
        request = AnalysisRequest.model_validate(state["request"])
        return (
            "crewai"
            if request.include_ai_narrative and self._settings.crewai_enabled
            else "fallback"
        )

    async def _crewai_committee(self, state: WorkflowState) -> dict[str, Any]:
        await self._emit(
            "agents",
            "CrewAI specialist agents are reviewing the evidence",
        )
        payload = self._narrative_payload(state)
        try:
            narrative = await build_ai_narrative(payload, self._settings)
            await self._emit("agents", "CrewAI investment committee completed")
        except Exception as exc:
            await self._emit(
                "agents",
                "CrewAI failed; deterministic narrative used",
                {"error": str(exc)[:500]},
            )
            narrative = build_fallback_narrative(payload)
        return {"narrative": narrative}

    async def _fallback_narrative(self, state: WorkflowState) -> dict[str, Any]:
        await self._emit("agents", "Building deterministic evidence summary")
        return {"narrative": build_fallback_narrative(self._narrative_payload(state))}

    async def _finalize(self, state: WorkflowState) -> dict[str, Any]:
        bundle = state["bundle"]
        latest = bundle.history.iloc[-1]
        previous = bundle.history.iloc[-2]
        output = {
            "metadata": {
                "generated_at": datetime.now(UTC).isoformat(),
                "workflow": "langgraph_stock_analysis_v1",
                "market_data_provider": "yfinance",
                "benchmark": self._settings.benchmark_ticker,
                "educational_use_only": True,
            },
            "company": bundle.identity.model_dump(mode="json"),
            "snapshot": {
                "last_price": float(latest["close"]),
                "previous_close": float(previous["close"]),
                "daily_change_pct": float(latest["close"] / previous["close"] - 1) * 100,
                "currency": bundle.identity.currency,
                "market_cap": bundle.info.get("marketCap"),
                "sector": bundle.info.get("sector"),
                "industry": bundle.info.get("industry"),
                "fifty_two_week_high": bundle.info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": bundle.info.get("fiftyTwoWeekLow"),
            },
            "technical": state["technical"],
            "fundamentals": state["fundamentals"],
            "forecast": state["forecasts"],
            "sentiment": state["sentiment"],
            "risk": state["risk"],
            "ratings": state["ratings"],
            "analyst_targets": bundle.analyst_targets,
            "analyst_recommendations": bundle.recommendations,
            "narrative": state["narrative"],
            "price_history": [
                {
                    "date": timestamp.isoformat(),
                    "close": round(float(row["close"]), 6),
                    "volume": round(float(row["volume"]), 2),
                }
                for timestamp, row in bundle.history.tail(120).iterrows()
            ],
        }
        await self._emit("complete", "Analysis report finalized")
        return {"output": output}

    def _narrative_payload(self, state: WorkflowState) -> dict[str, Any]:
        bundle = state["bundle"]
        return {
            "company": bundle.identity.model_dump(mode="json"),
            "technical": state["technical"],
            "fundamentals": state["fundamentals"],
            "forecast": state["forecasts"],
            "sentiment": {
                key: value
                for key, value in state["sentiment"].items()
                if key != "articles"
            },
            "risk": state["risk"],
            "ratings": state["ratings"],
            "analyst_targets": bundle.analyst_targets,
            "recent_news": bundle.news[:8],
        }

    async def _emit(
        self,
        stage: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        await self._on_event(stage, message, data or {})
