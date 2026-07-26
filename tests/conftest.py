"""Shared synthetic test fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_history() -> pd.DataFrame:
    """Return deterministic five-year-like daily OHLCV history."""
    random = np.random.default_rng(7)
    dates = pd.bdate_range("2024-01-01", periods=520, tz="UTC")
    returns = random.normal(loc=0.0006, scale=0.014, size=len(dates))
    close = 100 * np.exp(np.cumsum(returns))
    open_price = close * (1 + random.normal(0, 0.002, size=len(dates)))
    high = np.maximum(open_price, close) * (1 + random.uniform(0.001, 0.015, len(dates)))
    low = np.minimum(open_price, close) * (1 - random.uniform(0.001, 0.015, len(dates)))
    volume = random.integers(1_000_000, 8_000_000, len(dates))

    return pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume.astype(float),
        },
        index=dates,
    )
