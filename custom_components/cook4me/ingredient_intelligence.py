from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Iterable

INTELLIGENCE_SCHEMA_VERSION = 1

COMPATIBLE = "compatible"
INCOMPATIBLE = "incompatible"
UNKNOWN = "unknown"

DIET_KEYS: tuple[str, ...] = (
    "omnivore",
    "pescatarian",
    "vegetarian",
    "vegan",
)

# Stable application categories, not a claim about any jurisdiction's legal list.
# Keeping a fixed bit assignment makes per-user filtering an integer-mask check.
ALLERGEN_KEYS: tuple[str, ...] = (
    "gluten",
    "milk",
    "lactose",
    "egg",
    "fish",
    "shellfish",
    "peanut",
    "tree_nut",
    "soy",
    "sesame",
    "celery",
    "mustard",
    "sulfites",
    "lupin",
)

_DIET_BIT = {key: 1 << index for index, key in enumerate(DIET_KEYS)}
_ALLERGEN_BIT = {key: 1 << index for index, key in enumerate(ALLERGEN_KEYS)}
_ALL_DIET_MASK = sum(_DIET_BIT.values())
_ALL_ALLERGEN_MASK = sum(_ALLERGEN_BIT.values())


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _key(value: Any) -> str:
    return _text(value).casefold().replace("-", "_").replace(" ", "_")


def normalize_state(value: Any) -> str:
    if value is True:
        return COMPATIBLE
    if value is False:
        return INCOMPATIBLE
    state = _key(value)
    if state in {COMPATIBLE, "safe", "allowed", "yes", "true"}:
        return COMPATIBLE
    if state in {INCOMPATIBLE, "unsafe", "blocked", "no", "false", "present"}:
        return INCOMPATIBLE
    return UNKNOWN


def normalize_allergen_state(value: Any) -> str:
    if value is True:
        return "present"
    if value is False:
        return "absent"
    state = _key(value)
    if state in {"present", "contains", "yes", "true", INCOMPATIBLE}:
        return "present"
    if state in {"absent", "free", "no", "false", COMPATIBLE}:
        return "absent"
    return UNKNOWN


def normalize_ingredient_profile(row: Any) -> dict[str, Any]:
    """Normalize only explicit evidence; missing facts remain unknown."""
    source = row if isinstance(row, dict) else {}
    concept_id = _text(
        source.get("conceptId") or source.get("ingredientId") or source.get("id")
    )
    diets_raw = source.get("diets") if isinstance(source.get("diets"), dict) else {}
    allergens_raw = (
        source.get("allergens")
        if isinstance(source.get("allergens"), dict)
        else {}
    )

    diets = {
        diet: (
            COMPATIBLE
            if diet == "omnivore" and diet not in diets_raw
            else normalize_state(diets_raw.get(diet))
        )
        for diet in DIET_KEYS
    }
    allergens = {
        allergen: normalize_allergen_state(allergens_raw.get(allergen))
        for allergen in ALLERGEN_KEYS
    }
    return {
        "schemaVersion": INTELLIGENCE_SCHEMA_VERSION,
        "conceptId": concept_id,
        "diets": diets,
        "allergens": allergens,
        "evidence": list(source.get("evidence") or []),
        "substitutionClass": _text(source.get("substitutionClass")),
    }


def compile_ingredient_masks(profile: Any) -> dict[str, int]:
    normalized = normalize_ingredient_profile(profile)
    diet_compatible = 0
    diet_incompatible = 0
    for key, state in normalized["diets"].items():
        if state == COMPATIBLE:
            diet_compatible |= _DIET_BIT[key]
        elif state == INCOMPATIBLE:
            diet_incompatible |= _DIET_BIT[key]

    allergen_present = 0
    allergen_absent = 0
    for key, state in normalized["allergens"].items():
        if state == "present":
            allergen_present |= _ALLERGEN_BIT[key]
        elif state == "absent":
            allergen_absent |= _ALLERGEN_BIT[key]

    return {
        "dietCompatibleMask": diet_compatible,
        "dietIncompatibleMask": diet_incompatible,
        "dietUnknownMask": _ALL_DIET_MASK
        & ~(diet_compatible | diet_incompatible),
        "allergenPresentMask": allergen_present,
        "allergenAbsentMask": allergen_absent,
        "allergenUnknownMask": _ALL_ALLERGEN_MASK
        & ~(allergen_present | allergen_absent),
    }


def compile_recipe_masks(
    ingredient_profiles: Iterable[Any],
) -> dict[str, int]:
    """Precompute recipe safety in one pass so user filtering is constant-cost."""
    profiles = [compile_ingredient_masks(row) for row in ingredient_profiles]
    if not profiles:
        return {
            "dietCompatibleMask": _DIET_BIT["omnivore"],
            "dietIncompatibleMask": 0,
            "dietUnknownMask": _ALL_DIET_MASK & ~_DIET_BIT["omnivore"],
            "allergenPresentMask": 0,
            "allergenAbsentMask": 0,
            "allergenUnknownMask": _ALL_ALLERGEN_MASK,
        }

    recipe_diet_compatible = 0
    recipe_diet_incompatible = 0
    recipe_diet_unknown = 0
    for diet, bit in _DIET_BIT.items():
        if any(row["dietIncompatibleMask"] & bit for row in profiles):
            recipe_diet_incompatible |= bit
        elif all(row["dietCompatibleMask"] & bit for row in profiles):
            recipe_diet_compatible |= bit
        else:
            recipe_diet_unknown |= bit

    allergen_present = 0
    allergen_unknown = 0
    for allergen, bit in _ALLERGEN_BIT.items():
        if any(row["allergenPresentMask"] & bit for row in profiles):
            allergen_present |= bit
        elif all(row["allergenAbsentMask"] & bit for row in profiles):
            pass
        else:
            allergen_unknown |= bit
    allergen_absent = _ALL_ALLERGEN_MASK & ~(
        allergen_present | allergen_unknown
    )

    return {
        "dietCompatibleMask": recipe_diet_compatible,
        "dietIncompatibleMask": recipe_diet_incompatible,
        "dietUnknownMask": recipe_diet_unknown,
        "allergenPresentMask": allergen_present,
        "allergenAbsentMask": allergen_absent,
        "allergenUnknownMask": allergen_unknown,
    }


def requested_allergen_mask(allergies: Iterable[Any]) -> int:
    mask = 0
    for value in allergies:
        key = _key(value)
        bit = _ALLERGEN_BIT.get(key)
        if bit:
            mask |= bit
    return mask


def evaluate_recipe_masks(
    masks: dict[str, Any],
    *,
    diet: Any = "omnivore",
    allergies: Iterable[Any] = (),
) -> dict[str, Any]:
    """Evaluate a user profile without inspecting recipe ingredients again."""
    diet_key = _key(diet) or "omnivore"
    diet_bit = _DIET_BIT.get(diet_key)
    diet_state = UNKNOWN
    if diet_bit is not None:
        if int(masks.get("dietIncompatibleMask") or 0) & diet_bit:
            diet_state = INCOMPATIBLE
        elif int(masks.get("dietCompatibleMask") or 0) & diet_bit:
            diet_state = COMPATIBLE

    requested = requested_allergen_mask(allergies)
    present = int(masks.get("allergenPresentMask") or 0) & requested
    unknown = int(masks.get("allergenUnknownMask") or 0) & requested
    if present:
        allergy_state = INCOMPATIBLE
    elif unknown:
        allergy_state = UNKNOWN
    else:
        allergy_state = COMPATIBLE

    overall = (
        INCOMPATIBLE
        if INCOMPATIBLE in {diet_state, allergy_state}
        else UNKNOWN
        if UNKNOWN in {diet_state, allergy_state}
        else COMPATIBLE
    )
    return {
        "state": overall,
        "diet": diet_key,
        "dietState": diet_state,
        "allergyState": allergy_state,
        "requestedAllergenMask": requested,
        "allergenPresentConflictMask": present,
        "allergenUnknownConflictMask": unknown,
        # Strict filtering deliberately excludes unknown allergy/diet evidence.
        "strictlyAllowed": overall == COMPATIBLE,
    }


def _confidence_rank(value: Any) -> int:
    return {
        "reviewed": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(_key(value), 0)


def normalize_substitution_edge(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    source = _text(row.get("fromConceptId") or row.get("sourceConceptId"))
    target = _text(row.get("toConceptId") or row.get("targetConceptId"))
    evidence = _text(row.get("evidence") or row.get("evidenceSource"))
    if not source or not target or not evidence or source == target:
        return None
    contexts = [
        _key(value)
        for value in row.get("contexts") or [row.get("context") or "general"]
        if _key(value)
    ]
    ratio = row.get("ratio") if isinstance(row.get("ratio"), dict) else {}
    return {
        "fromConceptId": source,
        "toConceptId": target,
        "contexts": tuple(dict.fromkeys(contexts or ["general"])),
        "ratio": {
            key: value
            for key, value in ratio.items()
            if key in {"from", "to", "unit"} and value not in (None, "")
        },
        "confidence": _key(row.get("confidence")) or "reviewed",
        "evidence": evidence,
        "notes": _text(row.get("notes")),
    }


def build_substitution_index(edges: Iterable[Any]) -> dict[str, tuple[dict[str, Any], ...]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for raw in edges:
        edge = normalize_substitution_edge(raw)
        if edge is None:
            continue
        identity = (
            edge["fromConceptId"],
            edge["toConceptId"],
            edge["contexts"],
        )
        if identity in seen:
            continue
        seen.add(identity)
        grouped[edge["fromConceptId"]].append(edge)
    return {
        source: tuple(
            sorted(
                rows,
                key=lambda row: (
                    -_confidence_rank(row["confidence"]),
                    row["toConceptId"],
                    row["contexts"],
                ),
            )
        )
        for source, rows in grouped.items()
    }


def suggest_substitutions(
    source_concept_id: str,
    *,
    context: Any = "general",
    diet: Any = "omnivore",
    allergies: Iterable[Any] = (),
    ingredient_profiles: dict[str, Any],
    substitution_index: dict[str, Iterable[dict[str, Any]]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Return only explicitly evidenced substitutions proven safe for the user.

    No lexical, nutritional or culinary similarity is used to invent edges.
    Unknown diet/allergy safety is intentionally excluded from suggestions.
    """
    source = _text(source_concept_id)
    wanted_context = _key(context) or "general"
    out: list[dict[str, Any]] = []
    for edge in substitution_index.get(source, ()):
        contexts = tuple(edge.get("contexts") or ())
        if wanted_context not in contexts and "general" not in contexts:
            continue
        target = _text(edge.get("toConceptId"))
        profile = ingredient_profiles.get(target)
        if not isinstance(profile, dict):
            continue
        masks = compile_recipe_masks([profile])
        safety = evaluate_recipe_masks(
            masks,
            diet=diet,
            allergies=allergies,
        )
        if not safety["strictlyAllowed"]:
            continue
        out.append(
            {
                **edge,
                "safety": safety,
            }
        )
        if len(out) >= max(1, int(limit)):
            break
    return out


def schema_descriptor() -> dict[str, Any]:
    return {
        "schemaVersion": INTELLIGENCE_SCHEMA_VERSION,
        "states": [COMPATIBLE, INCOMPATIBLE, UNKNOWN],
        "dietKeys": list(DIET_KEYS),
        "allergenKeys": list(ALLERGEN_KEYS),
        "dietBits": dict(_DIET_BIT),
        "allergenBits": dict(_ALLERGEN_BIT),
        "unknownIsSafe": False,
        "substitutionsRequireExplicitEvidence": True,
    }
