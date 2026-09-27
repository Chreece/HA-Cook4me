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


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("M"))
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


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
    return payload


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


def _matches_source_profile(
    profile: dict[str, Any],
    *,
    text: str,
    hits: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]],
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
    return bool(hit_index is not None and hits[hit_index])


def substitution_candidate_keys(ingredient: dict[str, Any]) -> list[str]:
    """Return ordered reviewed candidate keys from catalog-owned source profiles."""
    text = _diet._ingredient_text(ingredient)
    if not text:
        return []
    hits = _diet._diet_hits(text)
    if not any(hits):
        return []
    catalog = load_substitution_catalog()
    for profile in catalog.get("sourceProfiles") or []:
        if not isinstance(profile, dict):
            continue
        if not _matches_source_profile(profile, text=text, hits=hits):
            continue
        return list(dict.fromkeys(
            str(value).strip()
            for value in profile.get("candidateKeys") or []
            if str(value).strip()
        ))
    return []

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
        keys = substitution_candidate_keys(row)
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
        "virtualIngredientCount": virtual_ingredients,
        "unresolvedTargets": sorted(unresolved_targets),
        "missingProfiles": sorted(missing_profiles),
    }
    return payload["_runtimeSubstitutionSummary"]


def catalog_substitution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload.get("_runtimeSubstitutionSummary") or {})
