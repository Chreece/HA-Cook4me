#!/usr/bin/env python3
"""Classify Cook4Me release recipes by diet suitability and meal/dish type.

This stage is deliberately conservative. Provider recipe/ingredient IDs are
never changed by classification. Positive diet claims (especially ``vegan``)
require every food line to have usable semantic evidence; one unresolved or
ambiguous ingredient blocks that claim. Proven meat is sufficient to resolve a
recipe as omnivore even when an unrelated line is still unresolved.

Ingredient semantics prefer stable provider food IDs. Keyless lines may borrow
only a *semantic English label* from the SEB marketing-food dictionary when an
exact localized label match is unambiguous, or when every exact candidate has
the same canonical English meaning. This never promotes a missing provider ID.

SEB category/exclusion metadata is retained as audit evidence only. Live catalog
evidence proves those categories can be overbroad, so they do not establish a
diet class by themselves. Likewise, SEB VEGAN/VEGETARIAN occasion tags are
handled later as non-authoritative hints.

Meal type prefers SEB ``courses`` / ``occasions`` when present. A later v3
refinement distinguishes normal recipes from SEB ``IS_FOOD_COOKING`` ingredient
preparation entries and applies the small reviewed taxonomy-gap table.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import functools
import gzip
import json
import math
from pathlib import Path
import re
import unicodedata
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REVIEWED_FOOD_ENGLISH = ROOT / "tools" / "release_catalog_reviewed_provider_food_english.v2.json"
PROVIDER_KIND = "cook4me-provider-capture"
MARKETING_KIND = "cook4me-marketing-food-capture-v3"
_GLOBAL_LABELS = "__global__"

MEAL_TYPES = (
    "breakfast", "starter", "salad", "soup", "main", "side", "dessert", "snack",
)
_MEAL_ALIASES: dict[str, tuple[str, ...]] = {
    "breakfast": (
        "BREAKFAST", "BRUNCH", "FRUHSTUCK", "FRUEHSTUECK", "FRÜHSTÜCK",
        "PETIT DEJEUNER", "PETIT-DÉJEUNER", "DESAYUNO", "COLAZIONE",
        "CAFE DA MANHA", "CAFÉ DA MANHÃ", "PROINO", "ΠΡΩΙΝΟ",
    ),
    "starter": (
        "STARTER", "APPETIZER", "APPETISER", "ENTREE", "ENTRÉE", "VORSPEISE",
        "ENTRADA", "ANTIPASTO", "OREKTIKO", "ΟΡΕΚΤΙΚΟ",
    ),
    "salad": ("SALAD", "SALAT", "SALADE", "ENSALADA", "INSALATA", "SALATA", "ΣΑΛΑΤΑ"),
    "soup": ("SOUP", "SUPPE", "SOUPE", "SOPA", "ZUPPA", "SOUPA", "ΣΟΥΠΑ"),
    "main": (
        "MAIN", "MAIN COURSE", "MAIN_COURSE", "MAIN DISH", "MAIN_DISH",
        "HAUPTGERICHT", "PLAT PRINCIPAL", "PLATO PRINCIPAL", "SECONDO",
        "KYRIOS", "ΚΥΡΙΩΣ", "ΚΥΡΙΟ",
    ),
    "side": (
        "SIDE", "SIDE DISH", "SIDE_DISH", "BEILAGE", "ACCOMPANIMENT",
        "GUARNICION", "GUARNICIÓN", "CONTORNO", "SYNODEFTIKO", "ΣΥΝΟΔΕΥΤΙΚΟ",
    ),
    "dessert": ("DESSERT", "NACHSPEISE", "POSTRE", "DOLCE", "EPIDORPIO", "ΓΛΥΚΟ", "ΕΠΙΔΟΡΠΙΟ"),
    "snack": ("SNACK", "COLLATION", "MERIENDA", "SPUNTINO", "SNAK", "ΣΝΑΚ"),
}

# Flesh/animal ingredients that are neither vegetarian nor pescatarian.
_MEAT_TERMS = {
    "meat", "beef", "veal", "pork", "ham", "bacon", "pancetta", "prosciutto",
    "sausage", "chorizo", "salami", "chicken", "poultry", "turkey", "duck",
    "goose", "lamb", "mutton", "rabbit", "venison", "liver", "kidney", "offal",
    "lard", "gelatin", "gelatine", "poussin", "cockerel", "capon", "quail",
    "guinea fowl", "foie gras", "tripe", "black pudding", "white pudding",
    "bresaola", "mortadella", "merguez", "andouille", "andouillette", "chipolata",
    "frankfurt sausage", "coppa", "bone marrow", "demi glace", "demi-glace",
    "snail", "snails",
}
_FISH_TERMS = {
    "fish", "salmon", "tuna", "cod", "haddock", "trout", "mackerel", "sardine",
    "anchovy", "bonito", "roe", "tarako", "shrimp", "prawn", "crab", "lobster",
    "mussel", "clam", "oyster", "scallop", "squid", "octopus", "seafood", "eel",
    "halibut", "plaice", "pollock", "hake", "sole", "bream", "mullet", "monkfish",
    "flatfish", "swordfish", "cuttlefish", "skate", "pike", "ling", "yellowtail",
    "perch", "crayfish", "cockle", "calamari", "milkfish", "barramundi", "flounder",
    "fish sauce", "oyster sauce", "seafood stick", "worcester sauce", "worcestershire",
}
# Animal products allowed by vegetarian but not vegan diets. Include provider
# names that omit the literal word "cheese" (Parmesan, Gruyère, etc.).
_NONVEGAN_TERMS = {
    "milk", "cream", "butter", "cheese", "yogurt", "yoghurt", "egg", "eggs",
    "honey", "whey", "casein", "ghee", "parmesan", "emmental", "mozzarella",
    "feta", "mascarpone", "ricotta", "cheddar", "gruyere", "gorgonzola",
    "mimolette", "camembert", "roquefort", "morbier", "raclette", "comte",
    "reblochon", "beaufort", "tomme", "fromage frais", "goat s cheese",
    "goat s milk", "creme fraiche", "bechamel", "mayonnaise", "dulce de leche",
    "ice cream",
}
# Composite/prepared ingredients whose animal content cannot be safely inferred
# from the generic label. These block positive diet claims until reviewed.
_AMBIGUOUS_ANIMAL_ORIGIN_TERMS = {
    "stock", "stock cube", "broth", "bouillon", "consomme", "dashi", "dashida",
    "dressing", "gravy", "pesto", "kimchi", "quenelle", "ravioli", "spring roll",
    "dehydrated soup", "jelly", "curry paste", "barbecue sauce", "satay sauce",
    "spicy sauce", "chocolate", "praline", "margarine", "brioche", "biscuit",
    "shortbread", "madeleine", "puff pastry", "shortcrust pastry", "filo dough",
    "bread", "crouton", "tortilla", "tacos", "hot cake mix",
}
_EQUIPMENT_TERMS = {
    "mold", "mould", "ramekin", "foil", "aluminium", "aluminum", "parchment",
    "baking paper", "skewer", "toothpick", "twine", "kitchen string", "jar",
    "container",
}
_PLANT_QUALIFIERS = {
    "coconut", "coco", "almond", "soy", "soya", "hazelnut", "oat", "rice",
    "cashew", "peanut", "cocoa", "cacao", "chestnut", "vegetable", "vegan", "plant",
}
_AMOUNT_PREPOSITIONS = (
    "d'", "de ", "du ", "des ", "di ", "da ", "do ", "dos ", "das ",
    "del ", "della ", "of ",
)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


@functools.lru_cache(maxsize=32768)
def _label_norm(value: str) -> str:
    """Unicode-safe exact-label normalization; never discard non-Latin scripts."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", _text(value))).casefold()


@functools.lru_cache(maxsize=32768)
def _english_norm(value: str) -> str:
    """ASCII-ish normalization used only after text is known to be English."""
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _contains_english(text: str, term: str) -> bool:
    haystack = _english_norm(text).split()
    needle = _english_norm(term).split()
    if not haystack or not needle:
        return False
    if len(needle) == 1:
        return needle[0] in set(haystack)
    size = len(needle)
    return any(haystack[i : i + size] == needle for i in range(len(haystack) - size + 1))


def _hits(text: str, terms: set[str]) -> list[str]:
    return sorted(term for term in terms if _contains_english(text, term))


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


def _marketing_maps(
    marketing: dict[str, Any],
) -> tuple[dict[str, str], dict[str, dict[str, set[str]]]]:
    english: dict[str, str] = {}
    localized: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    global_labels: dict[str, set[str]] = defaultdict(set)
    for catalog in marketing.get("catalogs") or []:
        language = _text(catalog.get("language")).lower()
        for item in catalog.get("items") or []:
            if not isinstance(item, dict):
                continue
            key = _text(item.get("key"))
            name = _text(item.get("name"))
            if not key or not name:
                continue
            normalized = _label_norm(name)
            localized[language][normalized].add(key)
            global_labels[normalized].add(key)
            if language == "en":
                english[key] = name
    reviewed, _medium = _reviewed_food_english()
    for key, name in reviewed.items():
        english.setdefault(key, name)
    localized[_GLOBAL_LABELS] = global_labels
    return english, localized


def _quantity_forms(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    try:
        number = float(value)
    except (TypeError, ValueError):
        return []
    if not math.isfinite(number):
        return []
    if number.is_integer():
        return list(dict.fromkeys((str(int(number)), f"{number:.1f}", f"{number:.1f}".replace(".", ","))))
    compact = f"{number:g}"
    return list(dict.fromkeys((compact, compact.replace(".", ","))))


def semantic_ingredient_name(item: dict[str, Any]) -> tuple[str, bool]:
    """Recover a semantic keyless label using only preserved structured evidence."""
    source = ""
    for field in ("foodName", "applianceDescription", "applicationDescription", "cleanName"):
        source = _text(item.get(field))
        if source:
            break
    if not source:
        return "", False
    unit = item.get("unit") if isinstance(item.get("unit"), dict) else {}
    units = list(
        dict.fromkeys(
            _text(unit.get(field))
            for field in ("name", "pluralName", "abbreviation")
            if _text(unit.get(field))
        )
    )
    for quantity in sorted(_quantity_forms(item.get("quantity")), key=len, reverse=True):
        for unit_name in sorted(units, key=len, reverse=True):
            pattern = (
                rf"^\s*{re.escape(quantity)}\s*{re.escape(unit_name)}"
                rf"(?=\s|[-–—,:;]|$)\s*[-–—,:;]?\s*"
            )
            cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
            if cleaned != source and _text(cleaned):
                cleaned = _text(cleaned)
                lowered = cleaned.casefold()
                for prefix in _AMOUNT_PREPOSITIONS:
                    if lowered.startswith(prefix):
                        cleaned = cleaned[len(prefix) :].strip(" '\t")
                        break
                return _text(cleaned), True
        pattern = rf"^\s*{re.escape(quantity)}(?=\s)\s+"
        cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
        if cleaned != source and _text(cleaned):
            return _text(cleaned), True
    return source, False


def _single_semantic_name(keys: set[str], english: dict[str, str]) -> str:
    names = {_text(english.get(key)) for key in keys if _text(english.get(key))}
    return next(iter(names)) if len(names) == 1 else ""


def _ingredient_english(
    item: dict[str, Any],
    language: str,
    english: dict[str, str],
    localized: dict[str, dict[str, set[str]]],
) -> tuple[str, str, bool]:
    key = _text(item.get("foodKey"))
    if key:
        name = _text(english.get(key))
        return name, f"provider:{key}", bool(name)

    source, _cleaned = semantic_ingredient_name(item)
    if not source:
        return "", "empty-keyless", False
    normalized = _label_norm(source)
    candidates = set((localized.get(language) or {}).get(normalized, set()))
    name = _single_semantic_name(candidates, english)
    if name:
        return name, "keyless:exact-label-semantic:" + "|".join(sorted(candidates)), True

    # A recipe line can contain a foreign-language label. Cross-language exact
    # matching is safe only when every provider candidate has the same English
    # semantic name. Identity remains keyless.
    global_candidates = set((localized.get(_GLOBAL_LABELS) or {}).get(normalized, set()))
    name = _single_semantic_name(global_candidates, english)
    if name:
        return name, "keyless:global-exact-label-semantic:" + "|".join(sorted(global_candidates)), True

    if language == "en":
        return source, "keyless:english", True
    return "", f"keyless:unresolved:{source}", False


def _plant_qualified(tokens: list[str], index: int) -> bool:
    return index > 0 and tokens[index - 1] in _PLANT_QUALIFIERS


def _semantic_food_flags(name: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return meat, fish, non-vegan and ambiguous evidence for one English food."""
    normalized = _english_norm(name)
    meat_hits = _hits(normalized, _MEAT_TERMS)
    fish_hits = _hits(normalized, _FISH_TERMS)
    nonvegan_hits = _hits(normalized, _NONVEGAN_TERMS)
    ambiguous_hits = _hits(normalized, _AMBIGUOUS_ANIMAL_ORIGIN_TERMS)

    if "kidney bean" in normalized or "kidney beans" in normalized:
        meat_hits = [value for value in meat_hits if value != "kidney"]
    if "oyster mushroom" in normalized or "oyster mushrooms" in normalized:
        fish_hits = [value for value in fish_hits if value != "oyster"]
    if any(
        phrase in normalized
        for phrase in ("vegetarian sausage", "vegan sausage", "plant based sausage")
    ):
        meat_hits = [value for value in meat_hits if value != "sausage"]
        if "vegan sausage" not in normalized:
            ambiguous_hits.append("vegetarian sausage composition")

    tokens = normalized.split()
    for term in ("milk", "cream", "butter"):
        if term not in nonvegan_hits:
            continue
        indices = [index for index, token in enumerate(tokens) if token == term]
        # peanut/coconut/etc milk/cream/butter are plant ingredients; "butter
        # bean" is handled separately below.
        if indices and all(_plant_qualified(tokens, index) for index in indices):
            nonvegan_hits = [value for value in nonvegan_hits if value != term]
    if "butter bean" in normalized or "butter beans" in normalized:
        nonvegan_hits = [value for value in nonvegan_hits if value != "butter"]

    for generic in ("stock", "stock cube", "broth", "bouillon"):
        if generic not in ambiguous_hits:
            continue
        if any(
            phrase in normalized
            for phrase in (
                f"vegetable {generic}", f"vegetarian {generic}", f"vegan {generic}"
            )
        ):
            ambiguous_hits = [value for value in ambiguous_hits if value != generic]

    # Explicit animal stock already has stronger meat/fish evidence; the generic
    # stock ambiguity adds nothing and would otherwise prevent resolution.
    if meat_hits or fish_hits:
        ambiguous_hits = [
            value for value in ambiguous_hits
            if value not in {"stock", "stock cube", "broth", "bouillon"}
        ]

    return (
        sorted(set(meat_hits)), sorted(set(fish_hits)),
        sorted(set(nonvegan_hits)), sorted(set(ambiguous_hits)),
    )


def _provider_category_hints(detail: dict[str, Any]) -> list[str]:
    """Expose noisy provider exclusion/categories for audit, never as diet truth."""
    values: set[str] = set()
    for field in ("excludedFoods", "detectedExcludedFoods"):
        for raw in detail.get(field) or []:
            if isinstance(raw, dict):
                value = raw.get("key") or raw.get("name")
            else:
                value = raw
            if value:
                values.add(_text(value).upper())
    return sorted(values)


def classify_variant_diet(
    detail: dict[str, Any],
    english: dict[str, str],
    localized: dict[str, dict[str, set[str]]],
) -> dict[str, Any]:
    language = _text(detail.get("language")).lower()
    unresolved: list[str] = []
    equipment: list[str] = []
    meat_hits: list[str] = []
    fish_hits: list[str] = []
    nonvegan_hits: list[str] = []
    ambiguous_hits: list[str] = []

    ingredients = [item for item in detail.get("ingredients") or [] if isinstance(item, dict)]
    if not ingredients:
        unresolved.append("no-classifiable-food-ingredients")
    for item in ingredients:
        name, source, resolved = _ingredient_english(item, language, english, localized)
        if not resolved:
            unresolved.append(source)
            continue
        # Equipment is only ignored on keyless lines. A provider marketing-food
        # identity is always treated as a food ingredient.
        if not _text(item.get("foodKey")) and any(
            _contains_english(name, term) for term in _EQUIPMENT_TERMS
        ):
            equipment.append(name)
            continue
        meat, fish, nonvegan, ambiguous = _semantic_food_flags(name)
        meat_hits.extend(meat)
        fish_hits.extend(fish)
        nonvegan_hits.extend(nonvegan)
        ambiguous_hits.extend(ambiguous)
        # Free English prose can prove animal presence but cannot prove absence
        # for a permanent positive vegan/vegetarian claim.
        if source == "keyless:english":
            unresolved.append(f"keyless:english:{name}")

    has_meat = bool(meat_hits)
    has_fish = bool(fish_hits)
    has_nonvegan = bool(nonvegan_hits)
    blockers = sorted(
        set(unresolved + [f"ambiguous:{value}" for value in ambiguous_hits])
    )

    vegan: bool | None = False if (has_meat or has_fish or has_nonvegan) else None
    vegetarian: bool | None = False if (has_meat or has_fish) else None
    pescatarian: bool | None = False if has_meat else None
    primary: str | None = None

    if has_meat:
        primary = "omnivore"
        vegan = vegetarian = pescatarian = False
        status = "resolved"
    elif not blockers:
        if has_fish:
            primary = "pescatarian"
            vegan = vegetarian = False
            pescatarian = True
        elif has_nonvegan:
            primary = "vegetarian"
            vegan = False
            vegetarian = pescatarian = True
        else:
            primary = "vegan"
            vegan = vegetarian = pescatarian = True
        status = "resolved"
    else:
        status = "review_required"

    if primary == "vegan":
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif primary == "vegetarian":
        tags = ["vegetarian", "pescatarian"]
    elif primary == "pescatarian":
        tags = ["pescatarian"]
    elif primary == "omnivore":
        tags = ["omnivore"]
    else:
        tags = []

    return {
        "primaryDiet": primary,
        "dietTags": tags,
        "vegan": vegan,
        "vegetarian": vegetarian,
        "pescatarian": pescatarian,
        "status": status,
        "source": "normalized_provider_ingredients",
        "evidence": {
            "meat": sorted(set(meat_hits)),
            "fishSeafood": sorted(set(fish_hits)),
            "vegetarianAnimalProducts": sorted(set(nonvegan_hits)),
            "equipmentIgnored": sorted(set(equipment)),
            "unresolved": blockers,
            "providerCategoryHints": _provider_category_hints(detail),
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
        if any(_contains_english(text, alias) for alias in _MEAL_ALIASES[meal_type]):
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
    meal_types = (
        list(next(iter(meal_sets)))
        if all_meal_resolved and len(meal_sets) == 1
        else sorted({value for row in meals for value in row.get("mealTypes") or []})
    )
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
            "source": "normalized_provider_ingredients",
        },
        "mealTypes": meal_types,
        "primaryMealType": primary_meal,
        "mealTypeClassification": {
            "status": "resolved" if primary_meal or (all_meal_resolved and meal_types) else "review_required",
            "variantConsistent": bool(all_meal_resolved and len(meal_sets) == 1),
            "sources": sorted({row.get("source") for row in meals if row.get("source")}),
        },
    }
    unresolved_diet = sorted(
        {item for row in diets for item in (row.get("evidence") or {}).get("unresolved") or []}
    )
    if unresolved_diet:
        result["dietClassification"]["blockers"] = unresolved_diet[:80]
    category_hints = sorted(
        {item for row in diets for item in (row.get("evidence") or {}).get("providerCategoryHints") or []}
    )
    if category_hints:
        result["dietClassification"]["providerCategoryHints"] = category_hints
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
            detail.get("groupingFunctionalId") or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId") or detail.get("variantId")
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
        "mealTypeResolvedFromProvider": sum(row["mealTypeClassification"]["status"] == "resolved" for row in recipes),
        "mealTypeReviewRequired": sum(row["mealTypeClassification"]["status"] != "resolved" for row in recipes),
        "reviewQueue": len(review),
    }
    for meal in MEAL_TYPES:
        summary[f"mealType_{meal}"] = counts[f"mealType:{meal}"]

    payload = {
        "schemaVersion": 2,
        "kind": "cook4me-release-recipe-classification-v2",
        "policy": {
            "providerIdentityUnchanged": True,
            "dietPositiveClaimsRequireCompleteEvidence": True,
            "providerCategoryHintsAreAuditOnly": True,
            "providerCoursesOccasionsPreferred": True,
            "titleMealTypeInferenceRequiresReview": True,
            "keylessExactSemanticMatchDoesNotAssignProviderIdentity": True,
            "allowedPrimaryDiets": ["vegan", "vegetarian", "pescatarian", "omnivore"],
            "allowedMealTypes": list(MEAL_TYPES),
        },
        "summary": summary,
        "recipes": recipes,
    }
    review_payload = {
        "schemaVersion": 2,
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
