#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
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


def _identifier(value: Any, *, depth: int = 0) -> Any:
    if depth > 2:
        return None
    if isinstance(value, list):
        rows = [_identifier(item, depth=depth + 1) for item in value[:24]]
        return [row for row in rows if row not in (None, "", [], {})]
    if not isinstance(value, dict):
        return value if value not in (None, "") else None
    out: dict[str, Any] = {}
    for key in (
        "_id",
        "id",
        "key",
        "name",
        "title",
        "functionalId",
        "functional_id",
        "sourceSystem",
        "version",
        "identifier",
        "topRecipeId",
        "groupingId",
        "fid",
        "lang",
        "market",
        "domain",
        "type",
        "status",
        "isCover",
    ):
        if key not in value or value[key] in (None, "", [], {}):
            continue
        nested = _identifier(value[key], depth=depth + 1)
        if nested not in (None, "", [], {}):
            out[key] = nested
    return out


def _media(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    media = value.get("media") if isinstance(value.get("media"), dict) else value
    result: dict[str, Any] = {}
    for key in ("identifier", "isCover"):
        if value.get(key) not in (None, ""):
            result[key] = value[key]
    media_out = {
        key: media[key]
        for key in ("_id", "id", "key", "type")
        if media.get(key) not in (None, "")
    }
    if media_out:
        result["media"] = media_out
    return result


def _ingredient(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    food = item.get("food") if isinstance(item.get("food"), dict) else {}
    unit = item.get("unit") if isinstance(item.get("unit"), dict) else {}
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    weight_unit = weight.get("unit") if isinstance(weight.get("unit"), dict) else {}
    result: dict[str, Any] = {
        "fid": _identifier(item.get("fid")),
        "applicationDescription": item.get("applicationDescription"),
        "applianceDescription": item.get("applianceDescription"),
        "quantity": item.get("quantity"),
        "unit": {
            key: unit[key]
            for key in ("key", "name", "abbreviation")
            if unit.get(key) not in (None, "")
        },
        "food": {
            key: food[key]
            for key in (
                "_id",
                "id",
                "key",
                "name",
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
                for key in ("key", "name", "abbreviation")
                if weight_unit.get(key) not in (None, "")
            },
        },
    }
    return {key: value for key, value in result.items() if value not in (None, "", [], {})}


def _step_signature(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    row: dict[str, Any] = {
        "fid": _identifier(value.get("fid")),
        "type": _identifier(value.get("type")),
    }
    sequences = value.get("sequences") if isinstance(value.get("sequences"), list) else []
    programs: list[dict[str, Any]] = []
    for sequence in sequences:
        if not isinstance(sequence, dict):
            continue
        group = sequence.get("applianceGroup") if isinstance(sequence.get("applianceGroup"), dict) else {}
        if _text(group.get("key")) != "APPLIANCE_GROUP_15":
            continue
        for operation in sequence.get("operations") or []:
            if not isinstance(operation, dict):
                continue
            program = operation.get("program") if isinstance(operation.get("program"), dict) else {}
            parameters = operation.get("parameters") if isinstance(operation.get("parameters"), list) else []
            programs.append(
                {
                    "program": _identifier(program),
                    "parameterKeys": sorted(
                        _text(item.get("key"))
                        for item in parameters
                        if isinstance(item, dict) and _text(item.get("key"))
                    ),
                }
            )
    if programs:
        row["cookeoPrograms"] = programs
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def _summary(root: dict[str, Any]) -> dict[str, Any]:
    ingredients = root.get("ingredients") if isinstance(root.get("ingredients"), list) else []
    medias = root.get("resourceMedias") if isinstance(root.get("resourceMedias"), list) else []
    steps = root.get("steps") if isinstance(root.get("steps"), list) else []
    variants = root.get("variants") if isinstance(root.get("variants"), list) else []
    return {
        "fid": _identifier(root.get("fid")),
        "groupingId": _identifier(root.get("groupingId")),
        "topRecipeId": _identifier(root.get("topRecipeId")),
        "masterRecipe": _identifier(root.get("masterRecipe")),
        "referenceRecipe": _identifier(root.get("referenceRecipe")),
        "communityTopRecipe": _identifier(root.get("communityTopRecipe")),
        "brand": _identifier(root.get("brand")),
        "creator": _identifier(root.get("creator")),
        "owner": _identifier(root.get("owner")),
        "title": root.get("title") or root.get("shortTitle") or root.get("normalizedTitle"),
        "normalizedTitle": root.get("normalizedTitle"),
        "lang": root.get("lang"),
        "market": root.get("market"),
        "domain": _identifier(root.get("domain")),
        "recipeType": _identifier(root.get("recipeType")),
        "status": root.get("status"),
        "publicationDate": root.get("publicationDate"),
        "recipeModificationDate": root.get("recipeModificationDate"),
        "topRecipeModificationDate": root.get("topRecipeModificationDate"),
        "cover": _media(root.get("cover")),
        "resourceMedias": [row for item in medias if (row := _media(item))],
        "variants": [_identifier(item) for item in variants[:24] if _identifier(item)],
        "ingredients": [_ingredient(item) for item in ingredients if isinstance(item, dict)],
        "stepSignatures": [row for item in steps if (row := _step_signature(item))],
        "rootKeys": sorted(str(key) for key in root.keys()),
    }


def _cluster_variants(probe: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    selection = probe.get("selection") if isinstance(probe.get("selection"), dict) else {}
    clusters = selection.get("clusters") if isinstance(selection.get("clusters"), list) else []
    quotas = {
        "cross_language_unique_cover_with_english": 3,
        "cross_language_ambiguous_cover_with_english": 3,
        "cross_language_cover_without_english": 3,
        "high_unkeyed_ingredient_recipe": 4,
    }
    used = Counter()
    chosen: list[str] = []
    selected: list[dict[str, Any]] = []
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        kind = _text(cluster.get("kind"))
        if kind not in quotas or used[kind] >= quotas[kind]:
            continue
        members = [item for item in cluster.get("members") or [] if isinstance(item, dict)]
        if not members:
            continue
        member_ids = [_text(item.get("variantId")) for item in members if _text(item.get("variantId"))]
        # Bound ambiguous cover groups while preserving at least two languages.
        if kind == "cross_language_ambiguous_cover_with_english" and len(member_ids) > 10:
            by_language: dict[str, list[str]] = {}
            for item in members:
                language = _text(item.get("language")).lower()
                variant_id = _text(item.get("variantId"))
                if language and variant_id:
                    by_language.setdefault(language, []).append(variant_id)
            member_ids = []
            for language in sorted(by_language):
                member_ids.extend(by_language[language][:4])
            member_ids = member_ids[:12]
        for variant_id in member_ids:
            if variant_id not in chosen:
                chosen.append(variant_id)
        selected.append(
            {
                "kind": kind,
                "coverKey": cluster.get("coverKey"),
                "members": [
                    {
                        key: item.get(key)
                        for key in ("variantId", "groupingFunctionalId", "language", "canonicalName")
                        if item.get(key) not in (None, "")
                    }
                    for item in members
                    if _text(item.get("variantId")) in member_ids
                ],
            }
        )
        used[kind] += 1
    return chosen, selected


def _fetch(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    configured_country: str,
    configured_language: str,
) -> tuple[str, dict[str, Any]]:
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
    return auth, _summary(catalog._recipe_root(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", required=True)
    parser.add_argument("--identity-probe", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--configured-language", default="de")
    args = parser.parse_args()

    source = Path(args.identity_probe).expanduser().resolve()
    prior = _load(source)
    variants, clusters = _cluster_variants(prior)
    if not variants:
        raise SystemExit("No representative variants found in identity probe")

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
    for index, variant_id in enumerate(variants, 1):
        print(f"[family] {index}/{len(variants)} {variant_id}", flush=True)
        try:
            auth, detail = _fetch(
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
        results[variant_id] = {"authMode": auth, "detail": detail}

    # Report whether candidate parent/reference fields actually vary from the
    # local grouping ID. This is descriptive evidence only; it does not infer a
    # family relationship.
    field_relations = Counter()
    for row in results.values():
        detail = row.get("detail") if isinstance(row.get("detail"), dict) else {}
        grouping = _fid(detail.get("groupingId"))
        for field in ("topRecipeId", "masterRecipe", "referenceRecipe"):
            value = _fid(detail.get(field))
            if not value:
                field_relations[f"{field}:missing"] += 1
            elif value == grouping:
                field_relations[f"{field}:equalsGrouping"] += 1
            else:
                field_relations[f"{field}:differsFromGrouping"] += 1

    out = {
        "schemaVersion": 1,
        "readOnly": True,
        "secretsPersisted": False,
        "sourceIdentityProbe": str(source),
        "selection": {"clusters": clusters, "variantIds": variants},
        "summary": {
            "selectedVariants": len(variants),
            "fetched": len(results),
            "failed": len(errors),
            "fieldRelations": dict(sorted(field_relations.items())),
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
