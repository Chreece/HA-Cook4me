"""Show each Cook4Me event once and respect HA notification dismissals."""
from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
import json
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import callback
from homeassistant.helpers.storage import Store


def event_key(*parts: Any) -> str:
    """Keep semantic identities, rather than changing text, in the durable ledger."""
    return sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Cook4MeNotifications:
    """One visible notification per category; only unseen events can reopen it.

    The ledger survives HA restarts. Active notifications are deliberately
    session-local: a status update may change a visible notification, but cannot
    recreate one removed by dismissal, dismiss-all, unload, or restart.
    """

    def __init__(self, hass, entry_id: str) -> None:
        self.hass = hass
        self._store = Store(hass, 1, f"cook4me.{entry_id}.notifications")
        self._seen: dict[str, set[str]] = {}
        self._active: dict[str, set[str]] = {}
        self._payloads: dict[str, str] = {}
        self._unsub = None
        self._loaded = False
        self._closed = False

    async def async_load(self) -> None:
        saved = await self._store.async_load()
        if isinstance(saved, dict) and isinstance(saved.get("seen"), dict):
            self._seen = {
                ident: {key for key in keys if isinstance(key, str)}
                for ident, keys in saved["seen"].items()
                if isinstance(ident, str) and isinstance(keys, list)
            }
        self._unsub = persistent_notification.async_register_callback(self.hass, self._changed)
        self._loaded = True

    def _snapshot(self) -> dict[str, Any]:
        return {"seen": {ident: sorted(keys) for ident, keys in self._seen.items()}}

    @callback
    def _changed(self, update_type, notifications) -> None:
        # HA uses the same callback for dismiss, dismiss-all and service calls.
        if update_type == persistent_notification.UpdateType.REMOVED:
            for ident in notifications:
                self._active.pop(ident, None)
                self._payloads.pop(ident, None)

    def unseen(self, ident: str, keys: Iterable[str]) -> set[str]:
        return set(keys) - self._seen.get(ident, set())

    def active_keys(self, ident: str) -> set[str]:
        return set(self._active.get(ident, set()))

    @callback
    def publish(self, ident: str, keys: Iterable[str], message: str, *, title: str,
                update: bool = False) -> bool:
        if not self._loaded or self._closed:
            return False
        keys = set(keys)
        if not keys:
            return False
        fresh = self.unseen(ident, keys)
        if not fresh and not (update and keys <= self._active.get(ident, set())):
            return False
        payload = event_key(sorted(keys), title, message)
        if self._payloads.get(ident) == payload:
            return False
        # Reserve synchronously so adjacent callbacks cannot send duplicates.
        if fresh:
            self._seen.setdefault(ident, set()).update(keys)
            self._store.async_delay_save(self._snapshot, 1)
        self._active[ident] = keys
        self._payloads[ident] = payload
        persistent_notification.async_create(self.hass, message, title=title, notification_id=ident)
        return True

    @callback
    def clear(self, ident: str) -> None:
        self._active.pop(ident, None)
        self._payloads.pop(ident, None)
        persistent_notification.async_dismiss(self.hass, ident)

    async def async_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        if self._loaded:
            # Store also flushes delayed saves on HA stop. Flush explicitly on
            # entry unload, after bridge-owned generation/completion tasks stop.
            await self._store.async_save(self._snapshot())
