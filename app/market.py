"""Market-data provider abstraction and Yahoo Finance implementation."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any, Protocol

import numpy as np
import orjson
import pandas as pd
import structlog
import yfinance as yf
from app.domain import CompanyCandidate, CompanyIdentity

logger = structlog.get_logger(__name__)


class MarketDataError(RuntimeError):
    """Raised when market data cannot be resolved or fetched."""


class CompanyNotFoundError(MarketDataError):
    """Raised when no equity matches the company query."""


@dataclass(slots=True)
class MarketBundle:
    """Normalized market data used by analytics and the agent workflow."""

    identity: CompanyIdentity
    info: dict[str, Any]
    history: pd.DataFrame
    benchmark_history: pd.DataFrame
    news: list[dict[str, Any]]
    analyst_targets: dict[str, Any]
    recommendations: list[dict[str, Any]]

    def to_cache(self) -> dict[str, Any]:
        return {
            "identity": self.identity.model_dump(mode="json"),
            "info": self.info,
            "history": _history_to_records(self.history),
            "benchmark_history": _history_to_records(self.benchmark_history),
            "news": self.news,
            "analyst_targets": self.analyst_targets,
            "recommendations": self.recommendations,
        }

    @classmethod
    def from_cache(cls, payload: dict[str, Any]) -> MarketBundle:
        return cls(
            identity=CompanyIdentity.model_validate(payload["identity"]),
            info=payload["info"],
            history=_records_to_history(payload["history"]),
            benchmark_history=_records_to_history(payload["benchmark_history"]),
            news=payload["news"],
            analyst_targets=payload["analyst_targets"],
            recommendations=payload["recommendations"],
        )



class CacheClient(Protocol):
    """Minimal async cache interface used by market-data adapters."""

    async def get(self, key: str) -> bytes | None:
        """Return cached bytes or None."""
        ...

    async def set(self, key: str, value: bytes, ex: int | None = None) -> bool:
        """Store cached bytes."""
        ...


class MarketDataProvider(Protocol):
    """Contract implemented by market-data adapters."""

    async def search(self, query: str, limit: int = 5) -> list[CompanyCandidate]:
        """Return ranked listed-equity candidates."""
        ...

    async def resolve(self, query: str) -> CompanyIdentity:
        """Resolve a user query to one listed company."""
        ...

    async def fetch_bundle(self, identity: CompanyIdentity, period: str) -> MarketBundle:
        """Return normalized data for analysis."""
        ...


class YahooFinanceProvider:
    """Fetch research-grade public data through yfinance.

    Replace this adapter with a licensed provider for commercial production use.
    """

    def __init__(
        self,
        cache: CacheClient,
        cache_ttl_seconds: int,
        benchmark_ticker: str,
    ) -> None:
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._benchmark_ticker = benchmark_ticker.upper()

    async def search(self, query: str, limit: int = 5) -> list[CompanyCandidate]:
        normalized = " ".join(query.split())
        cache_key = f"company-search:v1:{normalized.casefold()}:{limit}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return [CompanyCandidate.model_validate(item) for item in cached]

        candidates = await asyncio.to_thread(self._search_sync, normalized, limit)
        await self._cache_set(
            cache_key,
            [candidate.model_dump(mode="json") for candidate in candidates],
            ttl=min(self._cache_ttl_seconds, 3600),
        )
        return candidates

    async def resolve(self, query: str) -> CompanyIdentity:
        candidates = await self.search(query, limit=8)
        if not candidates:
            raise CompanyNotFoundError(f"No listed equity found for '{query}'")
        best = candidates[0]
        return CompanyIdentity(
            query=query,
            symbol=best.symbol,
            name=best.name,
            exchange=best.exchange,
            quote_type=best.quote_type or "EQUITY",
        )

    async def fetch_bundle(self, identity: CompanyIdentity, period: str) -> MarketBundle:
        cache_key = (
            f"market-bundle:v2:{identity.symbol.upper()}:{period}:{self._benchmark_ticker}"
        )
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return MarketBundle.from_cache(cached)

        bundle = await asyncio.to_thread(self._fetch_bundle_sync, identity, period)
        await self._cache_set(cache_key, bundle.to_cache(), ttl=self._cache_ttl_seconds)
        return bundle

    def _search_sync(self, query: str, limit: int) -> list[CompanyCandidate]:
        try:
            search = yf.Search(
                query,
                max_results=max(limit * 2, 8),
                news_count=0,
                lists_count=0,
                enable_fuzzy_query=True,
                timeout=20,
                raise_errors=True,
            )
            quotes = search.quotes or []
        except Exception as exc:
            logger.warning("company_search_failed", query=query, error=str(exc))
            quotes = []

        candidates: list[CompanyCandidate] = []
        query_folded = query.casefold()
        query_symbol = query.upper().replace(" ", "")

        for quote in quotes:
            quote_type = str(quote.get("quoteType") or quote.get("typeDisp") or "").upper()
            if quote_type not in {"EQUITY", "STOCK"}:
                continue
            symbol = str(quote.get("symbol") or "").upper()
            name = str(
                quote.get("longname")
                or quote.get("shortname")
                or quote.get("name")
                or symbol
            )
            if not symbol:
                continue

            similarity = SequenceMatcher(None, query_folded, name.casefold()).ratio()
            exact_symbol_bonus = 0.75 if symbol == query_symbol else 0.0
            prefix_bonus = 0.15 if name.casefold().startswith(query_folded) else 0.0
            score = round(min(1.0, similarity * 0.7 + exact_symbol_bonus + prefix_bonus), 4)
            candidates.append(
                CompanyCandidate(
                    symbol=symbol,
                    name=name,
                    exchange=quote.get("exchange") or quote.get("exchDisp"),
                    quote_type=quote_type,
                    score=score,
                )
            )

        candidates.sort(key=lambda item: (-item.score, item.symbol))
        return candidates[:limit]

    def _fetch_bundle_sync(self, identity: CompanyIdentity, period: str) -> MarketBundle:
        ticker = yf.Ticker(identity.symbol)
        try:
            history = ticker.history(
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=False,
                repair=True,
                timeout=30,
            )
        except TypeError:
            history = ticker.history(
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=False,
                repair=True,
            )

        history = _normalize_history(history)
        if history.empty or len(history) < 80:
            raise MarketDataError(
                f"Insufficient price history for {identity.symbol}; received {len(history)} rows"
            )

        benchmark = yf.Ticker(self._benchmark_ticker)
        try:
            benchmark_history = benchmark.history(
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=False,
                repair=True,
                timeout=30,
            )
        except TypeError:
            benchmark_history = benchmark.history(
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=False,
                repair=True,
            )
        benchmark_history = _normalize_history(benchmark_history)

        info = _selected_info(_safe_call(ticker.get_info, {}))
        identity.currency = _optional_string(info.get("currency"))

        news_raw = _safe_call(lambda: ticker.news, [])
        targets = _sanitize(_safe_call(ticker.get_analyst_price_targets, {}))
        recommendations_raw = _safe_call(ticker.get_recommendations_summary, None)

        recommendations: list[dict[str, Any]] = []
        if isinstance(recommendations_raw, pd.DataFrame) and not recommendations_raw.empty:
            recommendations = _sanitize(
                recommendations_raw.reset_index().to_dict(orient="records")
            )

        return MarketBundle(
            identity=identity,
            info=info,
            history=history,
            benchmark_history=benchmark_history,
            news=_normalize_news(news_raw),
            analyst_targets=targets if isinstance(targets, dict) else {},
            recommendations=recommendations,
        )

    async def _cache_get(self, key: str) -> Any | None:
        if self._cache_ttl_seconds <= 0:
            return None
        try:
            value = await self._cache.get(key)
            return orjson.loads(value) if value else None
        except Exception as exc:
            logger.warning("cache_read_failed", key=key, error=str(exc))
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int) -> None:
        if ttl <= 0:
            return
        try:
            await self._cache.set(key, orjson.dumps(value), ex=ttl)
        except Exception as exc:
            logger.warning("cache_write_failed", key=key, error=str(exc))


def _safe_call(callable_: Any, default: Any) -> Any:
    try:
        return callable_()
    except Exception as exc:
        logger.warning("optional_market_field_failed", error=str(exc))
        return default


def _selected_info(info: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "longName",
        "shortName",
        "sector",
        "industry",
        "country",
        "website",
        "currency",
        "marketCap",
        "enterpriseValue",
        "trailingPE",
        "forwardPE",
        "priceToBook",
        "enterpriseToEbitda",
        "profitMargins",
        "grossMargins",
        "operatingMargins",
        "returnOnEquity",
        "returnOnAssets",
        "debtToEquity",
        "currentRatio",
        "quickRatio",
        "revenueGrowth",
        "earningsGrowth",
        "freeCashflow",
        "operatingCashflow",
        "totalRevenue",
        "ebitda",
        "dividendYield",
        "payoutRatio",
        "sharesOutstanding",
        "floatShares",
        "beta",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow",
        "targetMeanPrice",
        "targetMedianPrice",
        "recommendationMean",
        "recommendationKey",
        "numberOfAnalystOpinions",
        "fullTimeEmployees",
        "longBusinessSummary",
    }
    return {key: _sanitize(info.get(key)) for key in keys if info.get(key) is not None}


def _normalize_history(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    normalized = frame.copy()
    normalized.columns = [str(column).lower().replace(" ", "_") for column in normalized.columns]
    normalized.index = pd.to_datetime(normalized.index, utc=True)
    required = ["open", "high", "low", "close", "volume"]
    for column in required:
        if column not in normalized:
            normalized[column] = np.nan
    normalized = normalized[required].replace([np.inf, -np.inf], np.nan)
    normalized = normalized.dropna(subset=["close"]).sort_index()
    return normalized.astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float}
    )


def _history_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for timestamp, row in frame.iterrows():
        records.append(
            {
                "date": pd.Timestamp(timestamp).isoformat(),
                "open": _finite_or_none(row.get("open")),
                "high": _finite_or_none(row.get("high")),
                "low": _finite_or_none(row.get("low")),
                "close": _finite_or_none(row.get("close")),
                "volume": _finite_or_none(row.get("volume")),
            }
        )
    return records


def _records_to_history(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    frame = pd.DataFrame.from_records(records)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.set_index("date").sort_index()


def _normalize_news(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        content = item.get("content") if isinstance(item.get("content"), dict) else item

        provider = content.get("provider")
        if isinstance(provider, dict):
            provider = provider.get("displayName")

        canonical = content.get("canonicalUrl")
        if isinstance(canonical, dict):
            canonical = canonical.get("url")

        published_at = (
            content.get("pubDate")
            or content.get("displayTime")
            or item.get("providerPublishTime")
        )
        if isinstance(published_at, (int, float)):
            published_at = datetime.fromtimestamp(published_at, tz=UTC).isoformat()

        title = content.get("title") or item.get("title")
        if not title:
            continue

        normalized.append(
            {
                "title": str(title)[:500],
                "publisher": _optional_string(provider or item.get("publisher")),
                "url": _optional_string(canonical or item.get("link")),
                "published_at": _optional_string(published_at),
                "summary": _optional_string(content.get("summary")),
            }
        )
    return normalized[:10]


def _sanitize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _sanitize(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _optional_string(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None
