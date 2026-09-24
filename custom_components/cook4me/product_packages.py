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
    from .inventory import normalize_ingredient_links
    lookup = {}
    for row in catalog:
        lookup[inventory_identity(row)] = row
        for key in row.get("sourceIngredientIds") or []:
            lookup['k:' + key] = row
    resolved = []
    for item in values:
        current = lookup.get(inventory_identity(item))
        if current:
            resolved.append(current)
        elif strict:
            raise ValueError("Choose every linked ingredient from the Cook4Me catalog")
    return normalize_ingredient_links(resolved)
