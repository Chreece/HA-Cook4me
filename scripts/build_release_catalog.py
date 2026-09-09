#!/usr/bin/env python3
"""Build the immutable Cook4Me release catalog from every proven SEB language.

This is a maintainer/release tool, not runtime integration work. It performs the
expensive authenticated audit once, writes only compact stable identifiers and
evidence-safe nutrition to the repository snapshot, and deliberately excludes
runtime prices and full recipe steps.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.cook4me import recipe_languages, recipe_search_v8  # noqa: E402
from custom_components.cook4me.nutrition import (  # noqa: E402
    calculate_recipe_nutrition,
    lookup_food_data_central,
    normalize_nutrition,
)
from custom_components.cook4me.vendor import cook4me_phonefree as c4m  # noqa: E402
from custom_components.cook4me.vendor import cook4me_recipe_catalog as base_catalog  # noqa: E402
from custom_components.cook4me.vendor import cook4me_recipe_detail_enriched as enriched_detail  # noqa: E402

DEFAULT_OUTPUT = ROOT / "custom_components" / "cook4me" / "catalog" / "release_catalog.json"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_tokens(storage_home: Path, token_file: Path | None) -> dict[str, Any]:
    path = token_file or storage_home / ".config" / "cook4me" / "tokens.json"
    if not path.exists():
        raise SystemExit(f"Cook4Me token file not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read Cook4Me token file: {type(exc).__name__}") from exc
    if not isinstance(value, dict) or not value:
        raise SystemExit("Cook4Me token file contains no usable token object")
    return value


def _page_total(result: dict[str, Any], fallback: int) -> int:
    page = result.get("page") if isinstance(result.get("page"), dict) else {}
    value = page.get("totalPages")
    try:
        return max(1, int(value)) if value is not None else max(1, fallback)
    except (TypeError, ValueError):
        return max(1, fallback)


def _scan_language(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    *,
    language: str,
    country: str,
    app_version: str,
    max_pages: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    seen: set[str] = set()
    page = 0
    total_pages = 1
    while page < total_pages and page < max_pages:
        result = recipe_search_v8.search_recipes(
            cfg,
            tokens,
            "",
            page=page,
            size=50,
            max_details=0,
            country=country,
            language=language,
            configured_language=language,
            app_version=app_version,
        )
        rows = [row for row in result.get("items") or [] if isinstance(row, dict)]
        total_pages = _page_total(result, page + (1 if rows else 0))
        for row in rows:
            variant = _text(row.get("searchVariantId") or row.get("variantFunctionalId"))
            if not variant or variant in seen:
                continue
            seen.add(variant)
            current = deepcopy(row)
            current["auditLanguage"] = language
            current["auditCountry"] = country
            variants.append(current)
        print(f"[{language}] page {page + 1}/{total_pages}: {len(rows)} rows ({len(variants)} unique)")
        if not rows:
            break
        page += 1
    return variants, {
        "language": language,
        "country": country,
        "pagesScanned": page,
        "reportedPages": total_pages,
        "variantCount": len(variants),
        "truncated": bool(page >= max_pages and page < total_pages),
    }


def _hydrate_variant(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    row: dict[str, Any],
    *,
    app_version: str,
) -> dict[str, Any]:
    language = _text(row.get("auditLanguage")) or "en"
    country = _text(row.get("auditCountry")) or recipe_languages.country_for_language(language, "DE")
    variant = _text(row.get("searchVariantId") or row.get("variantFunctionalId"))
    detail = enriched_detail.recipe_detail(
        cfg,
        tokens,
        variant,
        country=country,
        language=language,
        configured_language=language,
        app_version=app_version,
    )
    detail["auditLanguage"] = language
    detail["auditCountry"] = country
    if not detail.get("cover") and row.get("cover"):
        detail["cover"] = row.get("cover")
    return detail


def _load_nutrition_export(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read nutrition export: {type(exc).__name__}") from exc
    if isinstance(raw, dict) and isinstance(raw.get("generic"), dict):
        raw = raw["generic"]
    return raw if isinstance(raw, dict) else {}


def _exported_nutrition(exported: dict[str, Any], food_key: str) -> dict[str, Any] | None:
    candidates = [food_key, f"k:{food_key}"]
    for key in candidates:
        row = exported.get(key)
        if isinstance(row, dict) and isinstance(row.get("nutrition"), dict):
            row = row["nutrition"]
        normalized = normalize_nutrition(row)
        if normalized is not None:
            return normalized
    return None


def _ingredient_catalog(
    details: list[dict[str, Any]],
    *,
    nutrition_export: dict[str, Any],
    fdc_api_key: str,
    fdc_delay: float,
    skip_fdc: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for recipe in details:
        language = _text(recipe.get("auditLanguage") or recipe.get("language")).lower()
        for item in recipe.get("ingredients") or []:
            if not isinstance(item, dict):
                continue
            key = _text(item.get("foodKey") or item.get("key"))
            name = _text(item.get("foodName") or item.get("name"))
            if not key or not name:
                continue
            row = by_key.setdefault(key, {"id": key, "names": {}})
            row["names"].setdefault(language, name)

    resolved = 0
    unresolved = 0
    missing_english = 0
    rows: list[dict[str, Any]] = []
    for index, key in enumerate(sorted(by_key), start=1):
        raw = by_key[key]
        names = dict(sorted(raw["names"].items()))
        canonical = _text(names.get("en"))
        fallback_language, fallback_name = next(iter(names.items()))
        row: dict[str, Any] = {
            "id": key,
            "canonicalName": canonical,
            "canonicalLanguage": "en" if canonical else "",
            "fallbackName": fallback_name,
            "fallbackLanguage": fallback_language,
            "names": names,
        }
        if not canonical:
            missing_english += 1

        nutrition = _exported_nutrition(nutrition_export, key)
        if nutrition is None and canonical and not skip_fdc:
            lookup = lookup_food_data_central(canonical, api_key=fdc_api_key or "DEMO_KEY")
            if lookup.get("ok") and isinstance(lookup.get("nutrition"), dict):
                nutrition = normalize_nutrition(lookup["nutrition"])
            if fdc_delay > 0:
                time.sleep(fdc_delay)
        if nutrition is not None:
            row["nutrition"] = nutrition
            resolved += 1
        else:
            unresolved += 1
        rows.append(row)
        if index % 50 == 0 or index == len(by_key):
            print(f"ingredients: {index}/{len(by_key)} nutrition={resolved} unresolved={unresolved}")
    return rows, {
        "ingredientCount": len(rows),
        "nutritionResolved": resolved,
        "nutritionUnresolved": unresolved,
        "nutritionCoverage": round(resolved / len(rows), 4) if rows else 0.0,
        "missingEnglishCanonical": missing_english,
    }


def _canonical_ingredient_map(ingredients: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in ingredients:
        key = _text(row.get("id"))
        name = _text(row.get("canonicalName")) or _text(row.get("fallbackName"))
        if key and name:
            out[key] = name
    return out


def _compact_ingredients(detail: dict[str, Any], names: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in detail.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        key = _text(raw.get("foodKey") or raw.get("key"))
        name = names.get(key) or _text(raw.get("foodName") or raw.get("name"))
        if not name and not key:
            continue
        row: dict[str, Any] = {"name": name}
        if key:
            row["foodKey"] = key
            row["key"] = key
            row["foodName"] = name
        for field in ("quantity", "unit", "unitKey", "functionalId"):
            if raw.get(field) not in (None, ""):
                row[field] = deepcopy(raw[field])
        out.append(row)
    return out


def _recipe_catalog(
    details: list[dict[str, Any]],
    ingredients: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for detail in details:
        variant = _text(detail.get("searchVariantId") or detail.get("variantFunctionalId"))
        grouping = _text(detail.get("groupingFunctionalId"))
        identity = grouping or variant
        if identity:
            groups.setdefault(identity, []).append(detail)

    canonical_names = _canonical_ingredient_map(ingredients)
    generic: dict[str, Any] = {}
    for ingredient in ingredients:
        key = _text(ingredient.get("id"))
        nutrition = ingredient.get("nutrition")
        if key and isinstance(nutrition, dict):
            generic[f"k:{key}"] = {"nutrition": deepcopy(nutrition)}

    rows: list[dict[str, Any]] = []
    missing_english = 0
    nutrition_covered = 0
    for identity in sorted(groups):
        variants = groups[identity]
        english = next((row for row in variants if _text(row.get("auditLanguage") or row.get("language")).lower() == "en"), None)
        chosen = english or variants[0]
        titles: dict[str, str] = {}
        compact_variants: list[dict[str, Any]] = []
        for raw in variants:
            language = _text(raw.get("auditLanguage") or raw.get("language")).lower()
            title = _text(raw.get("title"))
            if language and title:
                titles.setdefault(language, title)
            variant_id = _text(raw.get("searchVariantId") or raw.get("variantFunctionalId"))
            variant_row = {
                "language": language,
                "country": _text(raw.get("auditCountry")),
                "market": _text(raw.get("market")),
                "variantId": variant_id,
                "recipeFunctionalId": _text(raw.get("recipeFunctionalId") or raw.get("variantFunctionalId")),
                "groupingFunctionalId": _text(raw.get("groupingFunctionalId")),
                "cover": raw.get("cover"),
                "yield": deepcopy(raw.get("yield")),
                "groupSize": raw.get("groupSize"),
            }
            compact_variants.append({key: value for key, value in variant_row.items() if value not in (None, "", {})})

        canonical_title = _text((english or {}).get("title"))
        if not canonical_title:
            missing_english += 1
        recipe: dict[str, Any] = {
            "id": identity,
            "canonicalTitle": canonical_title,
            "canonicalLanguage": "en" if canonical_title else "",
            "fallbackTitle": _text(chosen.get("title")),
            "fallbackLanguage": _text(chosen.get("auditLanguage") or chosen.get("language")),
            "titles": dict(sorted(titles.items())),
            "variants": compact_variants,
            "ingredients": _compact_ingredients(chosen, canonical_names),
        }
        for field in (
            "cover",
            "courses",
            "occasions",
            "excludedFoods",
            "detectedExcludedFoods",
            "durations",
            "yield",
            "difficulty",
            "recipeType",
            "groupSize",
            "officialNutrition",
        ):
            if chosen.get(field) not in (None, "", [], {}):
                recipe[field] = deepcopy(chosen[field])

        calculated = calculate_recipe_nutrition(recipe, [], generic=generic, stock_lots={})
        if isinstance(calculated, dict):
            recipe["nutrition"] = calculated
            if float(calculated.get("coverage") or 0.0) > 0:
                nutrition_covered += 1
        rows.append(recipe)

    return rows, {
        "recipeCount": len(rows),
        "recipesWithCalculatedNutrition": nutrition_covered,
        "recipeNutritionCoverage": round(nutrition_covered / len(rows), 4) if rows else 0.0,
        "missingEnglishCanonical": missing_english,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    storage_home = Path(args.storage_home).expanduser()
    token_file = Path(args.token_file).expanduser() if args.token_file else None
    tokens = _load_tokens(storage_home, token_file)
    cfg = c4m.read_apk_config(None)

    all_light: list[dict[str, Any]] = []
    language_stats: list[dict[str, Any]] = []
    failed_languages: list[dict[str, str]] = []
    for spec in recipe_languages.SUPPORTED_RECIPE_LANGUAGES:
        language, country = spec["code"], spec["country"]
        try:
            rows, stats = _scan_language(
                cfg,
                tokens,
                language=language,
                country=country,
                app_version=args.app_version,
                max_pages=args.max_pages,
            )
        except Exception as exc:
            failed_languages.append({"language": language, "reason": type(exc).__name__})
            print(f"[{language}] FAILED: {type(exc).__name__}: {exc}")
            continue
        all_light.extend(rows)
        language_stats.append(stats)

    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in all_light:
        variant = _text(row.get("searchVariantId") or row.get("variantFunctionalId"))
        language = _text(row.get("auditLanguage"))
        if variant:
            unique.setdefault((language, variant), row)

    details: list[dict[str, Any]] = []
    failed_details: list[dict[str, str]] = []
    for index, row in enumerate(unique.values(), start=1):
        try:
            details.append(_hydrate_variant(cfg, tokens, row, app_version=args.app_version))
        except base_catalog.CatalogAuthError:
            raise
        except Exception as exc:
            failed_details.append(
                {
                    "language": _text(row.get("auditLanguage")),
                    "variantId": _text(row.get("searchVariantId")),
                    "reason": type(exc).__name__,
                }
            )
        if index % 25 == 0 or index == len(unique):
            print(f"details: {index}/{len(unique)} usable={len(details)} failed={len(failed_details)}")

    nutrition_export = _load_nutrition_export(
        Path(args.nutrition_export).expanduser() if args.nutrition_export else None
    )
    ingredients, ingredient_stats = _ingredient_catalog(
        details,
        nutrition_export=nutrition_export,
        fdc_api_key=args.fdc_api_key,
        fdc_delay=args.fdc_delay,
        skip_fdc=args.skip_fdc,
    )
    recipes, recipe_stats = _recipe_catalog(details, ingredients)

    truncated = any(bool(row.get("truncated")) for row in language_stats)
    complete = bool(
        recipes
        and ingredients
        and not failed_languages
        and not truncated
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "schemaVersion": 1,
        "release": {
            "id": args.release_id,
            "generatedAt": generated_at,
            "complete": complete,
            "sourceLanguages": [row["code"] for row in recipe_languages.SUPPORTED_RECIPE_LANGUAGES],
            "languageAudit": language_stats,
            "failedLanguages": failed_languages,
            "failedDetailCount": len(failed_details),
            "failedDetails": failed_details[:500],
            "ingredientStats": ingredient_stats,
            "recipeStats": recipe_stats,
            "sourceContract": recipe_search_v8.SEARCH_CONTRACT,
            "nutritionContract": "ingredient-derived-evidence-safe-v1",
            "costContract": "runtime-local-only-not-in-release-snapshot",
        },
        "ingredients": ingredients,
        "recipes": recipes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-home", default=str(Path.home()), help="Home containing .config/cook4me/tokens.json")
    parser.add_argument("--token-file", default="", help="Optional explicit Cook4Me token JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--release-id", default=datetime.now(timezone.utc).strftime("%Y.%m.%d-catalog1"))
    parser.add_argument("--app-version", default="36.0.0-RC3")
    parser.add_argument("--max-pages", type=int, default=1000)
    parser.add_argument("--nutrition-export", default="", help="Optional generic nutrition JSON keyed by M_FOOD_* or k:M_FOOD_*")
    parser.add_argument("--fdc-api-key", default="", help="USDA FoodData Central API key; DEMO_KEY is used when omitted")
    parser.add_argument("--fdc-delay", type=float, default=0.0, help="Delay between FDC lookups")
    parser.add_argument("--skip-fdc", action="store_true", help="Do not resolve missing ingredient nutrition online")
    args = parser.parse_args()

    payload = build(args)
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    release = payload["release"]
    print(
        f"wrote {output}: complete={release['complete']} "
        f"ingredients={len(payload['ingredients'])} recipes={len(payload['recipes'])} "
        f"failed_languages={len(release['failedLanguages'])} failed_details={release['failedDetailCount']}"
    )
    return 0 if release["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
