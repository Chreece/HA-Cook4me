from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_MAX_FAILURES = 5000
_DEFAULT_TTL = timedelta(hours=6)
_REASON_TTL = {
    "ambiguous": timedelta(days=30),
    "no_nutrition": timedelta(days=14),
    "no_english_name": timedelta(days=7),
    "http_429": timedelta(hours=4),
    "http_401": timedelta(hours=6),
    "http_403": timedelta(hours=6),
    "URLError": timedelta(minutes=30),
    "TimeoutError": timedelta(minutes=30),
    "JSONDecodeError": timedelta(hours=1),
}
_TRANSIENT_REASONS = {"URLError", "TimeoutError", "JSONDecodeError"}
_SEMANTIC_REASONS = {"ambiguous", "no_nutrition", "no_english_name"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def retry_ttl(reason: Any) -> timedelta:
    token = _text(reason)
    if token in _REASON_TTL:
        return _REASON_TTL[token]
    if token.startswith("http_"):
        return timedelta(hours=6)
    return _DEFAULT_TTL


def is_transient_reason(reason: Any) -> bool:
    token = _text(reason)
    return token.startswith("http_") or token in _TRANSIENT_REASONS


def _mode_matches(row: dict[str, Any], mode: str | None) -> bool:
    if mode is None:
        return True
    if _text(row.get("mode")) == _text(mode):
        return True
    # A different API key cannot make a semantically ambiguous FDC result
    # become unambiguous. Keep those failures cached across key-mode changes.
    return _text(row.get("reason")) in _SEMANTIC_REASONS


class Cook4MeNutritionResolutionStore:
    """Persistent negative cache for generic nutrition lookups.

    Successful nutrition lives in Cook4MeNutritionStore.  This store only keeps
    lookup failures long enough to avoid repeatedly spending FoodData Central
    quota on the same unresolved ingredient.  The API key itself is never
    persisted here; only whether the request used demo or custom-key mode.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.nutrition_resolution"
        )
        self._loaded = False
        self._data: dict[str, Any] = {"failures": {}}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        failures = saved.get("failures") if isinstance(saved, dict) else None
        self._data = {"failures": failures if isinstance(failures, dict) else {}}
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    @property
    def failure_count(self) -> int:
        return len(self._data.get("failures") or {})

    def get_blocked(
        self,
        identity: str,
        *,
        query: str,
        mode: str,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        row = (self._data.get("failures") or {}).get(_text(identity))
        if not isinstance(row, dict):
            return None
        if _text(row.get("query")) != _text(query):
            return None
        if not _mode_matches(row, mode):
            return None
        retry_at = _parse_utc(row.get("retryAt"))
        current = (now or _utcnow()).astimezone(timezone.utc)
        if retry_at is None or retry_at <= current:
            return None
        return deepcopy(row)

    def active_count(
        self,
        identities: set[str] | None = None,
        *,
        mode: str | None = None,
        now: datetime | None = None,
    ) -> int:
        current = (now or _utcnow()).astimezone(timezone.utc)
        wanted = set(identities or ())
        count = 0
        for identity, row in (self._data.get("failures") or {}).items():
            if wanted and identity not in wanted:
                continue
            if not isinstance(row, dict) or not _mode_matches(row, mode):
                continue
            retry_at = _parse_utc(row.get("retryAt"))
            if retry_at is not None and retry_at > current:
                count += 1
        return count

    async def async_record_failure(
        self,
        identity: str,
        *,
        query: str,
        mode: str,
        reason: str,
        confidence: Any = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        identity = _text(identity)
        if not identity:
            raise ValueError("Nutrition resolution failure requires an identity")
        current = (now or _utcnow()).astimezone(timezone.utc)
        ttl = retry_ttl(reason)
        row: dict[str, Any] = {
            "identity": identity,
            "query": _text(query),
            "mode": _text(mode),
            "reason": _text(reason) or "not_resolved",
            "attemptedAt": current.isoformat(),
            "retryAt": (current + ttl).isoformat(),
        }
        try:
            numeric = float(confidence)
        except (TypeError, ValueError):
            numeric = None
        if numeric is not None:
            row["confidence"] = round(numeric, 3)

        failures = self._data.setdefault("failures", {})
        if identity not in failures and len(failures) >= _MAX_FAILURES:
            oldest = min(
                failures,
                key=lambda key: _text((failures.get(key) or {}).get("attemptedAt")),
            )
            failures.pop(oldest, None)
        failures[identity] = row
        await self._save()
        return deepcopy(row)

    async def async_clear(self, identity: str) -> bool:
        removed = (self._data.get("failures") or {}).pop(_text(identity), None)
        if removed is None:
            return False
        await self._save()
        return True

    async def async_clear_transient(self) -> int:
        failures = self._data.get("failures") or {}
        removed = 0
        for identity in list(failures):
            row = failures.get(identity)
            if isinstance(row, dict) and is_transient_reason(row.get("reason")):
                failures.pop(identity, None)
                removed += 1
        if removed:
            await self._save()
        return removed


async def nutrition_resolution_store_for_bridge(
    bridge: Any,
) -> Cook4MeNutritionResolutionStore:
    store = getattr(bridge, "_nutrition_resolution_store", None)
    if store is None:
        store = Cook4MeNutritionResolutionStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._nutrition_resolution_store = store
    return store
