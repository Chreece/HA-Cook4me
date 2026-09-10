#!/usr/bin/env python3
"""Prepare Cook4Me release-catalog v2 assembly entirely offline.

Consumes the reviewed provider-capture v2 and APK-exact marketing-food v3
capture. No SEB, Home Assistant, Ollama, USDA, or other network access occurs.
The output keeps exact provider recipe identity separate from canonical English
labels and prepares a deterministic local-only translation/classification queue.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata
from typing import Any
import zipfile

PROVIDER_KIND = "cook4me-provider-capture"
MARKETING_KIND = "cook4me-marketing-food-capture-v3"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        unicodedata.normalize("NFKC", _text(value)),
    ).casefold()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha_text(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _load_payload(path: Path, expected_kind: str) -> dict[str, Any]:
    """Load a raw capture or its review ZIP without needing extraction first."""
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if expected_kind == PROVIDER_KIND and name.endswith(
                    "provider-capture-v2.json.gz"
                ):
                    return json.loads(gzip.decompress(archive.read(name)))
                if expected_kind == MARKETING_KIND and name.endswith(
                    "marketing-foods-v3.json"
                ):
                    return json.loads(archive.read(name))
        raise RuntimeError(f"{path}: expected {expected_kind} payload not found")
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _validate_provider(payload: dict[str, Any]) -> None:
    if payload.get("kind") != PROVIDER_KIND or int(payload.get("schemaVersion") or 0) != 2:
        raise RuntimeError("provider capture is not reviewed schema v2")
    catalogs = ((payload.get("source") or {}).get("catalogs") or [])
    if len(catalogs) != 28:
        raise RuntimeError(f"provider capture audited {len(catalogs)} catalogs, expected 28")
    unresolved = sum(int(row.get("unresolvedVariants") or 0) for row in catalogs)
    if unresolved:
        raise RuntimeError(f"provider capture has {unresolved} unresolved variants")
    search_rows = sum(int(row.get("searchRows") or 0) for row in catalogs)
    details = payload.get("details") or []
    stale = payload.get("staleSearchOnly") or []
    if search_rows != len(details) + len(stale):
        raise RuntimeError("provider search/detail/stale totals do not balance")
    ids = [_text(row.get("variantId")) for row in details]
    if len(ids) != len(set(ids)):
        raise RuntimeError("provider capture contains duplicate detail variant IDs")


def _validate_marketing(payload: dict[str, Any]) -> None:
    if payload.get("kind") != MARKETING_KIND or int(payload.get("schemaVersion") or 0) != 3:
        raise RuntimeError("marketing-food capture is not reviewed schema v3")
    if (
        payload.get("requestContract") != "apk-th0.d-unfiltered"
        or int(payload.get("requestSize") or 0) != 100000
        or payload.get("isMixMainFilter") is not False
    ):
        raise RuntimeError("marketing-food capture does not use the proven APK unfiltered contract")
    catalogs = payload.get("catalogs") or []
    if len(catalogs) != 28:
        raise RuntimeError(f"marketing-food capture audited {len(catalogs)} catalogs, expected 28")
    if payload.get("errors"):
        raise RuntimeError(f"marketing-food capture has {len(payload['errors'])} errors")
    for catalog in catalogs:
        label = f"{catalog.get('language')}/{catalog.get('market')}"
        if catalog.get("state") != "POPULATED":
            raise RuntimeError(f"marketing-food {label} is {catalog.get('state')}")
        for field in ("unparsedRows", "missingNameRows", "missingKeyRows"):
            if int(catalog.get(field) or 0):
                raise RuntimeError(f"marketing-food {label} has {field}={catalog.get(field)}")
        if catalog.get("truncated"):
            raise RuntimeError(f"marketing-food {label} is truncated")
        keys = [_text(item.get("key")) for item in catalog.get("items") or []]
        if len(keys) != len(set(keys)):
            raise RuntimeError(f"marketing-food {label} contains duplicate provider keys")


def _quantity_forms(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    try:
        number = float(value)
    except (TypeError, ValueError):
        return []
    if not math.isfinite(number):
        return []
    if number.is_integer():
        return list(
            dict.fromkeys(
                (
                    str(int(number)),
                    f"{number:.1f}",
                    f"{number:.1f}".replace(".", ","),
                )
            )
        )
    compact = f"{number:g}"
    return list(dict.fromkeys((compact, compact.replace(".", ","))))


def semantic_ingredient_name(item: dict[str, Any]) -> tuple[str, bool]:
    """Recover the semantic keyless label from preserved structured evidence.

    Prefer provider food/appliance wording. If only a quantity-bearing label is
    available, remove a leading quantity and provider unit only when the same
    quantity/unit are explicitly preserved on that ingredient row. This repairs
    the old amount-in-identity capture without guessing densities or piece sizes.
    """
    source = ""
    for field in ("foodName", "applianceDescription", "applicationDescription", "cleanName"):
        source = _text(item.get(field))
        if source:
            break
    if not source:
        return "", False

    unit = item.get("unit") if isinstance(item.get("unit"), dict) else {}
    units: list[str] = []
    for field in ("name", "pluralName", "abbreviation"):
        value = _text(unit.get(field))
        if value and value not in units:
            units.append(value)

    for quantity in sorted(_quantity_forms(item.get("quantity")), key=len, reverse=True):
        for unit_name in sorted(units, key=len, reverse=True):
            pattern = (
                rf"^\s*{re.escape(quantity)}\s*{re.escape(unit_name)}"
                rf"(?=\s|[-–—,:;]|$)\s*[-–—,:;]?\s*"
            )
            cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
            if cleaned != source and _text(cleaned):
                return _text(cleaned), True
        pattern = rf"^\s*{re.escape(quantity)}(?=\s)\s+"
        cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
        if cleaned != source and _text(cleaned):
            return _text(cleaned), True
    return source, False


def _task_id(kind: str, language: str, text: str) -> str:
    return kind + ":" + _sha_text(
        "cook4me-translation-v2", kind, language, _norm(text)
    )[:24]


def prepare(
    provider: dict[str, Any], marketing: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_provider(provider)
    _validate_marketing(marketing)

    foods: dict[str, dict[str, Any]] = {}
    by_language_name: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for catalog in marketing["catalogs"]:
        language = _text(catalog.get("language")).lower()
        market = _text(catalog.get("market"))
        for item in catalog.get("items") or []:
            key = _text(item.get("key"))
            name = _text(item.get("name"))
            if not key or not name:
                continue
            row = foods.setdefault(
                key,
                {
                    "ingredientId": key,
                    "key": key,
                    "translations": [],
                    "usageCount": 0,
                    "recipeLanguages": set(),
                },
            )
            row["translations"].append(
                {"language": language, "market": market, "name": name}
            )
            if language == "en":
                row["canonicalEnglishName"] = name
                row["canonicalEnglishSource"] = "seb:en/GS_GB"
            by_language_name[language][_norm(name)].add(key)

    ingredient_lines = 0
    keyed_lines = 0
    unkeyed_lines = 0
    prefix_cleaned = 0
    unkeyed: dict[tuple[str, str], dict[str, Any]] = {}
    for detail in provider.get("details") or []:
        language = _text(detail.get("language")).lower()
        variant_id = _text(detail.get("variantId"))
        grouping_id = _text(
            detail.get("groupingFunctionalId")
            or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId")
            or variant_id
        )
        for ingredient in detail.get("ingredients") or []:
            if not isinstance(ingredient, dict):
                continue
            ingredient_lines += 1
            key = _text(ingredient.get("foodKey"))
            if key:
                keyed_lines += 1
                if key not in foods:
                    raise RuntimeError(
                        f"recipe food key {key} is missing from marketing-food dictionaries"
                    )
                foods[key]["usageCount"] += 1
                foods[key]["recipeLanguages"].add(language)
                continue

            unkeyed_lines += 1
            name, changed = semantic_ingredient_name(ingredient)
            if changed:
                prefix_cleaned += 1
            if not name:
                continue
            identity = (language, _norm(name))
            row = unkeyed.setdefault(
                identity,
                {
                    "sourceLanguage": language,
                    "sourceName": name,
                    "occurrenceCount": 0,
                    "samples": [],
                },
            )
            row["occurrenceCount"] += 1
            if len(row["samples"]) < 3:
                sample = {
                    "variantId": variant_id,
                    "groupingFunctionalId": grouping_id,
                }
                line_id = _text(ingredient.get("lineFunctionalId"))
                if line_id:
                    sample["lineFunctionalId"] = line_id
                row["samples"].append(sample)

    tasks: list[dict[str, Any]] = []
    used_keys = {key for key, value in foods.items() if value["usageCount"]}
    for key, row in foods.items():
        row["translations"].sort(
            key=lambda value: (
                value["language"],
                value["market"],
                value["name"].casefold(),
            )
        )
        row["recipeLanguages"] = sorted(row["recipeLanguages"])
        row["usedByRecipe"] = bool(row["usageCount"])
        if not row.get("canonicalEnglishName"):
            task_id = _task_id("provider_food_english", "mul", key)
            row["translationTaskId"] = task_id
            tasks.append(
                {
                    "taskId": task_id,
                    "type": "provider_food_english",
                    "providerFoodKey": key,
                    "evidenceLabels": deepcopy(row["translations"]),
                    "usedByRecipe": row["usedByRecipe"],
                    "usageCount": row["usageCount"],
                }
            )

    groups: dict[str, dict[str, Any]] = {}
    title_task_users: dict[tuple[str, str], list[str]] = defaultdict(list)
    for detail in provider.get("details") or []:
        grouping_id = _text(
            detail.get("groupingFunctionalId")
            or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId")
            or detail.get("variantId")
        )
        if not grouping_id:
            continue
        language = _text(detail.get("language")).lower()
        market = _text(detail.get("market"))
        title = _text(detail.get("title") or detail.get("normalizedTitle"))
        variant_id = _text(detail.get("variantId"))
        row = groups.get(grouping_id)
        if row is None:
            row = {
                "groupingFunctionalId": grouping_id,
                # Legacy representative fields remain for review-tool compatibility.
                "language": language,
                "market": market,
                "title": title,
                "variantIds": [],
                "originalTitles": [],
            }
            groups[grouping_id] = row
        row["variantIds"].append(variant_id)
        if title:
            row["originalTitles"].append(
                {
                    "variantId": variant_id,
                    "language": language,
                    "market": market,
                    "name": title,
                }
            )
            if language == "en" and not row.get("canonicalEnglishTitle"):
                row["canonicalEnglishTitle"] = title
                row["canonicalEnglishSource"] = "seb:en-sibling"

    # Only groups without an official English sibling need semantic review.
    for grouping_id, row in groups.items():
        if row.get("canonicalEnglishTitle"):
            continue
        language = _text(row.get("language")).lower()
        title = _text(row.get("title"))
        if title:
            title_task_users[(language, _norm(title))].append(grouping_id)

    title_tasks: dict[str, dict[str, Any]] = {}
    for (language, _normalized_title), grouping_ids in title_task_users.items():
        title = groups[grouping_ids[0]]["title"]
        task_id = _task_id("recipe_title_english", language, title)
        title_tasks[task_id] = {
            "taskId": task_id,
            "type": "recipe_title_english",
            "sourceLanguage": language,
            "sourceText": title,
            "groupCount": len(grouping_ids),
        }
        for grouping_id in grouping_ids:
            groups[grouping_id]["translationTaskId"] = task_id
    tasks.extend(title_tasks.values())

    unkeyed_rows: list[dict[str, Any]] = []
    exact_candidates = 0
    exact_candidates_with_english = 0
    for (language, _normalized), row in sorted(
        unkeyed.items(), key=lambda pair: (pair[0][0], pair[0][1])
    ):
        candidates = sorted(
            by_language_name[language].get(_norm(row["sourceName"]), set())
        )
        if len(candidates) == 1:
            key = candidates[0]
            exact_candidates += 1
            row["exactProviderFoodKeyCandidate"] = key
            row["candidateEvidence"] = "exact same-language SEB marketing-food label"
            provider_food = foods[key]
            if provider_food.get("canonicalEnglishName"):
                row["canonicalEnglishName"] = provider_food["canonicalEnglishName"]
                row["canonicalEnglishSource"] = (
                    "seb:provider-food-exact-label-candidate"
                )
                exact_candidates_with_english += 1
            elif provider_food.get("translationTaskId"):
                row["providerFoodTranslationTaskId"] = provider_food[
                    "translationTaskId"
                ]
            # This is strong translation/classification evidence, but the exact
            # provider key remains explicitly a candidate rather than silently
            # replacing the missing identity on the recipe line.
            row["classification"] = "food_candidate"
        else:
            if len(candidates) > 1:
                row["ambiguousProviderFoodKeyCandidates"] = candidates
            task_id = _task_id(
                "unkeyed_ingredient", language, row["sourceName"]
            )
            row["translationTaskId"] = task_id
            tasks.append(
                {
                    "taskId": task_id,
                    "type": "unkeyed_ingredient",
                    "sourceLanguage": language,
                    "sourceText": row["sourceName"],
                    "occurrenceCount": row["occurrenceCount"],
                    "needsTranslation": language != "en",
                    "requestedClassification": [
                        "food",
                        "equipment",
                        "other",
                        "ambiguous",
                    ],
                }
            )

        # Never merge keyless ingredients across languages from translation
        # alone. A later reviewed exact-provider association may replace this.
        row["localSyntheticIngredientId"] = (
            "local:"
            + language
            + ":"
            + _sha_text(
                "cook4me-local-ingredient-v2",
                language,
                _norm(row["sourceName"]),
            )[:20]
        )
        unkeyed_rows.append(row)

    tasks.sort(key=lambda row: (row["type"], row["taskId"]))
    provider_food_rows = sorted(foods.values(), key=lambda row: row["key"])
    group_rows = sorted(
        groups.values(),
        key=lambda row: (row["language"], row["groupingFunctionalId"]),
    )
    for group in group_rows:
        group["variantIds"] = sorted(set(group["variantIds"]))
        unique_originals = {}
        for original in group.get("originalTitles") or []:
            if not isinstance(original, dict):
                continue
            identity = (
                _text(original.get("variantId")),
                _text(original.get("language")).lower(),
                _text(original.get("market")),
                _text(original.get("name")),
            )
            unique_originals.setdefault(identity, original)
        group["originalTitles"] = sorted(
            unique_originals.values(),
            key=lambda value: (
                _text(value.get("language")),
                _text(value.get("market")),
                _text(value.get("variantId")),
                _text(value.get("name")).casefold(),
            ),
        )
        group["variantCount"] = len(group["variantIds"])

    summary = {
        "providerDetails": len(provider.get("details") or []),
        "staleSearchOnly": len(provider.get("staleSearchOnly") or []),
        "providerRecipeGroups": len(group_rows),
        "recipeGroupsWithMultipleOriginalTitles": sum(
            len(row.get("originalTitles") or []) > 1 for row in group_rows
        ),
        "providerFoodCatalogKeys": len(provider_food_rows),
        "recipeUsedProviderFoodKeys": len(used_keys),
        "recipeUsedProviderFoodKeysCoveredByDictionary": sum(
            1 for key in used_keys if key in foods
        ),
        "providerFoodsWithSebEnglish": sum(
            1 for row in provider_food_rows if row.get("canonicalEnglishName")
        ),
        "usedProviderFoodsWithSebEnglish": sum(
            1
            for row in provider_food_rows
            if row["usedByRecipe"] and row.get("canonicalEnglishName")
        ),
        "providerFoodsMissingSebEnglish": sum(
            1 for row in provider_food_rows if not row.get("canonicalEnglishName")
        ),
        "usedProviderFoodsMissingSebEnglish": sum(
            1
            for row in provider_food_rows
            if row["usedByRecipe"] and not row.get("canonicalEnglishName")
        ),
        "ingredientLines": ingredient_lines,
        "keyedIngredientLines": keyed_lines,
        "unkeyedIngredientLines": unkeyed_lines,
        "unkeyedUniqueLabels": len(unkeyed_rows),
        "unkeyedRowsWithStructuredPrefixCleaned": prefix_cleaned,
        "unkeyedExactProviderFoodCandidates": exact_candidates,
        "unkeyedExactProviderCandidatesWithSebEnglish": exact_candidates_with_english,
        "recipeGroupsNeedingEnglishTranslation": sum(
            1 for row in group_rows if row.get("translationTaskId")
        ),
        "uniqueRecipeTitleTranslationTasks": len(title_tasks),
        "translationTasks": len(tasks),
        "providerFoodTranslationTasks": sum(
            row["type"] == "provider_food_english" for row in tasks
        ),
        "unkeyedIngredientTranslationClassificationTasks": sum(
            row["type"] == "unkeyed_ingredient" for row in tasks
        ),
    }

    generated_at = _iso_now()
    preparation = {
        "schemaVersion": 2,
        "kind": "cook4me-release-assembly-prep",
        "generatedAt": generated_at,
        "readOnly": True,
        "secretsPersisted": False,
        "identityPolicy": {
            "recipeProviderIdentityAuthoritative": True,
            "translationNeverMergesRecipeGroups": True,
            "providerNativeTitlesPreserved": True,
            "unkeyedCrossLanguageMergeFromTranslation": False,
            "exactProviderFoodNameMatchesRemainCandidates": True,
        },
        "summary": summary,
        "providerFoods": provider_food_rows,
        "recipeGroups": group_rows,
        "unkeyedIngredients": unkeyed_rows,
    }
    queue = {
        "schemaVersion": 2,
        "kind": "cook4me-local-translation-queue",
        "generatedAt": generated_at,
        "privacy": (
            "local-only; public provider catalog labels/titles; "
            "no account credentials or provider secrets"
        ),
        "summary": {"taskCount": len(tasks)},
        "tasks": tasks,
    }
    return preparation, queue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-capture", required=True)
    parser.add_argument("--marketing-foods", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    provider = _load_payload(
        Path(args.provider_capture).expanduser(), PROVIDER_KIND
    )
    marketing = _load_payload(
        Path(args.marketing_foods).expanduser(), MARKETING_KIND
    )
    preparation, queue = prepare(provider, marketing)

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(
            preparation,
            handle,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    Path(args.queue).expanduser().write_text(
        json.dumps(queue, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    Path(args.summary).expanduser().write_text(
        json.dumps(preparation["summary"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(preparation["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
