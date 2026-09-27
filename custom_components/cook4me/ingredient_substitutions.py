from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from . import recipe_logic as _diet

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
        }.items()
        if value not in (None, "")
    }


def _virtual_target(key: str, name: str) -> dict[str, Any]:
    return {
        "ingredientId": f"substitution:{key}",
        "key": f"substitution:{key}",
        "foodKey": f"substitution:{key}",
        "conceptId": f"concept:substitution:{key}",
        "canonicalName": name,
        "substitutionOnly": True,
    }


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

    if raw.get("virtualCatalogIngredient"):
        result["target"] = _virtual_target(key, name)
        return result

    target_name = _text(raw.get("targetCanonicalName"))
    target = lookup.get(_norm(target_name))
    if not isinstance(target, dict):
        return None
    result["target"] = _target_ref(target)
    return result


def _has_any(text: str, phrases) -> bool:
    return any(_diet._contains_phrase(text, phrase) for phrase in phrases)


def substitution_candidate_keys(ingredient: dict[str, Any]) -> list[str]:
    """Return reviewed substitution profiles for one source ingredient."""
    text = _diet._ingredient_text(ingredient)
    if not text:
        return []
    hits = _diet._diet_hits(text)
    words = set(hits[2])
    if not any(hits):
        return []

    if _has_any(text, _diet._GELATIN_TERMS):
        return ["agar", "pectin", "cornstarch"]
    if _has_any(text, _diet._RENNET_TERMS):
        return ["microbial_rennet", "lemon_juice", "citric_acid"]
    if _has_any(text, _diet._ISINGLASS_TERMS):
        return ["bentonite"]
    if words & {"lard", "tallow", "suet", "schmalz"}:
        return ["olive_oil", "coconut_oil"]
    if any(_diet._contains_phrase(text, value) for value in (
        "fish sauce", "oyster sauce", "worcestershire", "sauce de poisson", "nuoc mam"
    )):
        return ["soy_sauce", "coconut_aminos"]
    if any(_diet._contains_phrase(text, value) for value in (
        "stock", "broth", "bouillon", "brühe", "bruehe", "fond", "caldo"
    )):
        return ["vegetable_stock", "vegetable_stock_cube", "water"]
    if hits[1]:
        return ["tofu", "mushrooms", "chickpeas"]
    if _has_any(text, _diet._EGG_WHITE_TERMS):
        return ["aquafaba", "ground_flaxseed_water", "cornstarch_water"]
    if _has_any(text, _diet._EGG_YOLK_TERMS):
        return ["ground_flaxseed_water", "tofu"]
    if _has_any(text, _diet._EGG_TERMS):
        return ["ground_flaxseed_water", "aquafaba", "tofu"]
    if _has_any(text, _diet._WHEY_CASEIN_TERMS):
        return ["pea_protein", "tofu"]
    if _has_any(text, _diet._KEFIR_TERMS) or words & {
        "yogurt", "yoghurt", "joghurt", "γιαουρτι", "γιαούρτι"
    }:
        return ["plant_yogurt", "tofu_lemon", "coconut_cream_lemon"]
    if _has_any(text, _diet._CHEESE_TERMS):
        return ["plant_cheese", "tofu", "nutritional_yeast"]
    if words & {"butter", "βουτυρο", "βούτυρο", "beurre", "burro", "mantequilla", "ghee"}:
        return ["olive_oil", "coconut_oil"]
    if words & {"cream", "sahne", "creme", "panna", "κρεμα", "κρέμα"}:
        return ["coconut_cream", "soy_cream"]
    if words & {"milk", "milch", "lait", "latte", "leche", "γαλα", "γάλα"}:
        return ["soy_milk", "rice_milk", "unsweetened_soy_milk"]
    if words & {"honey", "honig", "miel", "miele", "μελι", "μέλι"}:
        return ["maple_syrup", "agave_syrup", "sugar"]
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
    lookup = _target_lookup(payload)
    evidence = _text(catalog.get("evidence")) or "Cook4Me reviewed dietary substitution catalog"
    version = _text(catalog.get("version")) or "unknown"

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
        "unresolvedTargets": sorted(unresolved_targets),
        "missingProfiles": sorted(missing_profiles),
    }
    return payload["_runtimeSubstitutionSummary"]


def catalog_substitution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload.get("_runtimeSubstitutionSummary") or {})
