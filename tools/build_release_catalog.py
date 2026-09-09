#!/usr/bin/env python3
"""Build the reviewed, immutable Cook4Me release catalog.

Maintenance only: re-audit all 28 known language/market mappings, exhaustively
page every currently populated Cookeo catalog, hydrate each publication once,
merge stable recipe/ingredient IDs, resolve canonical English labels and generic
per-100-g nutrition, then write a normalized compact repo index.

The repo index intentionally stores ingredient translations/nutrition once in a
global ingredient table. Recipe variants reference those ingredients by ID and
store only lightweight card/ranking facts plus precomputed generic meal
nutrition. Steps, full official SEB nutrition detail, prices, account tokens and
provider secrets are never persisted in this release index.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
VENDOR = COMPONENT / "vendor"
for path in (COMPONENT, VENDOR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cook4me_phonefree as c4m  # type: ignore  # noqa: E402
import cook4me_recipe_catalog as catalog  # type: ignore  # noqa: E402

APP_VERSION = "36.0.0-RC3"
PAGE_SIZE = 50
FDC_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_MASS_TO_G = {"mg": 0.001, "g": 1.0, "kg": 1000.0}

# Re-check every exact mapping from the proven 2026-09-06 read-only audit on
# every release. Seven were empty then; they are deliberately retained here so
# a future SEB catalog appearing in one of those mappings is picked up without
# an architecture change.
AUDITED_CATALOGS: tuple[tuple[str, str], ...] = (
    ("ar", "AE"),
    ("bg", "BG"),
    ("cs", "CZ"),
    ("da", "DK"),
    ("de", "DE"),
    ("el", "GR"),
    ("en", "GB"),
    ("es", "ES"),
    ("fa", "AE"),
    ("fi", "FI"),
    ("fr", "FR"),
    ("hr", "HR"),
    ("hu", "HU"),
    ("it", "IT"),
    ("ja", "JP"),
    ("ko", "KR"),
    ("nl", "NL"),
    ("no", "NO"),
    ("pl", "PL"),
    ("pt", "PT"),
    ("ro", "RO"),
    ("ru", "RU"),
    ("sk", "SK"),
    ("sl", "SI"),
    ("sv", "SE"),
    ("tr", "TR"),
    ("uk", "UA"),
    ("zh", "TW"),
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _number(value: Any) -> float | None:
    try:
        out = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) and out >= 0 else None


def _fid(value: Any) -> str:
    return _text(catalog._fid(value))


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deepcopy(default)


def _save_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def _tokens(storage_home: Path) -> dict[str, Any]:
    raw = _load_json(storage_home / ".config" / "cook4me" / "tokens.json", {})
    return raw if isinstance(raw, dict) else {}


def app_search_body(language: str, market: str) -> dict[str, Any]:
    return {
        "fieldFilters": [
            {"field": "lang.key", "values": [_text(language).lower()]},
            {"field": "market.key", "values": [_text(market).upper()]},
            {
                "field": "applianceGroups.reference.key",
                "values": ["APPLIANCE_GROUP_15"],
            },
            {"field": "topRecipe.type.key", "values": ["BRAND"]},
        ]
    }


def _headers(cfg, tokens, country, configured_language, url, pcfg):
    return catalog._request_headers(
        cfg, tokens, country, configured_language, APP_VERSION, url, pcfg
    )


def _all_search_rows(
    cfg,
    tokens,
    pcfg,
    *,
    language: str,
    country: str,
    configured_language: str,
    configured_country: str,
) -> list[dict[str, Any]]:
    market = f"GS_{country}"
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/v4/search/recipes"
    rows: list[dict[str, Any]] = []
    page = 0
    total_pages: int | None = None
    while total_pages is None or page < total_pages:
        payload, _auth = catalog._http_json(
            "POST",
            url,
            headers_iter=_headers(
                cfg,
                tokens,
                configured_country,
                configured_language,
                url,
                pcfg,
            ),
            params={
                "lang": language,
                "market": market,
                "page": page,
                "size": PAGE_SIZE,
                "q": "",
                "groupBy": "",
                "myUniverse": "false",
                "myOwnRecipe": "false",
                "withAutomaticSpellcheck": "true",
            },
            body=app_search_body(language, market),
            timeout=30,
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"{language}/{market}: invalid search response")
        content = payload.get("content") if isinstance(payload.get("content"), list) else []
        for raw in content:
            if isinstance(raw, dict) and (row := catalog._light_search_row(raw)):
                rows.append(row)
        page_info = payload.get("page") if isinstance(payload.get("page"), dict) else {}
        try:
            total_pages = int(page_info.get("totalPages"))
        except (TypeError, ValueError):
            total_pages = page + (1 if content else 0)
        page += 1
        if not content:
            break
    return rows


def _detail(
    cfg,
    tokens,
    pcfg,
    *,
    variant_id: str,
    source_language: str,
    configured_language: str,
    configured_country: str,
) -> dict[str, Any]:
    """Hydrate only release-index facts; full detail remains runtime-cached."""
    variant = _fid(variant_id)
    url = (
        cfg["platform_base_url"].rstrip("/")
        + "/common-api/v3/recipes/PRO/"
        + urllib.parse.quote(variant, safe="")
        + "/?format=mobile"
    )
    payload, _auth = catalog._http_json(
        "GET",
        url,
        headers_iter=_headers(
            cfg,
            tokens,
            configured_country,
            configured_language,
            url,
            pcfg,
        ),
        timeout=30,
    )
    root = catalog._recipe_root(payload)
    grouping = _fid(root.get("groupingId")) or _fid(root.get("topRecipeId"))
    recipe_id = _fid(root.get("fid")) or _fid(root.get("identifier")) or variant
    return {
        "variantId": variant,
        "recipeFunctionalId": recipe_id,
        "groupingFunctionalId": grouping,
        "title": catalog._clean_text(
            root.get("title") or root.get("shortTitle") or root.get("normalizedTitle")
        ),
        "language": catalog._clean_text(root.get("lang")) or source_language,
        "market": catalog._clean_text(root.get("market")),
        "cover": catalog.extract_recipe_cover(root),
        "servings": (catalog._yield(root) or {}).get("quantity") or root.get("groupSize"),
        "yield": catalog._yield(root),
        "durations": catalog._durations(root),
        "difficulty": root.get("difficulty"),
        "ingredients": catalog.extract_recipe_ingredients(root),
    }


def _ingredient_id(item: dict[str, Any]) -> str:
    explicit = _text(item.get("ingredientId") or item.get("id"))
    if explicit:
        return explicit
    key = _text(item.get("foodKey") or item.get("key"))
    if key:
        return key
    name = _text(
        item.get("canonicalName")
        or item.get("foodName")
        or item.get("name")
    ).casefold()
    return "name:" + name if name else ""


def _fdc_nutrient(
    food: dict[str, Any], tokens: tuple[str, ...], unit: str | None = None
) -> float | None:
    rows = food.get("foodNutrients") if isinstance(food.get("foodNutrients"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("nutrientName") or row.get("name")).casefold()
        row_unit = _text(row.get("unitName") or row.get("unit")).casefold()
        if unit and row_unit != unit.casefold():
            continue
        if any(token in name for token in tokens):
            value = _number(row.get("value") if "value" in row else row.get("amount"))
            if value is not None:
                return value
    return None


def _fdc_profile(food: dict[str, Any], query: str) -> dict[str, Any] | None:
    values = {
        "energyKcal": _fdc_nutrient(food, ("energy",), "kcal"),
        "energyKJ": _fdc_nutrient(food, ("energy",), "kj"),
        "protein": _fdc_nutrient(food, ("protein",)),
        "carbohydrates": _fdc_nutrient(
            food, ("carbohydrate by difference", "carbohydrate")
        ),
        "sugars": _fdc_nutrient(food, ("total sugars", "sugars total")),
        "fat": _fdc_nutrient(food, ("total lipid fat", "total fat")),
        "saturatedFat": _fdc_nutrient(
            food, ("fatty acids total saturated", "saturated fat")
        ),
        "fiber": _fdc_nutrient(food, ("fiber total dietary", "dietary fiber")),
    }
    sodium_mg = _fdc_nutrient(food, ("sodium na", "sodium"), "mg")
    if sodium_mg is not None:
        values["sodium"] = sodium_mg / 1000.0
        values["salt"] = values["sodium"] * 2.5
    values = {key: value for key, value in values.items() if value is not None}
    if "energyKcal" not in values and "energyKJ" in values:
        values["energyKcal"] = values["energyKJ"] / 4.184
    if "energyKJ" not in values and "energyKcal" in values:
        values["energyKJ"] = values["energyKcal"] * 4.184
    if not values:
        return None
    return {
        "basis": "per100g",
        "values": {key: round(value, 4) for key, value in values.items()},
        "source": "usda_fdc",
        "sourceId": food.get("fdcId"),
        "sourceDescription": _text(food.get("description")),
        "query": query,
    }


def _lookup_fdc(query: str, key: str) -> dict[str, Any] | None:
    body = json.dumps(
        {"query": query, "pageSize": 8, "dataType": ["Foundation", "SR Legacy"]}
    ).encode()
    request = urllib.request.Request(
        FDC_URL + "?api_key=" + urllib.parse.quote(key),
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "HA-Cook4me-release-builder/1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    foods = payload.get("foods") if isinstance(payload, dict) else []
    for food in foods if isinstance(foods, list) else []:
        if isinstance(food, dict) and (profile := _fdc_profile(food, query)):
            return profile
    return None


def _recipe_nutrition(
    ingredients: list[dict[str, Any]],
    nutrition: dict[str, dict[str, Any]],
    servings: Any,
) -> dict[str, Any]:
    """Calculate only evidence-safe mass-based generic release nutrition."""
    totals: dict[str, float] = {}
    covered = 0
    for item in ingredients:
        ident = _ingredient_id(item)
        profile = nutrition.get(ident) or {}
        values = profile.get("values") if profile.get("basis") == "per100g" else None
        qty = _number(item.get("quantity"))
        unit = _text(item.get("unit")).lower()
        if not isinstance(values, dict) or qty is None or unit not in _MASS_TO_G:
            continue
        factor = qty * _MASS_TO_G[unit] / 100.0
        for key, value in values.items():
            if isinstance(value, (int, float)):
                totals[key] = totals.get(key, 0.0) + float(value) * factor
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
        "coverage": round(covered / len(ingredients), 4) if ingredients else 0.0,
        "fullyCovered": bool(ingredients and covered == len(ingredients)),
        "estimated": True,
        "sourceKinds": ["release_generic_per100g"],
    }


def _compact_variant_ingredient(
    item: dict[str, Any], ingredients: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    ident = _ingredient_id(item)
    global_row = ingredients.get(ident) or {}
    key = _text(item.get("foodKey") or item.get("key") or global_row.get("key"))
    row = {
        "ingredientId": ident,
        "key": key,
        "quantity": item.get("quantity"),
        "unit": item.get("unit"),
        "unitKey": item.get("unitKey"),
    }
    # A name-only fallback has no provider key, so retain one canonical label to
    # keep the reference understandable/recoverable without duplicating all
    # translations into every recipe.
    if not key:
        row["canonicalName"] = _text(global_row.get("canonicalName")) or _text(
            item.get("foodName") or item.get("name")
        )
    return {
        name: value
        for name, value in row.items()
        if value not in ("", None, {}, [])
    }


def _compact_variant_row(variant: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "variantId",
        "recipeFunctionalId",
        "groupingFunctionalId",
        "title",
        "language",
        "market",
        "cover",
        "servings",
        "yield",
        "durations",
        "difficulty",
        "ingredients",
        "nutrition",
    )
    return {
        key: deepcopy(variant[key])
        for key in fields
        if key in variant and variant[key] not in (None, "", {}, [])
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    cfg = c4m.read_apk_config(None)
    tokens = _tokens(Path(args.storage_home).expanduser())
    pcfg = catalog._platform_context(
        cfg, args.configured_country, args.configured_language, APP_VERSION
    )
    all_variants: dict[str, dict[str, Any]] = {}
    stats: list[dict[str, Any]] = []

    for language, country in AUDITED_CATALOGS:
        print(f"[catalog] {language}/GS_{country}", flush=True)
        search_rows = _all_search_rows(
            cfg,
            tokens,
            pcfg,
            language=language,
            country=country,
            configured_language=args.configured_language,
            configured_country=args.configured_country,
        )
        unique = {
            _text(row.get("searchVariantId")): row
            for row in search_rows
            if _text(row.get("searchVariantId"))
        }
        hydrated = 0
        failed = 0
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as pool:
            futures = {
                pool.submit(
                    _detail,
                    cfg,
                    tokens,
                    pcfg,
                    variant_id=variant_id,
                    source_language=language,
                    configured_language=args.configured_language,
                    configured_country=args.configured_country,
                ): variant_id
                for variant_id in unique
            }
            for future in as_completed(futures):
                variant_id = futures[future]
                try:
                    detail = future.result()
                except Exception as exc:
                    failed += 1
                    if args.verbose:
                        print(f"  ! {variant_id}: {type(exc).__name__}", flush=True)
                    continue
                detail["sourceCatalogLanguage"] = language
                detail["sourceCatalogCountry"] = country
                all_variants[variant_id] = detail
                hydrated += 1
        stats.append(
            {
                "language": language,
                "country": country,
                "market": f"GS_{country}",
                "state": "POPULATED" if unique else "EMPTY",
                "rawPublications": len(search_rows),
                "uniqueVariants": len(unique),
                "hydratedVariants": hydrated,
                "failedDetails": failed,
            }
        )

    variants = list(all_variants.values())
    ingredients: dict[str, dict[str, Any]] = {}
    for variant in variants:
        language = _text(
            variant.get("language") or variant.get("sourceCatalogLanguage")
        ).lower()
        for item in variant.get("ingredients") or []:
            if not isinstance(item, dict):
                continue
            ident = _ingredient_id(item)
            if not ident:
                continue
            name = _text(item.get("foodName") or item.get("name"))
            row = ingredients.setdefault(
                ident,
                {
                    "id": ident,
                    "key": _text(item.get("foodKey") or item.get("key")),
                    "canonicalName": "",
                    "translations": {},
                },
            )
            if name:
                row["translations"].setdefault(language, name)
                if language == "en":
                    row["canonicalName"] = name

    overrides = (
        _load_json(Path(args.english_overrides), {}) if args.english_overrides else {}
    )
    ingredient_overrides = (
        overrides.get("ingredients") if isinstance(overrides, dict) else {}
    )
    for ident, row in ingredients.items():
        override = (
            _text((ingredient_overrides or {}).get(ident))
            if isinstance(ingredient_overrides, dict)
            else ""
        )
        if override:
            row["canonicalName"] = override
            row["translations"].setdefault("en", override)
        elif not row["canonicalName"]:
            language, fallback = next(iter(row["translations"].items()), ("", ""))
            row["canonicalName"] = fallback
            row["canonicalNameSourceLanguage"] = language
            row["canonicalEnglishNeedsReview"] = True

    nutrition_path = Path(args.nutrition_cache).expanduser()
    nutrition_cache = _load_json(nutrition_path, {})
    fdc_key = _text(args.fdc_key or os.environ.get("FDC_API_KEY"))
    if args.resolve_nutrition and not fdc_key:
        raise SystemExit("--resolve-nutrition requires --fdc-key or FDC_API_KEY")
    if args.resolve_nutrition:
        for index, (ident, row) in enumerate(ingredients.items(), 1):
            if isinstance(nutrition_cache.get(ident), dict) or row.get(
                "canonicalEnglishNeedsReview"
            ):
                continue
            query = _text(row.get("canonicalName"))
            print(f"[nutrition] {index}/{len(ingredients)} {query}", flush=True)
            nutrition_cache[ident] = _lookup_fdc(query, fdc_key) or {
                "unresolved": True
            }
            _save_json(nutrition_path, nutrition_cache)
            if args.fdc_delay:
                time.sleep(args.fdc_delay)

    nutrition = {
        ident: row
        for ident, row in nutrition_cache.items()
        if isinstance(row, dict) and isinstance(row.get("values"), dict)
    }
    for ident, row in ingredients.items():
        if ident in nutrition:
            row["nutrition"] = deepcopy(nutrition[ident])

    for variant in variants:
        compact = [
            _compact_variant_ingredient(item, ingredients)
            for item in variant.get("ingredients") or []
            if isinstance(item, dict)
        ]
        variant["ingredients"] = compact
        variant["nutrition"] = _recipe_nutrition(
            compact, nutrition, variant.get("servings")
        )

    groups: dict[str, dict[str, Any]] = {}
    for variant in variants:
        grouping = _text(variant.get("groupingFunctionalId"))
        variant_id = _text(variant.get("variantId"))
        key = grouping or f"variant:{variant_id}"
        group = groups.setdefault(
            key,
            {
                "groupingFunctionalId": grouping,
                "canonicalName": "",
                "variants": [],
            },
        )
        group["variants"].append(_compact_variant_row(variant))
        if (
            _text(variant.get("language")).lower() == "en"
            and _text(variant.get("title"))
        ):
            group["canonicalName"] = _text(variant.get("title"))

    recipe_overrides = overrides.get("recipes") if isinstance(overrides, dict) else {}
    for key, group in groups.items():
        if group["canonicalName"]:
            continue
        override = (
            _text((recipe_overrides or {}).get(key))
            if isinstance(recipe_overrides, dict)
            else ""
        )
        if override:
            group["canonicalName"] = override
        else:
            group["canonicalName"] = next(
                (
                    _text(variant.get("title"))
                    for variant in group["variants"]
                    if _text(variant.get("title"))
                ),
                "",
            )
            group["canonicalEnglishNeedsReview"] = True

    unresolved_ingredients = sum(
        bool(row.get("canonicalEnglishNeedsReview")) for row in ingredients.values()
    )
    unresolved_recipes = sum(
        bool(row.get("canonicalEnglishNeedsReview")) for row in groups.values()
    )
    failed_details = sum(int(row["failedDetails"]) for row in stats)
    all_hydrated = all(
        row["hydratedVariants"] == row["uniqueVariants"] for row in stats
    )
    nutrition_complete = len(nutrition) == len(ingredients)
    complete = bool(
        not unresolved_ingredients
        and not unresolved_recipes
        and failed_details == 0
        and all_hydrated
        and (args.allow_missing_nutrition or nutrition_complete)
    )
    populated_count = sum(bool(row["uniqueVariants"]) for row in stats)
    empty_count = len(stats) - populated_count
    payload = {
        "schemaVersion": 1,
        "catalogVersion": args.catalog_version,
        "complete": complete,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "contract": "standalone-proven-cookeo-brand-v5",
            "format": "normalized-ingredient-references-v1",
            "applianceGroup": "APPLIANCE_GROUP_15",
            "recipeType": "BRAND",
            "auditedCatalogCount": len(AUDITED_CATALOGS),
            "sourceCatalogCount": populated_count,
            "emptyCatalogCount": empty_count,
            "catalogs": stats,
            "failedDetailCount": failed_details,
            "unresolvedCanonicalIngredientNames": unresolved_ingredients,
            "unresolvedCanonicalRecipeNames": unresolved_recipes,
            "nutritionResolvedCount": len(nutrition),
            "nutritionRequiredForComplete": not args.allow_missing_nutrition,
            "fullRecipeDetailStored": False,
            "officialSebDetailStored": False,
            "pricesStored": False,
            "secretsPersisted": False,
        },
        "ingredients": sorted(
            (
                {
                    key: value
                    for key, value in row.items()
                    if value not in ("", None, {}, [])
                }
                for row in ingredients.values()
            ),
            key=lambda row: _text(row.get("canonicalName")).casefold(),
        ),
        "recipes": sorted(
            (
                {
                    key: value
                    for key, value in row.items()
                    if value not in ("", None, {}, [])
                }
                for row in groups.values()
            ),
            key=lambda row: _text(row.get("canonicalName")).casefold(),
        ),
    }
    output = Path(args.output)
    _save_json(output, payload, compact=True)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", default=str(Path.home()))
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--catalog-version", required=True)
    parser.add_argument(
        "--output",
        default=str(COMPONENT / "catalog" / "merged_catalog.v1.json"),
    )
    parser.add_argument(
        "--nutrition-cache",
        default=str(ROOT / ".catalog-build" / "fdc-nutrition-cache.json"),
    )
    parser.add_argument("--english-overrides", default="")
    parser.add_argument("--resolve-nutrition", action="store_true")
    parser.add_argument("--allow-missing-nutrition", action="store_true")
    parser.add_argument("--fdc-key", default="")
    parser.add_argument("--fdc-delay", type=float, default=0.15)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    payload = build(args)
    output = Path(args.output)
    print(
        json.dumps(
            {
                "catalogVersion": payload["catalogVersion"],
                "complete": payload["complete"],
                "auditedCatalogs": payload["source"]["auditedCatalogCount"],
                "populatedCatalogs": payload["source"]["sourceCatalogCount"],
                "emptyCatalogs": payload["source"]["emptyCatalogCount"],
                "recipes": len(payload["recipes"]),
                "ingredients": len(payload["ingredients"]),
                "failedDetails": payload["source"]["failedDetailCount"],
                "nutritionResolvedCount": payload["source"][
                    "nutritionResolvedCount"
                ],
                "outputBytes": output.stat().st_size if output.exists() else 0,
                "output": args.output,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
