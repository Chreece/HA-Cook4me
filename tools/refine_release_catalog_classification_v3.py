#!/usr/bin/env python3
"""Refine v2 recipe classification with complete SEB taxonomy and reviewed gaps.

This stage makes meal/entry classification complete without inventing a meal
course for SEB's ingredient-cooking programs. Provider ``courses`` are the
strongest meal evidence; ``occasions`` can add secondary tags such as brunch.
``IS_FOOD_COOKING`` becomes ``entryType=ingredient_preparation``. Only the 28
provider-taxonomy gaps are handled by the reviewed override table.

SEB's VEGAN/VEGETARIAN occasion labels are retained only as hints because live
catalog evidence proves they can contradict actual ingredients. They never
override the ingredient/exclusion-based diet classifier.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "tools" / "release_catalog_reviewed_entry_meal_overrides.v1.json"

_PROVIDER_MEAL_KEYS = {
    "MAIN_COURSE": "main",
    "SECONDI": "main",
    "STARTER": "starter",
    "DESSERT": "dessert",
    "SIDE_DISH": "side",
    "OCCASION_MAIN_COURSE": "main",
    "OCCASION_STARTER": "starter",
    "BEST_DESSERTS": "dessert",
    "BRUNCH": "breakfast",
    "CHIC_EASY_STARTERS": "starter",
    "MEDITERRANEAN_STARTERS": "starter",
    "CHOCOLATE_DESSERTS": "dessert",
    "FRUIT_DESSERTS": "dessert",
    "CANDY_DESSERTS": "dessert",
}
_COURSE_KEYS = {"MAIN_COURSE", "SECONDI", "STARTER", "DESSERT", "SIDE_DISH"}
_DIET_HINTS = {"VEGAN": "vegan", "VEGETARIAN": "vegetarian"}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _keys(value: Any) -> list[str]:
    out: list[str] = []
    for raw in value if isinstance(value, list) else []:
        if isinstance(raw, dict):
            key = _text(raw.get("key") or raw.get("name"))
        else:
            key = _text(raw)
        if key and key not in out:
            out.append(key)
    return out


def _group_taxonomy(provider: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    grouped: dict[str, dict[str, set[str]]] = {}
    for detail in provider.get("details") or []:
        if not isinstance(detail, dict):
            continue
        grouping = _text(
            detail.get("groupingFunctionalId")
            or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId")
            or detail.get("variantId")
        )
        if not grouping:
            continue
        row = grouped.setdefault(
            grouping,
            {"courses": set(), "occasions": set(), "classifications": set()},
        )
        for field in row:
            row[field].update(_keys(detail.get(field)))
    return grouped


def _load_overrides() -> dict[str, dict[str, Any]]:
    value = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    if value.get("kind") != "cook4me-reviewed-entry-meal-overrides":
        raise RuntimeError("invalid reviewed entry/meal override file")
    return {
        str(key): row
        for key, row in (value.get("items") or {}).items()
        if isinstance(row, dict)
    }


def _provider_meal(row: dict[str, set[str]]) -> tuple[list[str], str | None, list[str]]:
    evidence: list[str] = []
    meal_types: list[str] = []
    for field in ("courses", "occasions", "classifications"):
        for key in sorted(row.get(field) or set()):
            meal = _PROVIDER_MEAL_KEYS.get(key)
            if not meal:
                continue
            evidence.append(f"{field}:{key}")
            if meal not in meal_types:
                meal_types.append(meal)

    course_types: list[str] = []
    for key in sorted(row.get("courses") or set()):
        meal = _PROVIDER_MEAL_KEYS.get(key) if key in _COURSE_KEYS else None
        if meal and meal not in course_types:
            course_types.append(meal)
    if len(course_types) == 1:
        primary = course_types[0]
    elif not course_types and len(meal_types) == 1:
        primary = meal_types[0]
    else:
        primary = None
    return meal_types, primary, evidence


def _diet_hints(row: dict[str, set[str]]) -> list[str]:
    hints: list[str] = []
    for key in sorted((row.get("occasions") or set()) | (row.get("classifications") or set())):
        hint = _DIET_HINTS.get(key)
        if hint and hint not in hints:
            hints.append(hint)
    return hints


def _hint_conflicts(primary: str | None, hints: list[str]) -> bool:
    if not primary or not hints:
        return False
    if "vegan" in hints and primary != "vegan":
        return True
    if "vegetarian" in hints and primary in {"pescatarian", "omnivore"}:
        return True
    return False


def refine(
    classification: dict[str, Any], provider: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if classification.get("kind") != "cook4me-release-recipe-classification-v2":
        raise RuntimeError("expected v2 release recipe classification")
    source = provider.get("source") if isinstance(provider.get("source"), dict) else {}
    if not source.get("taxonomyAugmented"):
        raise RuntimeError("provider capture has not been augmented with complete taxonomy")

    taxonomy = _group_taxonomy(provider)
    overrides = _load_overrides()
    output_rows: list[dict[str, Any]] = []
    unknown_meal: list[str] = []

    for raw in classification.get("recipes") or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        grouping = _text(row.get("groupingFunctionalId"))
        tax = taxonomy.get(grouping, {"courses": set(), "occasions": set(), "classifications": set()})
        override = overrides.get(grouping)

        is_food_cooking = "IS_FOOD_COOKING" in tax.get("classifications", set())
        if override:
            entry_type = _text(override.get("entryType")) or "recipe"
            meal_types = [str(value) for value in override.get("mealTypes") or []]
            primary_meal = override.get("primaryMealType")
            meal_status = "resolved" if meal_types else "not_applicable"
            meal_source = "reviewed_manual_override"
            meal_evidence = ["reviewed:taxonomy_gap"]
            row["reviewedMealConfidence"] = override.get("confidence")
            if override.get("notes"):
                row["reviewedMealNotes"] = override.get("notes")
        elif is_food_cooking:
            entry_type = "ingredient_preparation"
            meal_types = []
            primary_meal = None
            meal_status = "not_applicable"
            meal_source = "seb_classification"
            meal_evidence = ["classifications:IS_FOOD_COOKING"]
        else:
            entry_type = "recipe"
            meal_types, primary_meal, meal_evidence = _provider_meal(tax)
            meal_status = "resolved" if meal_types else "review_required"
            meal_source = "seb_courses_occasions_classifications"
            if not meal_types:
                unknown_meal.append(grouping)

        row["entryType"] = entry_type
        row["mealTypes"] = meal_types
        row["primaryMealType"] = primary_meal
        row["mealTypeClassification"] = {
            "status": meal_status,
            "source": meal_source,
            "evidence": meal_evidence,
        }

        diet_class = dict(row.get("dietClassification") or {})
        hints = _diet_hints(tax)
        if hints:
            diet_class["providerDietHints"] = hints
            if _hint_conflicts(row.get("primaryDiet"), hints):
                diet_class["providerDietHintConflict"] = True
        if entry_type == "non_food":
            row["primaryDiet"] = None
            row["dietTags"] = []
            diet_class = {"status": "not_applicable", "source": "reviewed_non_food"}
        row["dietClassification"] = diet_class
        output_rows.append(row)

    if unknown_meal:
        raise RuntimeError(
            f"meal classification still has {len(unknown_meal)} unreviewed provider groupings"
        )

    summary = dict(classification.get("summary") or {})
    summary.update(
        {
            "recipeGroups": len(output_rows),
            "mealTypeResolved": sum(
                row["mealTypeClassification"]["status"] == "resolved"
                for row in output_rows
            ),
            "mealTypeNotApplicable": sum(
                row["mealTypeClassification"]["status"] == "not_applicable"
                for row in output_rows
            ),
            "mealTypeReviewRequired": 0,
            "entryType_recipe": sum(row["entryType"] == "recipe" for row in output_rows),
            "entryType_ingredient_preparation": sum(
                row["entryType"] == "ingredient_preparation" for row in output_rows
            ),
            "entryType_beverage": sum(row["entryType"] == "beverage" for row in output_rows),
            "entryType_non_food": sum(row["entryType"] == "non_food" for row in output_rows),
            "providerDietHintConflicts": sum(
                bool((row.get("dietClassification") or {}).get("providerDietHintConflict"))
                for row in output_rows
            ),
        }
    )
    review = [
        {
            "groupingFunctionalId": row.get("groupingFunctionalId"),
            "language": row.get("language"),
            "title": row.get("title"),
            "entryType": row.get("entryType"),
            "needsDietReview": (row.get("dietClassification") or {}).get("status")
            == "review_required",
            "dietBlockers": (row.get("dietClassification") or {}).get("blockers") or [],
            "providerDietHints": (row.get("dietClassification") or {}).get("providerDietHints") or [],
        }
        for row in output_rows
        if (row.get("dietClassification") or {}).get("status") == "review_required"
    ]
    summary["dietReviewRequired"] = len(review)
    summary["reviewQueue"] = len(review)

    payload = {
        "schemaVersion": 3,
        "kind": "cook4me-release-recipe-classification-v3",
        "policy": {
            "providerIdentityUnchanged": True,
            "ingredientPreparationNotForcedIntoMealCourse": True,
            "providerCoursesPreferredForPrimaryMealType": True,
            "providerDietTagsAreHintsOnly": True,
            "mealClassificationComplete": True,
        },
        "summary": summary,
        "recipes": output_rows,
    }
    review_payload = {
        "schemaVersion": 3,
        "kind": "cook4me-release-recipe-classification-review-v3",
        "summary": {"items": len(review), "mealItems": 0, "dietItems": len(review)},
        "items": review,
    }
    return payload, review_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", required=True)
    parser.add_argument("--provider-capture", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    classification = _load_gzip(Path(args.classification).expanduser())
    provider = _load_gzip(Path(args.provider_capture).expanduser())
    payload, review = refine(classification, provider)
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
