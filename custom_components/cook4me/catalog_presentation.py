"""Display-only catalog names and families; never rewrites provider evidence."""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def norm(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", str(value).casefold()) if not unicodedata.combining(c)).split())


_PLURALS = dict(zip("onions tomatoes potatoes carrots mushrooms peppers chillies chilies courgettes zucchinis aubergines eggplants cucumbers leeks shallots scallions cloves lemons limes oranges apples pears peaches apricots plums cherries strawberries raspberries blueberries blackberries cranberries grapes bananas almonds hazelnuts walnuts peanuts cashews pistachios chestnuts lentils chickpeas beans peas eggs anchovies sardines prawns shrimps mussels oysters scallops fillets breasts thighs drumsticks wings sausages meatballs steaks ribs seeds leaves stalks florets sprigs olives capers noodles biscuits crackers tortillas".split(), "onion tomato potato carrot mushroom pepper chili chili courgette zucchini aubergine eggplant cucumber leek shallot scallion clove lemon lime orange apple pear peach apricot plum cherry strawberry raspberry blueberry blackberry cranberry grape banana almond hazelnut walnut peanut cashew pistachio chestnut lentil chickpea bean pea egg anchovy sardine prawn shrimp mussel oyster scallop fillet breast thigh drumstick wing sausage meatball steak rib seed leaf stalk floret sprig olive caper noodle biscuit cracker tortilla".split()))


def name_key(value):
    value = norm(value).replace("agar-agar", "agar agar").replace("chilli", "chili")
    return " ".join(_PLURALS.get(word, word) for word in value.split())


_AMOUNT = r"(?:\d+\s*/\s*\d+|/\d+|\d+(?:[.,]\d+)?|[¼½¾⅓⅔⅛⅜⅝⅞])"
_UNITS = r"(?:kg|grams?|g|mg|ml|cl|dl|litres?|liters?|l|tablespoons?|teaspoons?|tbsp|tsp|cups?|ounces?|oz|pounds?|lb|pinch(?:es)?|handfuls?|bunch(?:es)?|slices?|pieces?|cans?|tins?|jars?|packets?|packs?|bags?|bottles?)"
_PREP = r"(?:peeled|chopped|diced|sliced|rinsed|washed|trimmed|crushed|grated|shredded|drained|deseeded|seeded|pitted|halved|quartered|minced|sifted|beaten|divided|cleaned|scaled|deveined|deboned|skinless|boneless|thawed|defrosted|finely|roughly|thinly|thickly|coarsely|freshly|cut|squeezed|zested)"


def clean_name(value):
    """Strip recipe amounts and preparation; keep food type/composition/state."""
    name = " ".join(str(value or "").strip().split())
    name = re.sub(r"^[*+•]+\s*|^\[?[a-d]\]?\s*[-–:]\s*|^\[[a-d]\]\s*", "", name, flags=re.I)
    name = re.sub(r"^(?:a little|a few|some|a knob of|a sprig of|a handful of|a pinch of)\s+", "", name, flags=re.I)
    name = re.sub(r"^(?:drops|leaves|sprigs) of\s+", "", name, flags=re.I)
    name = re.sub(rf"^{_AMOUNT}\s*[-–]\s*{_AMOUNT}\s*{_UNITS}\b\s*", "", name, flags=re.I)
    # Percentages and flour type 00 are food specifications, not quantities.
    if not re.match(r"^\d+(?:[.,]\d+)?\s*%", name):
        name = re.sub(rf"^(?:{_AMOUNT}\s+)?{_AMOUNT}\s*{_UNITS}\b\s*(?:of\s+)?", "", name, flags=re.I)
        if not re.match(r"^00\s", name):
            name = re.sub(rf"^{_AMOUNT}\s+(?:of\s+)?", "", name)
    name = re.sub(r"\s*\([^)]*\)", "", name)
    if re.fullmatch(r"salt,?\s+(?:and\s+)?(?:white |black )?pepper", name, flags=re.I):
        name = name.replace(",", " and")
    else:
        name = re.split(r"[,;:]\s+(?!\d)", name, maxsplit=1)[0]
    name = re.split(rf"[,;]\s*(?:(?:and|then)\s+)?{_PREP}\b|\s+(?:to taste|as (?:needed|required)|for (?:serving|garnish|decoration))\b", name, maxsplit=1, flags=re.I)[0]
    name = re.sub(rf"^(?:(?:{_PREP})\s+)+", "", name, flags=re.I)
    name = re.split(rf"\s+(?:{_PREP})\b", name, maxsplit=1, flags=re.I)[0]
    name = re.sub(r"\s+(?:cut into|cut in|chopped into|sliced into|diced into)\b.*$", "", name, flags=re.I)
    name = re.sub(r"\s*\([^)]*(?:cm|mm|inch)[^)]*\)", "", name, flags=re.I)
    return name.strip(" ,;-.")


@lru_cache(maxsize=1)
def labels():
    path = Path(__file__).with_name("ingredient_ui_labels.json")
    result = json.loads(path.read_text()) if path.exists() else {}
    for overlay in sorted(Path(__file__).with_name("catalog_ui_locales").glob("*.json")):
        data = json.loads(overlay.read_text())
        if data.get("schemaVersion") == 1 and isinstance(data.get("labels"), dict):
            result.setdefault(str(data["language"]), {}).update(data["labels"])
    return result


def display_name(raw, language):
    canonical = clean_name(raw.get("canonicalName") or raw.get("name") or raw.get("foodName"))
    code = str(language or "en").lower().replace("_", "-").split("-")[0]
    translated = labels().get(code, {}).get(name_key(canonical))
    if translated:
        return translated
    source = (raw.get("translations") or {}).get(code)
    return clean_name(source) if source and code != "en" else canonical


def ingredient_choices(payload, language, query="", limit=None):
    """One choice per cleaned name, retaining all source IDs as display metadata."""
    groups = defaultdict(list)
    for raw in payload.get("ingredients", []):
        if raw.get("classification") in {"equipment", "other", "ambiguous"}:
            continue
        canonical = clean_name(raw.get("canonicalName"))
        if re.match(r"^(?:or\b|and\b|fragment\b|for\b|optional\b|quantity\b|a little\b)", canonical, re.I):
            continue
        if canonical:
            groups[name_key(canonical)].append(raw)
    choices = []
    wanted = norm(query)
    for canonical, members in groups.items():
        # Prefer the actual generic provider row; never assign its ID to siblings.
        raw = min(members, key=lambda r: (not bool(r.get("key")), name_key(r.get("canonicalName")) != canonical, not bool(r.get("nutrition")), str(r.get("id"))))
        name = display_name(raw, language)
        if wanted and wanted not in norm(name) and wanted not in canonical:
            continue
        row = {key: raw[key] for key in ("id", "key", "conceptId", "classification", "nutritionEligible") if key in raw}
        row.update(ingredientId=raw["id"], name=name, foodName=name, canonicalName=clean_name(raw.get("canonicalName")), displayGroupId="ingredient:"+hashlib.sha256(canonical.encode()).hexdigest()[:16], sourceIngredientIds=[member["id"] for member in members], displayLanguage=language, presentationVersion=62)
        if raw.get("key"):
            row["foodKey"] = raw["key"]
        choices.append(row)
    choices.sort(key=lambda row: norm(row["name"]))
    return choices if limit is None else choices[:max(0, int(limit))]


def prepare_families(payload):
    recipes = payload.get("recipes", [])
    lookup = payload.get("_runtimeIngredientById", {})
    parents = list(range(len(recipes)))
    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    keys = {}
    for index, recipe in enumerate(recipes):
        title = norm(recipe.get("canonicalName", ""))
        for variant in recipe.get("variants", []):
            cover = str(variant.get("cover") or "")
            ingredients = tuple(sorted({norm(clean_name(lookup.get(str(row.get("ingredientId") or row.get("key") or row.get("foodKey")), {}).get("canonicalName") or row.get("ingredientId") or row.get("name") or "")) for row in variant.get("ingredients", []) if isinstance(row, dict)}))
            unit = str((variant.get("yield") or {}).get("unitKey") or (variant.get("yield") or {}).get("unit") or "")
            # Exact title, image, food identities and yield dimension only.
            if not title or not cover or not ingredients:
                continue
            key = (title, cover, ingredients, unit)
            if key in keys:
                left, right = root(index), root(keys[key])
                parents[max(left, right)] = min(left, right)
            else:
                keys[key] = index
    families = defaultdict(list)
    for index in range(len(recipes)):
        families[root(index)].append(index)
    payload["_runtimeDisplayFamily"] = {index: root(index) for index in range(len(recipes))}
    payload["_runtimeDisplayFamilyMembers"] = dict(families)


def family_row(payload, members, *, language, configured_language, country, materialize, preferred_variant=""):
    """Group choices without using display similarity as a device-send proof."""
    recipes = payload["recipes"]
    publications = [(index, variant) for index in members for variant in recipes[index].get("variants", [])]
    if not publications:
        return None
    chosen = next(((i, v) for i, v in publications if str(v.get("variantId")) == preferred_variant), None)
    chosen = chosen or min(publications, key=lambda pair: (pair[1].get("language") != language, pair[1].get("language") != configured_language, abs(float(pair[1].get("servings") or 4)-4), str(pair[1].get("variantId"))))
    index, variant = chosen
    row = materialize(recipes[index], variant["variantId"], variant.get("language") or language)
    if row is None:
        return None
    root = payload["_runtimeDisplayFamily"][index]
    row["displayFamilyId"] = "family:"+str(recipes[root].get("groupingFunctionalId") or root)
    row["publicationCount"] = len(members)
    languages = defaultdict(list)
    variants = []
    seen = set()
    for member, publication in publications:
        ident = str(publication.get("variantId") or "")
        if not ident or ident in seen:
            continue
        seen.add(ident)
        # Materialize device identity from the ORIGINAL provider group only.
        option_row = materialize(recipes[member], ident, publication.get("language") or language, enrich=False)
        basis = publication.get("yield") or {}
        quantity = publication.get("servings") or basis.get("quantity")
        unit = basis.get("unit") if basis.get("unitKey") in {"UNIT_27", "UNIT_17"} or basis.get("unit") in {"g", "kg", "ml", "l"} else ""
        label = f"{quantity:g}" if isinstance(quantity, (int, float)) else str(quantity or "")
        option = {"servings": quantity, "label": f"{label} {unit}".strip(), "displayVariantId": ident, "displayRecipeFunctionalId": publication.get("recipeFunctionalId") or ident, "displayGroupingFunctionalId": publication.get("groupingFunctionalId"), "language": publication.get("language"), "yield": basis}
        for key in ("sendVariantId", "sendRecipeFunctionalId", "sendGroupingFunctionalId"):
            option[key] = option_row.get(key) if option_row else None
        languages[publication.get("language") or language].append(option)
        variants.extend(option_row.get("variants", []) if option_row else [])
    language_rows = []
    for code, options in sorted(languages.items()):
        # Same language/quantity may have multiple market publications.
        unique = {}
        for option in options:
            key = (option["servings"], str(option["yield"].get("unitKey") or option["yield"].get("unit") or ""))
            if key not in unique or option["displayVariantId"] == row.get("displayVariantId") or (option.get("sendVariantId") and not unique[key].get("sendVariantId")):
                unique[key] = option
        options = sorted(unique.values(), key=lambda r: (float(r.get("servings") or 0), r["displayVariantId"]))
        language_rows.append({"language": code, "servingVariants": options, "availableServings": [r["servings"] for r in options], "sendable": any(r.get("sendVariantId") for r in options)})
    row["languageVariants"] = language_rows
    row["availableLanguages"] = [r["language"] for r in language_rows]
    selected = next(r for r in language_rows if r["language"] == row["language"])
    row.update(selectedLanguage=row["language"], selectedServings=variant.get("servings"), servingVariants=selected["servingVariants"], availableServings=selected["availableServings"])
    row["variants"] = list({str(v.get("variantId")): v for v in variants}.values())
    return row
