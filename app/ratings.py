"""Explainable short-, medium-, and long-horizon rating engine."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.domain import RatingLabel


def build_ratings(
    forecasts: dict[str, Any],
    technical: dict[str, Any],
    fundamentals: dict[str, Any],
    sentiment: dict[str, Any],
    risk: dict[str, Any],
    analyst_targets: dict[str, Any],
) -> list[dict[str, Any]]:
    """Combine independent signals into explainable horizon ratings."""
    forecast_by_horizon = {
        int(item["horizon_days"]): item for item in forecasts.get("forecasts", [])
    }
    results: list[dict[str, Any]] = []

    current_price = float(technical["last_close"])
    analyst_mean = _number(
        analyst_targets.get("mean")
        or analyst_targets.get("targetMeanPrice")
        or analyst_targets.get("median")
    )
    analyst_upside = (analyst_mean / current_price - 1) * 100 if analyst_mean else 0.0

    for horizon, forecast in sorted(forecast_by_horizon.items()):
        if horizon <= 10:
            bucket = "short_term"
            weights = {
                "forecast": 0.38,
                "technical": 0.30,
                "fundamental": 0.07,
                "sentiment": 0.15,
                "analyst": 0.05,
                "risk": 0.05,
            }
        elif horizon <= 40:
            bucket = "medium_term"
            weights = {
                "forecast": 0.32,
                "technical": 0.22,
                "fundamental": 0.16,
                "sentiment": 0.10,
                "analyst": 0.10,
                "risk": 0.10,
            }
        else:
            bucket = "long_term"
            weights = {
                "forecast": 0.24,
                "technical": 0.12,
                "fundamental": 0.32,
                "sentiment": 0.06,
                "analyst": 0.12,
                "risk": 0.14,
            }

        forecast_signal = _bounded(float(forecast["predicted_return_pct"]) / 20)
        technical_signal = _technical_signal(technical)
        fundamental_signal = _bounded((float(fundamentals["quality_score"]) - 50) / 35)
        sentiment_signal = _bounded(float(sentiment.get("overall_score") or 0.0))
        analyst_signal = _bounded(analyst_upside / 25)
        risk_signal = _risk_signal(risk)

        signals = {
            "forecast": forecast_signal,
            "technical": technical_signal,
            "fundamental": fundamental_signal,
            "sentiment": sentiment_signal,
            "analyst": analyst_signal,
            "risk": risk_signal,
        }
        score = sum(signals[name] * weight for name, weight in weights.items()) * 100
        label = _label(score)

        drivers = sorted(
            (
                {
                    "signal": name,
                    "contribution": round(signals[name] * weights[name] * 100, 2),
                }
                for name in signals
            ),
            key=lambda item: abs(item["contribution"]),
            reverse=True,
        )

        forecast_confidence = float(forecasts.get("confidence") or 0.25)
        completeness = float(fundamentals.get("data_completeness") or 0.0)
        confidence = np.clip(
            0.45 * forecast_confidence
            + 0.25 * completeness
            + 0.20 * min(sentiment.get("article_count", 0) / 8, 1)
            + 0.10 * (1 - min(abs(float(risk.get("max_drawdown_pct") or 0)) / 80, 1)),
            0.15,
            0.9,
        )

        results.append(
            {
                "horizon_days": horizon,
                "bucket": bucket,
                "label": label.value,
                "score": round(float(score), 2),
                "confidence": round(float(confidence), 3),
                "predicted_return_pct": forecast["predicted_return_pct"],
                "drivers": drivers[:5],
            }
        )

    return results


def _technical_signal(technical: dict[str, Any]) -> float:
    trend = float(technical.get("trend_score") or 0) / 4
    rsi = float(technical.get("rsi_14") or 50)
    rsi_signal = 0.0
    if rsi < 30:
        rsi_signal = 0.35
    elif rsi > 70:
        rsi_signal = -0.35
    momentum = _bounded(float(technical.get("return_20d_pct") or 0) / 15)
    return _bounded(0.55 * trend + 0.30 * momentum + 0.15 * rsi_signal)


def _risk_signal(risk: dict[str, Any]) -> float:
    volatility = float(risk.get("annualized_volatility_pct") or 0)
    drawdown = abs(float(risk.get("max_drawdown_pct") or 0))
    beta = abs(float(risk.get("beta_to_benchmark") or 1))
    penalty = (
        min(volatility / 60, 1) * 0.45
        + min(drawdown / 60, 1) * 0.4
        + min(max(beta - 1, 0) / 2, 1) * 0.15
    )
    return -_bounded(penalty)


def _bounded(value: float) -> float:
    return float(np.clip(value, -1, 1))


def _label(score: float) -> RatingLabel:
    if score >= 35:
        return RatingLabel.STRONG_BUY
    if score >= 15:
        return RatingLabel.BUY
    if score <= -35:
        return RatingLabel.STRONG_SELL
    if score <= -15:
        return RatingLabel.SELL
    return RatingLabel.HOLD


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
