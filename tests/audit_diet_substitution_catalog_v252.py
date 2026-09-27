from __future__ import annotations

from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "custom_components" / "cook4me" / "catalog" / "merged_catalog.v1.json"
LOGIC = ROOT / "custom_components" / "cook4me" / "recipe_logic.py"

spec = importlib.util.spec_from_file_location("cook4me_recipe_logic_catalog_audit", LOGIC)
assert spec is not None and spec.loader is not None
logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logic)

DIETS = ("pescatarian", "vegetarian", "vegan")


def _text(value):
    return " ".join(str(value or "").strip().split())


def _profile(diet):
    return {
        "diet": diet,
        "allergies": [],
        "avoid": [],
        "pantry": [],
        "preferences": [],
        "habitTerms": [],
    }


def _candidate(recipe, variant):
    ingredients = variant.get("ingredients") or recipe.get("ingredients") or []
    return {
        "title": (
            variant.get("originalTitle")
            or variant.get("title")
            or recipe.get("canonicalName")
            or ""
        ),
        "ingredients": ingredients,
        **{
            key: variant.get(key, recipe.get(key))
            for key in ("excludedFoods", "detectedExcludedFoods", "recipeType")
            if key in variant or key in recipe
        },
    }


def main():
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    unresolved = Counter()
    unresolved_examples = defaultdict(list)
    totals = Counter()
    adapted = Counter()
    safe = Counter()
    incompatible = Counter()
    variants_seen = 0

    for recipe in payload.get("recipes") or []:
        if not isinstance(recipe, dict):
            continue
        variants = [
            row for row in recipe.get("variants") or [] if isinstance(row, dict)
        ]
        if not variants:
            variants = [recipe]
        for variant in variants:
            variants_seen += 1
            language = _text(
                variant.get("originalLanguage") or variant.get("language") or "unknown"
            ).lower()
            candidate = _candidate(recipe, variant)
            title = _text(candidate.get("title"))
            variant_id = _text(
                variant.get("variantId")
                or variant.get("searchVariantId")
                or variant.get("recipeFunctionalId")
            )

            for diet in DIETS:
                totals[diet] += 1
                match = logic.score_recipe(candidate, _profile(diet))
                if match.get("safe"):
                    safe[diet] += 1
                    continue
                incompatible[diet] += 1
                if (
                    match.get("eligibleWithSubstitutions")
                    and match.get("substitutionCoverageComplete")
                ):
                    adapted[diet] += 1
                    continue

                for change in match.get("ingredientChanges") or []:
                    reasons = change.get("reasons") or []
                    if f"diet:{diet}" not in reasons or change.get("replacement"):
                        continue
                    name = _text(change.get("original")) or "<unnamed>"
                    key = (diet, language, logic.normalize_text(name) or name.casefold())
                    unresolved[key] += 1
                    if len(unresolved_examples[key]) < 3:
                        unresolved_examples[key].append(
                            {
                                "ingredient": name,
                                "title": title,
                                "variantId": variant_id,
                            }
                        )

    rows = []
    for (diet, language, normalized), count in unresolved.most_common():
        examples = unresolved_examples[(diet, language, normalized)]
        rows.append(
            {
                "diet": diet,
                "language": language,
                "normalizedIngredient": normalized,
                "count": count,
                "examples": examples,
            }
        )

    report = {
        "variants": variants_seen,
        "totals": dict(totals),
        "safe": dict(safe),
        "incompatible": dict(incompatible),
        "adapted": dict(adapted),
        "unresolvedOccurrences": sum(unresolved.values()),
        "unresolvedGroups": len(unresolved),
        "topUnresolved": rows[:120],
    }
    print("DIET_SUBSTITUTION_CATALOG_AUDIT=" + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
