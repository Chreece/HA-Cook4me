from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

try:
    from . import recipe_logic as _diet
except ImportError:  # Standalone unit-test import via spec_from_file_location.
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "cook4me_recipe_logic_substitution_test", Path(__file__).with_name("recipe_logic.py")
    )
    if _spec is None or _spec.loader is None:
        raise ImportError("recipe_logic.py")
    _diet = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_diet)

_DATA_PATH = Path(__file__).with_name("catalog") / "ingredient_substitutions.v1.json"
_ALLERGY_DATA_PATH = Path(__file__).with_name("catalog") / "ingredient_allergy_substitutions.v1.json"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("M"))
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def _merge_catalog_overlay(payload: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge reviewed allergy metadata without duplicating the diet catalog."""
    if not isinstance(overlay, dict) or int(overlay.get("schemaVersion") or 0) != 1:
        return payload
    candidates = payload.setdefault("candidates", {})
    for key, value in (overlay.get("candidates") or {}).items():
        if isinstance(value, dict):
            candidates[str(key)] = deepcopy(value)

    profiles = [deepcopy(row) for row in payload.get("sourceProfiles") or [] if isinstance(row, dict)]
    by_id = {
        str(row.get("id")): index
        for index, row in enumerate(profiles)
        if str(row.get("id") or "").strip()
    }
    for raw in overlay.get("sourceProfiles") or []:
        if not isinstance(raw, dict):
            continue
        ident = str(raw.get("id") or "").strip()
        if ident and ident in by_id:
            merged = deepcopy(profiles[by_id[ident]])
            merged.update(deepcopy(raw))
            profiles[by_id[ident]] = merged
        else:
            profiles.append(deepcopy(raw))
            if ident:
                by_id[ident] = len(profiles) - 1
    payload["sourceProfiles"] = profiles
    payload["allergyCatalogVersion"] = str(overlay.get("version") or "unknown")
    payload["unsupportedAllergySubstitutions"] = list(
        dict.fromkeys(
            str(value).strip().lower()
            for value in overlay.get("unsupportedWithoutContext") or []
            if str(value).strip()
        )
    )
    return payload


@lru_cache(maxsize=1)
def load_substitution_catalog() -> dict[str, Any]:
    try:
        payload = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schemaVersion": 1, "version": "missing", "candidates": {}}
    if not isinstance(payload, dict) or int(payload.get("schemaVersion") or 0) != 1:
        return {"schemaVersion": 1, "version": "invalid", "candidates": {}}
    if not isinstance(payload.get("candidates"), dict):
        payload["candidates"] = {}
    if not isinstance(payload.get("sourceProfiles"), list):
        payload["sourceProfiles"] = []
    try:
        overlay = json.loads(_ALLERGY_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        overlay = {}
    return _merge_catalog_overlay(payload, overlay)


def _target_lookup(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        name = _norm(row.get("canonicalName") or row.get("name") or row.get("foodName"))
        if name:
            grouped.setdefault(name, []).append(row)

    def priority(row: dict[str, Any]) -> tuple:
        return (
            row.get("classification") == "substitution",
            not bool(row.get("conceptId")),
            row.get("classification") in {"equipment", "other", "ambiguous"},
            not bool(row.get("key")),
            len(_text(row.get("canonicalName"))),
            _text(row.get("id")),
        )

    return {name: min(rows, key=priority) for name, rows in grouped.items()}


def _target_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in {
            "ingredientId": row.get("id") or row.get("ingredientId"),
            "key": row.get("key") or row.get("foodKey"),
            "foodKey": row.get("foodKey") or row.get("key"),
            "conceptId": row.get("conceptId"),
            "canonicalName": row.get("canonicalName") or row.get("name") or row.get("foodName"),
            "classification": row.get("classification"),
            "substitutionOnly": row.get("substitutionOnly"),
            "substitutionCompatibleDiets": row.get("substitutionCompatibleDiets"),
            "substitutionAllergens": row.get("substitutionAllergens"),
        }.items()
        if value not in (None, "")
    }


def _virtual_catalog_row(
    key: str,
    raw: dict[str, Any],
    *,
    version: str,
) -> dict[str, Any]:
    name = _text(raw.get("name")) or key
    compatible = [
        str(value).strip().lower()
        for value in raw.get("compatibleDiets") or []
        if str(value).strip()
    ]
    return {
        "id": f"substitution:{key}",
        "ingredientId": f"substitution:{key}",
        "key": f"substitution:{key}",
        "foodKey": f"substitution:{key}",
        "conceptId": f"concept:substitution:{key}",
        "canonicalName": name,
        "classification": "substitution",
        "substitutionOnly": True,
        "substitutionCompatibleDiets": list(dict.fromkeys(compatible)),
        "substitutionAllergens": list(dict.fromkeys(
            str(value).strip().lower()
            for value in raw.get("allergens") or []
            if str(value).strip()
        )),
        "substitutionCatalogVersion": version,
    }


def _ensure_virtual_catalog_ingredients(
    payload: dict[str, Any],
    definitions: dict[str, Any],
    *,
    version: str,
) -> int:
    rows = payload.get("ingredients")
    if not isinstance(rows, list):
        return 0
    existing = {
        _text(row.get("id") or row.get("ingredientId"))
        for row in rows
        if isinstance(row, dict)
    }
    added = 0
    for key, raw in definitions.items():
        if not isinstance(raw, dict) or not raw.get("virtualCatalogIngredient"):
            continue
        ident = f"substitution:{key}"
        if ident in existing:
            continue
        rows.append(_virtual_catalog_row(str(key), raw, version=version))
        existing.add(ident)
        added += 1
    return added


def _resolve_component(
    raw: dict[str, Any],
    lookup: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    name = _text(raw.get("targetCanonicalName"))
    target = lookup.get(_norm(name))
    if not isinstance(target, dict):
        return None
    result = {"target": _target_ref(target)}
    for field in ("quantity", "unit"):
        if raw.get(field) not in (None, ""):
            result[field] = raw[field]
    return result


def _resolve_candidate(
    key: str,
    raw: dict[str, Any],
    *,
    lookup: dict[str, dict[str, Any]],
    evidence: str,
    version: str,
) -> dict[str, Any] | None:
    name = _text(raw.get("name")) or key
    result: dict[str, Any] = {
        "key": key,
        "name": name,
        "compatibleDiets": list(dict.fromkeys(
            str(value).strip().lower()
            for value in raw.get("compatibleDiets") or []
            if str(value).strip()
        )),
        "allergens": list(dict.fromkeys(
            str(value).strip().lower()
            for value in raw.get("allergens") or []
            if str(value).strip()
        )),
        "contexts": list(dict.fromkeys(
            str(value).strip().lower()
            for value in raw.get("contexts") or ["general"]
            if str(value).strip()
        )),
        "confidence": _text(raw.get("confidence")) or "reviewed",
        "evidence": evidence,
        "catalogVersion": version,
        "catalogSource": "ingredient_substitutions.v1",
    }
    if raw.get("allergenEvidence"):
        result["allergenEvidence"] = _text(raw.get("allergenEvidence"))

    components = raw.get("components")
    if isinstance(components, list) and components:
        resolved = []
        for component in components:
            if not isinstance(component, dict):
                return None
            item = _resolve_component(component, lookup)
            if item is None:
                return None
            resolved.append(item)
        result["components"] = resolved
        return result

    target_name = _text(raw.get("targetCanonicalName")) or name
    target = lookup.get(_norm(target_name))
    if not isinstance(target, dict):
        return None
    result["target"] = _target_ref(target)
    return result


def _ingredient_allergen_hits(ingredient: dict[str, Any]) -> set[str]:
    intelligence = (
        ingredient.get("intelligence")
        if isinstance(ingredient.get("intelligence"), dict)
        else {}
    )
    raw = (
        intelligence.get("allergens")
        if isinstance(intelligence.get("allergens"), dict)
        else ingredient.get("allergens")
        if isinstance(ingredient.get("allergens"), dict)
        else {}
    )
    present = set()
    for key, value in raw.items():
        state = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if value is True or state in {"present", "contains", "incompatible", "yes", "true"}:
            present.add(str(key).strip().lower().replace("-", "_").replace(" ", "_"))
    return present


def _matches_source_profile(
    profile: dict[str, Any],
    *,
    text: str,
    hits: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]],
    allergen_hits: set[str],
) -> bool:
    match = profile.get("match") if isinstance(profile.get("match"), dict) else {}
    terms = [
        str(value)
        for value in match.get("terms") or []
        if str(value).strip()
    ]
    if terms and any(_diet._contains_phrase(text, term) for term in terms):
        return True
    hit_name = _text(match.get("dietHit")).lower().replace("-", "_")
    hit_index = {"meat": 0, "animal": 1, "non_vegan": 2}.get(hit_name)
    if hit_index is not None and hits[hit_index]:
        return True
    allergen = _text(match.get("allergenHit")).lower().replace("-", "_").replace(" ", "_")
    return bool(allergen and allergen in allergen_hits)


def substitution_source_profiles(ingredient: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every reviewed source profile that applies to this ingredient."""
    text = _diet._ingredient_text(ingredient)
    if not text:
        return []
    hits = _diet._diet_hits(text)
    allergen_hits = _ingredient_allergen_hits(ingredient)
    catalog = load_substitution_catalog()
    return [
        profile
        for profile in catalog.get("sourceProfiles") or []
        if isinstance(profile, dict)
        and _matches_source_profile(
            profile,
            text=text,
            hits=hits,
            allergen_hits=allergen_hits,
        )
    ]


def substitution_candidate_keys(ingredient: dict[str, Any]) -> list[str]:
    """Return ordered reviewed candidate keys from all matching catalog profiles."""
    return list(dict.fromkeys(
        str(value).strip()
        for profile in substitution_source_profiles(ingredient)
        for value in profile.get("candidateKeys") or []
        if str(value).strip()
    ))


def _source_diets(ingredient: dict[str, Any]) -> list[str]:
    text = _diet._ingredient_text(ingredient)
    hits = _diet._diet_hits(text)
    result = []
    if hits[0]:
        result.append("pescatarian")
    if hits[1]:
        result.append("vegetarian")
    if hits[2]:
        result.append("vegan")
    return result


def _source_allergens(profiles: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(
        str(value).strip().lower().replace("-", "_").replace(" ", "_")
        for profile in profiles
        for value in profile.get("triggerAllergens") or []
        if str(value).strip()
    ))


def enrich_catalog_substitutions(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach reviewed multi-candidate substitutions directly to catalog rows."""
    catalog = load_substitution_catalog()
    definitions = catalog.get("candidates") if isinstance(catalog.get("candidates"), dict) else {}
    evidence = _text(catalog.get("evidence")) or "Cook4Me reviewed dietary substitution catalog"
    version = _text(catalog.get("version")) or "unknown"
    virtual_ingredients = _ensure_virtual_catalog_ingredients(
        payload, definitions, version=version
    )
    lookup = _target_lookup(payload)

    resolved: dict[str, dict[str, Any]] = {}
    unresolved_targets: list[str] = []
    for key, raw in definitions.items():
        if not isinstance(raw, dict):
            continue
        candidate = _resolve_candidate(
            str(key), raw, lookup=lookup, evidence=evidence, version=version
        )
        if candidate is None:
            unresolved_targets.append(str(key))
            continue
        resolved[str(key)] = candidate

    enriched = 0
    candidates_attached = 0
    missing_profiles: set[str] = set()
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        if row.get("substitutionOnly") or row.get("classification") == "substitution":
            continue
        profiles = substitution_source_profiles(row)
        keys = list(dict.fromkeys(
            str(value).strip()
            for profile in profiles
            for value in profile.get("candidateKeys") or []
            if str(value).strip()
        ))
        if not keys:
            continue
        candidates = []
        for key in keys:
            candidate = resolved.get(key)
            if candidate is None:
                missing_profiles.add(key)
                continue
            candidates.append(deepcopy(candidate))
        if not candidates:
            continue
        row["substitutions"] = candidates
        row["substitutionDiets"] = _source_diets(row)
        source_allergens = _source_allergens(profiles)
        if source_allergens:
            row["substitutionAllergens"] = source_allergens
        row["substitutionCatalogVersion"] = version
        enriched += 1
        candidates_attached += len(candidates)

    payload["_runtimeSubstitutionSummary"] = {
        "version": version,
        "ingredientCount": enriched,
        "candidateCount": candidates_attached,
        "resolvedProfiles": len(resolved),
        "sourceProfiles": len([
            row for row in catalog.get("sourceProfiles") or []
            if isinstance(row, dict)
        ]),
        "allergySourceProfiles": len([
            row for row in catalog.get("sourceProfiles") or []
            if isinstance(row, dict) and row.get("triggerAllergens")
        ]),
        "allergyIngredientCount": len([
            row for row in payload.get("ingredients") or []
            if isinstance(row, dict) and row.get("substitutionAllergens")
        ]),
        "allergyCatalogVersion": str(catalog.get("allergyCatalogVersion") or ""),
        "unsupportedAllergySubstitutions": list(catalog.get("unsupportedAllergySubstitutions") or []),
        "virtualIngredientCount": virtual_ingredients,
        "unresolvedTargets": sorted(unresolved_targets),
        "missingProfiles": sorted(missing_profiles),
    }
    return payload["_runtimeSubstitutionSummary"]


def catalog_substitution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload.get("_runtimeSubstitutionSummary") or {})
