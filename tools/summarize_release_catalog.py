#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Catalog is not a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _variant_rows(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in recipe.get("variants") or []:
        if not isinstance(raw, dict):
            continue
        rows.append(
            {
                key: raw[key]
                for key in (
                    "variantId",
                    "recipeFunctionalId",
                    "groupingFunctionalId",
                    "title",
                    "language",
                    "market",
                    "servings",
                )
                if raw.get(key) not in (None, "")
            }
        )
    return rows


def summarize(catalog: dict[str, Any], source_path: Path) -> dict[str, Any]:
    source = catalog.get("source") if isinstance(catalog.get("source"), dict) else {}
    ingredients = [row for row in catalog.get("ingredients") or [] if isinstance(row, dict)]
    recipes = [row for row in catalog.get("recipes") or [] if isinstance(row, dict)]

    unresolved_ingredients: list[dict[str, Any]] = []
    nutrition_missing: list[dict[str, Any]] = []
    ingredient_ids: list[str] = []
    for row in ingredients:
        ident = _text(row.get("id") or row.get("key"))
        if ident:
            ingredient_ids.append(ident)
        compact = {
            "id": ident,
            "key": _text(row.get("key")),
            "canonicalName": _text(row.get("canonicalName")),
            "canonicalNameSourceLanguage": _text(row.get("canonicalNameSourceLanguage")),
            "translations": row.get("translations") if isinstance(row.get("translations"), dict) else {},
        }
        if row.get("canonicalEnglishNeedsReview"):
            unresolved_ingredients.append(compact)
        if not isinstance(row.get("nutrition"), dict):
            nutrition_missing.append(compact)

    unresolved_recipes: list[dict[str, Any]] = []
    recipe_groups: list[str] = []
    variant_ids: list[str] = []
    languages = Counter()
    for row in recipes:
        grouping = _text(row.get("groupingFunctionalId"))
        if grouping:
            recipe_groups.append(grouping)
        variants = _variant_rows(row)
        for variant in variants:
            variant_id = _text(variant.get("variantId"))
            if variant_id:
                variant_ids.append(variant_id)
            language = _text(variant.get("language")).lower()
            if language:
                languages[language] += 1
        if row.get("canonicalEnglishNeedsReview"):
            unresolved_recipes.append(
                {
                    "groupingFunctionalId": grouping,
                    "canonicalName": _text(row.get("canonicalName")),
                    "variants": variants,
                }
            )

    catalog_rows = source.get("catalogs") if isinstance(source.get("catalogs"), list) else []
    failed_catalogs = [
        row
        for row in catalog_rows
        if isinstance(row, dict) and int(row.get("failedDetails") or 0) > 0
    ]
    empty_catalogs = [
        {
            "language": _text(row.get("language")),
            "country": _text(row.get("country")),
            "market": _text(row.get("market")),
        }
        for row in catalog_rows
        if isinstance(row, dict) and int(row.get("uniqueVariants") or 0) == 0
    ]

    duplicate_ingredient_ids = sorted(
        ident for ident, count in Counter(ingredient_ids).items() if ident and count > 1
    )
    duplicate_recipe_groups = sorted(
        ident for ident, count in Counter(recipe_groups).items() if ident and count > 1
    )
    duplicate_variant_ids = sorted(
        ident for ident, count in Counter(variant_ids).items() if ident and count > 1
    )

    integrity_ok = not (
        duplicate_ingredient_ids
        or duplicate_recipe_groups
        or duplicate_variant_ids
        or failed_catalogs
    )

    return {
        "catalogPath": str(source_path),
        "catalogSha256": _sha256(source_path),
        "catalogBytes": source_path.stat().st_size,
        "catalogVersion": _text(catalog.get("catalogVersion")),
        "generatedAt": _text(catalog.get("generatedAt")),
        "complete": bool(catalog.get("complete")),
        "counts": {
            "auditedCatalogs": int(source.get("auditedCatalogCount") or 0),
            "populatedCatalogs": int(source.get("sourceCatalogCount") or 0),
            "emptyCatalogs": int(source.get("emptyCatalogCount") or 0),
            "recipes": len(recipes),
            "recipeVariants": len(variant_ids),
            "ingredients": len(ingredients),
            "unresolvedCanonicalIngredientNames": len(unresolved_ingredients),
            "unresolvedCanonicalRecipeNames": len(unresolved_recipes),
            "nutritionResolved": len(ingredients) - len(nutrition_missing),
            "nutritionMissing": len(nutrition_missing),
            "failedDetailCatalogs": len(failed_catalogs),
        },
        "languageVariantCounts": dict(sorted(languages.items())),
        "emptyCatalogs": empty_catalogs,
        "failedCatalogs": failed_catalogs,
        "unresolvedIngredients": unresolved_ingredients,
        "unresolvedRecipes": unresolved_recipes,
        "nutritionMissing": nutrition_missing,
        "integrity": {
            "ok": integrity_ok,
            "duplicateIngredientIds": duplicate_ingredient_ids,
            "duplicateRecipeGroups": duplicate_recipe_groups,
            "duplicateVariantIds": duplicate_variant_ids,
        },
        "activationReady": bool(
            catalog.get("complete")
            and integrity_ok
            and not unresolved_ingredients
            and not unresolved_recipes
            and not nutrition_missing
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overrides-template", default="")
    args = parser.parse_args()

    catalog_path = Path(args.catalog).expanduser().resolve()
    report_path = Path(args.output).expanduser().resolve()
    report = summarize(_load(catalog_path), catalog_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if args.overrides_template:
        override_path = Path(args.overrides_template).expanduser().resolve()
        override_path.parent.mkdir(parents=True, exist_ok=True)
        overrides = {
            "ingredients": {
                row["id"]: ""
                for row in report["unresolvedIngredients"]
                if row.get("id")
            },
            "recipes": {
                row["groupingFunctionalId"]: ""
                for row in report["unresolvedRecipes"]
                if row.get("groupingFunctionalId")
            },
        }
        override_path.write_text(
            json.dumps(overrides, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "complete": report["complete"],
                "activationReady": report["activationReady"],
                **report["counts"],
                "integrityOk": report["integrity"]["ok"],
                "report": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
