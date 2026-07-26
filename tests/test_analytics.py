"""Unit tests for deterministic analytics."""

from __future__ import annotations

import math

import pandas as pd

from app.analytics import (
    forecast_prices,
    fundamental_analysis,
    risk_analysis,
    sentiment_analysis,
    technical_analysis,
)


def test_technical_analysis_has_expected_regime(
    synthetic_history: pd.DataFrame,
) -> None:
    result = technical_analysis(synthetic_history)

    assert result["regime"] in {
        "strong_uptrend",
        "uptrend",
        "range_bound",
        "downtrend",
        "strong_downtrend",
    }
    assert 0 <= result["rsi_14"] <= 100
    assert math.isfinite(result["last_close"])


def test_forecast_returns_all_requested_horizons(
    synthetic_history: pd.DataFrame,
) -> None:
    result = forecast_prices(synthetic_history, [5, 20, 60])

    assert result["model"] == "ridge_autoregressive_v1"
    assert [item["horizon_days"] for item in result["forecasts"]] == [5, 20, 60]
    assert 0.2 <= result["confidence"] <= 0.9
    for item in result["forecasts"]:
        assert item["low_80_price"] < item["high_80_price"]
        assert item["predicted_price"] > 0


def test_risk_analysis_is_finite(synthetic_history: pd.DataFrame) -> None:
    benchmark = synthetic_history.copy()
    benchmark["close"] = benchmark["close"].rolling(3, min_periods=1).mean()

    result = risk_analysis(synthetic_history, benchmark)

    assert result["risk_level"] in {"low", "moderate", "high", "very_high"}
    assert result["annualized_volatility_pct"] > 0
    assert result["historical_var_95_daily_pct"] <= 0


def test_fundamental_score_and_sentiment() -> None:
    fundamentals = fundamental_analysis(
        {
            "profitMargins": 0.22,
            "returnOnEquity": 0.28,
            "revenueGrowth": 0.14,
            "earningsGrowth": 0.18,
            "debtToEquity": 45,
            "currentRatio": 1.7,
            "forwardPE": 24,
            "freeCashflow": 5_000_000_000,
        }
    )
    sentiment = sentiment_analysis(
        [
            {
                "title": "Company beats estimates and raises guidance",
                "published_at": "2026-07-01T10:00:00+00:00",
            },
            {
                "title": "Analyst upgrades shares after strong growth",
                "published_at": "2026-07-02T10:00:00+00:00",
            },
        ]
    )

    assert fundamentals["quality_score"] > 70
    assert sentiment["label"] == "positive"
