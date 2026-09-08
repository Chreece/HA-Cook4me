from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import time
from typing import Any, Awaitable, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_MIN_CHECK_AGE = 24 * 60 * 60
_MAX_ROWS = 5000


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _iso(stamp: float) -> str:
    return datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat()


class Cook4MeOnlineCache:
    """Persistent cache whose values survive until upstream content changes.

    A cached online value is never discarded just because it is old. The
    upstream source may be revalidated only when at least 24 hours have elapsed
    since the previous check attempt. A successful unchanged check advances only
    checkedAt; updatedAt changes only when the upstream value actually changes.
    Failed revalidation keeps the last known value and also observes the same
    one-day minimum before another check, preventing provider hammering.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.online_cache"
        )
        self._loaded = False
        self._lock = asyncio.Lock()
        self._rows: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            rows = saved.get("rows") if isinstance(saved.get("rows"), dict) else saved
            self._rows = {
                str(key): deepcopy(row)
                for key, row in rows.items()
                if isinstance(row, dict) and "value" in row
            }
        self._prune()
        self._loaded = True

    def _prune(self) -> None:
        if len(self._rows) <= _MAX_ROWS:
            return
        ordered = sorted(
            self._rows.items(),
            key=lambda pair: float(
                pair[1].get("accessedAt")
                or pair[1].get("checkedAt")
                or pair[1].get("updatedAt")
                or 0
            ),
            reverse=True,
        )[:_MAX_ROWS]
        self._rows = dict(ordered)

    async def _save(self) -> None:
        await self._store.async_save({"rows": deepcopy(self._rows)})

    def row(self, key: str) -> dict[str, Any] | None:
        row = self._rows.get(str(key))
        if not isinstance(row, dict):
            return None
        row["accessedAt"] = time.time()
        return deepcopy(row)

    def get(self, key: str) -> Any | None:
        row = self.row(key)
        return deepcopy(row.get("value")) if row is not None else None

    def may_check(self, key: str, *, min_age: float = _MIN_CHECK_AGE) -> bool:
        row = self._rows.get(str(key))
        if not isinstance(row, dict):
            return True
        checked = float(row.get("checkedAt") or row.get("updatedAt") or 0)
        return not checked or time.time() - checked >= max(_MIN_CHECK_AGE, float(min_age))

    async def async_record(
        self,
        key: str,
        value: Any,
        *,
        source: str = "",
    ) -> dict[str, Any]:
        async with self._lock:
            now = time.time()
            existing = self._rows.get(str(key))
            digest = _fingerprint(value)
            changed = not isinstance(existing, dict) or existing.get("fingerprint") != digest
            updated_at = now if changed else float(existing.get("updatedAt") or now)
            self._rows[str(key)] = {
                "value": deepcopy(value),
                "fingerprint": digest,
                "source": str(source or (existing or {}).get("source") or "online"),
                "checkedAt": now,
                "updatedAt": updated_at,
                "accessedAt": now,
                "lastError": "",
            }
            self._prune()
            await self._save()
            return {
                "changed": changed,
                "checkedAt": _iso(now),
                "updatedAt": _iso(updated_at),
            }

    async def async_record_failure(self, key: str, error: Any) -> None:
        async with self._lock:
            row = self._rows.get(str(key))
            if not isinstance(row, dict):
                return
            now = time.time()
            row["checkedAt"] = now
            row["accessedAt"] = now
            row["lastError"] = str(error or "online_check_failed")[:300]
            await self._save()

    async def async_get_or_revalidate(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        *,
        source: str = "",
        min_age: float = _MIN_CHECK_AGE,
    ) -> dict[str, Any]:
        cached = self.get(key)
        if cached is not None and not self.may_check(key, min_age=min_age):
            row = self.row(key) or {}
            return {
                "value": cached,
                "cacheHit": True,
                "checkedOnline": False,
                "changed": False,
                "checkedAt": _iso(float(row.get("checkedAt") or 0)) if row.get("checkedAt") else "",
                "updatedAt": _iso(float(row.get("updatedAt") or 0)) if row.get("updatedAt") else "",
                "lastError": str(row.get("lastError") or ""),
            }

        try:
            value = await fetcher()
        except Exception as exc:
            if cached is None:
                raise
            await self.async_record_failure(key, exc)
            row = self.row(key) or {}
            return {
                "value": cached,
                "cacheHit": True,
                "checkedOnline": True,
                "changed": False,
                "checkedAt": _iso(float(row.get("checkedAt") or 0)) if row.get("checkedAt") else "",
                "updatedAt": _iso(float(row.get("updatedAt") or 0)) if row.get("updatedAt") else "",
                "lastError": str(row.get("lastError") or type(exc).__name__),
            }

        meta = await self.async_record(key, value, source=source)
        return {
            "value": self.get(key),
            "cacheHit": cached is not None,
            "checkedOnline": True,
            **meta,
            "lastError": "",
        }


async def online_cache_for_bridge(bridge: Any) -> Cook4MeOnlineCache:
    store = getattr(bridge, "_cook4me_online_cache", None)
    if store is None:
        store = Cook4MeOnlineCache(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._cook4me_online_cache = store
    return store
