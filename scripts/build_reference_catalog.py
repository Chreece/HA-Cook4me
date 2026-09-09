#!/usr/bin/env python3
"""Build the release-bundled Cook4Me reference catalog.

This is deliberately a *manual maintainer tool*. It reads an already-authenticated
local Cook4Me token store, but the generated catalog contains only sanitized
reference data. Never run this in GitHub Actions and never commit tokens,
credentials, HTTP headers, account identifiers or other user data.

Typical use from an environment where HA-Cook4me's Python dependencies exist:

  python scripts/build_reference_catalog.py \
      --storage-home /path/to/cook4me-storage-home \
      --fdc-api-key "$FDC_API_KEY" \
      --output custom_components/cook4me/data/reference_catalog.json

The builder is intentionally conservative: missing IDs/nutrition stay missing;
it never invents an SEB identity, density, piece weight, unit conversion or
English translation.
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
sys.path.insert(0, str(ROOT))

from custom_components.cook4me import recipe_languages  # noqa: E402
from custom_components.cook4me.ingredient_catalog import marketing_food_items  # noqa: E402
from custom_components.cook4me.nutrition import lookup_food_data_central  # noqa: E402
from custom_components.cook4me.reference_catalog import (  # noqa: E402
    SCHEMA_VERSION,
    calculate_reference_recipe_nutrition,
    validate_reference_catalog,
)
from custom_components.cook4me import recipe_search_v8  # noqa: E402
from custom_components.cook4me.vendor import cook4me_phonefree as c4m  # noqa: E402
from custom_components.cook4me.vendor import cook4me_recipe_catalog as catalog  # noqa: E402


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_tokens(storage_home: Path) -> dict[str, Any]:
    path = storage_home / ".config" / "cook4me" / "tokens.json"
    if not path.exists():
        raise SystemExit(f"Cook4Me token file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise SystemExit("Cook4Me token file is empty or invalid")
    return payload


def _language_rows(selected: list[str]) -> list[dict[str, str]]:
    all_rows = recipe_languages.language_options()
    if not selected:
        return all_rows
    wanted = {
        value.lower().replace("_", "-").split("-", 1)[0]
        for value in selected
        if value
    }
    rows = [row for row in all_rows if row["code"] in wanted]
    missing = wanted - {row["code"] for row in rows}
    if missing:
        raise SystemExit("Unsupported catalog languages: " + ", ".join(sorted(missing)))
    return rows


def _fetch_marketing_foods(cfg, tokens, *, country: str, language: str, configured_language: str, app_version: str) -> list[dict[str, str]]:
    market = f"GS_{country}"
    pcfg = catalog._platform_context(cfg, country, configured_language, app_version)
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/datarefs/marketingFoods/search"
    payload, _auth_mode = catalog._http_json(
        "POST",
        url,
        headers_iter=catalog._request_headers(
            cfg,
            tokens,
            country,
            configured_language,
            app_version,
            url,
            pcfg,
        ),
        params={"lang": language, "market": market, "size": 5000},
        body={},
    )
    return marketing_food_items(payload, language)


def _merge_ingredients(target: dict[str, dict[str, Any]], rows: list[dict[str, str]], *, language: str) -> None:
    for row in rows:
        identity = _text(row.get("key"))
        name = _text(row.get("name"))
        if not identity or not name:
            continue
        current = target.setdefault(identity, {"id": identity, "names": {}})
        current["names"][language] = name


def _page_recipes(cfg, tokens, *, country: str, language: str, configured_language: str, app_version: str, max_pages: int) -> list[dict[str, Any]]:
    pcfg = catalog._platform_context(cfg, country, configured_language, app_version)
    out: list[dict[str, Any]] = []
    for page in range(max_pages):
        payload, rows, _auth_mode = recipe_search_v8._page_request(
            cfg,
            tokens,
            pcfg,
            query="",
            page=page,
            size=50,
            country=country,
            language=language,
            configured_language=configured_language,
            app_version=app_version,
            appliance_group=recipe_search_v8.DEFAULT_APPLIANCE_GROUP,
            recipe_type=recipe_search_v8.DEFAULT_RECIPE_TYPE,
        )
        out.extend(rows)
        page_info = payload.get("page") if isinstance(payload, dict) and isinstance(payload.get("page"), dict) else {}
        total_pages = page_info.get("totalPages")
        number = page_info.get("number", page)
        if not rows:
            break
        try:
            if total_pages is not None and int(number) + 1 >= int(total_pages):
                break
        except (TypeError, ValueError):
            pass
    return out


def _merge_recipe_index(target: dict[str, dict[str, Any]], rows: list[dict[str, Any]], *, language: str, country: str) -> None:
    for row in rows:
        variant_id = _text(row.get("searchVariantId") or row.get("variantFunctionalId"))
        grouping_id = _text(row.get("groupingFunctionalId")) or variant_id
        title = _text(row.get("title"))
        if not grouping_id or not variant_id:
            continue
        current = target.setdefault(
            grouping_id,
            {
                "id": grouping_id,
                "groupingFunctionalId": grouping_id,
                "names": {},
                "variants": [],
            },
        )
        if title:
            current["names"][language] = title
        if not current.get("cover") and row.get("cover"):
            current["cover"] = row.get("cover")
        variant = {
            "language": language,
            "country": country,
            "market": _text(row.get("market")) or f"GS_{country}",
            "variantId": variant_id,
            "recipeFunctionalId": _text(row.get("recipeFunctionalId") or row.get("variantFunctionalId") or variant_id),
        }
        key = (variant["language"], variant["variantId"])
        if key not in {
            (_text(item.get("language")), _text(item.get("variantId")))
            for item in current["variants"]
            if isinstance(item, dict)
        }:
            current["variants"].append(variant)


def _representative_variant(recipe: dict[str, Any]) -> dict[str, Any] | None:
    variants = [row for row in recipe.get("variants") or [] if isinstance(row, dict)]
    if not variants:
        return None
    return next((row for row in variants if row.get("language") == "en"), variants[0])


def _hydrate_recipe(cfg, tokens, recipe: dict[str, Any], *, configured_language: str, app_version: str) -> None:
    variant = _representative_variant(recipe)
    if not variant:
        return
    language = _text(variant.get("language")) or configured_language
    country = _text(variant.get("country")) or recipe_languages.country_for_language(language, "DE")
    detail = catalog.recipe_detail(
        cfg,
        tokens,
        _text(variant.get("variantId")),
        country=country,
        language=language,
        configured_language=configured_language,
        app_version=app_version,
    )
    if detail.get("cover"):
        recipe["cover"] = detail["cover"]
    for key in ("yield", "groupSize", "courses", "occasions", "durations", "difficulty", "recipeType"):
        if detail.get(key) not in (None, ""):
            recipe[key] = deepcopy(detail[key])
    servings = None
    yield_data = detail.get("yield") if isinstance(detail.get("yield"), dict) else {}
    for value in (yield_data.get("quantity"), detail.get("groupSize")):
        try:
            number = float(value)
            if number > 0:
                servings = number
                break
        except (TypeError, ValueError):
            pass
    if servings is not None:
        recipe["servings"] = servings
    ingredients: list[dict[str, Any]] = []
    for raw in detail.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        identity = _text(raw.get("foodKey") or raw.get("key"))
        row: dict[str, Any] = {}
        if identity:
            row["id"] = identity
        if raw.get("quantity") not in (None, ""):
            row["quantity"] = raw.get("quantity")
        if raw.get("unit") not in (None, ""):
            row["unit"] = raw.get("unit")
        if row:
            ingredients.append(row)
    recipe["ingredients"] = ingredients


def _finalize_canonical_names(ingredients: dict[str, dict[str, Any]], recipes: dict[str, dict[str, Any]], *, strict_english: bool) -> None:
    missing: list[str] = []
    for collection, kind in ((ingredients, "ingredient"), (recipes, "recipe")):
        for identity, row in collection.items():
            names = row.get("names") if isinstance(row.get("names"), dict) else {}
            english = _text(names.get("en"))
            if english:
                row["canonicalName"] = english
                row["canonicalLanguage"] = "en"
                continue
            fallback_language = next((language for language in sorted(names) if _text(names.get(language))), "")
            fallback = _text(names.get(fallback_language))
            if fallback:
                row["canonicalName"] = fallback
                row["canonicalLanguage"] = fallback_language
            else:
                row["canonicalName"] = identity
                row["canonicalLanguage"] = "id"
            missing.append(f"{kind}:{identity}")
    if strict_english and missing:
        raise SystemExit(
            "Canonical English names are missing for "
            + str(len(missing))
            + " entries; first examples: "
            + ", ".join(missing[:20])
        )


def _resolve_nutrition(ingredients: dict[str, dict[str, Any]], *, api_key: str, delay: float, limit: int | None) -> None:
    attempted = 0
    for identity in sorted(ingredients):
        row = ingredients[identity]
        if isinstance(row.get("nutrition"), dict):
            continue
        if limit is not None and attempted >= limit:
            break
        query = _text(row.get("canonicalName"))
        if not query or row.get("canonicalLanguage") != "en":
            row["nutritionStatus"] = "missing_canonical_english_name"
            continue
        attempted += 1
        result = lookup_food_data_central(query, api_key=api_key)
        if result.get("ok") and isinstance(result.get("nutrition"), dict):
            row["nutrition"] = result["nutrition"]
            row["nutritionStatus"] = "resolved"
            row["nutritionMatchConfidence"] = result.get("confidence")
            row["nutritionReferenceId"] = result.get("fdcId")
        else:
            row["nutritionStatus"] = _text(result.get("reason")) or "unresolved"
            if result.get("confidence") is not None:
                row["nutritionMatchConfidence"] = result.get("confidence")
        if delay > 0:
            time.sleep(delay)


def _compute_recipe_nutrition(ingredients: dict[str, dict[str, Any]], recipes: dict[str, dict[str, Any]]) -> None:
    for recipe in recipes.values():
        recipe["nutrition"] = calculate_reference_recipe_nutrition(recipe, ingredients)


def build(args) -> dict[str, Any]:
    storage_home = Path(args.storage_home).expanduser().resolve()
    tokens = _load_tokens(storage_home)
    cfg = c4m.read_apk_config(None)
    configured_language = args.configured_language.lower()
    languages = _language_rows(args.language)

    ingredients: dict[str, dict[str, Any]] = {}
    recipes: dict[str, dict[str, Any]] = {}

    for index, language_row in enumerate(languages, 1):
        language = language_row["code"]
        country = language_row["country"]
        print(f"[{index}/{len(languages)}] ingredients {language}/{country}", flush=True)
        foods = _fetch_marketing_foods(
            cfg,
            tokens,
            country=country,
            language=language,
            configured_language=configured_language,
            app_version=args.app_version,
        )
        _merge_ingredients(ingredients, foods, language=language)

        print(f"[{index}/{len(languages)}] recipes {language}/{country}", flush=True)
        index_rows = _page_recipes(
            cfg,
            tokens,
            country=country,
            language=language,
            configured_language=configured_language,
            app_version=args.app_version,
            max_pages=args.max_pages,
        )
        _merge_recipe_index(recipes, index_rows, language=language, country=country)

    _finalize_canonical_names(ingredients, recipes, strict_english=args.strict_english)

    if not args.skip_recipe_details:
        recipe_rows = [recipes[key] for key in sorted(recipes)]
        for index, recipe in enumerate(recipe_rows, 1):
            print(f"[detail {index}/{len(recipe_rows)}] {recipe.get('canonicalName')}", flush=True)
            try:
                _hydrate_recipe(
                    cfg,
                    tokens,
                    recipe,
                    configured_language=configured_language,
                    app_version=args.app_version,
                )
            except Exception as exc:
                recipe["detailAuditError"] = type(exc).__name__

    if not args.skip_nutrition:
        _resolve_nutrition(
            ingredients,
            api_key=args.fdc_api_key or "DEMO_KEY",
            delay=max(0.0, args.fdc_delay),
            limit=args.nutrition_limit,
        )
    _compute_recipe_nutrition(ingredients, recipes)

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "catalogVersion": args.catalog_version,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "manual-release-audit",
        "populationComplete": len(languages) == len(recipe_languages.language_options()),
        "languages": languages,
        "ingredients": [ingredients[key] for key in sorted(ingredients)],
        "recipes": [recipes[key] for key in sorted(recipes)],
        "audit": {
            "ingredientCount": len(ingredients),
            "recipeCount": len(recipes),
            "languagesAudited": [row["code"] for row in languages],
            "nutritionResolved": sum(isinstance(row.get("nutrition"), dict) for row in ingredients.values()),
            "nutritionMissing": sum(not isinstance(row.get("nutrition"), dict) for row in ingredients.values()),
            "containsCredentials": False,
            "containsUserData": False,
        },
    }
    validate_reference_catalog(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", required=True)
    parser.add_argument("--output", default=str(ROOT / "custom_components/cook4me/data/reference_catalog.json"))
    parser.add_argument("--catalog-version", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--app-version", default="36.0.0-RC3")
    parser.add_argument("--language", action="append", default=[], help="Audit only this language; repeatable. Default: all proven catalogs.")
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--fdc-api-key", default="")
    parser.add_argument("--fdc-delay", type=float, default=0.0)
    parser.add_argument("--nutrition-limit", type=int, default=None)
    parser.add_argument("--skip-nutrition", action="store_true")
    parser.add_argument("--skip-recipe-details", action="store_true")
    parser.add_argument("--strict-english", action="store_true", help="Fail if any merged ID has no proven English catalog name.")
    args = parser.parse_args()

    payload = build(args)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote sanitized reference catalog: {output} "
        f"({len(payload['ingredients'])} ingredients, {len(payload['recipes'])} recipes)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
