"""Deterministic quantitative analytics used by the LangGraph workflow."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd


def technical_analysis(history: pd.DataFrame) -> dict[str, Any]:
    """Calculate trend, momentum, and volatility indicators."""
    close = _close_series(history)
    high = history["high"].astype(float)
    low = history["low"].astype(float)
    returns = close.pct_change()

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    rsi = _rsi(close, 14)
    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr14 = true_range.rolling(14).mean()

    latest = float(close.iloc[-1])
    trend_score = 0.0
    trend_score += 1.0 if latest > _last(sma20) else -1.0
    trend_score += 1.0 if latest > _last(sma50) else -1.0
    trend_score += 1.0 if latest > _last(sma200) else -1.0
    trend_score += 1.0 if _last(macd) > _last(macd_signal) else -1.0

    rsi_value = _last(rsi)
    if trend_score >= 3:
        regime = "strong_uptrend"
    elif trend_score >= 1:
        regime = "uptrend"
    elif trend_score <= -3:
        regime = "strong_downtrend"
    elif trend_score <= -1:
        regime = "downtrend"
    else:
        regime = "range_bound"

    return _clean(
        {
            "last_close": latest,
            "daily_change_pct": returns.iloc[-1] * 100 if len(returns.dropna()) else None,
            "return_5d_pct": close.pct_change(5).iloc[-1] * 100,
            "return_20d_pct": close.pct_change(20).iloc[-1] * 100,
            "return_60d_pct": close.pct_change(60).iloc[-1] * 100,
            "sma_20": _last(sma20),
            "sma_50": _last(sma50),
            "sma_200": _last(sma200),
            "distance_to_sma20_pct": (latest / _last(sma20) - 1) * 100,
            "distance_to_sma50_pct": (latest / _last(sma50) - 1) * 100,
            "distance_to_sma200_pct": (latest / _last(sma200) - 1) * 100,
            "rsi_14": rsi_value,
            "rsi_state": (
                "overbought" if rsi_value >= 70 else "oversold" if rsi_value <= 30 else "neutral"
            ),
            "macd": _last(macd),
            "macd_signal": _last(macd_signal),
            "atr_14": _last(atr14),
            "atr_pct": _last(atr14) / latest * 100,
            "annualized_volatility_pct": returns.std() * math.sqrt(252) * 100,
            "trend_score": trend_score,
            "regime": regime,
        }
    )


def fundamental_analysis(info: dict[str, Any]) -> dict[str, Any]:
    """Produce a transparent fundamental-quality and valuation score."""
    metrics = {
        "market_cap": _number(info.get("marketCap")),
        "enterprise_value": _number(info.get("enterpriseValue")),
        "trailing_pe": _number(info.get("trailingPE")),
        "forward_pe": _number(info.get("forwardPE")),
        "price_to_book": _number(info.get("priceToBook")),
        "enterprise_to_ebitda": _number(info.get("enterpriseToEbitda")),
        "profit_margin_pct": _percent(info.get("profitMargins")),
        "gross_margin_pct": _percent(info.get("grossMargins")),
        "operating_margin_pct": _percent(info.get("operatingMargins")),
        "return_on_equity_pct": _percent(info.get("returnOnEquity")),
        "return_on_assets_pct": _percent(info.get("returnOnAssets")),
        "revenue_growth_pct": _percent(info.get("revenueGrowth")),
        "earnings_growth_pct": _percent(info.get("earningsGrowth")),
        "debt_to_equity": _number(info.get("debtToEquity")),
        "current_ratio": _number(info.get("currentRatio")),
        "free_cashflow": _number(info.get("freeCashflow")),
        "dividend_yield_pct": _percent(info.get("dividendYield")),
    }

    score = 50.0
    strengths: list[str] = []
    risks: list[str] = []

    profit_margin = metrics["profit_margin_pct"]
    if profit_margin is not None:
        if profit_margin >= 15:
            score += 10
            strengths.append("Healthy net profit margin")
        elif profit_margin < 0:
            score -= 15
            risks.append("Business is currently unprofitable")

    roe = metrics["return_on_equity_pct"]
    if roe is not None:
        if roe >= 15:
            score += 10
            strengths.append("Strong return on equity")
        elif roe < 5:
            score -= 7
            risks.append("Weak return on equity")

    revenue_growth = metrics["revenue_growth_pct"]
    if revenue_growth is not None:
        if revenue_growth >= 10:
            score += 9
            strengths.append("Double-digit revenue growth")
        elif revenue_growth < 0:
            score -= 9
            risks.append("Revenue is contracting")

    earnings_growth = metrics["earnings_growth_pct"]
    if earnings_growth is not None:
        if earnings_growth >= 10:
            score += 9
            strengths.append("Double-digit earnings growth")
        elif earnings_growth < 0:
            score -= 9
            risks.append("Earnings are contracting")

    debt_to_equity = metrics["debt_to_equity"]
    if debt_to_equity is not None:
        if debt_to_equity <= 80:
            score += 7
            strengths.append("Conservative leverage")
        elif debt_to_equity >= 200:
            score -= 12
            risks.append("Elevated balance-sheet leverage")

    current_ratio = metrics["current_ratio"]
    if current_ratio is not None:
        if current_ratio >= 1.2:
            score += 5
        elif current_ratio < 0.8:
            score -= 7
            risks.append("Potential short-term liquidity pressure")

    forward_pe = metrics["forward_pe"]
    if forward_pe is not None:
        if 0 < forward_pe <= 30:
            score += 6
            strengths.append("Forward valuation is not extreme")
        elif forward_pe >= 60:
            score -= 8
            risks.append("Demanding forward earnings multiple")

    free_cashflow = metrics["free_cashflow"]
    if free_cashflow is not None:
        if free_cashflow > 0:
            score += 7
            strengths.append("Positive free cash flow")
        else:
            score -= 7
            risks.append("Negative free cash flow")

    available = sum(value is not None for value in metrics.values())
    completeness = available / len(metrics)

    return _clean(
        {
            "company_profile": {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "employees": info.get("fullTimeEmployees"),
            },
            "metrics": metrics,
            "quality_score": round(float(np.clip(score, 0, 100)), 1),
            "data_completeness": round(completeness, 3),
            "strengths": strengths[:5],
            "risks": risks[:5],
        }
    )


def risk_analysis(history: pd.DataFrame, benchmark_history: pd.DataFrame) -> dict[str, Any]:
    """Calculate market risk, downside risk, and benchmark sensitivity."""
    close = _close_series(history)
    returns = close.pct_change().dropna()
    benchmark_returns = pd.Series(dtype=float)
    if (
        not benchmark_history.empty
        and "close" in benchmark_history
        and benchmark_history["close"].dropna().shape[0] >= 30
    ):
        benchmark_returns = (
            benchmark_history["close"]
            .astype(float)
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
            .pct_change()
            .dropna()
        )

    cumulative = (1 + returns).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    annual_return = returns.mean() * 252
    annual_volatility = returns.std(ddof=1) * math.sqrt(252)
    downside = returns[returns < 0]
    downside_deviation = downside.std(ddof=1) * math.sqrt(252) if len(downside) > 1 else np.nan

    var95 = np.quantile(returns, 0.05)
    var99 = np.quantile(returns, 0.01)
    cvar95 = returns[returns <= var95].mean()

    aligned = pd.concat(
        [returns.rename("asset"), benchmark_returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    beta = None
    correlation = None
    annualized_alpha = None
    if len(aligned) >= 30 and aligned["benchmark"].var() > 0:
        beta = aligned["asset"].cov(aligned["benchmark"]) / aligned["benchmark"].var()
        correlation = aligned["asset"].corr(aligned["benchmark"])
        annualized_alpha = (
            aligned["asset"].mean() - beta * aligned["benchmark"].mean()
        ) * 252

    risk_level = "low"
    if annual_volatility >= 0.45 or abs(drawdown.min()) >= 0.5:
        risk_level = "very_high"
    elif annual_volatility >= 0.32 or abs(drawdown.min()) >= 0.35:
        risk_level = "high"
    elif annual_volatility >= 0.22 or abs(drawdown.min()) >= 0.22:
        risk_level = "moderate"

    latest = float(close.iloc[-1])
    daily_sigma = float(returns.std(ddof=1))

    return _clean(
        {
            "risk_level": risk_level,
            "annualized_return_pct": annual_return * 100,
            "annualized_volatility_pct": annual_volatility * 100,
            "sharpe_ratio": annual_return / annual_volatility if annual_volatility > 0 else None,
            "sortino_ratio": (
                annual_return / downside_deviation
                if downside_deviation and math.isfinite(downside_deviation)
                else None
            ),
            "max_drawdown_pct": drawdown.min() * 100,
            "historical_var_95_daily_pct": var95 * 100,
            "historical_var_99_daily_pct": var99 * 100,
            "historical_cvar_95_daily_pct": cvar95 * 100,
            "beta_to_benchmark": beta,
            "correlation_to_benchmark": correlation,
            "annualized_alpha_pct": annualized_alpha * 100 if annualized_alpha else None,
            "scenarios": {
                "one_sigma_down_price": latest * (1 - daily_sigma * math.sqrt(20)),
                "two_sigma_down_price": latest * (1 - 2 * daily_sigma * math.sqrt(20)),
                "one_sigma_up_price": latest * (1 + daily_sigma * math.sqrt(20)),
            },
        }
    )


POSITIVE_WORDS = {
    "beat",
    "beats",
    "bullish",
    "growth",
    "upgrade",
    "upgraded",
    "record",
    "profit",
    "profits",
    "strong",
    "surge",
    "surges",
    "expand",
    "expansion",
    "launch",
    "wins",
    "outperform",
    "positive",
    "raises",
    "raised",
    "partnership",
    "approval",
}
NEGATIVE_WORDS = {
    "miss",
    "misses",
    "bearish",
    "decline",
    "downgrade",
    "downgraded",
    "loss",
    "losses",
    "weak",
    "fall",
    "falls",
    "cut",
    "cuts",
    "lawsuit",
    "probe",
    "investigation",
    "recall",
    "risk",
    "warning",
    "layoff",
    "layoffs",
    "fraud",
}


def sentiment_analysis(news: list[dict[str, Any]]) -> dict[str, Any]:
    """Score headline sentiment using a deterministic, auditable lexicon."""
    scored: list[dict[str, Any]] = []
    weighted_total = 0.0
    total_weight = 0.0
    now = datetime.now(UTC)

    for item in news:
        text = f"{item.get('title', '')} {item.get('summary', '')}".casefold()
        tokens = re.findall(r"[a-z]+", text)
        positives = sum(token in POSITIVE_WORDS for token in tokens)
        negatives = sum(token in NEGATIVE_WORDS for token in tokens)
        denominator = max(positives + negatives, 1)
        score = (positives - negatives) / denominator

        age_days = 7.0
        published_at = item.get("published_at")
        if published_at:
            try:
                timestamp = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=UTC)
                age_days = max((now - timestamp).total_seconds() / 86_400, 0)
            except ValueError:
                pass
        weight = math.exp(-age_days / 14)
        weighted_total += score * weight
        total_weight += weight
        scored.append({**item, "sentiment_score": round(score, 3)})

    overall = weighted_total / total_weight if total_weight else 0.0
    label = "positive" if overall > 0.15 else "negative" if overall < -0.15 else "neutral"
    positives = sorted(scored, key=lambda item: item["sentiment_score"], reverse=True)
    negatives = sorted(scored, key=lambda item: item["sentiment_score"])

    return _clean(
        {
            "overall_score": overall,
            "label": label,
            "article_count": len(scored),
            "top_positive": positives[:3],
            "top_negative": negatives[:3],
            "articles": scored,
        }
    )


def forecast_prices(history: pd.DataFrame, horizons: list[int]) -> dict[str, Any]:
    """Forecast future prices with an explainable ridge-regression time-series model."""
    close = _close_series(history)
    features = _feature_frame(close)
    if len(features) < 100:
        return _momentum_fallback(close, horizons, "insufficient rows for ridge model")

    x = features.drop(columns=["target"]).to_numpy(dtype=float)
    y = features["target"].to_numpy(dtype=float)
    split = max(int(len(features) * 0.8), len(features) - 80)
    split = min(split, len(features) - 20)

    x_train, x_valid = x[:split], x[split:]
    y_train, y_valid = y[:split], y[split:]

    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale == 0] = 1.0

    x_train_scaled = (x_train - mean) / scale
    x_valid_scaled = (x_valid - mean) / scale
    weights = _fit_ridge(x_train_scaled, y_train, alpha=8.0)
    valid_predictions = _predict_ridge(x_valid_scaled, weights)
    residuals = y_valid - valid_predictions
    residual_std = float(np.std(residuals, ddof=1))
    directional_accuracy = float(np.mean(np.sign(valid_predictions) == np.sign(y_valid)))
    rmse = float(np.sqrt(np.mean(np.square(residuals))))

    synthetic = close.copy()
    horizon_set = set(horizons)
    predictions: dict[int, float] = {}
    for step in range(1, max(horizons) + 1):
        vector = _latest_feature_vector(synthetic)
        scaled = (vector - mean) / scale
        predicted_return = float(_predict_ridge(scaled.reshape(1, -1), weights)[0])
        predicted_return = float(np.clip(predicted_return, -0.12, 0.12))
        next_price = float(synthetic.iloc[-1] * (1 + predicted_return))
        next_index = synthetic.index[-1] + pd.offsets.BDay(1)
        synthetic.loc[next_index] = next_price
        if step in horizon_set:
            predictions[step] = next_price

    last_price = float(close.iloc[-1])
    sample_factor = min(len(features) / 500, 1.0)
    accuracy_factor = np.clip((directional_accuracy - 0.45) / 0.2, 0, 1)
    confidence = float(np.clip(0.35 + 0.35 * sample_factor + 0.3 * accuracy_factor, 0.2, 0.9))

    forecast_rows: list[dict[str, Any]] = []
    z90 = 1.2816
    for horizon in horizons:
        median = predictions[horizon]
        cumulative_sigma = residual_std * math.sqrt(horizon)
        low = median * math.exp(-z90 * cumulative_sigma)
        high = median * math.exp(z90 * cumulative_sigma)
        forecast_rows.append(
            {
                "horizon_days": horizon,
                "predicted_price": median,
                "predicted_return_pct": (median / last_price - 1) * 100,
                "low_80_price": low,
                "high_80_price": high,
            }
        )

    return _clean(
        {
            "model": "ridge_autoregressive_v1",
            "training_rows": len(features),
            "validation_rows": len(y_valid),
            "validation_directional_accuracy": directional_accuracy,
            "validation_daily_return_rmse": rmse,
            "confidence": confidence,
            "forecasts": forecast_rows,
            "limitations": [
                "Price-only model; macroeconomic and event shocks are not explicitly modeled",
                "Prediction intervals assume residual volatility remains broadly stable",
            ],
        }
    )


def _feature_frame(close: pd.Series) -> pd.DataFrame:
    returns = close.pct_change()
    frame = pd.DataFrame(index=close.index)
    frame["return_1"] = close.pct_change(1)
    frame["return_2"] = close.pct_change(2)
    frame["return_5"] = close.pct_change(5)
    frame["return_10"] = close.pct_change(10)
    frame["return_20"] = close.pct_change(20)
    frame["volatility_10"] = returns.rolling(10).std()
    frame["volatility_20"] = returns.rolling(20).std()
    frame["distance_sma20"] = close / close.rolling(20).mean() - 1
    frame["distance_sma50"] = close / close.rolling(50).mean() - 1
    frame["rsi_scaled"] = _rsi(close, 14) / 100
    frame["target"] = returns.shift(-1)
    return frame.replace([np.inf, -np.inf], np.nan).dropna()


def _latest_feature_vector(close: pd.Series) -> np.ndarray:
    returns = close.pct_change()
    values = [
        close.pct_change(1).iloc[-1],
        close.pct_change(2).iloc[-1],
        close.pct_change(5).iloc[-1],
        close.pct_change(10).iloc[-1],
        close.pct_change(20).iloc[-1],
        returns.rolling(10).std().iloc[-1],
        returns.rolling(20).std().iloc[-1],
        close.iloc[-1] / close.rolling(20).mean().iloc[-1] - 1,
        close.iloc[-1] / close.rolling(50).mean().iloc[-1] - 1,
        _rsi(close, 14).iloc[-1] / 100,
    ]
    return np.nan_to_num(np.asarray(values, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)


def _fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    augmented = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(augmented.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.pinv(augmented.T @ augmented + penalty) @ augmented.T @ y


def _predict_ridge(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    augmented = np.column_stack([np.ones(len(x)), x])
    return augmented @ weights


def _momentum_fallback(
    close: pd.Series,
    horizons: list[int],
    reason: str,
) -> dict[str, Any]:
    daily_returns = close.pct_change().dropna()
    drift = float(daily_returns.tail(60).median())
    volatility = float(daily_returns.tail(60).std(ddof=1))
    last_price = float(close.iloc[-1])
    forecasts = []
    for horizon in horizons:
        price = last_price * math.exp(drift * horizon)
        sigma = volatility * math.sqrt(horizon)
        forecasts.append(
            {
                "horizon_days": horizon,
                "predicted_price": price,
                "predicted_return_pct": (price / last_price - 1) * 100,
                "low_80_price": price * math.exp(-1.2816 * sigma),
                "high_80_price": price * math.exp(1.2816 * sigma),
            }
        )
    return _clean(
        {
            "model": "robust_momentum_fallback",
            "training_rows": len(daily_returns),
            "validation_rows": 0,
            "validation_directional_accuracy": None,
            "validation_daily_return_rmse": None,
            "confidence": 0.25,
            "forecasts": forecasts,
            "limitations": [reason],
        }
    )


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    relative_strength = gains / losses.replace(0, np.nan)
    return 100 - 100 / (1 + relative_strength)


def _close_series(history: pd.DataFrame) -> pd.Series:
    if history.empty or "close" not in history:
        raise ValueError("history must include non-empty close prices")
    close = history["close"].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(close) < 30:
        raise ValueError("at least 30 close prices are required")
    return close


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _percent(value: Any) -> float | None:
    number = _number(value)
    return number * 100 if number is not None else None


def _last(series: pd.Series) -> float:
    non_null = series.dropna()
    return float(non_null.iloc[-1]) if len(non_null) else float("nan")


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, np.generic):
        return _clean(value.item())
    if isinstance(value, float):
        return round(value, 6) if math.isfinite(value) else None
    return value
