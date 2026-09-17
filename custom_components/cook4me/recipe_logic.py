from __future__ import annotations

import re
import json
import unicodedata
from functools import lru_cache
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
    "τονος", "τόνος", "shrimp", "shrimps", "prawn", "prawns", "garnele", "garnelen", "γαριδα", "γαρίδα", "γαριδες", "γαρίδες",
    "mussel", "mussels", "muschel", "miesmuschel", "μυδι", "μύδι", "seafood", "meeresfruchte", "meeresfrüchte",
}

_MEAT_WORDS.update({
    "veal", "duck", "goose", "geese", "rabbit", "venison", "mutton", "liver", "offal",
    "chickens", "lard", "tallow", "suet", "pancetta", "prosciutto", "chorizo", "lardons",
    "sausages", "frankfurters", "bratwurst", "kalb", "kalbfleisch", "ente", "entenbrust",
    "gans", "kaninchen", "reh", "hirsch", "schmalz", "huhnerbrust", "hahnchenbrust",
    "poulet", "boeuf", "bœuf", "porc", "veau", "canard", "agneau", "jambon", "lapin",
    "dinde", "saucisse", "saucisses", "pollo", "manzo", "vitello", "maiale", "anatra",
    "agnello", "salsiccia", "cerdo", "ternera", "cordero", "pato", "jamon", "tocino",
    "kip", "rundvlees", "varkensvlees", "eend", "κιμας", "μπεικον", "παπια", "βοδινο",
    "quail", "pigeon", "pheasant", "partridge", "guinea fowl", "capon", "oxtail", "kidney", "kidneys",
    "sweetbreads", "tripe", "pepperoni", "mortadella", "andouille", "andouillette", "bresaola",
    "pastrami", "foie gras", "rillettes", "escargot", "snails", "frog", "frogs", "horse", "goat", "meats",
})
_FISH_WORDS.update({
    "cod", "haddock", "hake", "pollock", "trout", "sardine", "sardines", "anchovy", "anchovies",
    "mackerel", "herring", "halibut", "tilapia", "seabass", "sea bass", "bream", "sole",
    "monkfish", "swordfish", "snapper", "turbot", "eel", "bonito", "dashi", "surimi",
    "crab", "crabs", "lobster", "crayfish", "langoustine", "langoustines", "scallop", "scallops",
    "clam", "clams", "oyster", "oysters", "squid", "octopus", "cuttlefish", "calamari",
    "caviar", "roe", "fish sauce", "oyster sauce", "worcestershire",
    "kabeljau", "forelle", "sardellen", "sardinen", "makrele", "hering", "seelachs", "krabben",
    "tintenfisch", "muscheln", "jakobsmuscheln", "poisson", "saumon", "thon", "crevette", "crevettes",
    "cabillaud", "moules", "anchois", "calamar", "calamars", "poulpe", "crabe", "coquilles",
    "pesce", "salmone", "tonno", "gamberi", "gamberetti", "cozze", "vongole", "polpo",
    "acciughe", "merluzzo", "pescado", "atun", "gambas", "mejillones", "calamares",
    "pulpo", "anchoas", "garnalen", "kabeljauw", "zalm", "tonijn",
    "καλαμαρι", "καλαμαρια", "χταποδι", "μυδια", "αντζουγιες", "γαυρος", "μπακαλιαρος",
})
_ANIMAL_DERIVATIVES = {"gelatin", "gelatine", "gelatina", "ζελατινη", "rennet", "animal rennet", "isinglass"}
_MEAT_WORDS |= _ANIMAL_DERIVATIVES
_ANIMAL_WORDS = _MEAT_WORDS | _FISH_WORDS

_NON_VEGAN_WORDS = _ANIMAL_WORDS | {
    "milk", "milch", "γαλα", "γάλα", "butter", "βουτυρο", "βούτυρο", "cheese", "kase", "käse", "τυρι", "τυρί",
    "parmesan", "parmesankase", "parmesankäse", "mascarpone", "cream", "sahne", "κρεμα", "κρέμα",
    "yogurt", "yoghurt", "joghurt", "γιαουρτι", "γιαούρτι", "egg", "eggs", "ei", "eier", "αυγο", "αυγό",
    "αυγα", "αυγά", "honey", "honig", "μελι", "μέλι", "gelatin", "gelatine", "ζελατινη", "ζελατίνη",
}
_NON_VEGAN_WORDS.update({"lait", "beurre", "fromage", "creme", "oeuf", "oeufs", "œuf", "œufs", "miel",
    "latte", "burro", "formaggio", "panna", "uovo", "uova", "miele", "leche", "mantequilla", "queso", "huevo", "huevos",
    "whey", "casein", "ghee", "yolks", "yolk", "whites", "mozzarella", "feta", "ricotta", "quark", "kefir"})

_PESCATARIAN_EXCLUSION_KEYS = {
    "MEAT", "BEEF", "PORK", "POULTRY", "CHICKEN", "TURKEY", "LAMB", "VEAL", "DUCK", "GELATIN", "LARD",
}
_VEGETARIAN_EXCLUSION_KEYS = _PESCATARIAN_EXCLUSION_KEYS | {
    "FISH", "SEAFOOD", "SHELLFISH", "CRUSTACEAN", "CRUSTACEANS", "MOLLUSC", "MOLLUSCS",
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
_CATEGORY_TEXT_ALIASES.update({
    "soy": {"soy", "soya", "tofu", "tempeh", "edamame", "σογια"},
    "shellfish": {"shrimp", "prawns", "prawn", "crab", "lobster", "crayfish", "scallops", "mussels", "clams", "oyster", "squid", "octopus"},
})
for _alias, _canonical in {
    "milchprodukte": "dairy", "γαλακτοκομικα": "dairy", "laktose": "lactose",
    "nusse": "nuts", "ξηροι καρποι": "nuts", "eier": "egg", "αυγο": "egg",
    "fisch": "fish", "ψαρι": "fish", "alkohol": "alcohol", "αλκοολ": "alcohol", "soya": "soy", "soja": "soy",
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
    for key in ("name", "foodName", "canonicalName", "originalName", "description", "applicationDescription", "applianceDescription"):
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


# Exact plant-food phrases prevent coconut milk / cocoa butter being mistaken
# for dairy. A separate animal ingredient in the same row still causes a hit.
_PLANT_PHRASES = {"coconut milk", "coconut cream", "cocoa butter", "peanut butter", "almond butter",
    "soy milk", "soya milk", "oat milk", "almond milk", "rice milk", "cashew milk",
    "kokosmilch", "kokoscreme", "kakaobutter", "erdnussbutter", "hafermilch", "mandelmilch",
    "lait de coco", "creme de coco", "beurre de cacao", "latte di cocco", "leche de coco",
    "kidney beans", "kidney bean", "butter beans", "butter bean", "cashew butter", "hazelnut butter",
    "lamb s lettuce", "chicken of the woods"}


@lru_cache(maxsize=32768)
def _diet_hits(text: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    text = normalize_text(text)
    for phrase in _PLANT_PHRASES:
        text = re.sub(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", "plant ingredient", text)
    for phrase, replacement in {"goat cheese": "cheese", "goat s cheese": "cheese",
            "goat milk": "milk", "goat s milk": "milk"}.items():
        text = re.sub(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", replacement, text)
    tokens = set(text.split())
    def hits(words):
        return tuple(sorted(word for word in words if
            (normalize_text(word) in tokens if " " not in normalize_text(word) else _contains_phrase(text, word))))
    return hits(_MEAT_WORDS), hits(_ANIMAL_WORDS), hits(_NON_VEGAN_WORDS)


def dietary_flags(recipe: dict[str, Any]) -> dict[str, Any]:
    texts = [_ingredient_text(x) for x in recipe.get("ingredients") or []]
    exclusion_keys, _ = _excluded_values(recipe)
    groups = [_diet_hits(text) for text in texts]
    meat_hits, animal_hits, non_vegan_hits = [sorted({word for group in groups for word in group[index]}) for index in range(3)]
    pesc_exclusion_hits = sorted(exclusion_keys & _PESCATARIAN_EXCLUSION_KEYS)
    veg_exclusion_hits = sorted(exclusion_keys & _VEGETARIAN_EXCLUSION_KEYS)
    vegan_exclusion_hits = sorted(exclusion_keys & _VEGAN_EXCLUSION_KEYS)

    known = bool(texts) and all(text.strip() for text in texts)
    forbidden = {diet: any(_explicit_diet_conflict(item, diet) for item in recipe.get("ingredients") or [])
        for diet in ("pescatarian", "vegetarian", "vegan")}
    pescatarian = known and not meat_hits and not pesc_exclusion_hits and not forbidden["pescatarian"]
    vegetarian = known and not animal_hits and not veg_exclusion_hits and not forbidden["vegetarian"]
    vegan = vegetarian and not non_vegan_hits and not vegan_exclusion_hits and not forbidden["vegan"]
    return {
        "pescatarian": pescatarian,
        "vegetarian": vegetarian,
        "vegan": vegan,
        "meatIngredientHits": meat_hits,
        "animalIngredientHits": animal_hits,
        "nonVeganIngredientHits": non_vegan_hits,
        "exclusionKeys": sorted(exclusion_keys),
        "inference": "ingredient_text_and_backend_exclusions",
        "ingredientEvidenceAvailable": known,
    }


def _matches_term(text: str, term: str) -> bool:
    if _contains_phrase(text, term):
        return True
    normalized = normalize_text(term)
    if normalized and (_contains_phrase(text, normalized + "s") or
                       (normalized.endswith("s") and _contains_phrase(text, normalized[:-1]))):
        return True
    aliases = _CATEGORY_TEXT_ALIASES.get(normalize_text(term), set())
    return any(_contains_phrase(text, candidate) for candidate in aliases)


def _matches_exclusion_key(term: str, exclusion_keys: set[str]) -> bool:
    aliases = _CATEGORY_KEY_ALIASES.get(normalize_text(term), set())
    return bool(aliases & exclusion_keys)


def _explicit_diet_conflict(item, diet):
    if not isinstance(item, dict):
        return False
    intelligence = item.get("intelligence") if isinstance(item.get("intelligence"), dict) else {}
    diets = intelligence.get("diets") or item.get("diets") or {}
    state = diets.get(diet) if isinstance(diets, dict) else None
    return state is False or state == "incompatible"


# Culinary suggestions, never rewritten cloud recipes or invented nutrient data.
# Deliberately no generic replacement for gelatin, rennet or whole eggs: their
# functional role cannot be established from an ingredient list alone.
_DIET_REPLACEMENTS = {
    "tofu": ("Firm tofu", ("soy",)),
    "mushrooms": ("Mushrooms", ()),
    "chickpeas": ("Chickpeas", ()),
    "stock": ("Vegetable stock", ("celery",)),
    "cream": ("Oat cream", ("gluten",)),
    "milk": ("Oat milk", ("gluten",)),
    "oil": ("Olive oil", ()),
    "yogurt": ("Soy yogurt", ("soy",)),
    "sweetener": ("Maple syrup", ()),
    "sauce": ("Soy sauce", ("soy", "gluten")),
}
_PLANT_PHRASES.update({"oat cream", "soy yogurt", "soya yogurt", "oyster mushrooms", "oyster mushroom"})


def _diet_substitutions(recipe, profile, violations):
    diet = str(profile.get("diet") or "omnivore").lower()
    group = {"pescatarian": 0, "vegetarian": 1, "vegan": 2}.get(diet)
    if group is None or not violations:
        return [], False
    substitutions, unresolved = [], False
    ingredient_hits = []
    for index, item in enumerate(recipe.get("ingredients") or []):
        text = _ingredient_text(item)
        unresolved |= not bool(text)
        hits = _diet_hits(text)
        ingredient_hits.append(hits)
        if not hits[group]:
            unresolved |= _explicit_diet_conflict(item, diet)
            continue
        words = set(hits[group])
        options = []
        if words & _ANIMAL_DERIVATIVES:
            pass
        elif words & {"lard", "tallow", "suet", "schmalz"}:
            options = ["oil"]
        elif any(_contains_phrase(text, word) for word in ("fish sauce", "oyster sauce", "worcestershire", "sauce de poisson", "nuoc mam")):
            options = ["sauce"]
        elif any(_contains_phrase(text, word) for word in ("stock", "broth", "bouillon", "brühe", "bruehe", "fond", "caldo")):
            options = ["stock"]
        elif hits[1]:
            options = ["tofu", "mushrooms", "chickpeas"]
        elif words & {"butter", "βουτυρο", "βούτυρο", "beurre", "burro", "mantequilla", "ghee"}:
            options = ["oil"]
        elif words & {"cream", "sahne", "creme", "panna", "κρεμα", "κρέμα"}:
            options = ["cream"]
        elif words & {"milk", "milch", "lait", "latte", "leche", "γαλα", "γάλα"}:
            options = ["milk"]
        elif words & {"yogurt", "yoghurt", "joghurt", "γιαουρτι", "γιαούρτι"}:
            options = ["yogurt"]
        elif words & {"honey", "honig", "miel", "miele", "μελι", "μέλι"}:
            options = ["sweetener"]
        candidate = None
        for key in options:
            name, allergens = _DIET_REPLACEMENTS[key]
            safety_text = " ".join((name, *allergens))
            if any(_matches_term(safety_text, str(term)) for term in
                   [*(profile.get("allergies") or []), *(profile.get("avoid") or [])]):
                continue
            if _diet_hits(normalize_text(name))[group]:
                continue
            candidate = {"key": key, "name": name}
            break
        if candidate is None:
            unresolved = True
            continue
        names = recipe_ingredient_names({"ingredients": [item]})
        substitutions.append({"ingredientIndex": index, "original": names[0] if names else text,
            "replacement": candidate, "reason": "diet:" + diet, "advisory": True})

    # Recipe-level evidence must be accounted for by concrete ingredient rows.
    keys, _ = _excluded_values(recipe)
    incompatible_keys = {0: _PESCATARIAN_EXCLUSION_KEYS, 1: _VEGETARIAN_EXCLUSION_KEYS, 2: _VEGAN_EXCLUSION_KEYS}[group]
    all_words = {word for hits in ingredient_hits for word in hits[group]}
    for key in keys & incompatible_keys:
        if key == "GELATIN":
            accounted = bool(all_words & _ANIMAL_DERIVATIVES)
        elif key == "LARD":
            accounted = bool(all_words & {"lard", "tallow", "suet", "schmalz"})
        elif key in _PESCATARIAN_EXCLUSION_KEYS:
            accounted = any(hits[0] for hits in ingredient_hits)
        elif key in _VEGETARIAN_EXCLUSION_KEYS:
            accounted = bool(all_words & _FISH_WORDS)
        elif key in {"EGG", "EGGS"}:
            accounted = bool(all_words & {"egg", "eggs", "ei", "eier", "oeuf", "oeufs", "uovo", "uova", "αυγο", "αυγα"})
        elif key == "HONEY":
            accounted = bool(all_words & {"honey", "honig", "miel", "miele", "μελι"})
        else:
            accounted = bool(all_words & (_CATEGORY_TEXT_ALIASES["dairy"] | {"lait", "latte", "leche", "creme", "panna"}))
        unresolved |= not accounted
    only_diet = all(value == "diet:" + diet for value in violations)
    complete = bool(substitutions) and not unresolved and only_diet
    return substitutions, complete


def _profile_excluded_rows(profile):
    value = profile.get("excludedIngredients")
    rows = []
    for row in value if isinstance(value, list) else []:
        if not isinstance(row, dict):
            continue
        identity = str(row.get("ingredientId") or row.get("key") or row.get("id") or "")
        aliases = row.get("sourceIngredientIds")
        ids = {identity, *(str(x) for x in aliases if isinstance(x, str))} if isinstance(aliases, list) else {identity}
        ids.discard("")
        if ids:
            rows.append((str(row.get("name") or identity), ids))
    return rows


def _profile_excluded_matches(recipe, profile):
    identities = {str(row.get(key) or "") for row in recipe.get("ingredients") or [] if isinstance(row, dict)
                  for key in ("ingredientId", "key", "foodKey", "id")}
    return [name for name, aliases in _profile_excluded_rows(profile) if identities.intersection(aliases)]


def _profile_rules_signature(profile):
    ids = sorted({identity for _name, aliases in _profile_excluded_rows(profile) for identity in aliases})
    terms = sorted({str(x).strip().lower() for x in [*(profile.get("allergies") or []), *(profile.get("avoid") or [])] if str(x).strip()})
    return json.dumps([profile.get("diet") or "omnivore", ids, terms], ensure_ascii=False, separators=(",", ":"))


def _ingredient_changes(recipe, profile, substitutions):
    """Identify concrete incompatible rows for cooking, including unresolved ones."""
    diet = str(profile.get("diet") or "omnivore").lower()
    group = {"pescatarian": 0, "vegetarian": 1, "vegan": 2}.get(diet)
    suggested = {row["ingredientIndex"]: row for row in substitutions}
    changes = []
    for index, item in enumerate(recipe.get("ingredients") or []):
        text = _ingredient_text(item)
        reasons = []
        if group is not None and (_diet_hits(text)[group] or _explicit_diet_conflict(item, diet)):
            reasons.append("diet:" + diet)
        for kind, key in (("allergy", "allergies"), ("avoid", "avoid")):
            reasons.extend(f"{kind}:{term}" for term in profile.get(key) or []
                           if str(term).strip() and _matches_term(text, str(term)))
        reasons.extend("excluded:" + name for name in _profile_excluded_matches({"ingredients": [item]}, profile))
        if not reasons:
            continue
        names = recipe_ingredient_names({"ingredients": [item]})
        changes.append({"ingredientIndex": index, "original": names[0] if names else text,
                        "reasons": reasons, "replacement": suggested.get(index, {}).get("replacement"),
                        "advisory": True})
    return changes


def score_recipe(recipe: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Score one recipe against explicit pantry/diet restrictions.

    Diet/allergy exclusions filter discovery; they do not gate device delivery.
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

    violations.extend("excluded:" + name for name in _profile_excluded_matches(recipe, profile))
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
    substitutions, complete = _diet_substitutions(recipe, profile, violations)
    score = (coverage + preference_bonus + habit_bonus) * 100 if safe else (-100 if complete else -1000)

    return {
        "safe": safe,
        "diet": diet,
        "dietCheckVersion": 76,
        "dietRulesSignature": _profile_rules_signature(profile),
        "substitutions": substitutions,
        "ingredientChanges": _ingredient_changes(recipe, profile, substitutions),
        "eligibleWithSubstitutions": complete,
        "requiresSubstitutions": complete,
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
