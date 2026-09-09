#!/usr/bin/env python3
"""Classify Cook4Me release recipes by diet suitability and meal/dish type.

This stage is deliberately conservative. It consumes the reviewed provider v2
capture plus the APK-exact marketing-food v3 dictionaries and writes derived
classification metadata for the immutable release catalog. Provider recipe and
ingredient IDs are never changed by classification.

Diet suitability is derived from normalized/canonical ingredient evidence. A
negative claim such as ``vegan`` is emitted only when every ingredient line is
accounted for and no ambiguous animal-origin composite remains. Known meat is
enough to resolve ``omnivore`` immediately. Keyless/untranslated ingredients
remain explicit blockers rather than being guessed.

Meal type prefers SEB's provider taxonomy (``courses`` / ``occasions``) when it
is present. The older reviewed provider v2 capture predates retention of those
fields, so title-based matches are provisional/review-required for that capture.
Future crawls should retain provider taxonomy and then classify it as resolved.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
import re
import unicodedata
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REVIEWED_FOOD_ENGLISH = ROOT / "tools" / "release_catalog_reviewed_provider_food_english.v2.json"
PROVIDER_KIND = "cook4me-provider-capture"
MARKETING_KIND = "cook4me-marketing-food-capture-v3"

MEAL_TYPES = (
    "breakfast",
    "starter",
    "salad",
    "soup",
    "main",
    "side",
    "dessert",
    "snack",
)

_MEAL_ALIASES: dict[str, tuple[str, ...]] = {
    "breakfast": (
        "BREAKFAST", "BRUNCH", "FRUHSTUCK", "FRUEHSTUECK", "FRÜHSTÜCK",
        "PETIT DEJEUNER", "PETIT-DÉJEUNER", "DESAYUNO", "COLAZIONE",
        "CAFE DA MANHA", "CAFÉ DA MANHÃ", "PROINO", "ΠΡΩΙΝΟ",
    ),
    "starter": (
        "STARTER", "APPETIZER", "APPETISER", "ENTREE", "ENTRÉE",
        "VORSPEISE", "ENTRADA", "ANTIPASTO", "OREKTIKO", "ΟΡΕΚΤΙΚΟ",
    ),
    "salad": (
        "SALAD", "SALAT", "SALADE", "ENSALADA", "INSALATA", "SALATA",
        "ΣΑΛΑΤΑ",
    ),
    "soup": (
        "SOUP", "SUPPE", "SOUPE", "SOPA", "ZUPPA", "SOUPA", "ΣΟΥΠΑ",
    ),
    "main": (
        "MAIN", "MAIN COURSE", "MAIN_COURSE", "MAIN DISH", "MAIN_DISH",
        "HAUPTGERICHT", "PLAT PRINCIPAL", "PLATO PRINCIPAL", "SECONDO",
        "KYRIOS", "ΚΥΡΙΩΣ", "ΚΥΡΙΟ",
    ),
    "side": (
        "SIDE", "SIDE DISH", "SIDE_DISH", "BEILAGE", "ACCOMPANIMENT",
        "GUARNICION", "GUARNICIÓN", "CONTORNO", "SYNODEFTIKO",
        "ΣΥΝΟΔΕΥΤΙΚΟ",
    ),
    "dessert": (
        "DESSERT", "NACHSPEISE", "POSTRE", "DOLCE", "EPIDORPIO",
        "ΓΛΥΚΟ", "ΕΠΙΔΟΡΠΙΟ",
    ),
    "snack": (
        "SNACK", "COLLATION", "MERIENDA", "SPUNTINO", "SNAK", "ΣΝΑΚ",
    ),
}

_MEAT_TERMS = {
    "meat", "beef", "veal", "pork", "ham", "bacon", "pancetta",
    "prosciutto", "sausage", "chorizo", "salami", "chicken", "turkey",
    "duck", "goose", "lamb", "mutton", "rabbit", "venison", "liver",
    "kidney", "offal", "lard", "gelatin", "gelatine",
}
_FISH_TERMS = {
    "fish", "salmon", "tuna", "cod", "haddock", "trout", "mackerel",
    "sardine", "anchovy", "bonito", "roe", "tarako", "shrimp", "prawn",
    "crab", "lobster", "mussel", "clam", "oyster", "scallop", "squid",
    "octopus", "seafood", "eel", "halibut", "plaice", "pollock", "hake",
    "sole", "bream", "mullet", "monkfish", "flatfish",
}
_VEGETARIAN_ANIMAL_TERMS = {
    "milk", "cream", "butter", "cheese", "yogurt", "yoghurt", "egg",
    "eggs", "honey", "whey", "casein", "ghee",
}
# Composite ingredients that can materially change diet suitability and cannot
# safely be treated as plant-only from a generic label.
_AMBIGUOUS_ANIMAL_ORIGIN_TERMS = {
    "stock", "broth", "bouillon", "consomme", "dashi", "dashida",
    "dressing", "gravy", "worcestershire", "pesto", "kimchi",
}
_EQUIPMENT_TERMS = {
    "mold", "mould", "ramekin", "foil", "aluminium", "aluminum",
    "parchment", "baking paper", "skewer", "toothpick", "twine",
    "kitchen string", "jar", "container",
}

_MEAT_EXCLUSION_KEYS = {
    "MEAT", "BEEF", "PORK", "POULTRY", "CHICKEN", "TURKEY", "LAMB",
}
_FISH_EXCLUSION_KEYS = {"FISH", "SEAFOOD", "SHELLFISH"}
_NONVEGAN_EXCLUSION_KEYS = {
    "DAIRY", "CHEESE", "MILK", "EGG", "EGGS", "HONEY",
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _contains(text: str, term: str) -> bool:
    haystack = _norm(text).split()
    needle = _norm(term).split()
    if not haystack or not needle:
        return False
    if len(needle) == 1:
        return needle[0] in set(haystack)
    size = len(needle)
    return any(haystack[i : i + size] == needle for i in range(len(haystack) - size + 1))


def _hits(text: str, terms: set[str]) -> list[str]:
    return sorted(term for term in terms if _contains(text, term))


def _load_payload(path: Path, expected_kind: str) -> dict[str, Any]:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if expected_kind == PROVIDER_KIND and name.endswith("provider-capture-v2.json.gz"):
                    value = json.loads(gzip.decompress(archive.read(name)))
                    break
                if expected_kind == MARKETING_KIND and name.endswith("marketing-foods-v3.json"):
                    value = json.loads(archive.read(name))
                    break
            else:
                raise RuntimeError(f"{path}: expected {expected_kind} payload not found")
    elif path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("kind") != expected_kind:
        raise RuntimeError(f"{path}: expected {expected_kind}")
    return value


def _reviewed_food_english() -> tuple[dict[str, str], set[str]]:
    value = json.loads(REVIEWED_FOOD_ENGLISH.read_text(encoding="utf-8"))
    items = value.get("items") if isinstance(value, dict) else {}
    names: dict[str, str] = {}
    medium: set[str] = set()
    for key, row in (items or {}).items():
        if not isinstance(row, dict):
            continue
        name = _text(row.get("english"))
        if name:
            names[str(key)] = name
        if row.get("confidence") == "medium":
            medium.add(str(key))
    return names, medium


def _marketing_maps(marketing: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, set[str]]]]:
    english: dict[str, str] = {}
    localized: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for catalog in marketing.get("catalogs") or []:
        language = _text(catalog.get("language")).lower()
        for item in catalog.get("items") or []:
            if not isinstance(item, dict):
                continue
            key = _text(item.get("key"))
            name = _text(item.get("name"))
            if not key or not name:
                continue
            localized[language][_norm(name)].add(key)
            if language == "en":
                english[key] = name
    reviewed, _medium = _reviewed_food_english()
    for key, name in reviewed.items():
        english.setdefault(key, name)
    return english, localized


def _semantic_name(item: dict[str, Any]) -> str:
    for field in ("foodName", "applianceDescription", "applicationDescription", "cleanName"):
        value = _text(item.get(field))
        if value:
            return value
    return ""


def _ingredient_english(
    item: dict[str, Any],
    language: str,
    english: dict[str, str],
    localized: dict[str, dict[str, set[str]]],
) -> tuple[str, str, bool]:
    key = _text(item.get("foodKey"))
    if key:
        name = english.get(key, "")
        return name, f"provider:{key}", bool(name)

    source = _semantic_name(item)
    if not source:
        return "", "empty-keyless", False
    if language == "en":
        return source, "keyless:english", True
    candidates = localized.get(language, {}).get(_norm(source), set())
    if len(candidates) == 1:
        candidate = next(iter(candidates))
        name = english.get(candidate, "")
        if name:
            return name, f"keyless:exact-label-candidate:{candidate}", True
    return "", f"keyless:unresolved:{source}", False


def _excluded_keys(detail: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for field in ("excludedFoods", "detectedExcludedFoods"):
        for raw in detail.get(field) or []:
            if isinstance(raw, dict):
                value = raw.get("key") or raw.get("name")
            else:
                value = raw
            if value:
                out.add(_text(value).upper())
    return out


def classify_variant_diet(
    detail: dict[str, Any],
    english: dict[str, str],
    localized: dict[str, dict[str, set[str]]],
) -> dict[str, Any]:
    language = _text(detail.get("language")).lower()
    ingredient_names: list[str] = []
    unresolved: list[str] = []
    evidence_sources: list[str] = []
    equipment: list[str] = []
    for item in detail.get("ingredients") or []:
        if not isinstance(item, dict):
            continue
        name, source, resolved = _ingredient_english(item, language, english, localized)
        if not resolved:
            unresolved.append(source)
            continue
        if any(_contains(name, term) for term in _EQUIPMENT_TERMS):
            equipment.append(name)
            continue
        ingredient_names.append(name)
        evidence_sources.append(source)

    joined = " | ".join(ingredient_names)
    meat_hits = _hits(joined, _MEAT_TERMS)
    fish_hits = _hits(joined, _FISH_TERMS)
    vegetarian_animal_hits = _hits(joined, _VEGETARIAN_ANIMAL_TERMS)
    ambiguous_hits = _hits(joined, _AMBIGUOUS_ANIMAL_ORIGIN_TERMS)
    exclusion_keys = _excluded_keys(detail)
    meat_key_hits = sorted(exclusion_keys & _MEAT_EXCLUSION_KEYS)
    fish_key_hits = sorted(exclusion_keys & _FISH_EXCLUSION_KEYS)
    nonvegan_key_hits = sorted(exclusion_keys & _NONVEGAN_EXCLUSION_KEYS)

    has_meat = bool(meat_hits or meat_key_hits)
    has_fish = bool(fish_hits or fish_key_hits)
    has_nonvegan = bool(vegetarian_animal_hits or nonvegan_key_hits)
    blockers = list(unresolved)
    blockers.extend(f"ambiguous:{value}" for value in ambiguous_hits)

    # Positive animal evidence makes the corresponding negative suitability
    # false even when some other ingredient remains unresolved.
    vegan: bool | None = False if (has_meat or has_fish or has_nonvegan) else None
    vegetarian: bool | None = False if (has_meat or has_fish) else None
    pescatarian: bool | None = False if has_meat else None
    primary: str | None = None

    if has_meat:
        primary = "omnivore"
        vegan = False
        vegetarian = False
        pescatarian = False
        status = "resolved"
    elif not blockers:
        if has_fish:
            primary = "pescatarian"
            vegan = False
            vegetarian = False
            pescatarian = True
        elif has_nonvegan:
            primary = "vegetarian"
            vegan = False
            vegetarian = True
            pescatarian = True
        else:
            primary = "vegan"
            vegan = vegetarian = pescatarian = True
        status = "resolved"
    else:
        status = "review_required"

    tags: list[str] = []
    for key, value in (("vegan", vegan), ("vegetarian", vegetarian), ("pescatarian", pescatarian)):
        if value is True:
            tags.append(key)
    if primary == "omnivore":
        tags = ["omnivore"]

    return {
        "primaryDiet": primary,
        "dietTags": tags,
        "vegan": vegan,
        "vegetarian": vegetarian,
        "pescatarian": pescatarian,
        "status": status,
        "source": "normalized_provider_ingredients",
        "evidence": {
            "meat": sorted(set(meat_hits + meat_key_hits)),
            "fishSeafood": sorted(set(fish_hits + fish_key_hits)),
            "vegetarianAnimalProducts": sorted(set(vegetarian_animal_hits + nonvegan_key_hits)),
            "equipmentIgnored": sorted(set(equipment)),
            "unresolved": sorted(set(blockers)),
        },
    }


def _taxonomy_strings(detail: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for field in ("courses", "occasions"):
        for raw in detail.get(field) or []:
            if isinstance(raw, dict):
                for key in ("key", "name"):
                    value = _text(raw.get(key))
                    if value:
                        out.append(value)
            elif raw:
                out.append(_text(raw))
    return out


def _meal_matches(values: list[str]) -> list[str]:
    text = " | ".join(values)
    matched: list[str] = []
    for meal_type in MEAL_TYPES:
        if any(_contains(text, alias) for alias in _MEAL_ALIASES[meal_type]):
            matched.append(meal_type)
    return matched


def classify_variant_meal(detail: dict[str, Any]) -> dict[str, Any]:
    provider_values = _taxonomy_strings(detail)
    provider_matches = _meal_matches(provider_values)
    if provider_matches:
        return {
            "mealTypes": provider_matches,
            "primaryMealType": provider_matches[0] if len(provider_matches) == 1 else None,
            "status": "resolved",
            "source": "seb_courses_occasions",
            "providerTaxonomy": provider_values,
        }

    title = _text(detail.get("title") or detail.get("normalizedTitle"))
    title_matches = _meal_matches([title]) if title else []
    return {
        "mealTypes": title_matches,
        "primaryMealType": title_matches[0] if len(title_matches) == 1 else None,
        "status": "review_required",
        "source": "title_keyword_provisional" if title_matches else "missing_provider_taxonomy",
        "providerTaxonomy": provider_values,
    }


def _aggregate_group(grouping_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    diets = [row["diet"] for row in rows]
    meals = [row["meal"] for row in rows]
    diet_values = {row.get("primaryDiet") for row in diets}
    all_diet_resolved = all(row.get("status") == "resolved" for row in diets)
    primary_diet = next(iter(diet_values)) if all_diet_resolved and len(diet_values) == 1 else None
    if primary_diet == "vegan":
        diet_tags = ["vegan", "vegetarian", "pescatarian"]
    elif primary_diet == "vegetarian":
        diet_tags = ["vegetarian", "pescatarian"]
    elif primary_diet == "pescatarian":
        diet_tags = ["pescatarian"]
    elif primary_diet == "omnivore":
        diet_tags = ["omnivore"]
    else:
        diet_tags = []

    meal_sets = {tuple(row.get("mealTypes") or []) for row in meals}
    all_meal_resolved = all(row.get("status") == "resolved" for row in meals)
    meal_types = list(next(iter(meal_sets))) if all_meal_resolved and len(meal_sets) == 1 else sorted({x for row in meals for x in row.get("mealTypes") or []})
    primary_meal = meal_types[0] if all_meal_resolved and len(meal_types) == 1 else None

    sample = rows[0]["detail"]
    result = {
        "groupingFunctionalId": grouping_id,
        "language": _text(sample.get("language")).lower(),
        "market": _text(sample.get("market")),
        "title": _text(sample.get("title")),
        "primaryDiet": primary_diet,
        "dietTags": diet_tags,
        "dietClassification": {
            "status": "resolved" if primary_diet else "review_required",
            "variantConsistent": bool(all_diet_resolved and len(diet_values) == 1),
        },
        "mealTypes": meal_types,
        "primaryMealType": primary_meal,
        "mealTypeClassification": {
            "status": "resolved" if primary_meal or (all_meal_resolved and meal_types) else "review_required",
            "variantConsistent": bool(all_meal_resolved and len(meal_sets) == 1),
            "sources": sorted({row.get("source") for row in meals if row.get("source")}),
        },
    }
    unresolved_diet = sorted({item for row in diets for item in (row.get("evidence") or {}).get("unresolved") or []})
    if unresolved_diet:
        result["dietClassification"]["blockers"] = unresolved_diet[:40]
    provider_taxonomy = sorted({item for row in meals for item in row.get("providerTaxonomy") or []})
    if provider_taxonomy:
        result["providerCoursesOccasions"] = provider_taxonomy
    if len(rows) > 1 and (len(diet_values) > 1 or len(meal_sets) > 1):
        result["variantClassificationEvidence"] = [
            {
                "variantId": row["variantId"],
                "primaryDiet": row["diet"].get("primaryDiet"),
                "dietStatus": row["diet"].get("status"),
                "mealTypes": row["meal"].get("mealTypes") or [],
                "mealStatus": row["meal"].get("status"),
            }
            for row in rows
        ]
    return result


def classify(provider: dict[str, Any], marketing: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    english, localized = _marketing_maps(marketing)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detail in provider.get("details") or []:
        grouping_id = _text(
            detail.get("groupingFunctionalId")
            or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId")
            or detail.get("variantId")
        )
        if not grouping_id:
            continue
        grouped[grouping_id].append(
            {
                "variantId": _text(detail.get("variantId")),
                "detail": detail,
                "diet": classify_variant_diet(detail, english, localized),
                "meal": classify_variant_meal(detail),
            }
        )

    recipes = [_aggregate_group(key, grouped[key]) for key in sorted(grouped)]
    review = [
        {
            "groupingFunctionalId": row["groupingFunctionalId"],
            "language": row["language"],
            "title": row["title"],
            "needsDietReview": row["dietClassification"]["status"] != "resolved",
            "needsMealTypeReview": row["mealTypeClassification"]["status"] != "resolved",
            "provisionalDiet": row.get("primaryDiet"),
            "provisionalMealTypes": row.get("mealTypes") or [],
            "dietBlockers": row.get("dietClassification", {}).get("blockers") or [],
        }
        for row in recipes
        if row["dietClassification"]["status"] != "resolved"
        or row["mealTypeClassification"]["status"] != "resolved"
    ]
    counts = defaultdict(int)
    for row in recipes:
        counts[f"diet:{row.get('primaryDiet') or 'review_required'}"] += 1
        counts[f"meal:{row['mealTypeClassification']['status']}"] += 1
        for meal in row.get("mealTypes") or []:
            counts[f"mealType:{meal}"] += 1

    summary = {
        "recipeGroups": len(recipes),
        "dietResolved": sum(row["dietClassification"]["status"] == "resolved" for row in recipes),
        "dietReviewRequired": sum(row["dietClassification"]["status"] != "resolved" for row in recipes),
        "vegan": counts["diet:vegan"],
        "vegetarian": counts["diet:vegetarian"],
        "pescatarian": counts["diet:pescatarian"],
        "omnivore": counts["diet:omnivore"],
        "mealTypeResolvedFromProvider": sum(
            row["mealTypeClassification"]["status"] == "resolved" for row in recipes
        ),
        "mealTypeReviewRequired": sum(
            row["mealTypeClassification"]["status"] != "resolved" for row in recipes
        ),
        "reviewQueue": len(review),
    }
    for meal in MEAL_TYPES:
        summary[f"mealType_{meal}"] = counts[f"mealType:{meal}"]

    payload = {
        "schemaVersion": 1,
        "kind": "cook4me-release-recipe-classification-v2",
        "policy": {
            "providerIdentityUnchanged": True,
            "dietNegativeClaimsRequireCompleteEvidence": True,
            "providerCoursesOccasionsPreferred": True,
            "titleMealTypeInferenceRequiresReview": True,
            "allowedPrimaryDiets": ["vegan", "vegetarian", "pescatarian", "omnivore"],
            "allowedMealTypes": list(MEAL_TYPES),
        },
        "summary": summary,
        "recipes": recipes,
    }
    review_payload = {
        "schemaVersion": 1,
        "kind": "cook4me-release-recipe-classification-review-v2",
        "summary": {"items": len(review)},
        "items": review,
    }
    return payload, review_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-capture", required=True)
    parser.add_argument("--marketing-foods", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    provider = _load_payload(Path(args.provider_capture).expanduser(), PROVIDER_KIND)
    marketing = _load_payload(Path(args.marketing_foods).expanduser(), MARKETING_KIND)
    payload, review = classify(provider, marketing)
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    Path(args.review).expanduser().write_text(
        json.dumps(review, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    Path(args.summary).expanduser().write_text(
        json.dumps(payload["summary"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
