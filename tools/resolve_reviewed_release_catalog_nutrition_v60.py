#!/usr/bin/env python3
"""Resolve v60 catalog nutrition from explicitly reviewed USDA FDC identities.

This tool never accepts a USDA search result. A versioned review must bind one
Cook4Me ingredient identity to one exact FDC ID. Only that exact detail record is
fetched, its returned identity is verified, and API credentials are never saved.
Legacy structural nutrition cache entries are not grandfathered into v60.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import reviewed_nutrition_v60 as reviewed_nutrition  # type: ignore  # noqa: E402

FDC_DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _number(value: Any) -> float | None:
    try:
        result = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return deepcopy(default)


def _review_paths(root: Path = TOOLS) -> list[Path]:
    return sorted(root.glob("release_catalog_reviewed_nutrition_sources*.v1.json"))


def load_reviews(root: Path = TOOLS) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in _review_paths(root):
        value = _load(path, {})
        if (
            not isinstance(value, dict)
            or value.get("kind") != "cook4me-reviewed-nutrition-source"
        ):
            raise RuntimeError(f"invalid nutrition review file: {path.name}")
        policy = value.get("policy") if isinstance(value.get("policy"), dict) else {}
        if policy.get("searchResultAutoAccepted") is not False:
            raise RuntimeError(
                f"nutrition review file must explicitly forbid auto acceptance: {path.name}"
            )
        for raw in value.get("items") or []:
            if not isinstance(raw, dict):
                continue
            ingredient_id = _text(raw.get("ingredientId"))
            try:
                fdc_id = int(raw.get("fdcId"))
            except (TypeError, ValueError):
                continue
            if not ingredient_id or fdc_id <= 0:
                continue
            normalized = dict(raw)
            normalized["ingredientId"] = ingredient_id
            normalized["fdcId"] = fdc_id
            normalized["reviewFile"] = path.name
            existing = out.get(ingredient_id)
            if existing and int(existing["fdcId"]) != fdc_id:
                raise RuntimeError(
                    f"conflicting nutrition review for {ingredient_id}: "
                    f"{existing['fdcId']} vs {fdc_id}"
                )
            out.setdefault(ingredient_id, normalized)
    return out


def _nutrient(
    food: dict[str, Any], tokens: tuple[str, ...], unit: str | None = None
) -> float | None:
    rows = food.get("foodNutrients") if isinstance(food.get("foodNutrients"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nutrient = row.get("nutrient") if isinstance(row.get("nutrient"), dict) else {}
        name = _text(
            row.get("nutrientName")
            or row.get("name")
            or nutrient.get("name")
        ).casefold()
        row_unit = _text(
            row.get("unitName")
            or row.get("unit")
            or nutrient.get("unitName")
        ).casefold()
        if unit and row_unit != unit.casefold():
            continue
        if any(token in name for token in tokens):
            value = _number(
                row.get("value") if "value" in row else row.get("amount")
            )
            if value is not None:
                return value
    return None


def fdc_profile(food: dict[str, Any]) -> dict[str, Any] | None:
    values = {
        "energyKcal": _nutrient(food, ("energy",), "kcal"),
        "energyKJ": _nutrient(food, ("energy",), "kj"),
        "protein": _nutrient(food, ("protein",)),
        "carbohydrates": _nutrient(
            food, ("carbohydrate by difference", "carbohydrate")
        ),
        "sugars": _nutrient(food, ("total sugars", "sugars total")),
        "fat": _nutrient(food, ("total lipid fat", "total fat")),
        "saturatedFat": _nutrient(
            food, ("fatty acids total saturated", "saturated fat")
        ),
        "fiber": _nutrient(food, ("fiber total dietary", "dietary fiber")),
    }
    sodium_mg = _nutrient(food, ("sodium na", "sodium"), "mg")
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
        "values": {key: round(float(value), 4) for key, value in values.items()},
        "source": "usda_fdc",
        "sourceId": int(food.get("fdcId")),
        "sourceDescription": _text(food.get("description")),
        "dataType": _text(food.get("dataType")),
    }


def fetch_fdc_detail(fdc_id: int, api_key: str) -> dict[str, Any]:
    url = (
        FDC_DETAIL_URL
        + urllib.parse.quote(str(fdc_id))
        + "?api_key="
        + urllib.parse.quote(api_key)
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "HA-Cook4me-reviewed-nutrition-v60/1",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"FDC {fdc_id}: invalid response")
    return payload


def resolve(
    queue: dict[str, Any],
    cache: dict[str, Any],
    reviews: dict[str, dict[str, Any]],
    *,
    fetcher: Callable[[int], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if queue.get("kind") != "cook4me-release-catalog-nutrition-queue-v60":
        raise RuntimeError("expected cook4me-release-catalog-nutrition-queue-v60")
    policy = (
        queue.get("identityPolicy")
        if isinstance(queue.get("identityPolicy"), dict)
        else {}
    )
    if policy.get("providerIdentityInference") is not False:
        raise RuntimeError("nutrition queue must forbid provider identity inference")
    if policy.get("ambiguousExcluded") is not True:
        raise RuntimeError("nutrition queue must exclude ambiguous ingredients")
    if policy.get("reviewedExactFdcProvenanceRequired") is not True:
        raise RuntimeError("nutrition queue must require reviewed exact-FDC provenance")
    if policy.get("searchResultAutoAccepted") is not False:
        raise RuntimeError("nutrition queue must forbid search-result auto acceptance")

    output, rejected_held_cache = reviewed_nutrition.holds.filter_cache(cache)
    pending: list[dict[str, Any]] = []
    resolved_now = 0
    already_resolved = 0
    missing_review = 0
    held_identities = 0
    rejected_unreviewed_cache = 0

    for raw in queue.get("tasks") or []:
        if not isinstance(raw, dict):
            continue
        ingredient_id = _text(raw.get("ingredientId"))
        canonical = _text(raw.get("canonicalEnglishName"))
        if not ingredient_id or not canonical:
            raise RuntimeError("nutrition queue task is missing identity or canonical English")
        if _text(raw.get("identityKind")) not in {"provider", "source-local"}:
            raise RuntimeError(f"unsupported nutrition identity kind for {ingredient_id}")

        hold = reviewed_nutrition.holds.find_hold(ingredient_id, raw.get("conceptId"))
        if hold is not None:
            held_identities += 1
            if ingredient_id in output:
                rejected_held_cache += 1
                output.pop(ingredient_id)
            pending.append(reviewed_nutrition.holds.pending_hold(raw, hold))
            continue

        existing = output.get(ingredient_id)
        if reviewed_nutrition.is_reviewed_profile(
            existing,
            ingredient_id=ingredient_id,
            canonical_name=canonical,
        ):
            already_resolved += 1
            continue
        if isinstance(existing, dict) and existing:
            rejected_unreviewed_cache += 1
            output.pop(ingredient_id, None)

        review = reviews.get(ingredient_id)
        if not review:
            missing_review += 1
            pending.append(dict(raw))
            continue
        reviewed_name = _text(review.get("canonicalEnglishName"))
        if reviewed_name and _norm(reviewed_name) != _norm(canonical):
            raise RuntimeError(
                f"nutrition review name mismatch for {ingredient_id}: "
                f"queue={canonical!r} review={reviewed_name!r}"
            )

        fdc_id = int(review["fdcId"])
        food = fetcher(fdc_id)
        try:
            returned_id = int(food.get("fdcId"))
        except (TypeError, ValueError):
            raise RuntimeError(f"FDC {fdc_id}: response has no valid fdcId") from None
        if returned_id != fdc_id:
            raise RuntimeError(
                f"FDC identity mismatch: requested {fdc_id}, got {returned_id}"
            )
        profile = fdc_profile(food)
        if not profile:
            raise RuntimeError(f"FDC {fdc_id}: no usable nutrient profile")
        profile["ingredientId"] = ingredient_id
        profile["reviewedCanonicalEnglishName"] = canonical
        profile["reviewConfidence"] = _text(review.get("confidence")) or "reviewed"
        profile["reviewFile"] = _text(review.get("reviewFile"))
        if review.get("notes"):
            profile["reviewNotes"] = _text(review.get("notes"))
        if not reviewed_nutrition.is_reviewed_profile(
            profile,
            ingredient_id=ingredient_id,
            canonical_name=canonical,
        ):
            raise RuntimeError(
                f"reviewed resolver produced invalid provenance for {ingredient_id}"
            )
        output[ingredient_id] = profile
        resolved_now += 1

    reviewed_profile_count = sum(
        reviewed_nutrition.is_reviewed_profile(value, ingredient_id=ident)
        for ident, value in output.items()
    )
    summary = {
        "queueTaskCount": len(
            [row for row in queue.get("tasks") or [] if isinstance(row, dict)]
        ),
        "alreadyResolved": already_resolved,
        "resolvedNow": resolved_now,
        "missingReview": missing_review,
        "heldIdentities": held_identities,
        "rejectedHeldCacheCount": rejected_held_cache,
        "pendingCount": len(pending),
        "reviewedCacheProfileCount": reviewed_profile_count,
        "rejectedUnreviewedCacheCount": rejected_unreviewed_cache,
        "searchResultsAutoAccepted": False,
        "secretsPersisted": False,
    }
    return output, {"summary": summary, "pending": pending}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--fdc-key", default="")
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--pending-output", required=True)
    args = parser.parse_args()

    api_key = _text(args.fdc_key or os.environ.get("FDC_API_KEY"))
    if not api_key:
        raise SystemExit(
            "reviewed nutrition resolution requires --fdc-key or FDC_API_KEY"
        )
    queue = _load(Path(args.queue).expanduser(), {})
    cache_path = Path(args.cache).expanduser()
    cache = _load(cache_path, {})
    if not isinstance(queue, dict):
        raise RuntimeError("nutrition queue must be a JSON object")
    if not isinstance(cache, dict):
        raise RuntimeError("nutrition cache must be a JSON object keyed by ingredient ID")
    reviews = load_reviews(Path(args.review_root).expanduser())
    output, pending = resolve(
        queue,
        cache,
        reviews,
        fetcher=lambda fdc_id: fetch_fdc_detail(fdc_id, api_key),
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pending_path = Path(args.pending_output).expanduser()
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(
        json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(pending["summary"], ensure_ascii=False))
    return 0 if pending["summary"]["pendingCount"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
