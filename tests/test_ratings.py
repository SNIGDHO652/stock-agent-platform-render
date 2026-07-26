"""Unit tests for the rating policy."""

from __future__ import annotations

from app.ratings import build_ratings


def test_positive_signals_produce_non_bearish_ratings() -> None:
    ratings = build_ratings(
        forecasts={
            "confidence": 0.7,
            "forecasts": [
                {"horizon_days": 5, "predicted_return_pct": 4.0},
                {"horizon_days": 20, "predicted_return_pct": 9.0},
                {"horizon_days": 60, "predicted_return_pct": 18.0},
            ],
        },
        technical={
            "last_close": 100,
            "trend_score": 4,
            "rsi_14": 58,
            "return_20d_pct": 8,
        },
        fundamentals={"quality_score": 82, "data_completeness": 0.9},
        sentiment={"overall_score": 0.45, "article_count": 8},
        risk={
            "annualized_volatility_pct": 18,
            "max_drawdown_pct": -14,
            "beta_to_benchmark": 0.95,
        },
        analyst_targets={"mean": 118},
    )

    assert len(ratings) == 3
    assert all(item["label"] in {"strong_buy", "buy", "hold"} for item in ratings)
    assert all(item["drivers"] for item in ratings)
