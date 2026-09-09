from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1


class Cook4MeTodayStore:
    """Persist the last generated Today plan independently of browser state."""

    def __init__(self, bridge: Any) -> None:
        self._store: Store[dict[str, Any]] = Store(
            bridge.hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{bridge.entry.entry_id}.today_plan",
        )
        self._loaded = False
        self._data: dict[str, Any] = {}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            self._data = deepcopy(saved)
        self._loaded = True

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._data)

    async def async_save(self, value: dict[str, Any]) -> None:
        self._data = deepcopy(value if isinstance(value, dict) else {})
        self._loaded = True
        await self._store.async_save(deepcopy(self._data))

    async def async_clear(self) -> None:
        self._data = {}
        self._loaded = True
        await self._store.async_save({})


async def today_store_for_bridge(bridge: Any) -> Cook4MeTodayStore:
    store = getattr(bridge, "_cook4me_today_store", None)
    if not isinstance(store, Cook4MeTodayStore):
        store = Cook4MeTodayStore(bridge)
        await store.async_load()
        bridge._cook4me_today_store = store
    return store
