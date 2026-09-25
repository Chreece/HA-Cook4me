"""Turn reviewed catalog opening rules into explicit package settings."""
from copy import deepcopy
from datetime import date

from .ingredient_lifecycle import opening_window


def opening_rules(ingredient, lot):
    # Resolve by stable catalog identity, never by a product's display name.
    from .release_catalog import ingredient_lifecycle_profile
    profile = ingredient_lifecycle_profile(ingredient, include_sources=False)
    probe = {**lot, "openedAt": "2026-01-01", "bestBefore": "", "useWithinDays": None}
    result = []
    for rule in profile.get("afterOpening", {}).get("rules", []):
        window = opening_window(
            profile, {**probe, "storage": rule["storage"]},
            temperature_c=rule["maxTemperatureC"],
            confirmed_conditions=tuple(rule["conditions"]),
        )
        if window.get("ruleId") == rule["id"]:
            result.append(deepcopy(rule))
    return result


def configure_opening(ingredient, metadata):
    """Validate catalog scope and confirmation again at save time."""
    result = deepcopy(metadata)
    rule_id = result.get("openingRuleId")
    if not rule_id:
        return result
    rule = next((r for r in opening_rules(ingredient, result) if r["id"] == rule_id), None)
    if rule is None:
        raise ValueError("Use-within guidance no longer matches this ingredient, brand or barcode")
    if result.get("openingConditionsConfirmed") is not True:
        raise ValueError("Use-within guidance needs confirmation of the storage instructions")
    if result.get("storage") not in (None, "", rule["storage"]):
        raise ValueError("Storage place must match the opening instructions")
    result.update(useWithinDays=rule["daysMax"], storage=rule["storage"])
    return result


def mark_package_opened(ingredient, lot, request, *, opened_on=None):
    result = deepcopy(lot)
    # Repeated cooking reviews must never restart an existing opening clock.
    if request.get("ruleId"):
        result.update(openingRuleId=request["ruleId"],
                      openingConditionsConfirmed=request.get("confirmed") is True)
        result = configure_opening(ingredient, result)
    if not result.get("useWithinDays"):
        raise ValueError("Use-within days are required to mark this package opened")
    result["openedAt"] = result.get("openedAt") or opened_on or date.today().isoformat()
    result["applyOpeningExpiry"] = request.get("applyOpeningExpiry", True) is True
    return result
