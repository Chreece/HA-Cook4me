from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import gzip
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
_PROVIDER_DATA_PATH = Path(__file__).with_name("catalog") / "provider_ingredient_substitutions.v1.json"
_GENERATED_PROVIDER_DATA_PATH = Path(__file__).with_name("catalog") / "provider_ingredient_substitutions.generated.v1.json"
_CONCEPT_DATA_PATH = Path(__file__).with_name("catalog") / "concept_ingredient_substitutions.v1.json"
_ALLERGY_DATA_PATH = Path(__file__).with_name("catalog") / "ingredient_allergy_substitutions.v1.json"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("M"))
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def _merge_binding_overlay(payload: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Append stable provider-ID bindings without changing profile definitions."""
    if not isinstance(overlay, dict) or int(overlay.get("schemaVersion") or 0) != 1:
        return payload
    bindings = [
        deepcopy(row)
        for row in payload.get("ingredientBindings") or []
        if isinstance(row, dict)
    ]
    binding_ids = {
        _text(row.get("id"))
        for row in bindings
        if _text(row.get("id"))
    }
    for raw in overlay.get("ingredientBindings") or []:
        if not isinstance(raw, dict):
            continue
        ident = _text(raw.get("id"))
        if not ident or ident in binding_ids:
            continue
        bindings.append(deepcopy(raw))
        binding_ids.add(ident)
    payload["ingredientBindings"] = bindings
    payload["providerBindingCatalogVersion"] = _text(overlay.get("version")) or "unknown"
    return payload


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
    if not isinstance(payload.get("ingredientBindings"), list):
        payload["ingredientBindings"] = []
    try:
        provider_overlay = json.loads(_PROVIDER_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        provider_overlay = {}
    payload = _merge_binding_overlay(payload, provider_overlay)
    try:
        generated_provider_overlay = json.loads(
            _GENERATED_PROVIDER_DATA_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        generated_provider_overlay = {}
    payload = _merge_binding_overlay(payload, generated_provider_overlay)
    try:
        concept_overlay = json.loads(_CONCEPT_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        try:
            with gzip.open(
                Path(str(_CONCEPT_DATA_PATH) + ".gz"), "rt", encoding="utf-8"
            ) as handle:
                concept_overlay = json.load(handle)
        except (OSError, json.JSONDecodeError):
            concept_overlay = {}
    payload = _merge_binding_overlay(payload, concept_overlay)
    payload["conceptBindingCatalogVersion"] = _text(
        concept_overlay.get("version")
    ) or "missing"
    try:
        overlay = json.loads(_ALLERGY_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        overlay = {}
    return _merge_catalog_overlay(payload, overlay)


def _binding_signature(binding: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return (
        _text(binding.get("profileId")),
        tuple(sorted(
            _text(value).lower()
            for value in binding.get("substitutionDiets") or []
            if _text(value)
        )),
    )


def _catalog_with_payload_binding_concepts(
    catalog: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Expand reviewed provider-ID bindings to exact catalog concept siblings.

    Runtime matching never uses labels here. Each bound provider ID is resolved
    to its catalog conceptId; source-local rows sharing that exact concept inherit
    the reviewed profile. Conflicting concept claims are omitted fail-closed.
    """
    result = deepcopy(catalog)
    bindings = [
        row for row in result.get("ingredientBindings") or []
        if isinstance(row, dict)
    ]
    if not bindings:
        return result

    rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        for value in (
            row.get("id"),
            row.get("ingredientId"),
            row.get("key"),
            row.get("foodKey"),
            *(row.get("sourceIngredientIds") or []),
        ):
            ident = _text(value)
            if ident:
                rows_by_id.setdefault(ident, []).append(row)

    explicit_concepts = {
        _text(value)
        for binding in bindings
        for value in binding.get("conceptIds") or []
        if _text(value)
    }
    claims: dict[str, list[int]] = {}
    for index, binding in enumerate(bindings):
        for ident in binding.get("ingredientIds") or []:
            for row in rows_by_id.get(_text(ident), ()):
                concept = _text(row.get("conceptId"))
                if concept and concept not in explicit_concepts:
                    claims.setdefault(concept, []).append(index)

    expanded = 0
    ambiguous = 0
    for concept, indices in claims.items():
        unique_indices = list(dict.fromkeys(indices))
        signatures = {
            _binding_signature(bindings[index]) for index in unique_indices
        }
        if len(signatures) != 1:
            ambiguous += 1
            continue
        binding = bindings[unique_indices[0]]
        concepts = list(dict.fromkeys([
            *(
                _text(value)
                for value in binding.get("conceptIds") or []
                if _text(value)
            ),
            concept,
        ]))
        binding["conceptIds"] = concepts
        expanded += 1

    result["ingredientBindings"] = bindings
    result["_runtimeBindingConceptExpansion"] = {
        "expandedConcepts": expanded,
        "ambiguousConcepts": ambiguous,
    }
    return result

def _catalog_binding(
    ingredient: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any] | None:
    """Return an exact reviewed catalog binding by ID/concept, never by label."""
    ingredient_ids = {
        _text(value)
        for value in (
            ingredient.get("id"),
            ingredient.get("ingredientId"),
            ingredient.get("key"),
            ingredient.get("foodKey"),
            *(ingredient.get("sourceIngredientIds") or []),
        )
        if _text(value)
    }
    concept_ids = {
        _text(ingredient.get("conceptId"))
    } if _text(ingredient.get("conceptId")) else set()
    for raw in catalog.get("ingredientBindings") or []:
        if not isinstance(raw, dict):
            continue
        bound_ids = {
            _text(value) for value in raw.get("ingredientIds") or [] if _text(value)
        }
        bound_concepts = {
            _text(value) for value in raw.get("conceptIds") or [] if _text(value)
        }
        if ingredient_ids & bound_ids or concept_ids & bound_concepts:
            return raw
    return None


def _binding_profile(
    binding: dict[str, Any] | None,
    catalog: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(binding, dict):
        return None
    wanted = _text(binding.get("profileId"))
    return next(
        (
            row for row in catalog.get("sourceProfiles") or []
            if isinstance(row, dict) and _text(row.get("id")) == wanted
        ),
        None,
    )


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


def _ingredient_diet_states(ingredient: dict[str, Any]) -> dict[str, str]:
    """Return explicit catalog diet evidence; never infer it from display text."""
    intelligence = (
        ingredient.get("intelligence")
        if isinstance(ingredient.get("intelligence"), dict)
        else {}
    )
    raw = (
        intelligence.get("diets")
        if isinstance(intelligence.get("diets"), dict)
        else ingredient.get("diets")
        if isinstance(ingredient.get("diets"), dict)
        else {}
    )
    result: dict[str, str] = {}
    for diet in ("pescatarian", "vegetarian", "vegan"):
        if diet not in raw:
            continue
        value = raw.get(diet)
        if value is True:
            result[diet] = "compatible"
            continue
        if value is False:
            result[diet] = "incompatible"
            continue
        state = _text(value).lower().replace("-", "_").replace(" ", "_")
        if state in {"compatible", "safe", "allowed", "yes", "true"}:
            result[diet] = "compatible"
        elif state in {"incompatible", "unsafe", "blocked", "no", "false", "present"}:
            result[diet] = "incompatible"
        else:
            result[diet] = "unknown"
    return result


def _ingredient_substitution_class(ingredient: dict[str, Any]) -> str:
    intelligence = (
        ingredient.get("intelligence")
        if isinstance(ingredient.get("intelligence"), dict)
        else {}
    )
    return _text(
        intelligence.get("substitutionClass")
        or ingredient.get("substitutionClass")
    )


def _profile_by_id(catalog: dict[str, Any], profile_id: str) -> dict[str, Any] | None:
    wanted = _text(profile_id)
    if not wanted:
        return None
    return next(
        (
            row for row in catalog.get("sourceProfiles") or []
            if isinstance(row, dict) and _text(row.get("id")) == wanted
        ),
        None,
    )


def _catalog_source_profiles(
    ingredient: dict[str, Any],
    catalog: dict[str, Any],
    *,
    binding: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Resolve profiles for a catalog row from catalog evidence only.

    Official/resolved ingredients must never depend on a localized/canonical
    label to determine dietary incompatibility or replacement semantics.
    """
    profiles: list[dict[str, Any]] = []

    def add(profile: dict[str, Any] | None) -> None:
        if isinstance(profile, dict) and profile not in profiles:
            profiles.append(profile)

    add(_binding_profile(binding, catalog))

    substitution_class = _ingredient_substitution_class(ingredient)
    add(_profile_by_id(catalog, substitution_class))

    diets = _ingredient_diet_states(ingredient)
    allergens = _ingredient_allergen_hits(ingredient)
    diet_key = {
        "meat": "pescatarian",
        "animal": "vegetarian",
        "non_vegan": "vegan",
    }
    for profile in catalog.get("sourceProfiles") or []:
        if not isinstance(profile, dict):
            continue
        match = profile.get("match") if isinstance(profile.get("match"), dict) else {}
        hit_name = _text(match.get("dietHit")).lower().replace("-", "_")
        wanted_diet = diet_key.get(hit_name)
        if wanted_diet and diets.get(wanted_diet) == "incompatible":
            add(profile)
            continue
        allergen = _text(match.get("allergenHit")).lower().replace("-", "_").replace(" ", "_")
        if allergen and allergen in allergens:
            add(profile)
    return profiles


def _catalog_candidate_profile(
    ingredient: dict[str, Any],
    catalog: dict[str, Any],
    *,
    binding: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Choose a replacement profile using only exact catalog metadata."""
    bound = _binding_profile(binding, catalog)
    if isinstance(bound, dict):
        return bound
    classified = _profile_by_id(catalog, _ingredient_substitution_class(ingredient))
    if isinstance(classified, dict):
        return classified

    diets = _ingredient_diet_states(ingredient)
    profiles = _catalog_source_profiles(ingredient, catalog, binding=binding)
    # Prefer the narrowest diet incompatibility: meat > animal > non-vegan.
    wanted = (
        "meat" if diets.get("pescatarian") == "incompatible"
        else "animal" if diets.get("vegetarian") == "incompatible"
        else "non_vegan" if diets.get("vegan") == "incompatible"
        else ""
    )
    for profile in profiles:
        match = profile.get("match") if isinstance(profile.get("match"), dict) else {}
        if _text(match.get("dietHit")).lower().replace("-", "_") == wanted:
            return profile
    return profiles[0] if profiles else None


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
    term_match = bool(terms and any(_diet._contains_phrase(text, term) for term in terms))
    if term_match:
        required_hit = _text(profile.get("requireDietHit")).lower().replace("-", "_")
        required_index = {"meat": 0, "animal": 1, "non_vegan": 2}.get(required_hit)
        if required_hit and (required_index is None or not hits[required_index]):
            term_match = False
    if term_match:
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


def _candidate_source_profile(ingredient: dict[str, Any]) -> dict[str, Any] | None:
    """Choose the most specific matching profile for replacement candidates.

    Allergy triggers may aggregate across profiles, but candidate semantics must
    retain the catalog's specificity ordering. A concrete phrase such as
    "fish sauce", "egg white", or "chicken stock" therefore wins over generic
    animal/allergen fallbacks.
    """
    text = _diet._ingredient_text(ingredient)
    if not text:
        return None
    hits = _diet._diet_hits(text)
    allergen_hits = _ingredient_allergen_hits(ingredient)
    profiles = substitution_source_profiles(ingredient)
    if not profiles:
        return None

    best: dict[str, Any] | None = None
    best_score: tuple[int, int] = (-1, -1)
    for order, profile in enumerate(profiles):
        match = profile.get("match") if isinstance(profile.get("match"), dict) else {}
        matched_terms = [
            str(value)
            for value in match.get("terms") or []
            if str(value).strip() and _diet._contains_phrase(text, str(value))
        ]
        if matched_terms:
            specificity = max(len(_diet.normalize_text(value).split()) for value in matched_terms)
            score = (3, specificity)
        else:
            hit_name = _text(match.get("dietHit")).lower().replace("-", "_")
            hit_index = {"meat": 0, "animal": 1, "non_vegan": 2}.get(hit_name)
            if hit_index is not None and hits[hit_index]:
                score = (2, 0)
            else:
                allergen = _text(match.get("allergenHit")).lower().replace("-", "_").replace(" ", "_")
                score = (1, 0) if allergen and allergen in allergen_hits else (0, 0)
        # Strictly greater keeps catalog order as the deterministic tie-breaker.
        if score > best_score:
            best = profile
            best_score = score
    return best


def substitution_candidate_keys(ingredient: dict[str, Any]) -> list[str]:
    """Return reviewed candidates from the most specific matching source profile."""
    profile = _candidate_source_profile(ingredient)
    if not isinstance(profile, dict):
        return []
    return list(dict.fromkeys(
        str(value).strip()
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
    catalog = _catalog_with_payload_binding_concepts(
        load_substitution_catalog(), payload
    )
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
        binding = _catalog_binding(row, catalog)
        profiles = _catalog_source_profiles(row, catalog, binding=binding)
        candidate_profile = _catalog_candidate_profile(
            row, catalog, binding=binding
        )
        keys = list(dict.fromkeys(
            str(value).strip()
            for value in (
                candidate_profile.get("candidateKeys") if isinstance(candidate_profile, dict) else []
            )
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
        bound_diets = [
            str(value).strip().lower()
            for value in (binding or {}).get("substitutionDiets") or []
            if str(value).strip()
        ]
        explicit_diets = [
            diet for diet, state in _ingredient_diet_states(row).items()
            if state == "incompatible"
        ]
        row["substitutionDiets"] = list(dict.fromkeys(bound_diets or explicit_diets))
        if isinstance(binding, dict) and _text(binding.get("id")):
            row["substitutionBindingId"] = _text(binding.get("id"))
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
        "ingredientBindings": len([
            row for row in catalog.get("ingredientBindings") or []
            if isinstance(row, dict)
        ]),
        "providerBindingCatalogVersion": _text(
            catalog.get("providerBindingCatalogVersion")
        ),
        "conceptBindingCatalogVersion": _text(
            catalog.get("conceptBindingCatalogVersion")
        ),
        "expandedBindingConcepts": int(
            (catalog.get("_runtimeBindingConceptExpansion") or {}).get(
                "expandedConcepts"
            )
            or 0
        ),
        "ambiguousBindingConcepts": int(
            (catalog.get("_runtimeBindingConceptExpansion") or {}).get(
                "ambiguousConcepts"
            )
            or 0
        ),
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
