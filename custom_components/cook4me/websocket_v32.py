from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from . import websocket_v22 as v22
from . import websocket_v30 as v30
from . import websocket_v31 as v31
from .reference_catalog import bundled_reference_catalog
from .request_coordinator import request_coordinator


def _text(value) -> str:
    return str(value or "").strip()


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_official_search)
    websocket_api.async_register_command(hass, ws_reference_recommend)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v32/official_search",
    vol.Optional("entry_id"): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("query", default=""): str,
    vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Optional("strict_language", default=True): bool,
    vol.Optional("ui_language", default="en"): str,
})
@websocket_api.async_response
async def ws_official_search(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        languages = v22._selected_languages(bridge, msg.get("languages"))
        reference = bundled_reference_catalog()
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("official_search", "Search Cook4Me catalog", entry_ids=[bridge.entry.entry_id]):
            if reference.metadata.get("recipeCount"):
                coordinator.update_progress(phase="catalog", completed=0, total=1, message="Searching bundled recipe catalog")
                rows = v30.reference_recipe_candidates(
                    bridge,
                    languages=languages,
                    query=_text(msg.get("query")),
                    ui_language=_text(msg.get("ui_language")) or "en",
                    limit=max(50, int(msg.get("size", 20)) * 4),
                )
                coordinator.update_progress(phase="catalog", completed=1, total=1, message="Bundled recipe catalog ready")
                rows = v13._dedupe_recipes(rows)[: int(msg.get("size", 20))]
                items = []
                total = max(1, len(rows))
                for index, recipe in enumerate(rows, 1):
                    coordinator.update_progress(phase="nutrition", completed=index - 1, total=total, message=f"Preparing recipe {index}/{len(rows)}")
                    item = bridge.recipe_hub.annotate(recipe)
                    item["deviceCanAccept"] = bridge.can_accept_recipe
                    item = await v31._decorate_economics(bridge, item)
                    items.append(item)
                    coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Prepared recipe {index}/{len(rows)}")
                result = {
                    "items": items,
                    "languages": languages,
                    "count": len(items),
                    "catalogs": [{"language": language, "source": "bundled_reference_catalog", "cacheHit": True} for language in languages],
                    "deviceCanAccept": bridge.can_accept_recipe,
                    "loadedRecipe": bridge.loaded_recipe,
                    "referenceCatalog": reference.metadata,
                    "offlineIndex": True,
                    "onlineRequests": 0,
                }
            else:
                # Bootstrap releases deliberately ship no fabricated IDs. Until a
                # sanitized manual audit populates the release catalog, retain the
                # proven online/cache path rather than returning fake results.
                rows = []
                catalogs = []
                for index, language in enumerate(languages, 1):
                    coordinator.update_progress(phase="catalogs", completed=index - 1, total=len(languages), message=f"Searching {language.upper()}")
                    part = await v22._official_search(
                        hass,
                        bridge,
                        languages=[language],
                        query=_text(msg.get("query")),
                        page=0,
                        size=int(msg.get("size", 20)),
                        strict_language=bool(msg.get("strict_language", True)),
                    )
                    rows.extend(part.get("items") or [])
                    catalogs.extend(part.get("catalogs") or [])
                    coordinator.update_progress(phase="catalogs", completed=index, total=len(languages), message=f"Searched {language.upper()}")
                deduped = v13._dedupe_recipes(rows)[: int(msg.get("size", 20))]
                items = []
                total = max(1, len(deduped))
                for index, recipe in enumerate(deduped, 1):
                    coordinator.update_progress(phase="nutrition", completed=index - 1, total=total, message=f"Preparing recipe {index}/{len(deduped)}")
                    items.append(await v31._decorate_economics(bridge, recipe))
                    coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Prepared recipe {index}/{len(deduped)}")
                result = {
                    "items": items,
                    "languages": languages,
                    "catalogs": catalogs,
                    "count": len(items),
                    "deviceCanAccept": bridge.can_accept_recipe,
                    "loadedRecipe": bridge.loaded_recipe,
                    "referenceCatalog": reference.metadata,
                    "offlineIndex": False,
                }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v32/reference_recommend",
    vol.Optional("entry_id"): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("language", default="en"): str,
    vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
    vol.Optional("query", default=""): str,
    vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
})
@websocket_api.async_response
async def ws_reference_recommend(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        reference = bundled_reference_catalog()
        if not reference.metadata.get("recipeCount"):
            raise ValueError("Bundled recipe catalog is not populated yet")
        languages = v18._languages(bridge, msg.get("languages"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("reference_recommend", "Rank bundled Cook4Me recipes", entry_ids=[bridge.entry.entry_id]):
            coordinator.update_progress(phase="catalog", completed=0, total=1, message="Reading bundled catalog")
            rows = v30.reference_recipe_candidates(
                bridge,
                languages=languages,
                query=_text(msg.get("query")),
                ui_language=_text(msg.get("language")) or "en",
                limit=500,
            )
            coordinator.update_progress(phase="catalog", completed=1, total=1, message="Bundled catalog ready")
            ranked = v13._rank_filtered(
                bridge,
                rows,
                diet=str(msg.get("diet") or "profile"),
                limit=int(msg.get("limit", 12)),
            )
            items = []
            total = max(1, len(ranked))
            for index, recipe in enumerate(ranked, 1):
                coordinator.update_progress(phase="nutrition", completed=index - 1, total=total, message=f"Preparing recipe {index}/{len(ranked)}")
                recipe["deviceCanAccept"] = bridge.can_accept_recipe
                items.append(await v31._decorate_economics(bridge, recipe))
                coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Prepared recipe {index}/{len(ranked)}")
        result = {
            "items": items,
            "profile": bridge.recipe_hub.profile,
            "filters": {"query": _text(msg.get("query")), "diet": str(msg.get("diet") or "profile")},
            "referenceCatalog": reference.metadata,
            "offlineIndex": True,
            "onlineRequests": 0,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
