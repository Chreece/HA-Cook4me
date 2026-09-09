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
EVENT_OPERATION_PROGRESS = "cook4me_operation_progress"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded_text(value: Any, limit: int = 240) -> str:
    return str(value or "").strip()[:limit]


class Cook4MeRequestCoordinator:
    """One FIFO work lane plus one shared observable progress contract."""

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

    def progress(
        self,
        operation: dict[str, Any] | None,
        phase: str,
        *,
        completed: int | float | None = None,
        total: int | float | None = None,
        message: str = "",
        done: bool = False,
        error: Any = "",
    ) -> dict[str, Any] | None:
        """Publish measurable progress without fabricating percentages."""
        if not isinstance(operation, dict):
            return None
        client_id = _bounded_text(operation.get("clientOperationId"), 160)
        if not client_id:
            return None
        completed_number = float(completed) if isinstance(completed, (int, float)) else None
        total_number = float(total) if isinstance(total, (int, float)) else None
        percent: int | None = None
        if completed_number is not None and total_number is not None and total_number > 0:
            percent = round(max(0.0, min(100.0, completed_number / total_number * 100.0)))
        event = {
            "operationId": client_id,
            "serverOperationId": operation.get("id"),
            "kind": _bounded_text(operation.get("kind"), 80),
            "title": _bounded_text(operation.get("title"), 160),
            "phase": _bounded_text(phase, 100),
            "completed": completed_number,
            "total": total_number,
            "percent": percent,
            "message": _bounded_text(message, 400),
            "waitingCount": self._waiting,
            "done": bool(done),
            "error": _bounded_text(error, 300),
            "updatedAt": _utcnow(),
        }
        if self._running is operation:
            operation.update({
                "phase": event["phase"],
                "completed": completed_number,
                "total": total_number,
                "percent": percent,
                "message": event["message"],
            })
        self.hass.bus.async_fire(EVENT_OPERATION_PROGRESS, event)
        return deepcopy(event)

    @asynccontextmanager
    async def operation(
        self,
        kind: str,
        title: str,
        *,
        entry_ids: list[str] | tuple[str, ...] | None = None,
        client_operation_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        owner = _OWNER.get()
        if owner == id(self):
            yield self._running or {
                "id": 0,
                "kind": str(kind),
                "title": str(title),
                "entryIds": list(entry_ids or ()),
                "clientOperationId": _bounded_text(client_operation_id, 160),
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
            "clientOperationId": _bounded_text(client_operation_id, 160),
            "startedAt": _utcnow(),
            "phase": "starting",
            "completed": None,
            "total": None,
            "percent": None,
            "message": "",
        }
        self._running = op
        self.progress(op, "starting")
        try:
            yield op
        except Exception as exc:
            self.progress(op, "failed", message=type(exc).__name__, done=True, error=type(exc).__name__)
            raise
        else:
            self.progress(op, "done", completed=1, total=1, done=True)
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
