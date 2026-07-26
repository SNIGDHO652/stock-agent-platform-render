"""In-process cache and rate-limit primitives for free-tier deployments."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import orjson


@dataclass(slots=True)
class _Entry:
    value: bytes
    expires_at: float | None


class LocalTTLCache:
    """Small async-compatible TTL cache.

    This replaces Redis for Render free-tier demos. It is process-local, so cache
    and rate-limit counters reset when the web instance restarts or sleeps.
    """

    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}

    async def get(self, key: str) -> bytes | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at <= time.time():
            self._store.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: bytes, ex: int | None = None) -> bool:
        expires_at = time.time() + ex if ex else None
        self._store[key] = _Entry(value=value, expires_at=expires_at)
        return True

    async def incr(self, key: str) -> int:
        raw = await self.get(key)
        value = int(raw.decode("utf-8")) if raw else 0
        value += 1
        self._store[key] = _Entry(value=str(value).encode("utf-8"), expires_at=None)
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        entry.expires_at = time.time() + seconds
        return True

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self._store.clear()

    async def json_get(self, key: str) -> Any | None:
        value = await self.get(key)
        return orjson.loads(value) if value else None

    async def json_set(self, key: str, value: Any, ttl: int) -> None:
        if ttl > 0:
            await self.set(key, orjson.dumps(value), ex=ttl)
