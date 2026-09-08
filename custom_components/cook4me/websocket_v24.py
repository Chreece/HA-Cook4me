from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v9 as v9
from .costs import cost_store_for_bridge
from .currency_fx import (
    currency_fx_store_for_bridge,
    default_currency_for_language,
    fetch_ecb_daily_rates,
)
from .online_cache import online_cache_for_bridge
from .recipe_cache import stable_cache_key
from .request_coordinator import request_coordinator


def _text(value: Any) -> str:
    return str(value or "").strip()


async def _currency_state(
    hass: HomeAssistant,
    bridge,
    *,
    language: str,
) -> dict[str, Any]:
    cost_store = await cost_store_for_bridge(bridge)
    fx_store = await currency_fx_store_for_bridge(bridge)
    selected = await fx_store.async_resolve_currency(language, cost_store)
    cache = await online_cache_for_bridge(bridge)

    async def fetch() -> dict[str, Any]:
        result = await hass.async_add_executor_job(fetch_ecb_daily_rates)
        if not result.get("ok"):
            raise ValueError(_text(result.get("reason")) or "ECB reference-rate refresh failed")
        return result

    cached = await cache.async_get_or_revalidate(
        "ecb_reference_rates:daily",
        fetch,
        source="ecb_reference_rates",
    )
    payload = cached.get("value") if isinstance(cached.get("value"), dict) else {}
    table = dict(payload.get("rates") or {"EUR": 1.0})
    table["EUR"] = 1.0
    currencies = sorted(
        set(table)
        | {selected, default_currency_for_language(language)}
    )
    return {
        "currency": selected,
        "mode": fx_store.preference.get("mode") or "auto",
        "defaultCurrency": default_currency_for_language(language),
        "currencies": currencies,
        "rates": table,
        "rateDate": payload.get("date") or "",
        "fetchedAt": cached.get("updatedAt") or "",
        "checkedAt": cached.get("checkedAt") or "",
        "source": payload.get("source") or "ecb_reference_rates",
        "stale": bool(cached.get("lastError")),
        "refreshError": cached.get("lastError") or "",
        "cacheHit": bool(cached.get("cacheHit")),
        "checkedOnline": bool(cached.get("checkedOnline")),
        "changed": bool(cached.get("changed")),
        "currencyConversionApplied": True,
        "originalCurrenciesPreserved": True,
        "minimumOnlineCheckHours": 24,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_currency_state,
        ws_currency_set,
        ws_recipe_detail,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v24/currency_state",
    vol.Optional("entry_id"): str,
    vol.Optional("language", default="en"): str,
})
@websocket_api.async_response
async def ws_currency_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "currency_reference",
            "Currency reference rates",
            entry_ids=[bridge.entry.entry_id],
        ):
            result = await _currency_state(
                hass,
                bridge,
                language=_text(msg.get("language")) or "en",
            )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v24/currency_set",
    vol.Optional("entry_id"): str,
    vol.Optional("language", default="en"): str,
    vol.Required("mode"): vol.In(["auto", "fixed"]),
    vol.Optional("currency", default=""): str,
})
@websocket_api.async_response
async def ws_currency_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        cost_store = await cost_store_for_bridge(bridge)
        fx_store = await currency_fx_store_for_bridge(bridge)
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "currency_reference",
            "Currency preference",
            entry_ids=[bridge.entry.entry_id],
        ):
            await fx_store.async_set_preference(
                mode=_text(msg.get("mode")) or "auto",
                currency=_text(msg.get("currency")),
                language=_text(msg.get("language")) or "en",
                cost_store=cost_store,
            )
            result = await _currency_state(
                hass,
                bridge,
                language=_text(msg.get("language")) or "en",
            )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v24/recipe_detail",
    vol.Optional("entry_id"): str,
    vol.Required("variant_id"): str,
    vol.Optional("language", default="de"): str,
})
@websocket_api.async_response
async def ws_recipe_detail(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        variant_id = _text(msg.get("variant_id"))
        language = _text(msg.get("language")) or "de"
        cache = await online_cache_for_bridge(bridge)
        coordinator = await request_coordinator(hass)
        key = stable_cache_key("seb_recipe_detail_v24", variant_id, language.lower())

        async def fetch() -> dict[str, Any]:
            raw, _cache_hit = await v9._raw_detail(
                hass,
                bridge,
                variant_id=variant_id,
                language=language,
                refresh=True,
            )
            return raw

        async with coordinator.operation(
            "recipe_detail",
            "Official recipe detail",
            entry_ids=[bridge.entry.entry_id],
        ):
            cached = await cache.async_get_or_revalidate(
                key,
                fetch,
                source="seb_recipe_detail",
            )
        raw = cached.get("value") if isinstance(cached.get("value"), dict) else {}
        result = bridge.recipe_hub.annotate(raw)
        result["deviceCanAccept"] = bridge.can_accept_recipe
        result["cacheHit"] = bool(cached.get("cacheHit"))
        result["checkedOnline"] = bool(cached.get("checkedOnline"))
        result["changed"] = bool(cached.get("changed"))
        result["checkedAt"] = cached.get("checkedAt") or ""
        result["updatedAt"] = cached.get("updatedAt") or ""
        result["lastError"] = cached.get("lastError") or ""
        result["minimumOnlineCheckHours"] = 24
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)
