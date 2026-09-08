from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_COORDINATOR_KEY = "request_coordinator"
_OWNER: ContextVar[int | None] = ContextVar("cook4me_request_owner", default=None)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Cook4MeRequestCoordinator:
    """One FIFO work lane for Cook4Me external/device operations.

    The lock is deliberately global to the integration, not per config entry.
    This prevents AI, recipe catalog, price/reference and appliance work from
    competing for provider/device resources. Nested work from the same task is
    re-entrant so a high-level operation may call lower-level coordinated code
    without deadlocking itself.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._lock = asyncio.Lock()
        self._waiting = 0
        self._sequence = 0
        self._running: dict[str, Any] | None = None

    @property
    def snapshot(self) -> dict[str, Any]:
        return {
            "busy": self._running is not None,
            "waitingCount": self._waiting,
            "running": deepcopy(self._running),
        }

    @asynccontextmanager
    async def operation(
        self,
        kind: str,
        title: str,
        *,
        entry_ids: list[str] | tuple[str, ...] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        owner = _OWNER.get()
        if owner == id(self):
            # Re-entrant nested operation: the outer operation already owns
            # the single global work lane.
            yield self._running or {
                "id": 0,
                "kind": str(kind),
                "title": str(title),
                "entryIds": list(entry_ids or ()),
            }
            return

        self._waiting += 1
        try:
            await self._lock.acquire()
        finally:
            self._waiting = max(0, self._waiting - 1)

        self._sequence += 1
        token = _OWNER.set(id(self))
        op = {
            "id": self._sequence,
            "kind": str(kind or "work"),
            "title": str(title or kind or "Cook4Me work"),
            "entryIds": [str(value) for value in entry_ids or () if str(value)],
            "startedAt": _utcnow(),
        }
        self._running = op
        try:
            yield op
        finally:
            self._running = None
            _OWNER.reset(token)
            self._lock.release()


async def request_coordinator(hass: HomeAssistant) -> Cook4MeRequestCoordinator:
    data = hass.data.setdefault(DOMAIN, {})
    coordinator = data.get(_COORDINATOR_KEY)
    if not isinstance(coordinator, Cook4MeRequestCoordinator):
        coordinator = Cook4MeRequestCoordinator(hass)
        data[_COORDINATOR_KEY] = coordinator
    return coordinator
