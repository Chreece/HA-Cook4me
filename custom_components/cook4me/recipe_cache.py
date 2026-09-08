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
_MIN_ONLINE_CHECK_AGE = 24 * 60 * 60
_LIMITS = {"search": 120, "detail": 500, "translation": 1000, "ui": 20}


def stable_cache_key(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _value_fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
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


def _is_current_search_value(value: Any) -> bool:
    """Reject search results produced before the standalone-proven v12 contract."""

    return bool(
        isinstance(value, dict)
        and value.get("applianceGroup") == "APPLIANCE_GROUP_15"
        and value.get("recipeType") == "BRAND"
    )


class Cook4MeRecipeCache:
    """Persistent bounded recipe cache with daily upstream revalidation.

    Online values are retained until a newer upstream check proves that their
    content changed. Age alone never deletes a valid cached result. `checkedAt`
    records the last online check attempt while `updatedAt` changes only when the
    cached value itself changes. This lets callers revalidate no more than once
    per day without repeatedly downloading unchanged recipe data.
    """

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
                    normalized: dict[str, dict[str, Any]] = {}
                    for key, row in value.items():
                        if not isinstance(row, dict) or "value" not in row:
                            continue
                        stamp = float(row.get("timestamp") or 0)
                        current = deepcopy(row)
                        current.setdefault("checkedAt", stamp)
                        current.setdefault("updatedAt", stamp)
                        current.setdefault("accessedAt", stamp)
                        current.setdefault("fingerprint", _value_fingerprint(current.get("value")))
                        current.setdefault("lastError", "")
                        normalized[str(key)] = current
                    self._data[bucket] = normalized
        self._prune()

    def _prune(self) -> None:
        for bucket, rows in self._data.items():
            current = dict(rows)
            if bucket == "search":
                current = {
                    key: row
                    for key, row in current.items()
                    if _is_current_search_value(row.get("value"))
                }
            limit = _LIMITS[bucket]
            if len(current) > limit:
                ordered = sorted(
                    current.items(),
                    key=lambda pair: float(
                        pair[1].get("accessedAt")
                        or pair[1].get("checkedAt")
                        or pair[1].get("updatedAt")
                        or pair[1].get("timestamp")
                        or 0
                    ),
                    reverse=True,
                )[:limit]
                current = dict(ordered)
            self._data[bucket] = current

    def row(self, bucket: str, key: str) -> dict[str, Any] | None:
        rows = self._data.get(bucket)
        if rows is None:
            return None
        row = rows.get(str(key))
        if not isinstance(row, dict):
            return None
        value = row.get("value")
        if bucket == "search" and not _is_current_search_value(value):
            rows.pop(str(key), None)
            return None
        row["accessedAt"] = time.time()
        return deepcopy(row)

    def get(self, bucket: str, key: str) -> Any | None:
        row = self.row(bucket, key)
        return deepcopy(row.get("value")) if row is not None else None

    def should_revalidate(
        self,
        bucket: str,
        key: str,
        *,
        min_age: float = _MIN_ONLINE_CHECK_AGE,
    ) -> bool:
        row = self._data.get(bucket, {}).get(str(key))
        if not isinstance(row, dict):
            return True
        checked = float(row.get("checkedAt") or row.get("updatedAt") or row.get("timestamp") or 0)
        if not checked:
            return True
        return time.time() - checked >= max(_MIN_ONLINE_CHECK_AGE, float(min_age))

    async def async_mark_checked(
        self,
        bucket: str,
        key: str,
        *,
        error: Any = "",
    ) -> None:
        async with self._lock:
            row = self._data.get(bucket, {}).get(str(key))
            if not isinstance(row, dict):
                return
            now = time.time()
            row["checkedAt"] = now
            row["accessedAt"] = now
            row["lastError"] = str(error or "")[:300]
            self._store.async_delay_save(lambda: deepcopy(self._data), 5)

    async def async_set(self, bucket: str, key: str, value: Any) -> dict[str, Any]:
        if bucket not in self._data:
            raise ValueError(f"Unknown Cook4Me cache bucket: {bucket}")
        async with self._lock:
            now = time.time()
            existing = self._data[bucket].get(str(key))
            digest = _value_fingerprint(value)
            changed = not isinstance(existing, dict) or existing.get("fingerprint") != digest
            updated_at = now if changed else float(existing.get("updatedAt") or existing.get("timestamp") or now)
            self._data[bucket][str(key)] = {
                "timestamp": now,
                "checkedAt": now,
                "updatedAt": updated_at,
                "accessedAt": now,
                "fingerprint": digest,
                "lastError": "",
                "value": deepcopy(value),
            }
            self._prune()
            self._store.async_delay_save(lambda: deepcopy(self._data), 5)
            return {"changed": changed, "checkedAt": now, "updatedAt": updated_at}

    async def async_set_many(self, bucket: str, values: dict[str, Any]) -> None:
        if not values:
            return
        if bucket not in self._data:
            raise ValueError(f"Unknown Cook4Me cache bucket: {bucket}")
        for key, value in values.items():
            await self.async_set(bucket, key, value)

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
