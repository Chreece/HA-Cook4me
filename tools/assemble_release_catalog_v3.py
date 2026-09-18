#!/usr/bin/env python3
"""Assemble the reviewed Cook4Me capture into the immutable runtime catalog.

This stage is deliberately network-free. It consumes the authoritative provider
capture plus the reviewed assembly preparation, preserves provider identities,
keeps keyless food identities local, compacts recipe variants, attaches optional
generic per-100-g nutrition, and refuses to activate a catalog while any
required evidence is unresolved.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import re
import unicodedata
from typing import Any


AUDITED_CATALOG_COUNT = 28
_MASS_TO_G = {"mg": 0.001, "g": 1.0, "kg": 1000.0}
_ALLOWED_KEYLESS_CLASSIFICATIONS = {"food", "equipment", "other"}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _number(value: Any) -> float | None:
    try:
        result = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def _load(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _validate_inputs(prep: dict[str, Any], provider: dict[str, Any]) -> None:
    if prep.get("kind") != "cook4me-release-assembly-prep":
        raise RuntimeError("expected cook4me-release-assembly-prep")
    if provider.get("kind") != "cook4me-provider-capture":
        raise RuntimeError("expected cook4me-provider-capture")
    policy = prep.get("identityPolicy") if isinstance(prep.get("identityPolicy"), dict) else {}
    required = {
        "recipeProviderIdentityAuthoritative": True,
        "translationNeverMergesRecipeGroups": True,
        "providerNativeTitlesPreserved": True,
        "unkeyedCrossLanguageMergeFromTranslation": False,
        "exactProviderFoodNameMatchesRemainCandidates": True,
    }
    for key, expected in required.items():
        if policy.get(key) is not expected:
            raise RuntimeError(f"reviewed preparation violates identity policy: {key}")


def _translation_map(row: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    by_language: dict[str, str] = {}
    conflicts: list[dict[str, Any]] = []
    values: dict[str, set[str]] = {}
    originals: dict[tuple[str, str], str] = {}
    for raw in row.get("translations") or []:
        if not isinstance(raw, dict):
            continue
        language = _text(raw.get("language")).lower()
        market = _text(raw.get("market")).upper()
        name = _text(raw.get("name"))
        if not language or not name:
            continue
        values.setdefault(language, set()).add(name)
        originals[(language, market)] = name
    for language, names in sorted(values.items()):
        if len({_norm(name) for name in names}) == 1:
            by_language[language] = sorted(names, key=str.casefold)[0]
        else:
            conflicts.append(
                {
                    "ingredientId": _text(row.get("key")),
                    "language": language,
                    "names": sorted(names, key=str.casefold),
                }
            )
    english = _text(row.get("canonicalEnglishName"))
    if english:
        by_language.setdefault("en", english)
    return by_language, conflicts


def _provider_ingredient_rows(
    prep: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], int]:
    result: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    unresolved = 0
    for raw in prep.get("providerFoods") or []:
        if not isinstance(raw, dict):
            continue
        key = _text(raw.get("key"))
        canonical = _text(raw.get("canonicalEnglishName"))
        if not key:
            continue
        if not canonical or _text(raw.get("translationTaskId")):
            unresolved += 1
        translations, row_conflicts = _translation_map(raw)
        conflicts.extend(row_conflicts)
        row: dict[str, Any] = {
            "id": key,
            "key": key,
            "canonicalName": canonical,
            "translations": translations,
            "identityKind": "provider",
            "usedByRecipe": bool(raw.get("usedByRecipe")),
        }
        result[key] = row
    return result, conflicts, unresolved


def _keyless_index(
    prep: dict[str, Any],
) -> tuple[
    dict[tuple[str, str], dict[str, Any]],
    dict[str, dict[str, Any]],
    int,
]:
    by_source: dict[tuple[str, str], dict[str, Any]] = {}
    food_ingredients: dict[str, dict[str, Any]] = {}
    unresolved = 0
    for raw in prep.get("unkeyedIngredients") or []:
        if not isinstance(raw, dict):
            continue
        language = _text(raw.get("sourceLanguage")).lower()
        source = _text(raw.get("sourceName"))
        local_id = _text(raw.get("localSyntheticIngredientId"))
        classification = _text(raw.get("classification")).lower()
        canonical = _text(raw.get("canonicalEnglishName"))
        if not language or not source:
            continue
        by_source[(language, _norm(source))] = raw
        semantic_unresolved = bool(_text(raw.get("translationTaskId"))) or classification not in _ALLOWED_KEYLESS_CLASSIFICATIONS
        if classification == "food" and (not canonical or not local_id):
            semantic_unresolved = True
        if semantic_unresolved:
            unresolved += 1
            continue
        if classification != "food":
            continue
        translations = {language: source}
        if canonical:
            translations.setdefault("en", canonical)
        food_ingredients[local_id] = {
            "id": local_id,
            "canonicalName": canonical,
            "translations": translations,
            "identityKind": "local-keyless",
            "sourceLanguage": language,
            "classification": "food",
        }
    return by_source, food_ingredients, unresolved


def _semantic_source(item: dict[str, Any]) -> str:
    for field in ("foodName", "applianceDescription", "applicationDescription", "cleanName"):
        value = _text(item.get(field))
        if value:
            return value
    return ""


def _semantic_source_stripped(item: dict[str, Any]) -> str:
    source = _semantic_source(item)
    if not source:
        return ""
    quantity = _number(item.get("quantity"))
    unit = item.get("unit") if isinstance(item.get("unit"), dict) else {}
    abbreviation = _text(unit.get("abbreviation"))
    name = _text(unit.get("name"))
    if quantity is None:
        return source
    quantity_forms = {f"{quantity:g}", f"{quantity:g}".replace(".", ",")}
    for quantity_text in sorted(quantity_forms, key=len, reverse=True):
        for unit_text in sorted({abbreviation, name} - {""}, key=len, reverse=True):
            pattern = (
                rf"^\s*{re.escape(quantity_text)}\s*{re.escape(unit_text)}"
                rf"(?=\s|[-–—,:;]|$)\s*[-–—,:;]?\s*"
            )
            cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
            if cleaned != source and _text(cleaned):
                return _text(cleaned)
        pattern = rf"^\s*{re.escape(quantity_text)}(?=\s)\s+"
        cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
        if cleaned != source and _text(cleaned):
            return _text(cleaned)
    return source


def _compact_unit(item: dict[str, Any]) -> tuple[str, str]:
    unit = item.get("unit")
    if isinstance(unit, dict):
        key = _text(unit.get("key"))
        value = _text(unit.get("abbreviation") or unit.get("name"))
        return value, key
    return _text(unit), _text(item.get("unitKey"))


def _compact_ingredient(
    item: dict[str, Any],
    *,
    language: str,
    provider_ingredients: dict[str, dict[str, Any]],
    keyless_by_source: dict[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    food_key = _text(item.get("foodKey"))
    source = _semantic_source_stripped(item)
    line_id = _text(item.get("lineFunctionalId"))
    unit, unit_key = _compact_unit(item)
    row: dict[str, Any] = {
        "originalName": source,
        "originalLanguage": language,
        "quantity": item.get("quantity"),
        "unit": unit,
        "unitKey": unit_key,
        "functionalId": line_id,
    }
    mapped = True
    if food_key:
        if food_key not in provider_ingredients:
            mapped = False
        row["ingredientId"] = food_key
        row["key"] = food_key
    else:
        semantic = keyless_by_source.get((language, _norm(source))) if source else None
        if not semantic:
            mapped = False
        else:
            classification = _text(semantic.get("classification")).lower()
            row["classification"] = classification
            if classification == "food":
                local_id = _text(semantic.get("localSyntheticIngredientId"))
                if local_id:
                    row["ingredientId"] = local_id
                else:
                    mapped = False
    return (
        {key: value for key, value in row.items() if value not in (None, "", {}, [])},
        mapped,
    )


def _mass_grams(item: dict[str, Any]) -> float | None:
    quantity = _number(item.get("quantity"))
    if quantity is None:
        return None
    unit = _text(item.get("unit")).lower()
    factor = _MASS_TO_G.get(unit)
    return quantity * factor if factor is not None else None


def _recipe_nutrition(
    ingredients: list[dict[str, Any]],
    nutrition: dict[str, dict[str, Any]],
    servings: Any,
) -> dict[str, Any]:
    totals: dict[str, float] = {}
    food_lines = 0
    covered = 0
    for item in ingredients:
        if _text(item.get("classification")) in {"equipment", "other"}:
            continue
        ident = _text(item.get("ingredientId"))
        if not ident:
            continue
        food_lines += 1
        profile = nutrition.get(ident)
        if not isinstance(profile, dict) or profile.get("basis") != "per100g":
            continue
        values = profile.get("values")
        grams = _mass_grams(item)
        if not isinstance(values, dict) or grams is None:
            continue
        for key, value in values.items():
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                totals[key] = totals.get(key, 0.0) + float(value) * grams / 100.0
        covered += 1
    serving_count = _number(servings)
    per_serving = {
        key: round(value / serving_count, 4)
        for key, value in totals.items()
        if serving_count and serving_count > 0
    }
    return {
        "totals": {key: round(value, 4) for key, value in totals.items()},
        "perServing": per_serving,
        "servings": serving_count,
        "coverage": round(covered / food_lines, 4) if food_lines else 0.0,
        "fullyCovered": bool(food_lines and covered == food_lines),
        "estimated": True,
        "sourceKinds": ["release_generic_per100g"],
    }


def assemble(
    prep: dict[str, Any],
    provider: dict[str, Any],
    *,
    catalog_version: str,
    nutrition: dict[str, dict[str, Any]] | None = None,
    allow_missing_nutrition: bool = False,
) -> dict[str, Any]:
    _validate_inputs(prep, provider)
    nutrition = nutrition or {}

    provider_ingredients, translation_conflicts, unresolved_provider_foods = _provider_ingredient_rows(prep)
    keyless_by_source, local_foods, unresolved_keyless = _keyless_index(prep)
    global_ingredients = {**provider_ingredients, **local_foods}

    groups_by_id = {
        _text(row.get("groupingFunctionalId")): row
        for row in prep.get("recipeGroups") or []
        if isinstance(row, dict) and _text(row.get("groupingFunctionalId"))
    }
    unresolved_groups = sum(
        not _text(row.get("canonicalEnglishTitle")) or bool(_text(row.get("translationTaskId")))
        for row in groups_by_id.values()
    )

    runtime_groups: dict[str, dict[str, Any]] = {}
    ingredient_mapping_failures = 0
    missing_group_reviews = 0
    for detail in provider.get("details") or []:
        if not isinstance(detail, dict):
            continue
        grouping = _text(
            detail.get("groupingFunctionalId")
            or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId")
            or detail.get("variantId")
        )
        variant_id = _text(detail.get("variantId"))
        if not grouping or not variant_id:
            continue
        reviewed_group = groups_by_id.get(grouping)
        if not reviewed_group:
            missing_group_reviews += 1
            continue
        language = _text(detail.get("language")).lower()
        ingredients: list[dict[str, Any]] = []
        for raw in detail.get("ingredients") or []:
            if not isinstance(raw, dict):
                continue
            compact, mapped = _compact_ingredient(
                raw,
                language=language,
                provider_ingredients=provider_ingredients,
                keyless_by_source=keyless_by_source,
            )
            if not mapped:
                ingredient_mapping_failures += 1
            ingredients.append(compact)

        variant: dict[str, Any] = {
            "variantId": variant_id,
            "recipeFunctionalId": _text(detail.get("recipeFunctionalId") or variant_id),
            "groupingFunctionalId": grouping,
            "title": _text(detail.get("title") or detail.get("normalizedTitle")),
            "originalTitle": _text(detail.get("title") or detail.get("normalizedTitle")),
            "language": language,
            "originalLanguage": language,
            "market": _text(detail.get("market")).upper(),
            "cover": _text(detail.get("cover")),
            "servings": detail.get("servings"),
            "yield": deepcopy(detail.get("yield")),
            "durations": deepcopy(detail.get("durations")),
            "difficulty": detail.get("difficulty"),
            "ingredients": ingredients,
        }
        variant["nutrition"] = _recipe_nutrition(
            ingredients,
            nutrition,
            detail.get("servings"),
        )
        variant = {
            key: value
            for key, value in variant.items()
            if value not in (None, "", {}, [])
        }
        group = runtime_groups.setdefault(
            grouping,
            {
                "groupingFunctionalId": grouping,
                "canonicalName": _text(reviewed_group.get("canonicalEnglishTitle")),
                "variants": [],
            },
        )
        group["variants"].append(variant)

    for group in runtime_groups.values():
        group["variants"].sort(
            key=lambda row: (
                _text(row.get("language")),
                _text(row.get("market")),
                _text(row.get("variantId")),
            )
        )

    for ident, row in global_ingredients.items():
        profile = nutrition.get(ident)
        if isinstance(profile, dict) and isinstance(profile.get("values"), dict):
            row["nutrition"] = deepcopy(profile)

    catalogs = provider.get("source", {}).get("catalogs") if isinstance(provider.get("source"), dict) else []
    catalogs = [row for row in (catalogs or []) if isinstance(row, dict)]
    audited_count = int(provider.get("source", {}).get("auditedCatalogCount") or len(catalogs)) if isinstance(provider.get("source"), dict) else len(catalogs)
    unresolved_variants = sum(int(row.get("unresolvedVariants") or 0) for row in catalogs)
    populated_count = sum(_text(row.get("state")).upper() == "POPULATED" for row in catalogs)
    empty_count = sum(_text(row.get("state")).upper() == "EMPTY" for row in catalogs)

    nutrition_required_ids = set(global_ingredients)
    nutrition_resolved_ids = {
        ident
        for ident in nutrition_required_ids
        if isinstance(nutrition.get(ident), dict)
        and isinstance(nutrition[ident].get("values"), dict)
        and nutrition[ident].get("basis") == "per100g"
    }
    missing_nutrition = sorted(nutrition_required_ids - nutrition_resolved_ids)

    semantic_complete = not (
        unresolved_provider_foods
        or unresolved_keyless
        or unresolved_groups
        or translation_conflicts
        or ingredient_mapping_failures
        or missing_group_reviews
    )
    hydration_complete = audited_count == AUDITED_CATALOG_COUNT and len(catalogs) == AUDITED_CATALOG_COUNT and unresolved_variants == 0
    nutrition_complete = not missing_nutrition
    complete = bool(
        semantic_complete
        and hydration_complete
        and runtime_groups
        and global_ingredients
        and (allow_missing_nutrition or nutrition_complete)
    )

    source = provider.get("source") if isinstance(provider.get("source"), dict) else {}
    payload = {
        "schemaVersion": 1,
        "catalogVersion": _text(catalog_version),
        "complete": complete,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "contract": _text(source.get("contract")) or "standalone-proven-cookeo-brand-v5",
            "format": "reviewed-normalized-ingredient-references-v3",
            "applianceGroup": _text(source.get("applianceGroup")),
            "recipeType": _text(source.get("recipeType")),
            "auditedCatalogCount": audited_count,
            "sourceCatalogCount": populated_count,
            "emptyCatalogCount": empty_count,
            "catalogs": deepcopy(catalogs),
            "providerGeneratedAt": _text(provider.get("generatedAt")),
            "reviewedPreparationGeneratedAt": _text(prep.get("generatedAt")),
            "providerNativeNamesStored": True,
            "providerIngredientIdentityAuthoritative": True,
            "keylessFoodIdentityLocalOnly": True,
            "translationNeverMergesRecipeGroups": True,
            "fullRecipeDetailStored": False,
            "officialSebDetailStored": False,
            "pricesStored": False,
            "secretsPersisted": False,
            "unresolvedProviderFoods": unresolved_provider_foods,
            "unresolvedKeylessSemantics": unresolved_keyless,
            "unresolvedRecipeGroups": unresolved_groups,
            "providerTranslationConflicts": len(translation_conflicts),
            "ingredientMappingFailures": ingredient_mapping_failures,
            "missingGroupReviews": missing_group_reviews,
            "unresolvedProviderVariants": unresolved_variants,
            "nutritionResolvedCount": len(nutrition_resolved_ids),
            "nutritionRequiredCount": len(nutrition_required_ids),
            "nutritionMissingCount": len(missing_nutrition),
            "nutritionRequiredForComplete": not allow_missing_nutrition,
        },
        "ingredients": sorted(
            (
                {
                    key: value
                    for key, value in row.items()
                    if value not in (None, "", {}, [])
                }
                for row in global_ingredients.values()
            ),
            key=lambda row: (_norm(row.get("canonicalName")), _text(row.get("id"))),
        ),
        "recipes": sorted(
            runtime_groups.values(),
            key=lambda row: (_norm(row.get("canonicalName")), _text(row.get("groupingFunctionalId"))),
        ),
    }
    if translation_conflicts:
        payload["source"]["translationConflicts"] = translation_conflicts
    if missing_nutrition:
        payload["source"]["missingNutritionIngredientIds"] = missing_nutrition
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-prep", required=True)
    parser.add_argument("--provider-capture", required=True)
    parser.add_argument("--catalog-version", required=True)
    parser.add_argument("--nutrition-cache", default="")
    parser.add_argument("--allow-missing-nutrition", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    prep = _load(Path(args.reviewed_prep).expanduser())
    provider = _load(Path(args.provider_capture).expanduser())
    nutrition_raw = _load(Path(args.nutrition_cache).expanduser()) if args.nutrition_cache else {}
    nutrition = {
        _text(key): value
        for key, value in nutrition_raw.items()
        if _text(key) and isinstance(value, dict)
    }
    payload = assemble(
        prep,
        provider,
        catalog_version=args.catalog_version,
        nutrition=nutrition,
        allow_missing_nutrition=args.allow_missing_nutrition,
    )
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "catalogVersion": payload["catalogVersion"],
                "complete": payload["complete"],
                "recipes": len(payload["recipes"]),
                "ingredients": len(payload["ingredients"]),
                "unresolvedProviderFoods": payload["source"]["unresolvedProviderFoods"],
                "unresolvedKeylessSemantics": payload["source"]["unresolvedKeylessSemantics"],
                "unresolvedRecipeGroups": payload["source"]["unresolvedRecipeGroups"],
                "unresolvedProviderVariants": payload["source"]["unresolvedProviderVariants"],
                "ingredientMappingFailures": payload["source"]["ingredientMappingFailures"],
                "nutritionMissingCount": payload["source"]["nutritionMissingCount"],
                "outputBytes": output.stat().st_size,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
