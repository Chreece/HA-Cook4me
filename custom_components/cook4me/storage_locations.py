"""Named storage places; IDs remain stable when a place is renamed."""
from copy import deepcopy
from uuid import uuid4

KINDS = {"fridge", "freezer", "pantry", "other"}
DEFAULTS = [{"id": kind, "name": name, "kind": kind} for kind, name in
            (("fridge", "Fridge"), ("freezer", "Freezer"), ("pantry", "Pantry"))]


def normalize_locations(value):
    if not isinstance(value, list):
        return deepcopy(DEFAULTS)
    output, seen = [], set()
    for row in value[:100]:
        if not isinstance(row, dict):
            continue
        identity = str(row.get("id") or "").strip()[:80]
        name = str(row.get("name") or "").strip()[:80]
        kind = str(row.get("kind") or "other")
        if identity and name and identity not in seen and kind in KINDS:
            output.append({"id": identity, "name": name, "kind": kind})
            seen.add(identity)
    return output


def edit_location(profile, *, action, identity="", name="", kind="other"):
    locations = normalize_locations(profile.get("storageLocations"))
    existing = next((row for row in locations if row["id"] == identity), None)
    if identity and existing is None:
        raise ValueError("Storage place no longer exists; reload the list")
    lots = [lot for row in profile.get("houseIngredients") or [] for lot in row.get("lots") or []]
    if action == "delete":
        if existing is None:
            raise ValueError("Choose a storage place")
        if any(lot.get("storageLocationId") == identity for lot in lots):
            raise ValueError("Move the stock stored here before deleting this place")
        locations.remove(existing)
    elif action == "save":
        name = str(name).strip()
        if not name or len(name) > 80 or kind not in KINDS:
            raise ValueError("Enter a name of 1–80 characters and a valid storage type")
        if any(row["name"].casefold() == name.casefold() and row["id"] != identity for row in locations):
            raise ValueError("A storage place already has this name")
        if existing is None:
            if len(locations) >= 100:
                raise ValueError("At most 100 storage places are supported")
            locations.append({"id": str(uuid4()), "name": name, "kind": kind})
        else:
            existing.update(name=name, kind=kind)
            for lot in lots:
                if lot.get("storageLocationId") == identity:
                    lot["storage"] = kind
    else:
        raise ValueError("Unknown storage action")
    profile["storageLocations"] = locations
    return profile


def validate_location(profile, metadata):
    metadata = deepcopy(metadata or {})
    identity = metadata.get("storageLocationId")
    if identity:
        row = next((row for row in normalize_locations(profile.get("storageLocations")) if row["id"] == identity), None)
        if row is None:
            raise ValueError("Storage place no longer exists; choose another place")
        metadata["storage"] = row["kind"]
    return metadata
