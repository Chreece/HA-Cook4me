"""Stable package identity, optimistic edits and exact package details."""
from copy import deepcopy
import hashlib
import json

from .inventory import inventory_identity
from .nutrition_label import async_save_lot_nutrition
from .nutrition import serialize_nutrition_mutation


def find_package(inventory, lot_id):
    for row in inventory or []:
        for lot in row.get("lots") or []:
            if lot.get("id") == lot_id:
                return row, lot
    raise ValueError("This package no longer exists; reload your stock")


def package_version(row, lot):
    return hashlib.sha256(json.dumps([inventory_identity(row), row.get("unit"), lot],
                                     sort_keys=True).encode()).hexdigest()


@serialize_nutrition_mutation
async def replace_package_nutrition(store, inventory, lot_id, nutrition):
    # Prepare the complete replacement before saving, including when the package
    # has moved to another ingredient or its nutrition has explicitly been cleared.
    data = deepcopy(store._data)
    exact = data.setdefault("stockLots", {})
    for identity in list(exact):
        exact[identity] = [row for row in exact[identity] if row.get("inventoryLotId") != lot_id]
        if not exact[identity]:
            del exact[identity]

    class Draft:
        _data = data

        async def _save(self):
            pass

    if nutrition:
        draft = Draft()
        await async_save_lot_nutrition(draft, inventory, lot_id=lot_id,
                                       nutrition=nutrition, manually_edited=True)
        data = draft._data
    # A failed write must not change the in-memory package label.
    await store._store.async_save(data)
    store._data = data


def resolve_ingredient_links(values, catalog, *, strict=False):
    """Validate catalog links without replacing an exact recipe source identity.

    A display choice can represent several provider ingredient IDs.  Ingredient
    Info sends the exact recipe source ID the user clicked; keep that ID after
    validation instead of silently collapsing it to the display representative.
    """
    from .inventory import normalize_ingredient_links
    lookup = {}
    for row in catalog:
        primary = inventory_identity(row)
        lookup[primary] = (row, primary)
        for key in row.get("sourceIngredientIds") or []:
            lookup["k:" + key] = (row, "k:" + key)
    resolved = []
    for item in values:
        requested = inventory_identity(item)
        match = lookup.get(requested)
        if match:
            current, matched_identity = match
            selected = deepcopy(current)
            if matched_identity.startswith("k:") and matched_identity != inventory_identity(current):
                source_id = matched_identity[2:]
                selected["key"] = source_id
                selected["ingredientId"] = source_id
                selected["id"] = source_id
            resolved.append(selected)
        elif strict:
            raise ValueError("Choose every linked ingredient from the Cook4Me catalog")
    return normalize_ingredient_links(resolved)
