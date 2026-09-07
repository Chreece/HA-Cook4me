from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .recipe_experience import recipe_snapshot, recipe_storage_key

_STORAGE_VERSION = 1
_MAX_BOOK_ITEMS = 500


class Cook4MeRecipeBookStore:
    """Persist favourites, recipe-list entries and one deferred appliance send."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.recipe_book"
        )
        self._loaded = False
        self._data: dict[str, Any] = {
            "favorites": {},
            "recipeList": {},
            "queuedSend": None,
        }

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            for name in ("favorites", "recipeList"):
                raw = saved.get(name)
                if isinstance(raw, dict):
                    self._data[name] = {
                        str(key): deepcopy(value)
                        for key, value in list(raw.items())[-_MAX_BOOK_ITEMS:]
                        if isinstance(value, dict)
                    }
            queued = saved.get("queuedSend")
            if isinstance(queued, dict):
                self._data["queuedSend"] = deepcopy(queued)
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    def snapshot(self) -> dict[str, Any]:
        return {
            "favorites": list(deepcopy(self._data["favorites"]).values()),
            "recipeList": list(deepcopy(self._data["recipeList"]).values()),
            "queuedSend": deepcopy(self._data.get("queuedSend")),
        }

    @property
    def queued_send(self) -> dict[str, Any] | None:
        row = self._data.get("queuedSend")
        return deepcopy(row) if isinstance(row, dict) else None

    async def async_toggle(self, collection: str, recipe: dict[str, Any]) -> dict[str, Any]:
        if collection not in {"favorites", "recipeList"}:
            raise ValueError("Recipe collection must be favorites or recipeList")
        key = recipe_storage_key(recipe)
        if not key:
            raise ValueError("Recipe has no stable identity")
        rows = self._data[collection]
        if key in rows:
            rows.pop(key, None)
            added = False
        else:
            snapshot = recipe_snapshot(recipe)
            snapshot["bookKey"] = key
            snapshot["bookAddedAt"] = datetime.now(timezone.utc).isoformat()
            rows[key] = snapshot
            while len(rows) > _MAX_BOOK_ITEMS:
                rows.pop(next(iter(rows)), None)
            added = True
        await self._save()
        return {"added": added, "collection": collection, "key": key, **self.snapshot()}

    async def async_queue_send(self, recipe: dict[str, Any], *, reason: str) -> dict[str, Any]:
        snapshot = recipe_snapshot(recipe)
        variant = str(
            recipe.get("sendVariantId")
            or recipe.get("variantFunctionalId")
            or recipe.get("recipeFunctionalId")
            or recipe.get("displayVariantId")
            or ""
        ).strip()
        if not variant:
            raise ValueError("Official recipe has no sendable SEB recipe ID")
        previous = deepcopy(self._data.get("queuedSend"))
        self._data["queuedSend"] = {
            "variantId": variant,
            "title": str(recipe.get("title") or variant),
            "reason": str(reason or "waiting_for_device"),
            "queuedAt": datetime.now(timezone.utc).isoformat(),
            "recipe": snapshot,
        }
        await self._save()
        return {"queued": deepcopy(self._data["queuedSend"]), "replaced": previous}

    async def async_clear_queue(self) -> dict[str, Any] | None:
        previous = deepcopy(self._data.get("queuedSend"))
        self._data["queuedSend"] = None
        if previous is not None:
            await self._save()
        return previous
