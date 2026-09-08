from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
from typing import Any
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_ECB_DAILY_XML = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
_USER_AGENT = "HA-Cook4me/2026.9.8 (+https://github.com/Chreece/HA-Cook4me)"
_REFRESH_AFTER = timedelta(hours=12)

_LANGUAGE_CURRENCY = {
    "ar": "AED",
    "bg": "EUR",
    "cs": "CZK",
    "da": "DKK",
    "de": "EUR",
    "el": "EUR",
    "en": "GBP",
    "es": "EUR",
    "et": "EUR",
    "fi": "EUR",
    "fr": "EUR",
    "ga": "EUR",
    "hr": "EUR",
    "hu": "HUF",
    "it": "EUR",
    "ja": "JPY",
    "ko": "KRW",
    "lt": "EUR",
    "lv": "EUR",
    "mt": "EUR",
    "nl": "EUR",
    "no": "NOK",
    "pl": "PLN",
    "pt": "EUR",
    "ro": "RON",
    "sk": "EUR",
    "sl": "EUR",
    "sv": "SEK",
    "tr": "TRY",
    "uk": "UAH",
    "zh": "CNY",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _currency(value: Any) -> str:
    token = _text(value).upper()
    return token if len(token) == 3 and token.isalpha() else ""


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def default_currency_for_language(language: Any) -> str:
    code = _text(language).lower().replace("_", "-").split("-", 1)[0]
    return _LANGUAGE_CURRENCY.get(code, "EUR")


def _parse_datetime(value: Any) -> datetime | None:
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


def parse_ecb_daily_xml(payload: bytes | str) -> dict[str, Any]:
    root = ET.fromstring(payload)
    rate_date = ""
    rates: dict[str, float] = {"EUR": 1.0}
    for element in root.iter():
        tag = str(element.tag)
        if not tag.endswith("Cube"):
            continue
        if element.attrib.get("time"):
            rate_date = _text(element.attrib.get("time"))
        currency = _currency(element.attrib.get("currency"))
        rate = _number(element.attrib.get("rate"))
        if currency and rate is not None and rate > 0:
            rates[currency] = rate
    if len(rates) <= 1:
        raise ValueError("ECB response did not contain exchange rates")
    return {"date": rate_date, "rates": rates}


def fetch_ecb_daily_rates(timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(
        _ECB_DAILY_XML,
        headers={"Accept": "application/xml,text/xml", "User-Agent": _USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = parse_ecb_daily_xml(response.read())
    except urllib.error.HTTPError as exc:
        return {"ok": False, "reason": f"http_{exc.code}"}
    except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
        return {"ok": False, "reason": type(exc).__name__}
    return {
        "ok": True,
        "source": "ecb_reference_rates",
        "sourceUrl": _ECB_DAILY_XML,
        **parsed,
    }


def convert_amount(
    amount: Any,
    from_currency: Any,
    to_currency: Any,
    rates: Any,
) -> float | None:
    value = _number(amount)
    source = _currency(from_currency)
    target = _currency(to_currency)
    table = rates if isinstance(rates, dict) else {}
    if value is None or not source or not target:
        return None
    if source == target:
        return value
    source_rate = 1.0 if source == "EUR" else _number(table.get(source))
    target_rate = 1.0 if target == "EUR" else _number(table.get(target))
    if source_rate is None or source_rate <= 0 or target_rate is None or target_rate <= 0:
        return None
    eur_value = value / source_rate
    return eur_value * target_rate


def convert_currency_map(
    values: Any,
    target_currency: Any,
    rates: Any,
) -> dict[str, Any]:
    target = _currency(target_currency)
    source_values = values if isinstance(values, dict) else {}
    total = 0.0
    converted: dict[str, float] = {}
    unconverted: dict[str, float] = {}
    for raw_currency, raw_amount in source_values.items():
        source = _currency(raw_currency)
        amount = _number(raw_amount)
        if not source or amount is None:
            continue
        result = convert_amount(amount, source, target, rates)
        if result is None:
            unconverted[source] = round(amount, 2)
            continue
        converted[source] = round(result, 4)
        total += result
    return {
        "currency": target,
        "amount": round(total, 2),
        "converted": converted,
        "unconverted": unconverted,
        "complete": not unconverted,
    }


class Cook4MeCurrencyFxStore:
    """Persist currency preference and a bounded latest ECB reference-rate cache."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.currency_fx"
        )
        self._loaded = False
        self._data: dict[str, Any] = {
            "preference": {"initialized": False, "mode": "auto", "currency": ""},
            "rates": {},
        }

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            raw_pref = saved.get("preference") if isinstance(saved.get("preference"), dict) else {}
            mode = _text(raw_pref.get("mode")).lower()
            if mode not in {"auto", "fixed"}:
                mode = "auto"
            self._data["preference"] = {
                "initialized": bool(raw_pref.get("initialized")),
                "mode": mode,
                "currency": _currency(raw_pref.get("currency")),
            }
            raw_rates = saved.get("rates") if isinstance(saved.get("rates"), dict) else {}
            table = raw_rates.get("rates") if isinstance(raw_rates.get("rates"), dict) else {}
            normalized = {
                currency: float(rate)
                for raw_currency, raw_rate in table.items()
                if (currency := _currency(raw_currency))
                and (rate := _number(raw_rate)) is not None
                and rate > 0
            }
            if normalized:
                normalized["EUR"] = 1.0
                self._data["rates"] = {
                    "date": _text(raw_rates.get("date")),
                    "fetchedAt": _text(raw_rates.get("fetchedAt")),
                    "source": _text(raw_rates.get("source")) or "ecb_reference_rates",
                    "rates": normalized,
                }
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    @property
    def preference(self) -> dict[str, Any]:
        return deepcopy(self._data["preference"])

    async def async_resolve_currency(self, language: Any, cost_store: Any) -> str:
        pref = dict(self._data["preference"])
        existing = _currency((getattr(cost_store, "settings", {}) or {}).get("currency"))
        if not pref.get("initialized"):
            if existing:
                pref = {"initialized": True, "mode": "fixed", "currency": existing}
            else:
                pref = {"initialized": True, "mode": "auto", "currency": ""}
            self._data["preference"] = pref
            await self._save()
        selected = (
            default_currency_for_language(language)
            if pref.get("mode") == "auto"
            else _currency(pref.get("currency")) or default_currency_for_language(language)
        )
        if existing != selected:
            await cost_store.async_set_settings(currency=selected)
        return selected

    async def async_set_preference(
        self,
        *,
        mode: str,
        currency: str,
        language: Any,
        cost_store: Any,
    ) -> str:
        chosen_mode = _text(mode).lower()
        if chosen_mode not in {"auto", "fixed"}:
            raise ValueError("Currency mode must be auto or fixed")
        chosen_currency = _currency(currency)
        if chosen_mode == "fixed" and not chosen_currency:
            raise ValueError("A fixed currency requires a three-letter currency code")
        self._data["preference"] = {
            "initialized": True,
            "mode": chosen_mode,
            "currency": chosen_currency if chosen_mode == "fixed" else "",
        }
        await self._save()
        selected = (
            default_currency_for_language(language)
            if chosen_mode == "auto"
            else chosen_currency
        )
        await cost_store.async_set_settings(currency=selected)
        return selected

    async def async_rates(self, *, force: bool = False) -> dict[str, Any]:
        cached = self._data.get("rates") if isinstance(self._data.get("rates"), dict) else {}
        fetched = _parse_datetime(cached.get("fetchedAt"))
        fresh = bool(
            cached.get("rates")
            and fetched is not None
            and datetime.now(timezone.utc) - fetched < _REFRESH_AFTER
        )
        if fresh and not force:
            return {**deepcopy(cached), "stale": False, "refreshError": ""}

        result = await self.hass.async_add_executor_job(fetch_ecb_daily_rates)
        if result.get("ok"):
            stored = {
                "date": _text(result.get("date")),
                "fetchedAt": datetime.now(timezone.utc).isoformat(),
                "source": "ecb_reference_rates",
                "rates": dict(result.get("rates") or {}),
            }
            self._data["rates"] = stored
            await self._save()
            return {**deepcopy(stored), "stale": False, "refreshError": ""}

        if cached.get("rates"):
            return {
                **deepcopy(cached),
                "stale": True,
                "refreshError": _text(result.get("reason")) or "fx_refresh_failed",
            }
        return {
            "date": "",
            "fetchedAt": "",
            "source": "ecb_reference_rates",
            "rates": {"EUR": 1.0},
            "stale": True,
            "refreshError": _text(result.get("reason")) or "fx_refresh_failed",
        }


async def currency_fx_store_for_bridge(bridge: Any) -> Cook4MeCurrencyFxStore:
    store = getattr(bridge, "_currency_fx_store", None)
    if store is None:
        store = Cook4MeCurrencyFxStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._currency_fx_store = store
    return store
