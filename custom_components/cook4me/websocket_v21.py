from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from .costs import cost_store_for_bridge
from .currency_fx import (
    convert_currency_map,
    currency_fx_store_for_bridge,
    default_currency_for_language,
)


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_currency_state,
        ws_currency_set,
        ws_currency_convert,
    ):
        websocket_api.async_register_command(hass, command)


async def _state(bridge, *, language: str, refresh: bool = False) -> dict[str, Any]:
    cost_store = await cost_store_for_bridge(bridge)
    fx_store = await currency_fx_store_for_bridge(bridge)
    selected = await fx_store.async_resolve_currency(language, cost_store)
    fx = await fx_store.async_rates(force=refresh)
    table = dict(fx.get("rates") or {})
    currencies = sorted(set(table) | {selected, default_currency_for_language(language)})
    return {
        "currency": selected,
        "mode": fx_store.preference.get("mode") or "auto",
        "defaultCurrency": default_currency_for_language(language),
        "currencies": currencies,
        "rates": table,
        "rateDate": fx.get("date") or "",
        "fetchedAt": fx.get("fetchedAt") or "",
        "source": fx.get("source") or "ecb_reference_rates",
        "stale": bool(fx.get("stale")),
        "refreshError": fx.get("refreshError") or "",
        "currencyConversionApplied": True,
        "originalCurrenciesPreserved": True,
    }


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v21/currency_state",
    vol.Optional("entry_id"): str,
    vol.Optional("language", default="en"): str,
    vol.Optional("refresh", default=False): bool,
})
@websocket_api.async_response
async def ws_currency_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _state(
            bridge,
            language=str(msg.get("language") or "en"),
            refresh=bool(msg.get("refresh")),
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v21/currency_set",
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
        await fx_store.async_set_preference(
            mode=str(msg.get("mode") or "auto"),
            currency=str(msg.get("currency") or ""),
            language=str(msg.get("language") or "en"),
            cost_store=cost_store,
        )
        result = await _state(
            bridge,
            language=str(msg.get("language") or "en"),
            refresh=False,
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v21/currency_convert",
    vol.Optional("entry_id"): str,
    vol.Optional("language", default="en"): str,
    vol.Required("values"): dict,
    vol.Optional("currency", default=""): str,
    vol.Optional("refresh", default=False): bool,
})
@websocket_api.async_response
async def ws_currency_convert(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        state = await _state(
            bridge,
            language=str(msg.get("language") or "en"),
            refresh=bool(msg.get("refresh")),
        )
        target = str(msg.get("currency") or state["currency"]).upper()
        converted = convert_currency_map(msg.get("values") or {}, target, state["rates"])
        result = {
            **converted,
            "rateDate": state["rateDate"],
            "source": state["source"],
            "stale": state["stale"],
            "refreshError": state["refreshError"],
            "original": dict(msg.get("values") or {}),
            "currencyConversionApplied": bool(converted.get("converted")),
            "originalCurrenciesPreserved": True,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
