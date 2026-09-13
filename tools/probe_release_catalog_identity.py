#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
VENDOR = COMPONENT / "vendor"
for path in (COMPONENT, VENDOR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cook4me_phonefree as c4m  # type: ignore  # noqa: E402
import cook4me_recipe_catalog as catalog  # type: ignore  # noqa: E402

APP_VERSION = "36.0.0-RC3"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _fid(value: Any) -> str:
    return _text(catalog._fid(value))


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Not a JSON object: {path}")
    return value


def _tokens(storage_home: Path) -> dict[str, Any]:
    path = storage_home / ".config" / "cook4me" / "tokens.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _cover_key(variant: dict[str, Any]) -> str:
    cover = _text(variant.get("cover"))
    if not cover:
        return ""
    return os.path.basename(urllib.parse.urlsplit(cover).path)


def _group_language(recipe: dict[str, Any]) -> str:
    for variant in recipe.get("variants") or []:
        if isinstance(variant, dict) and _text(variant.get("language")):
            return _text(variant.get("language")).lower()
    return ""


def _representative_variant(recipe: dict[str, Any]) -> dict[str, Any] | None:
    variants = [row for row in recipe.get("variants") or [] if isinstance(row, dict)]
    if not variants:
        return None

    def score(row: dict[str, Any]) -> tuple[int, float, str]:
        servings = row.get("servings")
        try:
            distance = abs(float(servings) - 4.0)
        except (TypeError, ValueError):
            distance = 999.0
        return (
            1 if _text(row.get("cover")) else 0,
            -distance,
            _text(row.get("variantId")),
        )

    return max(variants, key=score)


def _unkeyed_count(recipe: dict[str, Any]) -> int:
    variant = _representative_variant(recipe) or {}
    return sum(
        1
        for item in variant.get("ingredients") or []
        if isinstance(item, dict) and not _text(item.get("key") or item.get("foodKey"))
    )


def select_samples(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    recipes = [row for row in payload.get("recipes") or [] if isinstance(row, dict)]
    covers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for recipe in recipes:
        variant = _representative_variant(recipe)
        key = _cover_key(variant or {})
        if key:
            covers[key].append(recipe)

    chosen: dict[str, dict[str, Any]] = {}
    selected_clusters: list[dict[str, Any]] = []

    def add_cluster(kind: str, cover: str, rows: list[dict[str, Any]]) -> None:
        members = []
        for recipe in rows:
            variant = _representative_variant(recipe)
            if not variant:
                continue
            variant_id = _text(variant.get("variantId"))
            if not variant_id:
                continue
            chosen.setdefault(variant_id, variant)
            members.append(
                {
                    "groupingFunctionalId": _text(recipe.get("groupingFunctionalId")),
                    "language": _group_language(recipe),
                    "canonicalName": _text(recipe.get("canonicalName")),
                    "variantId": variant_id,
                    "cover": _text(variant.get("cover")),
                    "unkeyedIngredients": _unkeyed_count(recipe),
                }
            )
        if members:
            selected_clusters.append({"kind": kind, "coverKey": cover, "members": members})

    simple = []
    ambiguous = []
    cross_no_en = []
    for cover, rows in covers.items():
        languages = [_group_language(row) for row in rows]
        counts = Counter(languages)
        unique_languages = {value for value in languages if value}
        if len(unique_languages) < 2:
            continue
        if "en" in unique_languages:
            if all(count == 1 for count in counts.values()):
                simple.append((cover, rows))
            elif any(count > 1 for count in counts.values()):
                ambiguous.append((cover, rows))
        else:
            cross_no_en.append((cover, rows))

    simple.sort(key=lambda item: (-len(item[1]), item[0]))
    ambiguous.sort(key=lambda item: (-len(item[1]), item[0]))
    cross_no_en.sort(key=lambda item: (-len(item[1]), item[0]))

    for cover, rows in simple[:10]:
        add_cluster("cross_language_unique_cover_with_english", cover, rows)
    for cover, rows in ambiguous[:10]:
        # Keep this bounded: enough members to expose collision semantics without
        # turning a focused probe into another catalog crawl.
        en = [row for row in rows if _group_language(row) == "en"][:4]
        other = [row for row in rows if _group_language(row) != "en"][:8]
        add_cluster("cross_language_ambiguous_cover_with_english", cover, en + other)
    for cover, rows in cross_no_en[:8]:
        add_cluster("cross_language_cover_without_english", cover, rows[:10])

    # Add recipes with the most unkeyed ingredients. These samples answer
    # whether food/ingredient objects expose stronger identity fields than the
    # normalized extractor currently retains.
    for recipe in sorted(recipes, key=_unkeyed_count, reverse=True):
        if _unkeyed_count(recipe) <= 0:
            break
        variant = _representative_variant(recipe)
        if not variant:
            continue
        variant_id = _text(variant.get("variantId"))
        if not variant_id or variant_id in chosen:
            continue
        chosen[variant_id] = variant
        selected_clusters.append(
            {
                "kind": "high_unkeyed_ingredient_recipe",
                "coverKey": _cover_key(variant),
                "members": [
                    {
                        "groupingFunctionalId": _text(recipe.get("groupingFunctionalId")),
                        "language": _group_language(recipe),
                        "canonicalName": _text(recipe.get("canonicalName")),
                        "variantId": variant_id,
                        "cover": _text(variant.get("cover")),
                        "unkeyedIngredients": _unkeyed_count(recipe),
                    }
                ],
            }
        )
        if sum(1 for row in selected_clusters if row["kind"] == "high_unkeyed_ingredient_recipe") >= 12:
            break

    return list(chosen.values()), {
        "clusters": selected_clusters,
        "sampleVariantCount": len(chosen),
        "simpleClusterCandidates": len(simple),
        "ambiguousClusterCandidates": len(ambiguous),
        "crossLanguageNoEnglishCandidates": len(cross_no_en),
    }


def _small_identifier(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key in (
            "functionalId",
            "functional_id",
            "id",
            "identifier",
            "key",
            "sourceSystem",
            "version",
            "name",
            "title",
            "lang",
            "market",
            "domain",
            "type",
            "status",
        ):
            if value.get(key) not in (None, "", [], {}):
                out[key] = value[key]
        return out
    return value


def _media_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    media = value.get("media") if isinstance(value.get("media"), dict) else value
    return {
        key: media[key]
        for key in ("key", "type")
        if media.get(key) not in (None, "")
    } | ({"identifier": value.get("identifier")} if value.get("identifier") else {})


def _ingredient_summary(item: dict[str, Any]) -> dict[str, Any]:
    food = item.get("food") if isinstance(item.get("food"), dict) else {}
    unit = item.get("unit") if isinstance(item.get("unit"), dict) else {}
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    weight_unit = weight.get("unit") if isinstance(weight.get("unit"), dict) else {}
    out: dict[str, Any] = {
        "fid": _small_identifier(item.get("fid")),
        "applicationDescription": item.get("applicationDescription"),
        "applianceDescription": item.get("applianceDescription"),
        "quantity": item.get("quantity"),
        "unit": {
            key: unit[key]
            for key in ("key", "name", "abbreviation", "pluralName")
            if unit.get(key) not in (None, "")
        },
        "food": {
            key: food[key]
            for key in (
                "key",
                "name",
                "id",
                "identifier",
                "functionalId",
                "sourceSystem",
                "version",
                "type",
            )
            if food.get(key) not in (None, "")
        },
        "foodKeys": sorted(str(key) for key in food.keys()),
        "weight": {
            "quantity": weight.get("quantity"),
            "unit": {
                key: weight_unit[key]
                for key in ("key", "name", "abbreviation", "pluralName")
                if weight_unit.get(key) not in (None, "")
            },
        },
    }
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def summarize_root(root: dict[str, Any]) -> dict[str, Any]:
    cover = root.get("cover") if isinstance(root.get("cover"), dict) else {}
    ingredients = root.get("ingredients") if isinstance(root.get("ingredients"), list) else []
    resource_medias = root.get("resourceMedias") if isinstance(root.get("resourceMedias"), list) else []
    identifiers = {}
    for key in (
        "fid",
        "identifier",
        "groupingId",
        "topRecipeId",
        "topRecipe",
        "parentRecipe",
        "recipe",
        "variant",
    ):
        if root.get(key) not in (None, "", [], {}):
            identifiers[key] = _small_identifier(root.get(key))
    return {
        "rootKeys": sorted(str(key) for key in root.keys()),
        "identifiers": identifiers,
        "title": root.get("title") or root.get("shortTitle") or root.get("normalizedTitle"),
        "lang": root.get("lang"),
        "market": root.get("market"),
        "domain": root.get("domain"),
        "recipeType": root.get("recipeType"),
        "status": root.get("status"),
        "cover": _media_summary(cover),
        "resourceMedias": [
            row for value in resource_medias if isinstance(value, dict) and (row := _media_summary(value))
        ],
        "ingredients": [
            _ingredient_summary(value) for value in ingredients if isinstance(value, dict)
        ],
    }


def fetch_detail_raw(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    configured_country: str,
    configured_language: str,
) -> dict[str, Any]:
    base = cfg["platform_base_url"].rstrip("/")
    url = (
        base
        + "/common-api/v3/recipes/PRO/"
        + urllib.parse.quote(_fid(variant_id), safe="")
        + "/?format=mobile&applianceGroup=APPLIANCE_GROUP_15"
    )
    payload, auth = catalog._http_json(
        "GET",
        url,
        headers_iter=catalog._request_headers(
            cfg,
            tokens,
            configured_country,
            configured_language,
            APP_VERSION,
            url,
            pcfg,
        ),
        timeout=30,
    )
    root = catalog._recipe_root(payload)
    return {"authMode": auth, "detail": summarize_root(root)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--configured-language", default="de")
    args = parser.parse_args()

    source = Path(args.catalog).expanduser().resolve()
    payload = _load(source)
    samples, selection = select_samples(payload)
    cfg = c4m.read_apk_config(None)
    tokens = _tokens(Path(args.storage_home).expanduser())
    pcfg = catalog._platform_context(
        cfg,
        args.configured_country,
        args.configured_language,
        APP_VERSION,
    )

    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for index, sample in enumerate(samples, 1):
        variant_id = _text(sample.get("variantId"))
        print(f"[identity] {index}/{len(samples)} {variant_id}", flush=True)
        try:
            fetched = fetch_detail_raw(
                cfg,
                tokens,
                pcfg,
                variant_id=variant_id,
                configured_country=args.configured_country,
                configured_language=args.configured_language,
            )
        except Exception as exc:
            errors[variant_id] = type(exc).__name__ + ": " + str(exc)
            continue
        results[variant_id] = {
            "catalog": {
                key: sample.get(key)
                for key in (
                    "variantId",
                    "recipeFunctionalId",
                    "groupingFunctionalId",
                    "title",
                    "language",
                    "market",
                    "cover",
                    "servings",
                )
                if sample.get(key) not in (None, "")
            },
            **fetched,
        }

    out = {
        "schemaVersion": 1,
        "readOnly": True,
        "secretsPersisted": False,
        "sourceCatalog": str(source),
        "selection": selection,
        "summary": {
            "selectedVariants": len(samples),
            "fetched": len(results),
            "failed": len(errors),
        },
        "errors": errors,
        "results": results,
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out["summary"], ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
