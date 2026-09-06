from __future__ import annotations

import re
import unicodedata
from typing import Any

_STAPLES = {
    "water", "wasser", "eau", "νερο", "νερό", "salt", "salz", "sel", "αλατι", "αλάτι",
    "pepper", "pfeffer", "poivre", "πιπερι", "πιπέρι", "oil", "ol", "öl", "oel",
    "olive oil", "olivenol", "olivenöl", "ελαιολαδο", "ελαιόλαδο",
}

_MEAT_WORDS = {
    "meat", "fleisch", "κρεας", "κρέας", "beef", "rind", "rindfleisch", "μοσχαρι", "μοσχάρι",
    "pork", "schwein", "schweinefleisch", "χοιρινο", "χοιρινό", "chicken", "huhn", "hahnchen",
    "hähnchen", "κοτοπουλο", "κοτόπουλο", "turkey", "pute", "truthahn", "γαλοπουλα", "γαλοπούλα",
    "lamb", "lamm", "αρνι", "αρνί", "ham", "schinken", "ζαμπον", "ζαμπόν", "bacon", "speck",
    "sausage", "wurst", "mettwurst", "λουκανικο", "λουκάνικο", "salami", "hackfleisch", "minced meat",
}

_FISH_WORDS = {
    "fish", "fisch", "ψαρι", "ψάρι", "salmon", "lachs", "σολομος", "σολομός", "tuna", "thunfisch",
    "τονος", "τόνος", "shrimp", "prawn", "garnele", "garnelen", "γαριδα", "γαρίδα", "γαριδες", "γαρίδες",
    "mussel", "muschel", "miesmuschel", "μυδι", "μύδι", "seafood", "meeresfruchte", "meeresfrüchte",
}

_ANIMAL_WORDS = _MEAT_WORDS | _FISH_WORDS

_NON_VEGAN_WORDS = _ANIMAL_WORDS | {
    "milk", "milch", "γαλα", "γάλα", "butter", "βουτυρο", "βούτυρο", "cheese", "kase", "käse", "τυρι", "τυρί",
    "parmesan", "parmesankase", "parmesankäse", "mascarpone", "cream", "sahne", "κρεμα", "κρέμα",
    "yogurt", "yoghurt", "joghurt", "γιαουρτι", "γιαούρτι", "egg", "eggs", "ei", "eier", "αυγο", "αυγό",
    "αυγα", "αυγά", "honey", "honig", "μελι", "μέλι", "gelatin", "gelatine", "ζελατινη", "ζελατίνη",
}

_PESCATARIAN_EXCLUSION_KEYS = {
    "MEAT", "BEEF", "PORK", "POULTRY", "CHICKEN", "TURKEY", "LAMB",
}
_VEGETARIAN_EXCLUSION_KEYS = _PESCATARIAN_EXCLUSION_KEYS | {
    "FISH", "SEAFOOD", "SHELLFISH",
}
_VEGAN_EXCLUSION_KEYS = _VEGETARIAN_EXCLUSION_KEYS | {
    "DAIRY", "CHEESE", "MILK", "EGG", "EGGS", "HONEY", "GELATIN",
}

_CATEGORY_KEY_ALIASES = {
    "dairy": {"DAIRY", "MILK", "CHEESE"}, "milk": {"DAIRY", "MILK"},
    "milch": {"DAIRY", "MILK"}, "milchprodukte": {"DAIRY", "MILK", "CHEESE"},
    "γαλα": {"DAIRY", "MILK"}, "γαλακτοκομικα": {"DAIRY", "MILK", "CHEESE"},
    "cheese": {"CHEESE", "DAIRY"}, "kase": {"CHEESE", "DAIRY"}, "τυρι": {"CHEESE", "DAIRY"},
    "egg": {"EGG", "EGGS"}, "eggs": {"EGG", "EGGS"}, "ei": {"EGG", "EGGS"}, "eier": {"EGG", "EGGS"},
    "αυγο": {"EGG", "EGGS"}, "αυγα": {"EGG", "EGGS"},
    "fish": {"FISH", "SEAFOOD", "SHELLFISH"}, "fisch": {"FISH", "SEAFOOD", "SHELLFISH"},
    "ψαρι": {"FISH", "SEAFOOD", "SHELLFISH"}, "seafood": {"SEAFOOD", "SHELLFISH", "FISH"},
    "meeresfruchte": {"SEAFOOD", "SHELLFISH", "FISH"},
    "nuts": {"NUT", "NUTS", "TREE_NUT", "TREE_NUTS", "PEANUT", "PEANUTS"},
    "nusse": {"NUT", "NUTS", "TREE_NUT", "TREE_NUTS", "PEANUT", "PEANUTS"},
    "alcohol": {"LIQUOR", "ALCOHOL"}, "alkohol": {"LIQUOR", "ALCOHOL"},
    "αλκοολ": {"LIQUOR", "ALCOHOL"},
    "gluten": {"GLUTEN"}, "glutenfrei": {"GLUTEN"},
    "lactose": {"LACTOSE", "DAIRY", "MILK"}, "laktose": {"LACTOSE", "DAIRY", "MILK"},
    "peanut": {"PEANUT", "PEANUTS"}, "peanuts": {"PEANUT", "PEANUTS"},
}

_CATEGORY_TEXT_ALIASES = {
    "dairy": {"milk", "cheese", "cream", "butter", "yogurt", "yoghurt", "mascarpone", "parmesan",
              "milch", "kase", "sahne", "butter", "joghurt", "mascarpone", "parmesan",
              "γαλα", "τυρι", "κρεμα", "βουτυρο", "γιαουρτι"},
    "milk": {"milk", "cream", "butter", "yogurt", "milch", "sahne", "joghurt", "γαλα", "κρεμα", "γιαουρτι"},
    "lactose": {"milk", "cream", "mascarpone", "milch", "sahne", "γαλα", "κρεμα"},
    "nuts": {"nut", "nuts", "peanut", "peanuts", "almond", "almonds", "hazelnut", "hazelnuts",
             "walnut", "walnuts", "cashew", "cashews", "pistachio", "pistachios",
             "nuss", "nusse", "erdnuss", "mandel", "haselnuss", "walnuss", "cashew", "pistazie"},
    "egg": {"egg", "eggs", "ei", "eier", "αυγο", "αυγα"},
    "fish": {"fish", "seafood", "salmon", "tuna", "shrimp", "prawn", "fisch", "meeresfruchte",
             "lachs", "thunfisch", "garnele", "ψαρι", "θαλασσινα", "σολομος", "τονος", "γαριδα"},
    "alcohol": {"alcohol", "wine", "beer", "liquor", "alkohol", "wein", "bier", "likor", "αλκοολ", "κρασι", "μπυρα"},
    "gluten": {"gluten", "wheat", "barley", "rye", "weizen", "gerste", "roggen", "σιταρι", "κριθαρι", "σικαλη"},
}
# Map common translated/category spellings to the same conservative text groups.
for _alias, _canonical in {
    "milchprodukte": "dairy", "γαλακτοκομικα": "dairy", "laktose": "lactose",
    "nusse": "nuts", "ξηροι καρποι": "nuts", "eier": "egg", "αυγο": "egg",
    "fisch": "fish", "ψαρι": "fish", "alkohol": "alcohol", "αλκοολ": "alcohol",
}.items():
    _CATEGORY_TEXT_ALIASES[_alias] = _CATEGORY_TEXT_ALIASES[_canonical]


def normalize_text(value: Any) -> str:
    """Normalize user/backend text for conservative local matching."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9α-ωάέήίόύώϊϋΐΰ]+", " ", text)
    return " ".join(text.split())


def _ingredient_text(item: Any) -> str:
    if isinstance(item, str):
        return normalize_text(item)
    if not isinstance(item, dict):
        return normalize_text(item)
    values: list[str] = []
    for key in ("name", "description", "applicationDescription", "applianceDescription"):
        if item.get(key):
            values.append(str(item[key]))
    food = item.get("food")
    if isinstance(food, dict):
        for key in ("name", "key"):
            if food.get(key):
                values.append(str(food[key]))
    elif food:
        values.append(str(food))
    return normalize_text(" ".join(values))


def recipe_ingredient_names(recipe: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in recipe.get("ingredients") or []:
        if isinstance(item, str):
            name = item.strip()
        elif isinstance(item, dict):
            name = str(
                item.get("name")
                or item.get("foodName")
                or item.get("applicationDescription")
                or item.get("applianceDescription")
                or item.get("description")
                or ""
            ).strip()
        else:
            name = str(item).strip()
        if name:
            names.append(name)
    return names


def _excluded_values(recipe: dict[str, Any]) -> tuple[set[str], str]:
    keys: set[str] = set()
    labels: list[str] = []
    for field in ("excludedFoods", "detectedExcludedFoods"):
        for item in recipe.get(field) or []:
            if isinstance(item, dict):
                key = item.get("key")
                name = item.get("name")
                if key:
                    keys.add(str(key).upper())
                    labels.append(str(key))
                if name:
                    labels.append(str(name))
            elif item:
                keys.add(str(item).upper())
                labels.append(str(item))
    return keys, normalize_text(" ".join(labels))


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match one normalized token exactly or a multi-token phrase by boundaries."""
    ntext = normalize_text(text)
    nphrase = normalize_text(phrase)
    if not ntext or not nphrase:
        return False
    text_tokens = ntext.split()
    phrase_tokens = nphrase.split()
    if len(phrase_tokens) == 1:
        return phrase_tokens[0] in set(text_tokens)
    width = len(phrase_tokens)
    return any(text_tokens[i : i + width] == phrase_tokens for i in range(len(text_tokens) - width + 1))


def dietary_flags(recipe: dict[str, Any]) -> dict[str, Any]:
    texts = [_ingredient_text(x) for x in recipe.get("ingredients") or []]
    joined = " | ".join(texts)
    exclusion_keys, _ = _excluded_values(recipe)

    meat_hits = sorted(word for word in _MEAT_WORDS if _contains_phrase(joined, word))
    animal_hits = sorted(word for word in _ANIMAL_WORDS if _contains_phrase(joined, word))
    non_vegan_hits = sorted(word for word in _NON_VEGAN_WORDS if _contains_phrase(joined, word))
    pesc_exclusion_hits = sorted(exclusion_keys & _PESCATARIAN_EXCLUSION_KEYS)
    veg_exclusion_hits = sorted(exclusion_keys & _VEGETARIAN_EXCLUSION_KEYS)
    vegan_exclusion_hits = sorted(exclusion_keys & _VEGAN_EXCLUSION_KEYS)

    pescatarian = not meat_hits and not pesc_exclusion_hits
    vegetarian = not animal_hits and not veg_exclusion_hits
    vegan = vegetarian and not non_vegan_hits and not vegan_exclusion_hits
    return {
        "pescatarian": pescatarian,
        "vegetarian": vegetarian,
        "vegan": vegan,
        "meatIngredientHits": meat_hits,
        "animalIngredientHits": animal_hits,
        "nonVeganIngredientHits": non_vegan_hits,
        "exclusionKeys": sorted(exclusion_keys),
        "inference": "ingredient_text_and_backend_exclusions",
    }


def _matches_term(text: str, term: str) -> bool:
    if _contains_phrase(text, term):
        return True
    aliases = _CATEGORY_TEXT_ALIASES.get(normalize_text(term), set())
    return any(_contains_phrase(text, candidate) for candidate in aliases)


def _matches_exclusion_key(term: str, exclusion_keys: set[str]) -> bool:
    aliases = _CATEGORY_KEY_ALIASES.get(normalize_text(term), set())
    return bool(aliases & exclusion_keys)


def score_recipe(recipe: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Score one recipe against explicit pantry/diet restrictions.

    Diet/allergy exclusions are hard gates; pantry matching is a ranking signal.
    The result explicitly labels locally inferred decisions.
    """
    diet = str(profile.get("diet") or "omnivore").lower()
    allergies = [str(x) for x in profile.get("allergies") or [] if str(x).strip()]
    avoid = [str(x) for x in profile.get("avoid") or [] if str(x).strip()]
    pantry = [str(x) for x in profile.get("pantry") or [] if str(x).strip()]
    preferences = [str(x) for x in profile.get("preferences") or [] if str(x).strip()]
    habit_terms = [str(x) for x in profile.get("habitTerms") or [] if str(x).strip()]

    ingredients = recipe.get("ingredients") or []
    ingredient_names = recipe_ingredient_names(recipe)
    ingredient_texts = [_ingredient_text(item) for item in ingredients]
    all_text = " | ".join(ingredient_texts)
    exclusion_keys, exclusion_text = _excluded_values(recipe)
    safety_text = " | ".join(x for x in (all_text, exclusion_text) if x)
    flags = dietary_flags(recipe)

    violations: list[str] = []
    if diet == "pescatarian" and not flags["pescatarian"]:
        violations.append("diet:pescatarian")
    elif diet == "vegetarian" and not flags["vegetarian"]:
        violations.append("diet:vegetarian")
    elif diet == "vegan" and not flags["vegan"]:
        violations.append("diet:vegan")

    for term in allergies:
        if _matches_term(safety_text, term) or _matches_exclusion_key(term, exclusion_keys):
            violations.append(f"allergy:{term}")
    for term in avoid:
        if _matches_term(safety_text, term) or _matches_exclusion_key(term, exclusion_keys):
            violations.append(f"avoid:{term}")

    pantry_norm = [normalize_text(x) for x in pantry if normalize_text(x)]
    staple_norm = {normalize_text(x) for x in _STAPLES if normalize_text(x)}
    matched: list[str] = []
    missing: list[str] = []
    relevant = 0
    for original, text in zip(ingredient_names, ingredient_texts, strict=False):
        if not text:
            continue
        # The normalized ingredient/food name is safer than free-form descriptions
        # for staples (e.g. "Wasser" with quantity text should still be a staple).
        if normalize_text(original) in staple_norm:
            continue
        relevant += 1
        if any(_contains_phrase(text, p) or _contains_phrase(p, text) for p in pantry_norm):
            matched.append(original)
        else:
            missing.append(original)

    coverage = 1.0 if relevant == 0 else len(matched) / relevant
    title_text = normalize_text(recipe.get("title"))
    preference_hits = [p for p in preferences if _matches_term(title_text + " | " + all_text, p)]
    habit_hits = [p for p in habit_terms if _matches_term(title_text + " | " + all_text, p)]
    preference_bonus = min(0.15, 0.03 * len(preference_hits))
    habit_bonus = min(0.10, 0.02 * len(habit_hits))
    safe = not violations
    score = (coverage + preference_bonus + habit_bonus) * 100 if safe else -1000

    return {
        "safe": safe,
        "score": round(score, 1),
        "pantryCoverage": round(coverage, 3),
        "matchedIngredients": matched,
        "missingIngredients": missing,
        "violations": violations,
        "preferenceHits": preference_hits,
        "habitHits": habit_hits,
        "dietary": flags,
        "backendExclusionKeys": sorted(exclusion_keys),
        "decisionSource": "explicit_profile_plus_local_ingredient_and_backend_exclusion_matching",
    }


def normalize_manual_recipe(recipe: dict[str, Any], *, source: str = "manual") -> dict[str, Any]:
    title = str(recipe.get("title") or "").strip()
    if not title:
        raise ValueError("Recipe title is required")

    ingredients: list[dict[str, Any]] = []
    for item in recipe.get("ingredients") or []:
        if isinstance(item, str):
            name = item.strip()
            if name:
                ingredients.append({"name": name})
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("description") or "").strip()
            if name:
                normalized = {"name": name}
                for key in ("quantity", "unit"):
                    if item.get(key) not in (None, ""):
                        normalized[key] = item.get(key)
                ingredients.append(normalized)

    steps: list[dict[str, Any]] = []
    for idx, item in enumerate(recipe.get("steps") or []):
        if isinstance(item, str):
            instruction = item.strip()
            obj = {"instruction": instruction} if instruction else None
        elif isinstance(item, dict):
            instruction = str(item.get("instruction") or item.get("text") or "").strip()
            obj = {"instruction": instruction} if instruction else None
            if obj and item.get("type"):
                obj["type"] = str(item["type"])
        else:
            obj = None
        if obj:
            obj["stepIndex"] = idx
            steps.append(obj)

    if not ingredients:
        raise ValueError("At least one ingredient is required")
    if not steps:
        raise ValueError("At least one step is required")

    servings = recipe.get("servings")
    try:
        servings = float(servings) if servings not in (None, "") else None
    except (TypeError, ValueError):
        servings = None

    return {
        "source": source if source in {"manual", "ai"} else "manual",
        "title": title,
        "servings": servings,
        "ingredients": ingredients,
        "steps": steps,
        "notes": str(recipe.get("notes") or "").strip(),
        "tags": [str(x).strip() for x in recipe.get("tags") or [] if str(x).strip()],
        "sendable": False,
        "sendRestriction": "Custom/AI recipes have no proven SEB cloud recipe IDs and cannot be pushed to this Wi-Fi Cook4Me.",
    }
