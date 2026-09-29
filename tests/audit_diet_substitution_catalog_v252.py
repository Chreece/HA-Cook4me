from __future__ import annotations

from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "custom_components" / "cook4me" / "catalog" / "merged_catalog.v1.json"
LOGIC = ROOT / "custom_components" / "cook4me" / "recipe_logic.py"
SUBSTITUTIONS = ROOT / "custom_components" / "cook4me" / "ingredient_substitutions.py"

spec = importlib.util.spec_from_file_location("cook4me_recipe_logic_catalog_audit", LOGIC)
assert spec is not None and spec.loader is not None
logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logic)

sub_spec = importlib.util.spec_from_file_location(
    "cook4me_ingredient_substitutions_catalog_audit", SUBSTITUTIONS
)
assert sub_spec is not None and sub_spec.loader is not None
substitutions = importlib.util.module_from_spec(sub_spec)
sub_spec.loader.exec_module(substitutions)

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


def _identity_values(row):
    if not isinstance(row, dict):
        return ()
    return tuple(
        _text(row.get(key))
        for key in ("ingredientId", "id", "key", "foodKey")
        if _text(row.get(key))
    )


def _ingredient_lookup(payload):
    lookup = {}
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        for identity in _identity_values(row):
            lookup.setdefault(identity, row)
    return lookup


def _resolved_ingredient(raw, lookup):
    if not isinstance(raw, dict):
        return raw
    source = next((lookup.get(value) for value in _identity_values(raw) if value in lookup), None)
    if not isinstance(source, dict):
        return raw
    out = dict(source)
    out.update(raw)
    if raw.get("originalName"):
        out["originalName"] = raw["originalName"]
    if not out.get("canonicalName"):
        out["canonicalName"] = source.get("canonicalName") or source.get("name") or source.get("foodName")
    for key in ("intelligence", "diets", "allergens", "classification", "conceptId"):
        if key not in out and key in source:
            out[key] = source[key]
    return out


def _candidate(recipe, variant, lookup):
    ingredients = variant.get("ingredients") or recipe.get("ingredients") or []
    return {
        "title": (
            variant.get("originalTitle")
            or variant.get("title")
            or recipe.get("canonicalName")
            or ""
        ),
        "ingredients": [_resolved_ingredient(row, lookup) for row in ingredients],
        **{
            key: variant.get(key, recipe.get(key))
            for key in ("excludedFoods", "detectedExcludedFoods", "recipeType")
            if key in variant or key in recipe
        },
    }


def main():
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    substitution_summary = substitutions.enrich_catalog_substitutions(payload)
    lookup = _ingredient_lookup(payload)
    unresolved = Counter()
    unresolved_examples = defaultdict(list)
    unresolved_concepts = Counter()
    unresolved_concept_examples = defaultdict(list)
    totals = Counter()
    adapted = Counter()
    safe = Counter()
    incompatible = Counter()
    legacy_fallback = Counter()
    legacy_examples = defaultdict(list)
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
            candidate = _candidate(recipe, variant, lookup)
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
                    sources = set(match.get("substitutionSources") or [])
                    if "legacy_text_fallback" in sources:
                        legacy_fallback[diet] += 1
                        if len(legacy_examples[diet]) < 5:
                            legacy_examples[diet].append({
                                "title": title,
                                "variantId": variant_id,
                                "language": language,
                                "sources": sorted(sources),
                            })
                    continue

                for change in match.get("ingredientChanges") or []:
                    reasons = change.get("reasons") or []
                    if f"diet:{diet}" not in reasons or change.get("replacement"):
                        continue
                    name = _text(change.get("original")) or "<unnamed>"
                    key = (diet, language, logic.normalize_text(name) or name.casefold())
                    unresolved[key] += 1
                    index = change.get("ingredientIndex")
                    ingredient = (
                        candidate.get("ingredients", [])[index]
                        if isinstance(index, int)
                        and 0 <= index < len(candidate.get("ingredients") or [])
                        else {}
                    )
                    concept_id = _text(ingredient.get("conceptId")) if isinstance(ingredient, dict) else ""
                    ingredient_id = next(iter(_identity_values(ingredient)), "") if isinstance(ingredient, dict) else ""
                    concept_key = (diet, concept_id or "<missing-concept>", ingredient_id or "<missing-id>")
                    unresolved_concepts[concept_key] += 1
                    intelligence = (
                        ingredient.get("intelligence")
                        if isinstance(ingredient, dict)
                        and isinstance(ingredient.get("intelligence"), dict)
                        else {}
                    )
                    concept_example = {
                        "ingredient": name,
                        "title": title,
                        "variantId": variant_id,
                        "language": language,
                        "conceptId": concept_id,
                        "ingredientId": ingredient_id,
                        "classification": ingredient.get("classification") if isinstance(ingredient, dict) else None,
                        "dietEligible": ingredient.get("dietEligible") if isinstance(ingredient, dict) else None,
                        "diets": intelligence.get("diets") if isinstance(intelligence.get("diets"), dict) else ingredient.get("diets") if isinstance(ingredient, dict) else None,
                        "substitutionClass": intelligence.get("substitutionClass") or ingredient.get("substitutionClass") if isinstance(ingredient, dict) else None,
                        "substitutionDiets": ingredient.get("substitutionDiets") if isinstance(ingredient, dict) else None,
                        "substitutionBindingId": ingredient.get("substitutionBindingId") if isinstance(ingredient, dict) else None,
                    }
                    if len(unresolved_concept_examples[concept_key]) < 3:
                        unresolved_concept_examples[concept_key].append(concept_example)
                    if len(unresolved_examples[key]) < 3:
                        unresolved_examples[key].append(concept_example)

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
        "legacyFallback": dict(legacy_fallback),
        "legacyExamples": dict(legacy_examples),
        "catalogSubstitutionSummary": substitution_summary,
        "unresolvedOccurrences": sum(unresolved.values()),
        "unresolvedGroups": len(unresolved),
        "unresolvedConceptCount": len(unresolved_concepts),
        "topUnresolvedConcepts": [
            {
                "diet": diet,
                "conceptId": concept_id,
                "ingredientId": ingredient_id,
                "count": count,
                "examples": unresolved_concept_examples[(diet, concept_id, ingredient_id)],
            }
            for (diet, concept_id, ingredient_id), count
            in unresolved_concepts.most_common(160)
        ],
        "topUnresolved": rows[:120],
    }
    print("DIET_SUBSTITUTION_CATALOG_AUDIT=" + json.dumps(report, ensure_ascii=False))

    if variants_seen <= 0:
        raise SystemExit("Diet substitution audit did not scan any catalog variants")
    for diet in DIETS:
        if totals[diet] != variants_seen:
            raise SystemExit(f"Diet substitution audit missed variants for {diet}")
        if safe[diet] <= 0 or incompatible[diet] <= 0 or adapted[diet] <= 0:
            raise SystemExit(f"Diet substitution audit did not exercise all states for {diet}")
        if adapted[diet] != incompatible[diet]:
            raise SystemExit(
                f"Incomplete {diet} catalog coverage: "
                f"{adapted[diet]}/{incompatible[diet]} incompatible variants adapted"
            )
    if unresolved:
        raise SystemExit(
            f"Catalog has {sum(unresolved.values())} unresolved diet-conflict occurrences "
            f"across {len(unresolved)} groups"
        )
    if any(legacy_fallback.values()):
        raise SystemExit(
            "Official catalog diet adaptations still use legacy text fallback: "
            + json.dumps(dict(legacy_fallback), sort_keys=True)
        )
    if int(substitution_summary.get("ingredientCount") or 0) <= 0:
        raise SystemExit("No ingredient-owned substitutions were mounted")
    if substitution_summary.get("missingProfiles"):
        raise SystemExit(
            "Mounted substitution profiles are missing: "
            + ", ".join(substitution_summary["missingProfiles"])
        )


if __name__ == "__main__":
    main()
