"""Canonical pending-delivery reconciliation for Cook4Me recipe sends."""
from __future__ import annotations

from typing import Any

_VARIANT_FIELDS = (
    "variantId",
    "sendVariantId",
    "selectedSendVariantId",
    "searchVariantId",
    "variantFunctionalId",
    "recipeFunctionalId",
    "displayVariantId",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def queued_variant_ids(queued: Any) -> set[str]:
    """Return exact sendable variant IDs represented by one queue entry."""
    if not isinstance(queued, dict):
        return set()
    result = {_text(queued.get("variantId"))}
    recipe = queued.get("recipe")
    if isinstance(recipe, dict):
        result.update(_text(recipe.get(key)) for key in _VARIANT_FIELDS)
    result.discard("")
    return result


def observed_variant_ids(state: Any) -> set[str]:
    """Return exact variant IDs currently observed on the appliance."""
    if not isinstance(state, dict):
        return set()
    result = {
        _text(state.get("variantFunctionalId")),
        _text(state.get("loadedVariantId")),
    }
    loaded = state.get("loadedRecipe")
    if isinstance(loaded, dict):
        result.update(
            {
                _text(loaded.get("recipeFunctionalId")),
                _text(loaded.get("variantFunctionalId")),
                _text(loaded.get("variantId")),
            }
        )
    result.discard("")
    return result


def queued_recipe_received(queued: Any, state: Any) -> bool:
    """True only when appliance state proves the queued variant is present."""
    queued_ids = queued_variant_ids(queued)
    observed_ids = observed_variant_ids(state)
    return bool(queued_ids and observed_ids and queued_ids.intersection(observed_ids))
