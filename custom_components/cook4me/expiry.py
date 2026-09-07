from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .inventory import (
    DEFAULT_EXPIRY_WARNING_DAYS,
    expiring_inventory_items,
    format_stock,
)

_NOTIFICATION_PREFIX = "cook4me_best_before_"

_TEXT = {
    "en": {
        "title": "Cook4Me · Food should be used soon",
        "intro": "These stock batches should be used soon. Cook4Me gives recipes using them extra priority in **For what I have in my house**.",
        "past": "use date passed {days} day(s) ago",
        "today": "use today",
        "tomorrow": "use by tomorrow",
        "days": "use within {days} days",
        "opened": "opened-package limit",
        "storage": "stored in {storage}",
        "open": "Open Cook4Me",
    },
    "de": {
        "title": "Cook4Me · Lebensmittel bald verwenden",
        "intro": "Diese Vorratschargen sollten bald verwendet werden. Cook4Me priorisiert passende Rezepte unter **Für das, was ich zu Hause habe** stärker.",
        "past": "Verbrauchsdatum seit {days} Tag(en) überschritten",
        "today": "heute verwenden",
        "tomorrow": "bis morgen verwenden",
        "days": "innerhalb von {days} Tagen verwenden",
        "opened": "Frist nach dem Öffnen",
        "storage": "Lagerort: {storage}",
        "open": "Cook4Me öffnen",
    },
    "el": {
        "title": "Cook4Me · Τρόφιμα για σύντομη κατανάλωση",
        "intro": "Αυτές οι παρτίδες πρέπει να χρησιμοποιηθούν σύντομα. Το Cook4Me δίνει μεγαλύτερη προτεραιότητα σε συνταγές που τις χρησιμοποιούν στο **Για όσα έχω στο σπίτι**.",
        "past": "η ημερομηνία χρήσης πέρασε πριν από {days} ημέρα/ημέρες",
        "today": "χρήση σήμερα",
        "tomorrow": "χρήση έως αύριο",
        "days": "χρήση μέσα σε {days} ημέρες",
        "opened": "όριο μετά το άνοιγμα",
        "storage": "αποθήκευση: {storage}",
        "open": "Άνοιγμα Cook4Me",
    },
}


def notification_id(entry_id: str) -> str:
    return f"{_NOTIFICATION_PREFIX}{entry_id}"


def _language(hass) -> str:
    code = str(getattr(hass.config, "language", "en") or "en").lower().split("-", 1)[0]
    return code if code in _TEXT else "en"


def _relative_text(days_remaining: int, text: dict[str, str]) -> str:
    if days_remaining < 0:
        return text["past"].format(days=abs(days_remaining))
    if days_remaining == 0:
        return text["today"]
    if days_remaining == 1:
        return text["tomorrow"]
    return text["days"].format(days=days_remaining)


@callback
def update_expiry_notification(
    bridge: Any,
    *,
    today: date | None = None,
    warning_days: int = DEFAULT_EXPIRY_WARNING_DAYS,
) -> None:
    reference = today or dt_util.now().date()
    items = expiring_inventory_items(
        bridge.recipe_hub.profile.get("houseIngredients") or [],
        today=reference,
        within_days=warning_days,
        include_past=True,
    )
    ident = notification_id(bridge.entry.entry_id)
    if not items:
        persistent_notification.async_dismiss(bridge.hass, ident)
        return

    lang = _language(bridge.hass)
    text = _TEXT[lang]
    lines: list[str] = []
    for row in items[:40]:
        days_remaining = int(row.get("daysRemaining") or 0)
        stock = format_stock(row)
        amount = f" · {stock}" if stock else ""
        effective = row.get("effectiveBestBefore") or row.get("bestBefore") or ""
        extras: list[str] = []
        if row.get("openedDrivenExpiry"):
            extras.append(text["opened"])
        if row.get("storage"):
            extras.append(text["storage"].format(storage=row.get("storage")))
        suffix = f" · {' · '.join(extras)}" if extras else ""
        lines.append(
            f"- **{row.get('name') or 'Ingredient'}**{amount} · "
            f"{effective} · {_relative_text(days_remaining, text)}{suffix}"
        )

    message = text["intro"] + "\n\n" + "\n".join(lines) + f"\n\n[{text['open']}](/cook4me)"
    persistent_notification.async_create(
        bridge.hass,
        message,
        title=text["title"],
        notification_id=ident,
    )


@callback
def dismiss_expiry_notification(bridge: Any) -> None:
    persistent_notification.async_dismiss(
        bridge.hass, notification_id(bridge.entry.entry_id)
    )


def register_daily_expiry_check(bridge: Any):
    @callback
    def _daily_check(_now: datetime) -> None:
        update_expiry_notification(bridge)

    return async_track_time_change(
        bridge.hass,
        _daily_check,
        hour=9,
        minute=0,
        second=0,
    )
