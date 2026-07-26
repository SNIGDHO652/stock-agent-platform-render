"""CrewAI investment-committee synthesis with a deterministic fallback."""

from __future__ import annotations

import json
import os
from typing import Any

from app.config import Settings
from app.domain import InvestmentNarrative


async def build_ai_narrative(
    payload: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    """Run specialist CrewAI agents and return a validated narrative."""
    if not settings.crewai_enabled:
        return build_fallback_narrative(payload)

    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    from crewai import Agent, Crew, Process, Task

    quant = Agent(
        role="Quantitative Market Analyst",
        goal="Interpret forecasts and technical regimes without overstating predictability.",
        backstory=(
            "You are a systematic equities researcher who focuses on signal quality, "
            "validation metrics, and uncertainty."
        ),
        llm=settings.crewai_model,
        verbose=False,
        allow_delegation=False,
    )
    fundamental = Agent(
        role="Fundamental Equity Analyst",
        goal="Evaluate business quality, growth, valuation, and balance-sheet resilience.",
        backstory=(
            "You are an evidence-driven public-markets analyst. You distinguish missing data "
            "from weak fundamentals and avoid unsupported claims."
        ),
        llm=settings.crewai_model,
        verbose=False,
        allow_delegation=False,
    )
    catalyst = Agent(
        role="News and Catalyst Analyst",
        goal="Identify sentiment, catalysts, and event risks only from the supplied evidence.",
        backstory=(
            "You analyze headline tone and catalysts while treating unverified headlines "
            "cautiously."
        ),
        llm=settings.crewai_model,
        verbose=False,
        allow_delegation=False,
    )
    risk = Agent(
        role="Portfolio Risk Officer",
        goal="Challenge optimistic assumptions and quantify downside and model limitations.",
        backstory=(
            "You are responsible for drawdown, volatility, concentration, liquidity, and "
            "forecast-risk review."
        ),
        llm=settings.crewai_model,
        verbose=False,
        allow_delegation=False,
    )
    committee = Agent(
        role="Investment Committee Chair",
        goal="Synthesize specialists into a balanced, horizon-aware educational research memo.",
        backstory=(
            "You reconcile conflicting evidence, preserve uncertainty, and never present the "
            "output as personalized financial advice."
        ),
        llm=settings.crewai_model,
        verbose=False,
        allow_delegation=False,
    )

    quant_task = Task(
        description=(
            "Analyze the technical, forecast, and rating sections in the supplied JSON. "
            "Call out validation quality and differences between horizons.\n"
            "DATA:\n{analysis_payload}"
        ),
        expected_output="A concise evidence-based quantitative assessment.",
        agent=quant,
    )
    fundamental_task = Task(
        description=(
            "Analyze fundamentals, valuation, growth, data completeness, and analyst targets. "
            "Do not infer facts absent from the JSON.\nDATA:\n{analysis_payload}"
        ),
        expected_output="A concise fundamental assessment with strengths and weaknesses.",
        agent=fundamental,
    )
    catalyst_task = Task(
        description=(
            "Analyze the supplied news sentiment and headlines for catalysts and event risks. "
            "Treat headline-only evidence as uncertain.\nDATA:\n{analysis_payload}"
        ),
        expected_output="A concise catalyst and sentiment assessment.",
        agent=catalyst,
    )
    risk_task = Task(
        description=(
            "Review volatility, drawdown, VaR, benchmark sensitivity, scenario outputs, and "
            "forecast limitations. Challenge the bullish and bearish cases.\n"
            "DATA:\n{analysis_payload}"
        ),
        expected_output="A concise independent risk assessment.",
        agent=risk,
    )
    committee_task = Task(
        description=(
            "Synthesize the four specialist reviews and the supplied JSON. Produce a balanced "
            "memo that distinguishes short-, medium-, and long-term signals. Every claim must "
            "be traceable to the supplied data. Include a clear educational-use disclaimer."
        ),
        expected_output="A validated structured investment research narrative.",
        agent=committee,
        context=[quant_task, fundamental_task, catalyst_task, risk_task],
        output_pydantic=InvestmentNarrative,
    )

    crew = Crew(
        agents=[quant, fundamental, catalyst, risk, committee],
        tasks=[quant_task, fundamental_task, catalyst_task, risk_task, committee_task],
        process=Process.sequential,
        verbose=False,
        memory=False,
        cache=True,
        max_rpm=30,
    )
    result = await crew.akickoff(
        inputs={"analysis_payload": json.dumps(payload, separators=(",", ":"), default=str)}
    )
    if result.pydantic:
        return result.pydantic.model_dump(mode="json")
    return InvestmentNarrative.model_validate(result.to_dict()).model_dump(mode="json")


def build_fallback_narrative(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic narrative when LLM execution is disabled or unavailable."""
    ratings = payload.get("ratings", [])
    fundamentals = payload.get("fundamentals", {})
    risk = payload.get("risk", {})
    sentiment = payload.get("sentiment", {})
    technical = payload.get("technical", {})

    rating_text = ", ".join(
        f"{item['bucket'].replace('_', ' ')}: {item['label'].replace('_', ' ')} "
        f"({item['score']:+.1f})"
        for item in ratings
    )
    strengths = fundamentals.get("strengths", [])[:4]
    fundamental_risks = fundamentals.get("risks", [])[:4]
    risk_level = risk.get("risk_level", "unknown")
    regime = technical.get("regime", "unknown")
    sentiment_label = sentiment.get("label", "neutral")

    narrative = InvestmentNarrative(
        executive_summary=(
            f"The model currently classifies the price regime as {regime}, news tone as "
            f"{sentiment_label}, and overall risk as {risk_level}. Horizon ratings are "
            f"{rating_text or 'unavailable'}. The signals are indicators, not guarantees."
        ),
        bull_case=strengths
        or [
            "A sustained positive price trend could improve forward return estimates.",
            "Improving earnings or revenue growth would strengthen the fundamental score.",
        ],
        bear_case=fundamental_risks
        or [
            "Forecast errors can widen materially during event-driven volatility.",
            "A trend reversal would weaken the technical contribution to the rating.",
        ],
        catalysts=[
            "Upcoming earnings and guidance changes",
            "Analyst estimate and price-target revisions",
            "Material product, regulatory, or capital-allocation announcements",
        ],
        key_risks=[
            f"Historical risk classification is {risk_level}",
            "The forecast uses historical prices and does not explicitly model macro shocks",
            "Public market data can be delayed, incomplete, or revised",
        ],
        confidence_notes=(
            "Confidence combines forecast validation, fundamental-data completeness, news "
            "coverage, and historical risk. Low confidence should reduce reliance on the label."
        ),
        disclaimer=(
            "Educational research only. This is not personalized investment advice, a "
            "solicitation, or a guarantee of future performance."
        ),
    )
    return narrative.model_dump(mode="json")
