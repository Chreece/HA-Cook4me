from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_SEARCH_TTL = 7 * 24 * 60 * 60
_DETAIL_TTL = 30 * 24 * 60 * 60
_TRANSLATION_TTL = 90 * 24 * 60 * 60
_UI_TTL = 10 * 365 * 24 * 60 * 60
_LIMITS = {"search": 120, "detail": 500, "translation": 1000, "ui": 20}
_TTLS = {
    "search": _SEARCH_TTL,
    "detail": _DETAIL_TTL,
    "translation": _TRANSLATION_TTL,
    "ui": _UI_TTL,
}


def stable_cache_key(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def translation_cache_key(recipe: dict[str, Any], target_language: str) -> str:
    source = {
        "title": recipe.get("title"),
        "language": recipe.get("language") or recipe.get("sourceLanguage"),
        "ingredients": recipe.get("ingredients") or [],
        "steps": recipe.get("steps") or [],
        "missing": (recipe.get("match") or {}).get("missingIngredients") or [],
    }
    return stable_cache_key("translation", str(target_language).lower(), source)


class Cook4MeRecipeCache:
    """Persistent bounded cache for normalized recipe catalog and UI data."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.recipe_cache"
        )
        self._lock = asyncio.Lock()
        self._data: dict[str, dict[str, dict[str, Any]]] = {
            "search": {},
            "detail": {},
            "translation": {},
            "ui": {},
        }

    async def async_load(self) -> None:
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            for bucket in self._data:
                value = saved.get(bucket)
                if isinstance(value, dict):
                    self._data[bucket] = {
                        str(key): row
                        for key, row in value.items()
                        if isinstance(row, dict) and "value" in row
                    }
        self._prune()

    def _prune(self) -> None:
        now = time.time()
        for bucket, rows in self._data.items():
            ttl = _TTLS[bucket]
            current = {
                key: row
                for key, row in rows.items()
                if now - float(row.get("timestamp") or 0) <= ttl
            }
            limit = _LIMITS[bucket]
            if len(current) > limit:
                ordered = sorted(
                    current.items(),
                    key=lambda pair: float(pair[1].get("timestamp") or 0),
                    reverse=True,
                )[:limit]
                current = dict(ordered)
            self._data[bucket] = current

    def get(self, bucket: str, key: str) -> Any | None:
        rows = self._data.get(bucket)
        if rows is None:
            return None
        row = rows.get(str(key))
        if not isinstance(row, dict):
            return None
        if time.time() - float(row.get("timestamp") or 0) > _TTLS[bucket]:
            rows.pop(str(key), None)
            return None
        return deepcopy(row.get("value"))

    async def async_set(self, bucket: str, key: str, value: Any) -> None:
        if bucket not in self._data:
            raise ValueError(f"Unknown Cook4Me cache bucket: {bucket}")
        async with self._lock:
            self._data[bucket][str(key)] = {
                "timestamp": time.time(),
                "value": deepcopy(value),
            }
            self._prune()
            self._store.async_delay_save(lambda: deepcopy(self._data), 5)

    async def async_set_many(self, bucket: str, values: dict[str, Any]) -> None:
        if not values:
            return
        if bucket not in self._data:
            raise ValueError(f"Unknown Cook4Me cache bucket: {bucket}")
        async with self._lock:
            stamp = time.time()
            for key, value in values.items():
                self._data[bucket][str(key)] = {
                    "timestamp": stamp,
                    "value": deepcopy(value),
                }
            self._prune()
            self._store.async_delay_save(lambda: deepcopy(self._data), 5)

    async def async_clear(self, bucket: str | None = None) -> None:
        async with self._lock:
            if bucket is None:
                for name in self._data:
                    self._data[name] = {}
            elif bucket in self._data:
                self._data[bucket] = {}
            else:
                raise ValueError(f"Unknown Cook4Me cache bucket: {bucket}")
            await self._store.async_save(deepcopy(self._data))
